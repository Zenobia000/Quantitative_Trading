# 測試策略 — backtest_platform

> **版本：** v1.0 | **更新：** 2026-05-31
> **適用 M**：全 milestone 測試規範
> **進度**：見 [`16_wbs_development_plan.md §9`](./16_wbs_development_plan.md)（單一狀態真相源）
> **適用範圍：** 全 milestone 測試規範
> **關聯文件：** `03_behavior_driven_development_guide.md`、`13_security_and_readiness_checklists.md`、`.claude/rules/testing.md`

---

## 1. 測試金字塔

### 1.1 比例與工具

```
           ┌──────────────────┐
           │   E2E  (10%)     │  pytest + zipline run + docker
           │  ~30 個 scenario │  smoke test per mode
           ├──────────────────┤
           │ Integration (20%)│  pytest + docker-compose
           │  ~80 個 test     │  DB / API sandbox / 對拍
           ├──────────────────┤
           │   Unit  (70%)    │  pytest + hypothesis
           │  ~280 個 test    │  pure functions / adapters
           └──────────────────┘
```

| 層 | 比例 | 工具 | 跑時 | 失敗影響 |
| :--- | :---: | :--- | :--- | :--- |
| **Unit** | 70% | pytest, hypothesis, freezegun | < 30s | block PR |
| **Integration** | 20% | pytest + docker-compose（DB/Sandbox） | < 5min | block PR |
| **E2E** | 10% | pytest -m e2e + zipline run + docker | < 30min | block release |
| **對拍 (Reconciliation)** | 跨層 | pytest -m recon | < 10min | block milestone |
| **Performance** | 跨層 | pytest -m slow + pytest-benchmark | < 2h | warn only |

### 1.2 目錄結構

```
backtest_platform/tests/
├── unit/                          # 70%
│   ├── strategy/                  # M1 既有 36 個
│   ├── adapters/
│   ├── validation/
│   └── monitoring/
├── integration/                   # 20%
│   ├── test_bundle_ingest.py
│   ├── test_shioaji_sandbox.py
│   ├── test_streamlit_db.py
│   └── conftest.py                # docker-compose fixture
├── recon/                         # 對拍
│   ├── test_zipline_vs_vectorbt.py
│   ├── test_vectorbt_vs_m1.py
│   ├── test_finlab_vs_finmind.py
│   ├── test_pbo_vs_pypbo.py
│   └── test_event_vs_vector_paper.py
├── e2e/                           # 10%
│   ├── test_backtest_smoke.py
│   ├── test_paper_smoke.py
│   └── test_live_smoke.py
├── performance/                   # warn-only
│   ├── test_100stocks_10years.py
│   └── test_grid_1000trials.py
├── regression/                    # M1 baseline
│   └── test_2330_matches_m1.py
└── fixtures/
    ├── finlab_2330_2024.parquet
    ├── finmind_2330_2024.parquet
    └── bailey_paper_pbo_data.csv
```

### 1.3 標記策略

```python
# pyproject.toml [tool.pytest.ini_options]
markers = [
    "unit: pure unit tests, no IO",
    "integration: requires docker services",
    "e2e: end-to-end smoke tests",
    "recon: cross-engine reconciliation",
    "slow: > 5 minutes",
    "live: requires real Shioaji credentials (manual only)",
]
```

執行範例：
```bash
pytest -m unit                          # PR check
pytest -m "integration and not slow"    # nightly
pytest -m recon                         # milestone gate
pytest -m e2e                           # release gate
```

---

## 2. 單元測試規範

### 2.1 Strategy 純函式（M1 既有 36 個 — 必須持續綠）

| 模組 | 既有測試 | 新增（M2-5） |
| :--- | :--- | :--- |
| `strategy/indicators.py` | RSI/KD/MACD/box 共 12 個 | — |
| `strategy/scoring.py` | 四層計分邊界值 14 個 | M3 補 quantile/IC test |
| `strategy/signals.py` | 7 訊號優先序 10 個 | M3 補 hook 整合 |

**鐵律**：搬到 `strategies/four_layer_resonance/` 後測試 import path 更新即可，**0 邏輯變動**。

### 2.1.1 M2 Mainframe 模組測試（Stream D Wave 2 2026-06-02）

