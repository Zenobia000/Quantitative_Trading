import { afterEach, describe, expect, it, vi } from 'vitest'
import { getEvaluation, resolveEvaluationId } from './reportViewer'
import type { Candidate } from './candidates'

function candidatesEnvelope(cands: Partial<Candidate>[]) {
  return { success: true, data: cands, error: null, meta: { data_source: 'ledger' } }
}

/** Route the mock by URL: candidates list vs a specific evaluation. */
function stubRoutes(routes: { candidates?: unknown; evaluation?: (id: string) => { status: number; payload: unknown } }) {
  vi.stubGlobal(
    'fetch',
    vi.fn(async (url: string) => {
      const u = String(url)
      if (u.endsWith('/research/candidates')) {
        if (routes.candidates === undefined) return { status: 404, json: async () => ({ detail: 'nf' }) }
        return { status: 200, json: async () => routes.candidates }
      }
      const m = u.match(/\/research\/evaluations\/([^/?]+)$/)
      if (m && routes.evaluation) {
        const { status, payload } = routes.evaluation(decodeURIComponent(m[1]))
        return { status, json: async () => payload }
      }
      return { status: 404, json: async () => ({ detail: 'nf' }) }
    }) as unknown as typeof fetch,
  )
}

afterEach(() => vi.unstubAllGlobals())

describe('resolveEvaluationId', () => {
  it('passes an eval_-prefixed id straight through (no candidates fetch)', async () => {
    const spy = vi.fn(async () => ({ status: 200, json: async () => ({}) }))
    vi.stubGlobal('fetch', spy as unknown as typeof fetch)
    expect(await resolveEvaluationId('eval_inst_flow_quick_triage_abc')).toBe('eval_inst_flow_quick_triage_abc')
    expect(spy).not.toHaveBeenCalled()
  })

  it('reverse-looks-up a run_id via the candidate pool report_pack_ref', async () => {
    stubRoutes({
      candidates: candidatesEnvelope([
        { report_pack_ref: 'reports/research_runs/deadbeef01/manifest.json', latest_evaluation_id: 'eval_x_quick_triage_deadbeef01' },
        { report_pack_ref: 'reports/research_runs/other99/manifest.json', latest_evaluation_id: 'eval_y' },
      ]),
    })
    expect(await resolveEvaluationId('deadbeef01')).toBe('eval_x_quick_triage_deadbeef01')
  })

  it('returns the original run_id when no candidate matches', async () => {
    stubRoutes({ candidates: candidatesEnvelope([{ report_pack_ref: 'reports/research_runs/zzz/manifest.json', latest_evaluation_id: 'eval_z' }]) })
    expect(await resolveEvaluationId('deadbeef01')).toBe('deadbeef01')
  })

  it('returns the original id when the candidate endpoint is unreachable', async () => {
    stubRoutes({}) // candidates → 404
    expect(await resolveEvaluationId('deadbeef01')).toBe('deadbeef01')
  })
})

describe('getEvaluation id mapping', () => {
  it('a run_id link resolves to the candidate latest_evaluation_id and GETs the real evaluation', async () => {
    stubRoutes({
      candidates: candidatesEnvelope([
        { report_pack_ref: 'reports/research_runs/deadbeef01/manifest.json', latest_evaluation_id: 'eval_x_quick_triage_deadbeef01' },
      ]),
      evaluation: (id) =>
        id === 'eval_x_quick_triage_deadbeef01'
          ? { status: 200, payload: { success: true, data: { evaluation_id: id, strategy: 'x' }, error: null, meta: {} } }
          : { status: 404, payload: { detail: 'nf' } },
    })
    const out = await getEvaluation('deadbeef01')
    expect(out.source).toBe('api')
    expect(out.data.evaluation_id).toBe('eval_x_quick_triage_deadbeef01')
  })

  it('falls back to the bundled fixture when resolution + GET both miss', async () => {
    stubRoutes({ candidates: candidatesEnvelope([]), evaluation: () => ({ status: 404, payload: { detail: 'nf' } }) })
    const out = await getEvaluation('deadbeef01')
    expect(out.source).toBe('fixture')
    expect(out.data.evaluation_id).toBeTruthy()
  })
})
