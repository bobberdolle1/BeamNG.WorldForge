import { useCallback, useEffect, useRef, useState } from 'react'

import { ApiError, generateMap, getGenerationStatus } from '../services/api'
import type { GenerationStatus, MapGenerationRequest } from '../types'
import { isTerminal } from '../types'

/** How often to poll a running job. */
const POLL_INTERVAL_MS = 2000

/**
 * Consecutive poll failures tolerated before giving up.
 *
 * A single dropped request (a reload, a blip) previously killed polling
 * outright and left the UI stuck on stale progress, so transient failures are
 * now absorbed.
 */
const MAX_CONSECUTIVE_POLL_ERRORS = 3

export interface UseGenerationJob {
  status: GenerationStatus | null
  error: string | null
  isBusy: boolean
  start: (request: MapGenerationRequest) => Promise<void>
  reset: () => void
}

/**
 * Owns the lifecycle of one map generation job.
 *
 * Two bugs in the previous inline implementation are fixed here:
 *
 * 1. **The poll timer restarted on every tick.** The effect depended on
 *    `generationStatus`, and each poll replaced that object, so the effect
 *    re-ran, cleared its interval and created a new one - every two seconds,
 *    forever. The interval is now created once per job id.
 * 2. **`isGenerating` could get stuck on.** It was only cleared inside the
 *    polling effect, so if polling never started (or the component re-rendered
 *    through a different path) the Generate button stayed disabled until a
 *    page reload. Busy state is now derived from the job status itself.
 */
export function useGenerationJob(): UseGenerationJob {
  const [status, setStatus] = useState<GenerationStatus | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [isStarting, setIsStarting] = useState(false)

  // Held in a ref so the polling effect depends only on the job id: reading
  // status from state would reintroduce the restart-every-tick bug.
  const jobIdRef = useRef<string | null>(null)
  const [jobId, setJobId] = useState<string | null>(null)

  const start = useCallback(async (request: MapGenerationRequest) => {
    setError(null)
    setStatus(null)
    setIsStarting(true)

    try {
      const response = await generateMap(request)
      if (!response.success || !response.map_id) {
        throw new ApiError(response.error ?? 'The server did not accept the request')
      }

      jobIdRef.current = response.map_id
      setJobId(response.map_id)
      setStatus({
        job_id: response.map_id,
        status: 'queued',
        progress: 0,
        message: response.message,
        map_name: response.map_name,
      })
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : 'Failed to start map generation')
      jobIdRef.current = null
      setJobId(null)
    } finally {
      setIsStarting(false)
    }
  }, [])

  const reset = useCallback(() => {
    jobIdRef.current = null
    setJobId(null)
    setStatus(null)
    setError(null)
  }, [])

  useEffect(() => {
    if (!jobId) {
      return
    }

    let cancelled = false
    let consecutiveErrors = 0

    const poll = async () => {
      try {
        const next = await getGenerationStatus(jobId)
        if (cancelled) {
          return
        }

        consecutiveErrors = 0
        setStatus(next)

        if (isTerminal(next.status)) {
          window.clearInterval(timer)
          if (next.status === 'failed') {
            setError(next.error ?? 'Map generation failed')
          }
        }
      } catch (caught) {
        if (cancelled) {
          return
        }

        consecutiveErrors += 1
        if (consecutiveErrors >= MAX_CONSECUTIVE_POLL_ERRORS) {
          window.clearInterval(timer)
          setError(
            caught instanceof Error
              ? `Lost contact with the server: ${caught.message}`
              : 'Lost contact with the server',
          )
        }
      }
    }

    const timer = window.setInterval(poll, POLL_INTERVAL_MS)
    void poll() // Poll immediately so short jobs do not wait a full interval.

    return () => {
      cancelled = true
      window.clearInterval(timer)
    }
  }, [jobId])

  const isBusy = isStarting || (status !== null && !isTerminal(status.status))

  return { status, error, isBusy, start, reset }
}