| 模組 | 新增測試檔 | 覆蓋率 | 重點 |
| :--- | :--- | :--- | :--- |
| `engines/zipline_adapter/algorithms/four_layer_resonance.py` | `tests/engines/zipline_adapter/algorithms/test_four_layer_resonance.py`（29 個）| 0% → 97% | initialize / evaluate_and_trade 用 mock zipline.api，evaluate_bar wrapper, _execute_action priority, _portfolio_state / _current_weight |
| `engines/zipline_adapter/cli.py` | `tests/engines/zipline_adapter/test_cli.py`（18 個）| 0% → 95% | _ensure_bundle_registered、_resolve_zipline_root（explicit>env>default）、_format_perf_summary 邊界（empty/1bar/zero-std）、_maybe_write_tearsheet ImportError 退化、_maybe_notify_discord token 缺/錯誤吞噬、Click `backtest-run` / `list-bundles` 整合 |
| `pipeline.py` | `tests/test_pipeline.py`（10 個）| 0% → 100% | run_pipeline mock fetch/score/signal 三組依賴、signal_calendar 欄位切片、summary_stats 空 vs 有資料、run_cmd Click 寫 CSV 與 console |
| `data/schemas.py` | `tests/data/test_schemas.py`（16 個）| 已 98% → 維持 | Pydantic ValidationError 邊界（empty stock_id、price ≤ 0、volume 負、adj_factor 0）、ETLBundle.merged() NaN 補零、排序 |
| `data/finmind_etl.py` | `tests/data/test_finmind_etl.py`（既有 4 + 新增 11） | 75% → 98% | 空 loader、dividend fetch 失敗吞噬、apply_adjustment=False short-circuit、`_normalize_*` empty 路徑、`_build_loader` token / no-token、CLI dry-run + parquet 路徑 |

**整體覆蓋率**：Stream D Wave 1 baseline 66% → Wave 2 後 **93.74%**（pyproject.toml `--cov-fail-under` 80）。

### 2.2 Adapter 單元測試（M2+）

每個 adapter 必須：

| 測試類型 | 範例 |
| :--- | :--- |
| Happy path | `test_finlab_bundle_ingest_2024()` 拉 fixture，驗證 bcolz 結構 |
| ACL 邊界 | `test_finmind_normalize_handles_missing_volume()` raw schema 缺欄位 |
| Retry | `test_finlab_429_retries_with_backoff()` mock 連 3 次 429 後成功 |
| Schema 驗證 | `test_shioaji_fill_rejects_invalid_status()` Pydantic ValidationError |

```python
# tests/unit/adapters/test_finlab_bundle.py
import pytest
from unittest.mock import patch

@pytest.fixture
def fake_finlab_response():
    return pd.read_parquet("tests/fixtures/finlab_2330_2024.parquet")

def test_finlab_bundle_normalizes_to_long_table(fake_finlab_response):
    with patch("finlab.data.get", return_value=fake_finlab_response):
        result = normalize_finlab_to_long(fake_finlab_response, ["2330"])
    assert list(result.columns) == ["stock_id", "trade_date", "open", "high", "low", "close", "volume"]
    assert result["stock_id"].nunique() == 1
```

### 2.3 Validator 數學正確性（M3）

對 Bailey-López de Prado 論文範例做 unit test：

| 函式 | 參考來源 | 容忍 |
| :--- | :--- | :--- |
| `pbo.compute_pbo()` | Bailey et al. (2017) Table 5.2 | < 1e-4 |
| `dsr.compute_dsr()` | Bailey & López de Prado (2014) Eq. 9 範例 | < 1e-4 |
| `wfa.walk_forward_split()` | López de Prado (2018) Ch.7.4 | 索引精確匹配 |

```python
# tests/unit/validation/test_pbo.py
def test_pbo_matches_bailey_paper_table_5_2():
    M = pd.read_csv("tests/fixtures/bailey_paper_pbo_data.csv")
    pbo = compute_pbo(M, n_partitions=16)
    assert abs(pbo - 0.227) < 1e-4  # 論文公告值
```

### 2.4 Hypothesis property-based test

對複雜計算（如 portfolio heat、signal priority）用 property test：

```python
from hypothesis import given, strategies as st

@given(
    positions=st.lists(st.tuples(st.floats(0, 1e6), st.floats(0.01, 0.1)), min_size=1, max_size=15),
    equity=st.floats(1e5, 1e8),
)
def test_portfolio_heat_invariants(positions, equity):
    heat = compute_heat(positions, equity)
    assert 0 <= heat
    assert heat == sum(qty * stop_pct for qty, stop_pct in positions) / equity
```

---

## 3. 整合測試規範

### 3.1 Bundle ingester ↔ Zipline

