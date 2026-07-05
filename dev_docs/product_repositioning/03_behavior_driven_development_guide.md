# BDD 行為驅動情境指南 - 個人級 EOD 量化交易平台

> 版本: v1.0 | 日期: 2026-07-05 | 狀態: Golden baseline

## 1. Gherkin 規範

- Feature 以七層命名：`data_bundle.feature`、`research_validation.feature`、`governance_release.feature`。
- Scenario 必須可自動化，避免「看起來合理」這類主觀描述。
- 每個交易相關 Scenario 必須包含 `strategy_id`、`strategy_version`、`bundle_ref` 或說明為何不需要。

## 2. 核心 Feature

### Feature: Data bundle 可重現

```gherkin
Feature: Versioned EOD data bundle
  Scenario: Build a reproducible bundle
    Given EOD source data for a closed trading date
    And financial statement and chip data are available
    When the data platform builds a bundle
    Then the bundle has a stable bundle_ref
    And the bundle manifest records source hashes and coverage
    And failed DQ checks prevent release promotion
```

### Feature: Research 不可下單

```gherkin
Feature: Research boundary
  Scenario: Research emits target portfolio only
    Given an approved research configuration
    When the strategy backtest finishes
    Then it emits StrategyDefinition
    And it emits AlphaSignal
    And it emits TargetPortfolio
    But it does not call any BrokerGateway
    And it does not create any BrokerOrder
```

### Feature: Governance 發布閘門

```gherkin
Feature: Strategy release gate
  Scenario: Promote a validated strategy to paper
    Given a strategy has WFA and DSR evidence
    And the report pack contains trials and failed variants
    When the approver approves the release
    Then an immutable ApprovedStrategyPackage is created
    And a rollback plan is attached
    And the package starts in paper mode
```

### Feature: Risk Gate fail closed

```gherkin
Feature: Pre-trade risk gate
  Scenario: Block an order intent with concentration breach
    Given an ApprovedStrategyPackage produces an OrderIntent
    And the intent would exceed single_position_limit
    When the RiskGate evaluates the intent
    Then the decision is Block
    And the reason contains the triggered rule_id
    And PersonalExecution does not submit a broker order
```

### Feature: Fill 單一真相

```gherkin
Feature: Fill as single source of truth
  Scenario: Update position from broker fill
    Given a broker fill is received with exec_id
    When the FillStore appends the fill
    Then PositionService folds the fill into positions
    And Monitoring calculates PnL from fills
    And duplicate exec_id is ignored idempotently
```

### Feature: Reconciliation halt

```gherkin
Feature: Daily reconciliation
  Scenario: Halt next trading on broker mismatch
    Given internal positions differ from broker positions
    When EOD reconciliation runs
    Then a CRIT alert is sent
    And affected strategies are halted
    And the next trading session cannot submit orders until manually resolved
```

## 3. BDD 分層對照

| 層 | Feature 檔 | 主要 Given |
| :--- | :--- | :--- |
| Data | `data_bundle.feature` | source data、calendar、DQ rules |
| Research | `research_validation.feature` | bundle、RunConfig、strategy definition |
| Governance | `governance_release.feature` | report pack、approval、package |
| Strategy/Portfolio | `target_position.feature` | approved package、market state、cash |
| Risk | `pre_trade_risk.feature` | order intent、risk config、positions |
| Execution | `personal_execution.feature` | risk decision、broker adapter |
| Monitoring | `operations.feature` | fills、jobs、alerts |

## 4. 最佳實踐

- 每個 Scenario 只能測一個行為。
- 所有 negative path 都要覆蓋：缺資料、未核准、超限、對帳失敗、重複 fill。
- BDD 是需求契約，不綁定特定 UI 或 Python class。

