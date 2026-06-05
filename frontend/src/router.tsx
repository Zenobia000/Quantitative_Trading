/*
 * 路由表。Phase 0 全部指向 Placeholder；Phase 2 逐頁替換為實頁。
 * 路徑對齊各 page 規格的 route_path（dev_docs/web_design/pages/）。
 */
import type { ReactElement } from 'react'
import { createBrowserRouter } from 'react-router-dom'
import { AppShell } from '@/layouts/AppShell'
import { Placeholder } from '@/components/Placeholder'
import { PendingPage } from '@/components/PendingPage'
import { RunsTablePage } from '@/features/research/pages/RunsTablePage'
import { RunReportPage } from '@/features/research/pages/RunReportPage'
import { ComparePage } from '@/features/research/pages/ComparePage'

// Phase 2 已建的實頁（其餘暫 Placeholder）
const REAL: Record<string, ReactElement> = {
  'research/runs': <RunsTablePage />,
  'research/runs/:id': <RunReportPage />,
  'research/compare': <ComparePage />,
}

interface RouteDef {
  path: string
  title: string
  spec: string
}

// index（/）單獨處理
const ROUTES: RouteDef[] = [
  // Research
  { path: 'research/strategies', title: '策略庫', spec: 'research_01_strategy_library' },
  { path: 'research/runs/new', title: 'New Run 設定', spec: 'research_02_run_new' },
  { path: 'research/runs', title: 'Runs Table', spec: 'research_03_runs_table' },
  { path: 'research/runs/:id', title: 'Run Report', spec: 'research_04_run_report' },
  { path: 'research/runs/:id/trades', title: '逐筆覆盤', spec: 'research_trade_review' },
  { path: 'research/compare', title: 'Compare', spec: 'research_05_compare' },
  { path: 'research/sweep', title: 'Sweep', spec: 'research_06_sweep' },
  { path: 'research/validate', title: 'Validate gate', spec: 'research_07_validate_gate' },
  { path: 'research/promote/:strategyId', title: 'Promote', spec: 'research_08_promote' },
  // Monitor
  { path: 'monitor', title: '策略艦隊總控', spec: 'monitor_fleet' },
  { path: 'monitor/performance', title: '績效總覽', spec: 'monitor_a_performance' },
  { path: 'monitor/positions', title: '部位狀態', spec: 'monitor_b_positions' },
  { path: 'monitor/signals', title: '訊號日誌', spec: 'monitor_c_signals' },
  { path: 'monitor/risk', title: '風控指標', spec: 'monitor_d_risk' },
  // System
  { path: 'system/data', title: '資料管理', spec: 'system_data' },
  { path: 'system/alerts', title: '告警設定', spec: 'system_alerts' },
]

export const router = createBrowserRouter([
  {
    path: '/',
    element: <AppShell />,
    children: [
      { index: true, element: <PendingPage title="首頁 · 控制塔" route="/" spec="home_overview" /> },
      ...ROUTES.map((r) => ({
        path: r.path,
        element: REAL[r.path] ?? <PendingPage title={r.title} route={`/${r.path}`} spec={r.spec} />,
      })),
      { path: '*', element: <Placeholder title="找不到頁面" route="404" spec="—" /> },
    ],
  },
])