```python
# tests/integration/test_bundle_ingest.py
@pytest.mark.integration
def test_finlab_bundle_zipline_can_read(tmp_zipline_root):
    # 1. ingest 小型 fixture（10 檔 1 年）
    register_finlab_bundle(source="fixture")
    run_zipline_ingest("finlab", start="2024-01-01", end="2024-12-31")
    # 2. zipline run hello world
    result = subprocess.run(
        ["zipline", "run", "-f", "tests/fixtures/hello_algo.py", "-b", "finlab",
         "--start", "2024-06-01", "--end", "2024-06-30"],
        capture_output=True, env={"ZIPLINE_ROOT": str(tmp_zipline_root)},
    )
    assert result.returncode == 0
    assert b"end of run" in result.stdout
```

### 3.1.b TimescaleDB schema 防漂移（unit test, no DB needed）

`tests/data/test_init_sql_schema.py` 是 fast 路徑：純 regex 解析 `docker/timescaledb/init.sql`，斷言 §4 13 張表 / hypertable / GIN index / UUID PK / UNIQUE constraint / retention policy 都齊。任何 DDL 與 21 §4 spec 漂移會立刻紅燈。

| 屬性 | 值 |
| :--- | :--- |
| 標記 | 無（純 unit，每次 CI 跑） |
| 耗時 | < 1s |
| 依賴 | 無（不啟 Docker / 不連 DB） |
| 補強 | `test_real_upsert_idempotent`（integration marker）跑真實 round-trip |

### 3.2 Broker ↔ Sandbox

```python
# tests/integration/test_shioaji_sandbox.py
@pytest.mark.integration
@pytest.mark.skipif(not os.getenv("SHIOAJI_SANDBOX_TOKEN"), reason="needs sandbox creds")
def test_shioaji_sandbox_place_order():
    broker = ShioajiBroker(env="sandbox")
    broker.connect()
    order = broker.submit(stock_id="2330", side="Buy", qty=1000, order_type="MOC")
    assert order.status in {"SUBMITTED", "FILLED"}
    broker.disconnect()
```

### 3.3 Streamlit ↔ TimescaleDB

```python
# tests/integration/test_streamlit_db.py
@pytest.mark.integration
def test_streamlit_equity_panel_renders_under_2s(seeded_tsdb):
    from dashboard.streamlit_app import load_equity
    start = time.monotonic()
    df = load_equity("four_layer_resonance", date(2024,1,1), date(2024,12,31))
    elapsed = time.monotonic() - start
    assert len(df) > 0
    assert elapsed < 2.0
```

### 3.4 conftest fixture

```python
# tests/integration/conftest.py
@pytest.fixture(scope="session")
def docker_compose_services():
    subprocess.run(["docker-compose", "-f", "docker-compose.test.yml", "up", "-d"], check=True)
    wait_for_health("timescaledb", port=5433)
    yield
    subprocess.run(["docker-compose", "-f", "docker-compose.test.yml", "down", "-v"])

@pytest.fixture
def seeded_tsdb(docker_compose_services):
    conn = psycopg2.connect(host="localhost", port=5433, ...)
    with conn, open("tests/fixtures/seed.sql") as f:
        cur.execute(f.read())
    yield conn
```

---

## 4. 對拍測試（核心）

### 4.1 對拍矩陣

| Recon ID | 對拍 A | 對拍 B | 範圍 | 容忍 | 啟用 |
| :--- | :--- | :--- | :--- | :--- | :---: |
| **R-001** | Zipline | vectorbt | 同 IS 期間 portfolio equity | < 0.5% | M3 |
| **R-002** | VectorBtEngine | M1 `pipeline.py` | 2330 單檔 calendar action | < 0.1% | M2 |
| **R-003** | FinLab | FinMind | 同股 OHLCV | < 1% | M2 |
| **R-004** | 自寫 PBO | pypbo（read-only ref） | Bailey 論文範例 | < 1e-4 | M3 |
| **R-005** | EventDriven (Zipline) | Vectorized (vectorbt) | 30 天 paper 期間 equity | < 0.5% | M4 |
| **R-006** | Backtest equity | Paper equity（同 strategy） | 同期 daily return | < 0.3%/day | M4 |
| **R-007** | Paper position | Live position（M5 切換時） | reconciliation | 精確 | M5 |

### 4.2 R-002 詳例（M2 必過）

