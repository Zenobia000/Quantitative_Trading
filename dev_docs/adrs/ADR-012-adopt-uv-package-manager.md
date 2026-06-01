# ADR-012: 採用 uv 為 Python 套件管理器（取代 poetry）

> **狀態：** 已接受 | **日期：** 2026-06-01 | **決策者：** Self
> **追溯實作：** 同 commit（poetry → uv 全檔替換）
> **關聯：** ADR-005~011 文件中對 poetry 指令的引用

---

## 1. 背景與問題

- **上下文**：Sprint 0 scaffolding (commit `a8c7a00`) 與後續所有文檔均使用 `poetry install` / `poetry run` 指令。使用者改採 uv 為 Python 套件管理工具。
- **問題**：13 個檔（8 spike 腳本 + RUNBOOK + README + 5 文檔）的 poetry 指令需替換；需明確紀錄為何切換 + 對應指令對照表，避免未來再改回。
- **驅動因素 / 約束**：
  - `pyproject.toml` 為 PEP 621 標準格式（用 setuptools build backend），與 uv / poetry / pip 皆相容 — 不用改
  - 使用者已有 uv 安裝、無 poetry 偏好
  - Sprint 0 spike 尚未跑（無 `poetry.lock` 已產出，零遷移成本）

---

## 2. 考量的選項

### 選項一：維持 poetry

- **描述**：不改，繼續用 poetry
- **優點**：0 改動；poetry 是業界長期主流
- **缺點**：使用者明確要求改 uv；poetry 較慢、虛擬環境管理較重
- **成本/複雜度**：0

### 選項二：採用 uv（採納）

- **描述**：13 檔的 poetry 指令替換為 uv；pyproject.toml 不變（已 PEP 621）
- **優點**：
  - uv 安裝/解析快 10-100×（Rust 實作）
  - `uv run` 無需 `shell` 啟動 venv，每次自動處理
  - PEP 621 標準格式相容，無 lock 格式特殊性
  - 使用者偏好
- **缺點**：
  - uv 較新（2024 首版），生態系穩定度低於 poetry
  - 部分 IDE 整合可能不如 poetry 成熟
- **成本/複雜度**：低（純指令替換 + 13 檔 + 1 ADR）

### 選項三：併用 pip-tools / Hatch / pdm

- **描述**：用其他標準 PEP 621 工具
- **優點**：更多選項
- **缺點**：使用者沒提；無理由捨棄已選 uv
- **成本/複雜度**：—

---

## 3. 決策

**選擇：選項二（採用 uv）**

**理由**：
- 使用者明確要求
- pyproject.toml 已是 PEP 621，無 build-backend 重寫成本
- Sprint 0 尚未產出 lock file，現在切是最佳時機
- uv 與 poetry 在「dev 體驗」上的差距在 Rust 速度優勢下顯著

---

## 4. 後果

### 正面

- 依賴解析快 10-100×（heavy deps 如 TA-Lib、zipline-tej、vectorbt 安裝更順）
- `uv run X` 取代 `poetry shell + python X` — 流程更直接
- `uv.lock` 為原生 lock，格式穩定
- 與 PEP 621 標準相容，未來換工具阻力低

### 負面

- uv 較新，遇 edge case 時社群解答可能少於 poetry
- 部分 CI/IDE 整合可能需手動配置（M2-M3 才會觸發）

### 影響範圍

- **指令層**：所有 `poetry install --extras X` → `uv sync --extra X`；`poetry run Y` → `uv run Y`
- **檔案**：13 檔（已替換完畢，見執行計畫）
- **lock file**：M2 Sprint 1 初次 `uv sync` 後 commit `uv.lock`
- **CI/CD（M3+）**：GitHub Actions 用 `astral-sh/setup-uv@v3` action 取代 poetry setup
- **使用者文檔**：README、RUNBOOK、brief HTML 均同步

### 重新評估觸發

- uv 重大 breaking change（例如 lock 格式重大版號跳）
- 團隊增員，新人偏好 poetry/pdm
- 與某關鍵套件相容性問題（如 vectorbt 強制要求 poetry）

---

## 5. 執行計畫

實作於同 commit 完成：

1. ✅ 確認 `pyproject.toml` 為 PEP 621 標準（已 setuptools build backend，無需改）
2. ✅ 替換 8 個 spike 腳本內的 poetry 引用（RUNBOOK + s1/s3/s6_*/gate_review + __init__）
3. ✅ 替換 `backtest_platform/README.md` 安裝指令
4. ✅ 替換 5 個 dev_docs 引用（09、13、15、16、brief/03、brief/06）
5. ✅ 寫本 ADR-012
6. ⏳ Sprint 0 第一次 `uv sync --extra sprint0` 後 commit `uv.lock`（M2 啟動時做）

---

## 6. 指令對照表（給未來使用者）

| poetry | uv | 備註 |
|:--|:--|:--|
| `poetry install` | `uv sync` | 依預設依賴 |
| `poetry install --extras sprint0` | `uv sync --extra sprint0` | uv 用 `--extra`（單數）|
| `poetry install --extras "a b c"` | `uv sync --extra a --extra b --extra c` | uv 重複 flag |
| `poetry install --all-extras` | `uv sync --all-extras` | — |
| `poetry run python xxx.py` | `uv run python xxx.py` | 自動進 venv |
| `poetry run pytest` | `uv run pytest` | — |
| `poetry shell` | `uv venv && source .venv/bin/activate` | 或不需要，直接 `uv run` |
| `poetry add X` | `uv add X` | 寫入 pyproject.toml |
| `poetry add --dev X` | `uv add --dev X` | — |
| `poetry remove X` | `uv remove X` | — |
| `poetry update` | `uv sync --upgrade` | — |
| `poetry show --outdated` | `uv pip list --outdated` | — |
| `poetry lock` | `uv lock` | 產出 lock 不安裝 |
| `poetry.lock` | `uv.lock` | 格式不同，需 commit |
| `poetry version` | `uv version`（無對應，看 pyproject.toml）| — |

---

| 日期 | 審核人 | 備註 |
| :--- | :--- | :--- |
| 2026-06-01 | Self | 初版；同 commit 已完成 13 檔替換 |
