# ADR-R03: Execution/Risk/Monitoring 與 research package 物理分離 + import fitness functions

> 狀態: Accepted | 日期: 2026-07-05 | 決策者: refactor 任務

## 背景

`backtest_platform` package 內藏一整套 forward/live paper-trading 執行棧：`orchestration/`（scheduler、collaborators、after_close）、`runtime/`（paper_daemon、market_reader）、`adapters/brokers/paper_broker`、`risk/`、`monitoring/`。其中 **`orchestration/collaborators.py` + `after_close.py` 經 `paper_broker.submit_order` 在 research package 內實際下單**，`runtime/market_reader.py` 把 live broker 餵進 config——直接違反 golden 中央 Anti-Decision「Research 不直連 Broker」。

## 決策

1. **立即**（W1.1）用 import-linter 契約禁止 `research`/`strategies`/`validation` import `adapters.brokers`、`risk`、`orchestration`、`runtime`、`monitoring`；`domain` 禁 import `sqlalchemy`/`fastapi`/`shioaji`/`requests`。接入 CI 作為 architecture test，把邊界**現在**鎖住（這些規則今日已綠）。
2. **後續**（M3–M5，W5.x）將這些叢集物理搬到 `services/{strategy_runtime,execution_gateway,risk_gate,monitoring_ops}`；`runtime/market_reader.py` 於 runtime 拆分後刪除。
3. `orchestration/{after_close,collaborators}.py` 為 **relocate 非 delete**（撐著 systemd after-close daemon），搬到 strategy_runtime/execution，經 governance port 呼叫 watch-gate。

## 理由

fitness function 先鎖邊界，讓後續物理搬移在**綠色 wall** 之後進行，不會回頭再犯。先鎖後搬，把「理論正確」變成「CI 可驗」。

## 後果

- 任何未來 PR 若讓 research 重新 import broker/execution，CI 直接 RED。
- 物理搬移分波、一 service 一 PR，破壞性移動前打 backup tag，daemon 端到端驗證後才刪舊路徑。
- 具體違規清單見 [18_refactor_wbs §5](../18_refactor_wbs.md)。