```python
# tests/recon/test_vectorbt_vs_m1.py
@pytest.mark.recon
def test_vectorbt_engine_matches_m1_pipeline_for_2330():
    # M1 baseline
    from backtest_platform.pipeline import run_for_stock
    m1_result = run_for_stock("2330", "2023-01-01", "2024-12-31")
    m1_actions = m1_result.calendar_df["action"]

    # M2 new engine
    from backtest_platform.engines.vectorbt_adapter import VectorBtEngine
    vbt_result = VectorBtEngine().run("2330", "2023-01-01", "2024-12-31")
    vbt_actions = vbt_result.actions

    # action sequence must match exactly
    diff_ratio = (m1_actions != vbt_actions).mean()
    assert diff_ratio < 0.001, f"action mismatch {diff_ratio:.4%}"
```

### 4.3 R-001 詳例（M3 必過）

```python
# tests/recon/test_zipline_vs_vectorbt.py
@pytest.mark.recon
@pytest.mark.slow
def test_zipline_equity_matches_vectorbt_within_0_5_percent():
    period = ("2020-01-01", "2024-12-31")
    universe = ["2330", "2454", "2317", "3008", "0050"]

    zl_equity = run_zipline_backtest(universe, period).equity_curve
    vbt_equity = run_vectorbt_backtest(universe, period).equity_curve

    aligned_zl, aligned_vbt = align_index(zl_equity, vbt_equity)
    relative_diff = ((aligned_zl - aligned_vbt) / aligned_vbt).abs()
    assert relative_diff.max() < 0.005, f"max diff {relative_diff.max():.4%}"
```

### 4.4 對拍失敗的優先處理順序

1. **檢查日期對齊**：trading day vs calendar day 差異
2. **檢查手續費假設**：fixed bps vs tiered
3. **檢查滑點模型**：vectorbt 預設 0 vs Zipline `VolumeShareSlippage`
4. **檢查訂單時序**：next-bar open vs same-bar close
5. **檢查復權**：bundle 已調整 vs vectorbt 手動 adjust

---

## 5. E2E 測試

### 5.1 三模式各自 smoke

```python
# tests/e2e/test_backtest_smoke.py
@pytest.mark.e2e
def test_backtest_mode_end_to_end(docker_compose_services):
    """從 zipline run 到 Streamlit 顯示 equity curve"""
    # 1. ingest
    subprocess.run(["zipline", "ingest", "-b", "finlab",
                    "--start", "2024-01-01", "--end", "2024-12-31"], check=True)
    # 2. backtest
    subprocess.run(["zipline", "run", "-b", "finlab",
                    "--algo-namespace", "strategies.four_layer_resonance",
                    "--start", "2024-01-01", "--end", "2024-12-31",
                    "--output", "/tmp/result.pkl"], check=True)
    # 3. metrics emit 到 DB（透過 algo analyze hook）
    assert query_db("SELECT COUNT(*) FROM equity_snapshots WHERE run_id = ?", [run_id]) > 0
    # 4. Streamlit 可讀
    response = httpx.get("http://localhost:8501/?strategy=four_layer_resonance")
    assert response.status_code == 200
```

### 5.2 三模式 E2E 對照

| 模式 | E2E 步驟 | 預期 |
| :--- | :--- | :--- |
| **Backtest** | ingest → run → DB write → Streamlit render | equity_snapshots 有資料、頁面 < 2s |
| **Paper** | live_feed 啟動 → algo 觸發 → PaperBroker 模擬 fill → fills 表寫入 → Discord digest | fill 表有當日 5+ 筆、digest 14:35 收到 |
| **Live** | 連 Shioaji sandbox → algo 觸發 → ShioajiBroker submit → 收到 fill → reconciliation pass | Shioaji `list_positions()` == DB `positions` |

---

## 6. 性能測試

### 6.1 目標

| 場景 | 目標 | 工具 |
| :--- | :--- | :--- |
| 100 檔 × 10 年 backtest | < 30 分鐘 | pytest-benchmark |
| 1000 trials grid search (vectorbt) | < 2 小時 | pytest -m slow |
| Streamlit 首頁載入 | < 2 秒 | locust |
| Discord alert 端到端延遲 | < 5 秒 | manual stopwatch |
| TimescaleDB query `equity_snapshots` 1 年 | < 200ms | EXPLAIN ANALYZE |

### 6.2 範例

```python
# tests/performance/test_100stocks_10years.py
@pytest.mark.slow
def test_100_stocks_10_years_backtest_under_30min(benchmark):
    universe = load_top_100_universe()
    result = benchmark.pedantic(
        lambda: run_zipline_backtest(universe, "2015-01-01", "2024-12-31"),
        rounds=1, iterations=1,
    )
    assert benchmark.stats["mean"] < 1800  # 30min in seconds
```

