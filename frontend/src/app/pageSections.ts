/*
 * Pending page section hints. Legacy page specs were replaced by
 * dev_docs/product_repositioning/17_frontend_information_architecture.md; keep these
 * names only as transitional UI skeleton anchors until FE-R2/FE-R5 rewrites pages.
 */
export const PAGE_SECTIONS: Record<string, string[]> = {
  home_overview: ['command_hero', 'fleet_strip', 'research_status', 'system_health', 'recent_activity', 'empty_state'],
  research_01_strategy_library: ['toolbar', 'strategy_list', 'version_timeline', 'empty_state'],
  research_02_run_new: ['hypothesis', 'parameters', 'cost_engine', 'period', 'submit_bar'],
  research_06_sweep: ['sweep_config', 'estimate_guard', 'guardrail_bar', 'optimization_heatmap', 'cell_drilldown'],
  research_07_validate_gate: [
    'gate_status_header',
    'is_gate_checklist',
    'oos_sealed_vault',
    'wfa_fold_view',
    'overfitting_redline',
    'commitment_signoff',
  ],
  research_08_promote: ['promotion_stepper', 'current_stage_checklist', 'paper_observation', 'promote_action', 'audit_log'],
  research_trade_review: ['review_header', 'candlestick_chart', 'trade_list', 'resonance_attribution', 'context_drawer'],
  monitor_a_performance: ['filter_bar', 'kpi_overview', 'equity_curve', 'drawdown_chart', 'rolling_sharpe', 'monthly_heatmap'],
  monitor_b_positions: ['header_bar', 'kpi_row', 'positions_table', 'industry_allocation', 'concentration_risk'],
  monitor_c_signals: ['filter_bar', 'todays_signals_table', 'signal_timeline_30d', 'signal_fill_funnel'],
  monitor_d_risk: ['risk_status_header', 'risk_water_levels', 'mdd_trend_chart', 'recent_risk_events'],
  monitor_fleet: ['fleet_toolbar', 'portfolio_summary', 'fleet_table', 'degradation_panel', 'correlation_matrix', 'empty_state'],
  system_data: ['toolbar', 'bundle_list', 'ingest_status', 'data_quality', 'empty_state'],
  system_alerts: ['toolbar', 'channel_config', 'alert_rules', 'alert_history', 'test_delivery'],
}
