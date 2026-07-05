/*
 * 單一 HTTP client：解 envelope + 帶 static Bearer。
 * 所有 API 呼叫一律走這裡（GOAL.md 硬約束 #3）。對齊 dev_docs/25_fe_be_rest_contract.md。
 */
import type { ApiErrorCode, ApiResult, Envelope } from '@/types/domain'
import { statusToCode } from '@/types/domain'

const BASE = import.meta.env.VITE_API_BASE ?? '' // dev 走 vite proxy（相對路徑）
const TOKEN = import.meta.env.VITE_API_TOKEN ?? 'dev-token'

export class ApiError extends Error {
  code: ApiErrorCode
  detail?: unknown
  status?: number
  constructor(code: ApiErrorCode, message: string, detail?: unknown, status?: number) {
    super(message)
    this.name = 'ApiError'
    this.code = code
    this.detail = detail
    this.status = status
  }
}

export interface HttpOptions extends Omit<RequestInit, 'body'> {
  /** query string 物件（自動序列化，略過 undefined/null） */
  query?: Record<string, string | number | boolean | undefined | null>
  /** JSON body（自動 stringify） */
  json?: unknown
}

function buildUrl(path: string, query?: HttpOptions['query']): string {
  const url = `${BASE}${path}`
  if (!query) return url
  const qs = new URLSearchParams()
  for (const [k, v] of Object.entries(query)) {
    if (v !== undefined && v !== null) qs.append(k, String(v))
  }
  const s = qs.toString()
  return s ? `${url}?${s}` : url
}

/**
 * 打後端裸根端點，回傳解包後的 { data, meta }。
 * envelope.success=false 或網路錯誤 → 拋 ApiError（由上層 section 渲染 error 態）。
 */
export async function http<T>(path: string, opts: HttpOptions = {}): Promise<ApiResult<T>> {
  const { query, json, headers, ...init } = opts
  let res: Response
  try {
    res = await fetch(buildUrl(path, query), {
      ...init,
      headers: {
        Accept: 'application/json',
        Authorization: `Bearer ${TOKEN}`,
        ...(json !== undefined ? { 'Content-Type': 'application/json' } : {}),
        ...headers,
      },
      body: json !== undefined ? JSON.stringify(json) : undefined,
    })
  } catch (e) {
    throw new ApiError('NETWORK', '網路連線失敗，請稍後再試', e)
  }

  let env: Envelope<T> | null = null
  try {
    env = (await res.json()) as Envelope<T>
  } catch {
    // 非 envelope 回應（如 502 HTML）
    throw new ApiError('INTERNAL', `伺服器回應異常 (${res.status})`, undefined, res.status)
  }

  if (!env.success || env.error) {
    const err = env.error
    if (typeof err === 'string' || err == null) {
      // v0.6 後端：error 為字串 → 由 status 推 code
      throw new ApiError(statusToCode(res.status), err ?? `請求失敗 (${res.status})`, undefined, res.status)
    }
    // doc 25 目標：error 為 {code,message,detail} 物件
    throw new ApiError(
      (err.code as ApiErrorCode) ?? statusToCode(res.status),
      err.message ?? `請求失敗 (${res.status})`,
      err.detail,
      res.status,
    )
  }

  return { data: env.data as T, meta: env.meta ?? {} }
}