---

## 7. 覆蓋率門檻

### 7.1 整體 vs critical path

| 範圍 | 門檻 | 工具 |
| :--- | :---: | :--- |
| 全 repo | 80% | `pytest --cov --cov-fail-under=80` |
| `strategies/` | 95% | `pytest --cov=strategies --cov-fail-under=95` |
| `adapters/brokers/` | 95% | 同上 |
| `validation/` | 90% | 同上 |
| `monitoring/alerter.py` | 90% | 同上 |
| `dashboard/` | 50%（UI 寬鬆） | 同上 |

### 7.2 排除清單與 gate 設定

實際 `pyproject.toml`（Stream D Wave 1 baseline，2026-06-02）：

```toml
[tool.pytest.ini_options]
addopts = "-ra --strict-markers --cov=backtest_platform --cov-report=term-missing --cov-fail-under=65"

[tool.coverage.run]
source = ["src/backtest_platform"]
branch = true
omit = [
    # Skeleton modules with no production code (per Q4 workflow decision)
    "src/backtest_platform/adapters/__init__.py",
    "src/backtest_platform/adapters/*/__init__.py",
    "src/backtest_platform/dashboard/__init__.py",
    "src/backtest_platform/orchestration/__init__.py",
    "src/backtest_platform/strategies/__init__.py",
    # Validation harnesses (covered by integration tests, not unit)
    "src/backtest_platform/engines/zipline_adapter/validation/*",
]

[tool.coverage.report]
show_missing = true
skip_covered = false
exclude_lines = [
    "pragma: no cover",
    "raise NotImplementedError",
    "if TYPE_CHECKING:",
    "if __name__ == .__main__.:",
    "\\.\\.\\.$",
]
```

**Gate ratchet 計畫**：

| 階段 | fail_under | 觸發條件 |
|:--|:--:|:--|
| Wave 1 baseline | 65 | adjustment.py 100% 後總覆蓋 ~68% |
| Wave 2 中段 | 75 | Stream A FinMind bundle 補測 + Stream D TEST-002/003/005 |
| Wave 2 結尾 | 80 | Stream D 全 TEST-* 完成（algorithms / cli / pipeline 從 0% 補滿） |

---

## 8. CI/CD 設計

### 8.1 GitHub Actions YAML 草案

```yaml
# .github/workflows/ci.yml
name: CI

on: [push, pull_request]

jobs:
  unit-test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: { python-version: '3.10' }
      - run: pip install -e ".[dev]"
      - run: ruff check src/ tests/
      - run: mypy --strict src/
      - run: pytest -m unit --cov=src --cov-fail-under=80

  integration-test:
    runs-on: ubuntu-latest
    needs: unit-test
    services:
      timescaledb:
        image: timescale/timescaledb:2.14.2-pg16
        env: { POSTGRES_PASSWORD: test_pw }
        ports: ['5433:5432']
        options: >-
          --health-cmd "pg_isready -U postgres"
          --health-interval 10s
    steps:
      - uses: actions/checkout@v4
      - run: pip install -e ".[dev]"
      - run: pytest -m "integration and not slow" --maxfail=3

  recon-test:
    runs-on: ubuntu-latest
    needs: integration-test
    if: github.event_name == 'pull_request' && contains(github.event.pull_request.labels.*.name, 'milestone-gate')
    steps:
      - uses: actions/checkout@v4
      - run: pip install -e ".[dev]"
      - run: pytest -m recon
```

### 8.2 Pre-commit hooks

```yaml
# .pre-commit-config.yaml
repos:
  - repo: https://github.com/astral-sh/ruff-pre-commit
    rev: v0.4.0
    hooks:
      - id: ruff
        args: [--fix]
      - id: ruff-format
  - repo: https://github.com/pre-commit/mirrors-mypy
    rev: v1.10.0
    hooks:
      - id: mypy
        args: [--strict, src/]
  - repo: local
    hooks:
      - id: pytest-unit
        name: pytest unit tests
        entry: pytest -m unit --maxfail=1
        language: system
        pass_filenames: false
```

### 8.3 觸發矩陣

| 觸發 | unit | integration | recon | e2e | performance |
| :--- | :---: | :---: | :---: | :---: | :---: |
| `git push` (feature branch) | ✅ | — | — | — | — |
| Pull Request (any) | ✅ | ✅ | — | — | — |
| PR labeled `milestone-gate` | ✅ | ✅ | ✅ | — | — |
| Push to `main` | ✅ | ✅ | ✅ | ✅ | — |
| Nightly schedule | ✅ | ✅ | ✅ | ✅ | ✅ |

