/*
 * 前後端契約型別（手寫 view-model 與 envelope 殼）。
 * 注意：API 端點的「資料形狀」一律由 OpenAPI 生成到 src/types/api.gen.ts（禁手寫）。
 * 本檔只放 envelope 殼與跨頁共用的 view-model。對齊 dev_docs/25_fe_be_rest_contract.md。
 */

/** doc 25 §2 error code enum（單人：只用到 401，無 403/RBAC） */
export type ApiErrorCode =
  | 'VALIDATION_ERROR'
  | 'IS_GATE_NOT_PASSED'
  | 'OOS_VAULT_LOCKED'
  | 'NOT_FOUND'
  | 'BAD_REQUEST'
  | 'UNAUTHORIZED'
  | 'QUERY_TIMEOUT'
  | 'INTERNAL'
  | 'NETWORK'

export interface ApiErrorShape {
  code: ApiErrorCode
  message: string
  detail?: unknown
}

/** doc 25 §1.1 meta */
export interface ApiMeta {
  total?: number
  page?: number
  limit?: number
  /** 建議的快取/輪詢秒數 */
  ttl?: number
  /** 例如 "pending_m4"：端點尚未有 producer，前端渲染 pending 態，不假造數字 */
  data_source?: string
}

/**
 * envelope.error 的兩種形狀：
 * - v0.6 後端（shipped）：純字串
 * - doc 25 目標契約：{code,message,detail} 物件
 * http client 會把兩者正規化成 ApiError。
 */
export type EnvelopeError = string | ApiErrorShape

/** doc 25 §1.1 統一信封 */
export interface Envelope<T> {
  success: boolean
  data: T | null
  error: EnvelopeError | null
  meta?: ApiMeta
}

/** 由 HTTP status 推 error code（後端 error 為字串時用；對齊 doc 25 §2 status↔code）。 */
export function statusToCode(status: number): ApiErrorCode {
  switch (status) {
    case 400:
      return 'BAD_REQUEST'
    case 401:
      return 'UNAUTHORIZED'
    case 404:
      return 'NOT_FOUND'
    case 409:
      return 'IS_GATE_NOT_PASSED'
    case 422:
      return 'VALIDATION_ERROR'
    case 423:
      return 'OOS_VAULT_LOCKED'
    case 504:
      return 'QUERY_TIMEOUT'
    default:
      return 'INTERNAL'
  }
}

/** 解包後給頁面用的結果 */
export interface ApiResult<T> {
  data: T
  meta: ApiMeta
}

/** 是否為「尚未上線」的 pending 端點（渲染 pending 態用） */
export function isPending(meta: ApiMeta | undefined): boolean {
  return typeof meta?.data_source === 'string' && meta.data_source.startsWith('pending')
}
