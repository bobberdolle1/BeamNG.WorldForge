import { act, renderHook, waitFor } from '@testing-library/react'
import MockAdapter from 'axios-mock-adapter'
import { afterEach, beforeEach, describe, expect, it } from 'vitest'

import { api } from '../services/api'
import type { MapGenerationRequest } from '../types'
import { useGenerationJob } from './useGenerationJob'

let mock: MockAdapter

beforeEach(() => {
  mock = new MockAdapter(api)
})

afterEach(() => {
  mock.restore()
})

const REQUEST: MapGenerationRequest = {
  name: 'test_map',
  bbox: { min_lat: 37.77, max_lat: 37.8, min_lon: -122.43, max_lon: -122.4 },
}

function statusPayload(overrides: Record<string, unknown> = {}) {
  return {
    job_id: 'job-1',
    status: 'processing',
    progress: 40,
    message: 'Processing terrain',
    ...overrides,
  }
}

describe('useGenerationJob', () => {
  it('starts a job and exposes the queued state immediately', async () => {
    mock.onPost('/generate').reply(202, {
      success: true,
      map_id: 'job-1',
      map_name: 'test_map',
      message: 'Map generation started',
    })
    mock.onGet('/status/job-1').reply(200, statusPayload())

    const { result } = renderHook(() => useGenerationJob())

    await act(async () => {
      await result.current.start(REQUEST)
    })

    expect(result.current.status?.job_id).toBe('job-1')
    expect(result.current.status?.map_name).toBe('test_map')
    expect(result.current.error).toBeNull()
  })

  it('polls immediately rather than waiting a full interval', async () => {
    mock.onPost('/generate').reply(202, { success: true, map_id: 'job-1', message: 'ok' })
    mock.onGet('/status/job-1').reply(200, statusPayload({ progress: 60 }))

    const { result } = renderHook(() => useGenerationJob())

    await act(async () => {
      await result.current.start(REQUEST)
    })

    await waitFor(() => expect(result.current.status?.progress).toBe(60))
  })

  it('stops polling once the job completes', async () => {
    mock.onPost('/generate').reply(202, { success: true, map_id: 'job-1', message: 'ok' })
    mock.onGet('/status/job-1').reply(200, statusPayload({ status: 'completed', progress: 100 }))

    const { result } = renderHook(() => useGenerationJob())

    await act(async () => {
      await result.current.start(REQUEST)
    })

    await waitFor(() => expect(result.current.status?.status).toBe('completed'))

    const callsAfterCompletion = mock.history.get.length
    await new Promise((resolve) => setTimeout(resolve, 2500))

    expect(mock.history.get.length).toBe(callsAfterCompletion)
    expect(result.current.isBusy).toBe(false)
  })

  it('surfaces the failure reason when the job fails', async () => {
    mock.onPost('/generate').reply(202, { success: true, map_id: 'job-1', message: 'ok' })
    mock.onGet('/status/job-1').reply(
      200,
      statusPayload({ status: 'failed', error: 'OpenTopography is not configured' }),
    )

    const { result } = renderHook(() => useGenerationJob())

    await act(async () => {
      await result.current.start(REQUEST)
    })

    await waitFor(() => expect(result.current.error).toMatch(/not configured/))
    expect(result.current.isBusy).toBe(false)
  })

  it('tolerates a single dropped poll instead of giving up', async () => {
    mock.onPost('/generate').reply(202, { success: true, map_id: 'job-1', message: 'ok' })

    let call = 0
    mock.onGet('/status/job-1').reply(() => {
      call += 1
      if (call === 1) {
        return [500, {}]
      }
      return [200, statusPayload({ status: 'completed', progress: 100 })]
    })

    const { result } = renderHook(() => useGenerationJob())

    await act(async () => {
      await result.current.start(REQUEST)
    })

    await waitFor(() => expect(result.current.status?.status).toBe('completed'), { timeout: 6000 })
    expect(result.current.error).toBeNull()
  })

  it('reports a start failure and stays idle', async () => {
    mock.onPost('/generate').reply(422, { detail: 'name: too short' })

    const { result } = renderHook(() => useGenerationJob())

    await act(async () => {
      await result.current.start(REQUEST)
    })

    expect(result.current.error).toMatch(/too short/)
    expect(result.current.status).toBeNull()
    // isBusy must clear, or the Generate button stays disabled forever.
    expect(result.current.isBusy).toBe(false)
  })

  it('treats a success:false response as a failure', async () => {
    mock.onPost('/generate').reply(202, { success: false, message: 'nope', error: 'refused' })

    const { result } = renderHook(() => useGenerationJob())

    await act(async () => {
      await result.current.start(REQUEST)
    })

    expect(result.current.error).toBe('refused')
    expect(result.current.isBusy).toBe(false)
  })

  it('clears state on reset', async () => {
    mock.onPost('/generate').reply(202, { success: true, map_id: 'job-1', message: 'ok' })
    mock.onGet('/status/job-1').reply(200, statusPayload({ status: 'completed', progress: 100 }))

    const { result } = renderHook(() => useGenerationJob())

    await act(async () => {
      await result.current.start(REQUEST)
    })
    await waitFor(() => expect(result.current.status?.status).toBe('completed'))

    act(() => result.current.reset())

    expect(result.current.status).toBeNull()
    expect(result.current.error).toBeNull()
  })

  it('stops polling when unmounted', async () => {
    mock.onPost('/generate').reply(202, { success: true, map_id: 'job-1', message: 'ok' })
    mock.onGet('/status/job-1').reply(200, statusPayload())

    const { result, unmount } = renderHook(() => useGenerationJob())

    await act(async () => {
      await result.current.start(REQUEST)
    })
    await waitFor(() => expect(mock.history.get.length).toBeGreaterThan(0))

    unmount()
    const callsAtUnmount = mock.history.get.length
    await new Promise((resolve) => setTimeout(resolve, 2500))

    expect(mock.history.get.length).toBe(callsAtUnmount)
  })
})
