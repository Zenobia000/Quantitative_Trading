/*
 * Route table for the Codex-style operations console.
 * Golden IA is seven-layer: Data / Research / Governance / Trading / Risk / Operations / System.
 * Some URLs stay legacy-compatible, but comments and navigation semantics follow the new product layers.
 */
import type { ReactElement } from 'react'
import { createBrowserRouter, Navigate } from 'react-router-dom'
import { AppShell } from '@/layouts/AppShell'
import { WiredPage } from '@/components/WiredPage'
import { NotFoundPage } from '@/components/NotFoundPage'
import { RunsTablePage } from '@/features/research/pages/RunsTablePage'
import { RunReportPage } from '@/features/research/pages/RunReportPage'
import { ReportViewerPage } from '@/features/research/pages/ReportViewerPage'
import { ComparePage } from '@/features/research/pages/ComparePage'
import { NewRunPage } from '@/features/research/pages/NewRunPage'
import { ValidateGatePage } from '@/features/research/pages/ValidateGatePage'
import { StrategyHubListPage } from '@/features/research/pages/StrategyHubListPage'
import { StrategyHubDetailPage } from '@/features/research/pages/StrategyHubDetailPage'
import { CandidatePoolPage } from '@/features/research/pages/CandidatePoolPage'
import { PromotePage } from '@/features/research/pages/PromotePage'
import { TradeReviewPage } from '@/features/research/pages/TradeReviewPage'
import { SweepPage } from '@/features/research/pages/SweepPage'
import { LiveOosQueuePage } from '@/features/liveOos/pages/LiveOosQueuePage'
import { GateRedirect, PromoteRedirect } from '@/app/redirects'
import { HomePage } from '@/features/home/pages/HomePage'
import { FleetPage } from '@/features/monitor/pages/FleetPage'
import { BoardPage } from '@/features/monitor/pages/BoardPage'
import { WatchPage } from '@/features/monitor/pages/WatchPage'
import { PerformancePage } from '@/features/monitor/pages/PerformancePage'
import { PositionsPage } from '@/features/monitor/pages/PositionsPage'
import { SignalsPage } from '@/features/monitor/pages/SignalsPage'
import { RiskPage } from '@/features/monitor/pages/RiskPage'
import { DataPage } from '@/features/system/pages/DataPage'
import { AlertsPage } from '@/features/system/pages/AlertsPage'

// 有完整真實資料的實頁
const REAL: Record<string, ReactElement> = {
  'research/strategies': <StrategyHubListPage />,
  'research/strategies/:name': <StrategyHubDetailPage />,
  'research/candidates': <CandidatePoolPage />,
  'research/runs/new': <NewRunPage />,
  'research/runs': <RunsTablePage />,
  'research/runs/:id': <RunReportPage />,
  'research/reports/:runId': <ReportViewerPage />,
  'research/runs/:id/trades': <TradeReviewPage />,
  'research/compare': <ComparePage />,
  'research/sweep': <SweepPage />,
  // Governance: old research validate/promote URLs remain client redirects.
  'research/validate': <GateRedirect />,
  'research/promote/:strategyId': <PromoteRedirect />,
  // Governance: human-selected OOS queue + Paper-Watch observation.
  'live-oos/queue': <LiveOosQueuePage />,
  'live-oos/watch': <WatchPage />,
  'deploy/gate': <ValidateGatePage />,
  'deploy/promote/:strategyId': <PromotePage />,
  // Operations / Trading / Risk pages backed by monitor endpoints.
  monitor: <FleetPage />,
  'monitor/board': <BoardPage />,
  'monitor/watch': <Navigate to="/live-oos/watch" replace />,
  'monitor/performance': <PerformancePage />,
  'monitor/positions': <PositionsPage />,
  'monitor/signals': <SignalsPage />,
  'monitor/risk': <RiskPage />,
  // System zone — real feature pages
  'system/data': <DataPage />,
  'system/alerts': <AlertsPage />,
}

// 其餘頁：接真實端點（多為 typed-empty stub / M4 deferred）→ WiredPage 渲染四態
const ENDPOINT: Record<string, string | null> = {}

interface RouteDef {
  path: string
  title: string
  spec: string
}

// index（/）單獨處理
const ROUTES: RouteDef[] = [
  // Research
  { path: 'research/strategies', title: '策略中心', spec: 'research_01_strategy_library' },
  { path: 'research/strategies/:name', title: '策略中心 · 詳情', spec: 'research_01_strategy_library' },
  { path: 'research/candidates', title: '候選池', spec: 'research_candidate_pool' },
  { path: 'research/runs/new', title: 'New Run 設定', spec: 'research_02_run_new' },
  { path: 'research/runs', title: 'Runs Table', spec: 'research_03_runs_table' },
  { path: 'research/runs/:id', title: 'Run Report', spec: 'research_04_run_report' },
  { path: 'research/reports/:runId', title: 'Report Viewer', spec: 'research_04_run_report' },
  { path: 'research/runs/:id/trades', title: '逐筆覆盤', spec: 'research_trade_review' },
  { path: 'research/compare', title: 'Compare', spec: 'research_05_compare' },
  { path: 'research/sweep', title: 'Sweep', spec: 'research_06_sweep' },
  // Governance
  { path: 'research/validate', title: 'Validate gate（→ Governance）', spec: 'research_07_validate_gate' },
  { path: 'research/promote/:strategyId', title: 'Promote（→ Governance）', spec: 'research_08_promote' },
  { path: 'live-oos/queue', title: 'OOS Governance Queue', spec: 'live_oos_queue' },
  { path: 'live-oos/watch', title: 'Paper-Watch Observation', spec: 'monitor_watch' },
  { path: 'deploy/gate', title: 'Release Gate', spec: 'research_07_validate_gate' },
  { path: 'deploy/promote/:strategyId', title: 'Capital Promotion', spec: 'research_08_promote' },
  // Operations / Trading / Risk
  { path: 'monitor', title: 'Operations Fleet', spec: 'monitor_fleet' },
  { path: 'monitor/board', title: 'Operations Board', spec: 'monitor_board' },
  { path: 'monitor/watch', title: 'Paper-Watch Observation（→ Governance）', spec: 'monitor_watch' },
  { path: 'monitor/performance', title: 'PnL / Performance', spec: 'monitor_a_performance' },
  { path: 'monitor/positions', title: 'Target / Position Blotter', spec: 'monitor_b_positions' },
  { path: 'monitor/signals', title: 'Signal Ledger', spec: 'monitor_c_signals' },
  { path: 'monitor/risk', title: 'Risk Blotter', spec: 'monitor_d_risk' },
  // System
  { path: 'system/data', title: '資料管理', spec: 'system_data' },
  { path: 'system/alerts', title: '告警設定', spec: 'system_alerts' },
]

export const router = createBrowserRouter([
  {
    path: '/',
    element: <AppShell />,
    children: [
      { index: true, element: <HomePage /> },
      ...ROUTES.map((r) => ({
        path: r.path,
        element: REAL[r.path] ?? (
          <WiredPage
            title={r.title}
            route={`/${r.path}`}
            spec={r.spec}
            endpoint={r.path in ENDPOINT ? ENDPOINT[r.path] : null}
          />
        ),
      })),
      { path: '*', element: <NotFoundPage /> },
    ],
  },
])
