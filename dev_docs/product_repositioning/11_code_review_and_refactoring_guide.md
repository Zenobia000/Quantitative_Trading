# 程式碼審查與重構指南 - 個人級 EOD 量化交易平台

> 版本: v1.0 | 日期: 2026-07-05 | 狀態: Golden baseline

## 1. 審查前檢查

- PR 是否標明 SAD 層級。
- 是否更新對應文件與 ADR。
- 是否新增或更新 contract/schema。
- 是否有 negative path 測試。
- 是否通過 architecture fitness functions。
- AI 撰寫的策略是否通過 conformance gate、sweep/DOE trials 是否誠實計入 trials counter。

## 2. 高風險審查點

| 類別 | 檢查 |
| :--- | :--- |
| Research 邊界 | 不可 import broker/execution |
| Risk | fail closed，不可 fail open |
| Execution | order/fill idempotency |
| Data | bundle lineage、DQ gate |
| Security | secrets 不進 log/git |
| Observability | trace_id、strategy_id、package_id |
| AI 撰寫 harness | agent 只碰 research；execution off-limits；trials 誠實；跨 governance 閘門須人核准（ADR-009） |

## 3. 重構時機

- 跨層依賴開始出現。
- Strategy / Portfolio / Risk 邏輯混在同一 class。
- Broker SDK 細節滲入 application/domain。
- 同一 risk rule 在多處重複。
- 文件與程式碼 contract 不一致。

## 4. PR 模板

```markdown
## 摘要

## SAD 層級
- [ ] Data
- [ ] Research
- [ ] Governance
- [ ] Strategy/Portfolio
- [ ] Risk
- [ ] Execution
- [ ] Monitoring
- [ ] Foundation

## 契約變更
- [ ] API
- [ ] Event
- [ ] DB schema
- [ ] 無

## 測試
- [ ] Unit
- [ ] Contract
- [ ] Integration
- [ ] BDD
- [ ] Architecture fitness

## 風險與回滾
```

## 5. 合併 Gate

- High severity finding = 不可合併。
- Medium severity finding 必須有修復或 ADR waiver。
- 交易相關 PR 必須有 reviewer 確認 risk/fill/reconciliation。

