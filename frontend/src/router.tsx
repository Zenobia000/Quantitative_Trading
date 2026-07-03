/*
 * 路由表。Phase 0 全部指向 Placeholder；Phase 2 逐頁替換為實頁。
 * 路徑對齊各 page 規格的 route_path（dev_docs/web_design/pages/）。
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
  // validate/promote migrated to Deployment zone → keep old paths as client redirects (rebuild IA §5.6)
  'research/validate': <GateRedirect />,
  'research/promote/:strategyId': <PromoteRedirect />,
  // Live OOS zone — human-selected expensive OOS journey (rebuild IA §1.2)
  'live-oos/queue': <LiveOosQueuePage />,
  'live-oos/watch': <WatchPage />, // Paper-Watch 觀察艙 migrated from monitor (元件搬 route 不搬檔)
  // Deployment zone — strict gate + capital promotion, journey 3 (rebuild IA §1.3)
  'deploy/gate': <ValidateGatePage />, // 承接 validate；元件搬 route 不搬檔
  'deploy/promote/:strategyId': <PromotePage />,
  // Monitor zone — real feature pages (telemetry-backed; light up as the daemon feeds data)
  monitor: <FleetPage />,
  'monitor/board': <BoardPage />,
  // watch migrated to Live OOS zone → keep the old path as a client redirect (rebuild IA §5.6)
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
  // validate/promote 已移 Deployment zone；舊 path 保留為 client 重導（→ /deploy/*）
  { path: 'research/validate', title: 'Validate gate（→ Deployment）', spec: 'research_07_validate_gate' },
  { path: 'research/promote/:strategyId', title: 'Promote（→ Deployment）', spec: 'research_08_promote' },
  // Live OOS
  { path: 'live-oos/queue', title: 'OOS 佇列', spec: 'live_oos_queue' },
  { path: 'live-oos/watch', title: 'Paper-Watch 觀察艙', spec: 'monitor_watch' },
  // Deployment
  { path: 'deploy/gate', title: '部署嚴格閘', spec: 'research_07_validate_gate' },
  { path: 'deploy/promote/:strategyId', title: '晉升', spec: 'research_08_promote' },
  // Monitor
  { path: 'monitor', title: '策略艦隊總控', spec: 'monitor_fleet' },
  { path: 'monitor/board', title: '運行看板', spec: 'monitor_board' },
  { path: 'monitor/watch', title: 'Paper-Watch 觀察艙（→ Live OOS）', spec: 'monitor_watch' },
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
