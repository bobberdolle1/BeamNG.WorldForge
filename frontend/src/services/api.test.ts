import MockAdapter from 'axios-mock-adapter'
import { afterEach, beforeEach, describe, expect, it } from 'vitest'

import {
  ApiError,
  api,
  generateMap,
  getGenerationStatus,
  getSettings,
  saveSettings,
  validateCredential,
} from './api'

let mock: MockAdapter

beforeEach(() => {
  mock = new MockAdapter(api)
})

afterEach(() => {
  mock.restore()
})

const REQUEST = {
  name: 'test_map',
  bbox: { min_lat: 37.77, max_lat: 37.8, min_lon: -122.43, max_lon: -122.4 },
}

describe('error normalisation', () => {
  it("surfaces the backend's detail rather than axios's generic message", async () => {
    // The old client threw `err.message` — "Request failed with status code 422" —
    // which told the user nothing about what was actually wrong.
    mock.onPost('/generate').reply(422, {
      detail: 'bbox: Value error, Selected area is too large (900.0 km2).',
    })

    await expect(generateMap(REQUEST)).rejects.toThrow(/Selected area is too large/)
  })

  it('attaches the HTTP status to the error', async () => {
    mock.onGet('/status/abc').reply(404, { detail: 'Job not found or expired' })

    const error = await getGenerationStatus('abc').catch((caught) => caught)
    expect(error).toBeInstanceOf(ApiError)
    expect((error as ApiError).status).toBe(404)
  })

  it('explains a network failure instead of leaking axios internals', async () => {
    mock.onGet('/status/abc').networkError()

    await expect(getGenerationStatus('abc')).rejects.toThrow(/Cannot reach the server/)
  })

  it('explains a timeout', async () => {
    mock.onGet('/status/abc').timeout()

    await expect(getGenerationStatus('abc')).rejects.toThrow(/took too long/)
  })

  it('falls back to the axios message when the body carries no detail', async () => {
    mock.onGet('/status/abc').reply(500, {})

    await expect(getGenerationStatus('abc')).rejects.toBeInstanceOf(ApiError)
  })
})

describe('request shapes', () => {
  it('sends credentials in the body, never the query string', async () => {
    // Regression guard: this used to be `POST ...?api_key=<secret>`, which
    // wrote the key into access logs, proxies and browser history.
    mock.onPost('/settings/validate/sentinel_hub').reply(200, { valid: true })

    await validateCredential('sentinel_hub', 'client-id', 'client-secret')

    const [request] = mock.history.post
    expect(request.url).toBe('/settings/validate/sentinel_hub')
    expect(request.url).not.toContain('api_key')
    expect(JSON.parse(request.data)).toEqual({
      api_key: 'client-id',
      api_secret: 'client-secret',
    })
  })

  it('posts the generation request as JSON', async () => {
    mock.onPost('/generate').reply(202, { success: true, map_id: 'job-1' })

    await generateMap(REQUEST)

    expect(JSON.parse(mock.history.post[0].data)).toEqual(REQUEST)
  })

  it('reads and writes settings on /settings', async () => {
    mock.onGet('/settings').reply(200, { api_keys: {}, preferences: {} })
    mock.onPut('/settings').reply(200, { api_keys: {}, preferences: {} })

    await getSettings()
    await saveSettings({ api_keys: { opentopography_api_key: 'k' } })

    expect(mock.history.get[0].url).toBe('/settings')
    expect(mock.history.put[0].url).toBe('/settings')
    expect(JSON.parse(mock.history.put[0].data)).toEqual({
      api_keys: { opentopography_api_key: 'k' },
    })
  })
})
