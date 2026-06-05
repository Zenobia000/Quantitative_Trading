import { afterEach, describe, expect, it, vi } from 'vitest'
import { ApiError, http } from './http'

function mockFetch(status: number, body: unknown) {
  vi.stubGlobal(
    'fetch',
    vi.fn(async () => ({
      status,
      json: async () => body,
    })) as unknown as typeof fetch,
  )
}

afterEach(() => vi.unstubAllGlobals())

describe('http envelope client', () => {
  it('解包 success → 回 { data, meta }', async () => {
    mockFetch(200, { success: true, data: [{ id: 'r1' }], error: null, meta: { ttl: 300 } })
    const res = await http<{ id: string }[]>('/runs')
    expect(res.data).toEqual([{ id: 'r1' }])
    expect(res.meta.ttl).toBe(300)
  })

  it('error 為字串（v0.6）→ 由 status 推 code 並拋 ApiError', async () => {
    mockFetch(409, { success: false, data: null, error: 'IS gate 未過', meta: null })
    await expect(http('/gate/evaluate')).rejects.toMatchObject({
      name: 'ApiError',
      code: 'IS_GATE_NOT_PASSED',
      message: 'IS gate 未過',
      status: 409,
    })
  })

  it('error 為物件（doc 25 目標）→ 用其 code/message', async () => {
    mockFetch(423, {
      success: false,
      data: null,
      error: { code: 'OOS_VAULT_LOCKED', message: 'OOS 已封存' },
      meta: null,
    })
    await expect(http('/research/validate')).rejects.toMatchObject({
      code: 'OOS_VAULT_LOCKED',
      message: 'OOS 已封存',
    })
  })

  it('網路失敗 → ApiError(NETWORK)', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn(async () => {
        throw new Error('down')
      }) as unknown as typeof fetch,
    )
    const err = await http('/runs').catch((e) => e)
    expect(err).toBeInstanceOf(ApiError)
    expect((err as ApiError).code).toBe('NETWORK')
  })
})
