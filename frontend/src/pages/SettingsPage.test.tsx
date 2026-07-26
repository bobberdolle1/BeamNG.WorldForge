import { render, screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import MockAdapter from 'axios-mock-adapter'
import { afterEach, beforeEach, describe, expect, it } from 'vitest'

import '../i18n/config'

import { api } from '../services/api'
import { SettingsPage } from './SettingsPage'

let mock: MockAdapter

const STORED = {
  api_keys: {
    sentinel_hub_client_id: null,
    sentinel_hub_client_secret: null,
    opentopography_api_key: '***7b3e',
    azure_maps_subscription_key: null,
    bing_maps_api_key: null,
    gee_project_id: 'my-gcp-project',
  },
  preferences: {
    default_data_source: 'auto',
    default_image_source: 'sentinel_hub',
    language: 'en',
  },
}

beforeEach(() => {
  mock = new MockAdapter(api)
  mock.onGet('/settings').reply(200, STORED)
})

afterEach(() => {
  mock.restore()
})

async function renderPage() {
  render(<SettingsPage />)
  await waitFor(() => expect(screen.getByLabelText(/OpenTopography API Key/)).toBeInTheDocument())
}

describe('SettingsPage', () => {
  it('sends validation credentials in the body, not the query string', async () => {
    // Regression guard. The page used to call
    //   axios.post(url, null, { params: { api_key } })
    // which the backend now rejects with 422 - every Verify click was broken,
    // and the key was written into logs and browser history on the way.
    mock.onPost('/settings/validate/opentopography').reply(200, { valid: true, message: 'ok' })

    await renderPage()

    const input = screen.getByLabelText(/OpenTopography API Key/)
    await userEvent.type(input, 'my-real-key')

    // Scope to this field's card so the assertion cannot drift onto another
    // provider's Verify button when the field order changes.
    const card = input.closest('div.border') as HTMLElement
    await userEvent.click(within(card).getByRole('button', { name: /verify/i }))

    await waitFor(() => expect(mock.history.post).toHaveLength(1))

    const request = mock.history.post[0]
    expect(request.url).toBe('/settings/validate/opentopography')
    expect(request.url).not.toContain('api_key')
    expect(request.params?.api_key).toBeUndefined()
    expect(JSON.parse(request.data)).toMatchObject({ api_key: 'my-real-key' })
  })

  it('validates Sentinel Hub with the ID and secret together', async () => {
    // Each field used to be verified in isolation, so the OAuth2
    // client-credentials exchange could never succeed.
    mock.onPost('/settings/validate/sentinel_hub').reply(200, { valid: true, message: 'ok' })

    await renderPage()

    await userEvent.type(screen.getByLabelText(/Sentinel Hub Client ID/), 'the-id')
    await userEvent.type(screen.getByLabelText(/Sentinel Hub Client Secret/), 'the-secret')

    await userEvent.click(screen.getAllByRole('button', { name: /verify/i })[0])

    await waitFor(() => expect(mock.history.post).toHaveLength(1))
    expect(JSON.parse(mock.history.post[0].data)).toEqual({
      api_key: 'the-id',
      api_secret: 'the-secret',
    })
  })

  it('refuses to validate Sentinel Hub with only half the pair', async () => {
    await renderPage()

    await userEvent.type(screen.getByLabelText(/Sentinel Hub Client ID/), 'the-id')
    await userEvent.click(screen.getAllByRole('button', { name: /verify/i })[0])

    expect(await screen.findByText(/both the Client ID and the Client Secret/i)).toBeInTheDocument()
    expect(mock.history.post).toHaveLength(0)
  })

  it('offers no Verify button for the GEE project id', async () => {
    // The backend has no `gee` validator; the old button returned 400 always.
    await renderPage()

    const geeInput = screen.getByLabelText(/Google Earth Engine Project ID/)
    expect(geeInput).toBeInTheDocument()

    // One Verify button per validatable service field: two Sentinel Hub,
    // OpenTopography, Azure Maps. Not GEE.
    expect(screen.getAllByRole('button', { name: /verify/i })).toHaveLength(4)
  })

  it('never puts a masked placeholder in an editable input', async () => {
    await renderPage()

    const input = screen.getByLabelText(/OpenTopography API Key/) as HTMLInputElement
    expect(input.value).toBe('')
    expect(input.placeholder).toMatch(/stored/i)
    expect(screen.getAllByText(/configured/i).length).toBeGreaterThan(0)
  })

  it('sends only edited keys when saving', async () => {
    // A preferences-only change must not resend masked keys as credentials.
    mock.onPut('/settings').reply(200, STORED)

    await renderPage()

    await userEvent.selectOptions(screen.getByLabelText(/Language/), 'ru')
    await userEvent.click(screen.getByRole('button', { name: /save settings/i }))

    await waitFor(() => expect(mock.history.put).toHaveLength(1))

    const body = JSON.parse(mock.history.put[0].data)
    expect(body.api_keys).toBeUndefined()
    expect(body.preferences.language).toBe('ru')
  })

  it('includes an edited key when saving', async () => {
    mock.onPut('/settings').reply(200, STORED)

    await renderPage()

    await userEvent.type(screen.getByLabelText(/Azure Maps/), 'azure-key')
    await userEvent.click(screen.getByRole('button', { name: /save settings/i }))

    await waitFor(() => expect(mock.history.put).toHaveLength(1))
    expect(JSON.parse(mock.history.put[0].data).api_keys).toEqual({
      azure_maps_subscription_key: 'azure-key',
    })
  })

  it('shows the backend reason when saving fails', async () => {
    mock.onPut('/settings').reply(500, { detail: 'Failed to update settings' })

    await renderPage()

    await userEvent.selectOptions(screen.getByLabelText(/Language/), 'ru')
    await userEvent.click(screen.getByRole('button', { name: /save settings/i }))

    expect(await screen.findByText(/Failed to update settings/)).toBeInTheDocument()
  })

  it('disables Save until something changes', async () => {
    await renderPage()

    expect(screen.getByRole('button', { name: /save settings/i })).toBeDisabled()

    await userEvent.type(screen.getByLabelText(/Azure Maps/), 'x')
    expect(screen.getByRole('button', { name: /save settings/i })).toBeEnabled()
  })

  it('reports a load failure instead of showing an empty form silently', async () => {
    mock.reset()
    mock.onGet('/settings').reply(500, { detail: 'Failed to retrieve settings' })

    render(<SettingsPage />)

    expect(await screen.findByText(/Failed to retrieve settings/)).toBeInTheDocument()
  })
})
