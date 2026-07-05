/*
 * Route table for the Codex-style operations console.
 * Golden IA is seven-layer: Data / Research / Governance / Trading / Risk / Operations / System.
 * Some URLs stay legacy-compatible, but comments and navigation semantics follow the new product layers.
 * Every route is a real page; unknown paths fall through to NotFound.
 */
import type { ReactElement } from 'react'
import { createBrowserRouter, Navigate } from 'react-router-dom'
import { AppShell } from '@/layouts/AppShell'
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

// path → 實頁元件。單一真相源，router 直接迭代（無過渡佔位態）。
const ROUTES: Record<string, ReactElement> = {
  // Research
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
  // System zone
  'system/data': <DataPage />,
  'system/alerts': <AlertsPage />,
}

export const router = createBrowserRouter([
  {
    path: '/',
    element: <AppShell />,
    children: [
      { index: true, element: <HomePage /> },
      ...Object.entries(ROUTES).map(([path, element]) => ({ path, element })),
      { path: '*', element: <NotFoundPage /> },
    ],
  },
])
