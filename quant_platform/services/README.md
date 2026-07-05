# services/

Eight bounded services (ADR-R05). Physically isolated from research (import-linter contract 1 enforces research ⊄ services).

| Service | Source | Status |
| :-- | :-- | :-- |
| data_platform | `services/data_platform/` + `data/` ETL | shell built (W5.2d) |
| research_validation | `research/` + `validation/` | layer-2 core |
| governance_release | `governance/` | built (W2.1) |
| strategy_runtime | `services/strategy_runtime/` | built (W5.1c) |
| portfolio_engine | (not yet carved — SizingGate/portfolio) | future |
| risk_gate | `services/risk_gate/` | built (W5.1a) |
| execution_gateway | `services/execution_gateway/` | built (W5.1b) |
| monitoring_ops | `services/monitoring_ops/` | built (W5.2a/b/e/f) |
