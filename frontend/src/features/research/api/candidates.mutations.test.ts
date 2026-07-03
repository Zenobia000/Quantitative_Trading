import { afterEach, describe, expect, it, vi } from 'vitest'
import { ApiError } from '@/services/http'
import {
  describeMutationError,
  postCandidateDecision,
  postSelectLiveOos,
} from './candidates'

interface Captured {
  url: string
  method?: string
  body?: unknown
}

function stubFetch(status: number, payload: unknown): Captured {
  const cap: Captured = { url: '' }
  vi.stubGlobal(
    'fetch',
    vi.fn(async (url: string, init?: RequestInit) => {
      cap.url = String(url)
      cap.method = init?.method
      cap.body = init?.body ? JSON.parse(String(init.body)) : undefined
      return { status, json: async () => payload }
    }) as unknown as typeof fetch,
  )
  return cap
}

afterEach(() => vi.unstubAllGlobals())

describe('postCandidateDecision', () => {
  it('POSTs to /research/candidates/{id}/decision with the decision body and unwraps data', async () => {
    const cap = stubFetch(201, { success: true, data: { decision_id: 'dec_cand_x_0002' }, error: null, meta: {} })
    const out = await postCandidateDecision('cand_x', { action: 'keep', label: 'promising' })
    expect(cap.url).toContain('/research/candidates/cand_x/decision')
    expect(cap.method).toBe('POST')
    expect(cap.body).toEqual({ action: 'keep', label: 'promising' })
    expect(out).toEqual({ decision_id: 'dec_cand_x_0002' })
  })

  it('url-encodes the candidate id', async () => {
    const cap = stubFetch(201, { success: true, data: {}, error: null, meta: {} })
    await postCandidateDecision('cand a/b', { action: 'rerun' })
    expect(cap.url).toContain('/research/candidates/cand%20a%2Fb/decision')
  })

  it('throws ApiError with the backend message + detail on a 422', async () => {
    stubFetch(422, {
      success: false,
      data: null,
      error: { code: 'VALIDATION_ERROR', message: "action 'archive' requires a non-empty reason", detail: null },
      meta: {},
    })
    await expect(postCandidateDecision('cand_x', { action: 'archive' })).rejects.toMatchObject({
      code: 'VALIDATION_ERROR',
      message: "action 'archive' requires a non-empty reason",
    })
  })
})

describe('postSelectLiveOos', () => {
  it('POSTs to /research/candidates/{id}/select-live-oos with override + reason', async () => {
    const cap = stubFetch(201, { success: true, data: { queue_id: 'q1' }, error: null, meta: {} })
    const out = await postSelectLiveOos('cand_x', { reason: 'probe', override: true, observation_kind: 'paper_replay' })
    expect(cap.url).toContain('/research/candidates/cand_x/select-live-oos')
    expect(cap.method).toBe('POST')
    expect(cap.body).toEqual({ reason: 'probe', override: true, observation_kind: 'paper_replay' })
    expect(out).toEqual({ queue_id: 'q1' })
  })

  it('propagates a 409 blocked as an ApiError', async () => {
    stubFetch(409, {
      success: false,
      data: null,
      error: { code: 'IS_GATE_NOT_PASSED', message: "recommendation is 'blocked'", detail: { state: 'triaged' } },
      meta: {},
    })
    await expect(postSelectLiveOos('cand_x', { override: false })).rejects.toBeInstanceOf(ApiError)
  })
})

describe('describeMutationError', () => {
  it('returns the backend message, appending a 400 hint when present', () => {
    const err = new ApiError('BAD_REQUEST', 'illegal transition', { hint: "cannot 'keep' from 'archived'" }, 400)
    expect(describeMutationError(err)).toBe("illegal transition（cannot 'keep' from 'archived'）")
  })

  it('returns the bare message when there is no hint', () => {
    const err = new ApiError('VALIDATION_ERROR', 'reason required', null, 422)
    expect(describeMutationError(err)).toBe('reason required')
  })

  it('falls back to Error.message for non-ApiError', () => {
    expect(describeMutationError(new Error('boom'))).toBe('boom')
    expect(describeMutationError('weird')).toBe('unknown error')
  })
})