---

## 9. 回歸測試 — M1 baseline 凍結

### 9.1 baseline 策略

M1 已交付 `pipeline.py` 對 2330 跑出的 calendar CSV 視為 **golden output**，凍結到 `tests/fixtures/golden/`：

```
tests/fixtures/golden/
├── 2330_2023-2024_calendar.csv      # M1 pipeline.py output
├── 2454_2023-2024_calendar.csv
└── 0050_2023-2024_calendar.csv
```

### 9.2 回歸測試

```python
# tests/regression/test_2330_matches_m1.py
def test_m1_pipeline_2330_unchanged():
    """禁止改動 M1 既有純函式邏輯。任何改動須先更新 golden，並在 PR 註明 reason"""
    result = run_for_stock("2330", "2023-01-01", "2024-12-31")
    golden = pd.read_csv("tests/fixtures/golden/2330_2023-2024_calendar.csv")
    pd.testing.assert_frame_equal(result.calendar_df, golden, check_exact=False, atol=1e-6)
```

### 9.3 更新 golden 的流程

1. 在 PR description 解釋為何要動 M1 邏輯
2. `python scripts/update_golden.py` 重新生成
3. 截圖新舊 diff 貼到 PR
4. 需 reviewer 明確 approve

---

## 10. Sprint 0 spike 測試（強制 gate）

對應 plan §8，每個 spike 對應一個 test：

| Spike | Test 檔 | Pass 標準 |
| :--- | :--- | :--- |
| S1 zipline-reloaded（原 TQuant-Lab）| `tests/spike/test_s1_zipline_xtai.py` | `zipline ingest -b finmind` + `zipline run` 回傳 0（ADR-013 改 bundle，原 `tquant` bundle 不再使用）|
| S2 M1 plug | `tests/spike/test_s2_m1_in_zipline.py` | 2330 1 年 action sequence 與 M1 pipeline 一致 |
| S3 FinLab bundle | `tests/spike/test_s3_finlab_bundle.py` | 10 檔 1 年 ingest + zipline run 不 raise |
| S4 Shioaji sandbox | `tests/spike/test_s4_shioaji.py` | 模擬下一筆 MOC 單成功 |
| S5 FinLab live | `tests/spike/test_s5_finlab_live.py` | 拉 1 檔 1 分鐘 quote 寫入 DB |
| S6 Streamlit DB | `tests/spike/test_s6_streamlit.py` | 開頁 < 2 秒 + equity curve 顯示 |

**任一 spike 失敗 → Sprint 0 fail → 退回 Plan B（自寫 adapter）**

---

## 11. 測試失敗排除流程

對應 `.claude/rules/testing.md`：

1. **載入 sunnydata-testing skill**
2. **檢查測試隔離**：是否有 shared state 殘留
3. **驗證 mock 正確性**：是否 mock 過多以致無實際測試
4. **修實作而非測試**（除非測試本身有誤）
5. **若多次 flaky** → 標 `@pytest.mark.flaky(reruns=3)` 並開 issue 追蹤

---

## 12. 驗收 Checklist（per milestone）

### Sprint 0

- [ ] 6 spike test 全綠
- [ ] M1 既有 36 個 unit test 全綠
- [ ] CI pipeline 跑通

### M2

- [ ] R-002 對拍 < 0.1%
- [ ] R-003 對拍 < 1%
- [ ] backtest E2E smoke 綠
- [ ] 性能：100 檔 10 年 < 30 分鐘
- [ ] 覆蓋率 ≥ 80%

### M3

- [ ] R-001 對拍 < 0.5%
- [ ] R-004 對拍 < 1e-4
- [ ] validation 模組覆蓋率 ≥ 90%
- [ ] grid 1000 trials < 2 小時

### M4

- [ ] R-005 對拍 < 0.5%
- [ ] R-006 對拍 < 0.3%/day
- [ ] paper E2E 連跑 3 個月無失敗
- [ ] Discord alert 端到端 < 5 秒

### M5

- [ ] R-007 對拍精確
- [ ] live E2E smoke 綠（sandbox）
- [ ] 熔斷規則手動模擬通過

---

## 13. 變更紀錄

| 版本 | 日期 | 變更 |
| :--- | :--- | :--- |
| v1.0 | 2026-05-31 | 初版（對應 plan §7/§8/§11；對拍矩陣 7 條） |
