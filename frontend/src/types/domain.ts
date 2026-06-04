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

/** doc 25 §1.1 統一信封 */
export interface Envelope<T> {
  success: boolean
  data: T | null
  error: ApiErrorShape | null
  meta?: ApiMeta
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
