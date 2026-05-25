"""
FinMind POC — 驗證資料源是否能支撐四層共振戰法的 IC 測試

目的：
    在花錢買 TEJ 之前，先用 FinMind 免費版測一遍：
    - 四層共振戰法需要的所有資料欄位是否齊全
    - 下市股資料的覆蓋度
    - 券商分點是否可取得（最關鍵）

執行：
    pip install FinMind pandas
    python finmind_poc.py

依賴：
    - Python 3.10+
    - FinMind (https://finmind.github.io)
    - pandas

退出碼：
    0  全部資料就位
    1  基礎資料可用，但關鍵資料缺失（需 sponsor 或上 TEJ）
    2  基礎資料就有問題（檢查 token / 網路）

參考：
    - strategy/v2.md Part 2.3 四層計分系統
    - strategy/research/v2.2_ic_test_plan.md 第一階段資料準備
"""

from __future__ import annotations

import sys
import traceback
from dataclasses import dataclass, field
from typing import Callable, Optional

import pandas as pd

try:
    from FinMind.data import DataLoader
except ImportError:
    print("ERROR: FinMind 未安裝。執行：pip install FinMind")
    sys.exit(2)


# =====================================================
# 設定 — 改這裡即可調整測試範圍
# =====================================================

TEST_STOCK = "2330"          # 台積電：流動性與資料覆蓋最完整
START_DATE = "2024-01-01"
END_DATE = "2024-12-31"

# FinMind 免費註冊 token（部分 API 需要）
# 註冊：https://finmindtrade.com/analysis/#/account/login
# 若為空字串，僅測試 public endpoints
TOKEN = ""


# =====================================================
# 工具函式
# =====================================================

@dataclass
class TestResult:
    name: str
    description: str
    criticality: str  # "P0", "P1", "P2"
    ok: bool = False
    rows: int = 0
    columns: list = field(default_factory=list)
    error: Optional[str] = None
    sample: Optional[pd.DataFrame] = None


def run_test(
    name: str,
    description: str,
    criticality: str,
    fetcher: Callable[[], pd.DataFrame],
) -> TestResult:
    """執行一個 API 測試，捕捉所有例外。"""
    result = TestResult(name=name, description=description, criticality=criticality)
    try:
        df = fetcher()
        if df is None or len(df) == 0:
            result.error = "Empty response"
            return result
        result.ok = True
        result.rows = len(df)
        result.columns = list(df.columns)
        result.sample = df.head(3)
    except Exception as e:
        result.error = f"{type(e).__name__}: {str(e)[:120]}"
        if "--verbose" in sys.argv:
            traceback.print_exc()
    return result


def print_result(r: TestResult) -> None:
    status = "OK  " if r.ok else "FAIL"
    print(f"[{status}] [{r.criticality}] {r.name}")
    print(f"       {r.description}")
    if r.ok:
        print(f"       rows={r.rows}  columns={len(r.columns)}")
        print(f"       fields: {r.columns}")
    else:
        print(f"       error: {r.error}")
    print()


# =====================================================
# 初始化 API
# =====================================================

print("=" * 70)
print("FinMind POC — 四層共振戰法資料源驗證")
print("=" * 70)
print(f"測試標的: {TEST_STOCK}")
print(f"測試期間: {START_DATE} ~ {END_DATE}")
print(f"Token   : {'已設定' if TOKEN else '未設定（僅 public endpoints）'}")
print()

api = DataLoader()
if TOKEN:
    try:
        api.login_by_token(api_token=TOKEN)
        print("Token 登入成功")
    except Exception as e:
        print(f"Token 登入失敗: {e}")
        print("繼續用 public endpoint 測試")
print()


# =====================================================
# 測試項目（對應 v2.md Part 2.3 四層）
# =====================================================

tests: list[TestResult] = []


# --- L1: OHLCV 價量（結構分基礎）---
tests.append(run_test(
    name="L1_OHLCV",
    description="原始 OHLCV — L1 結構分、L4 動能指標的基礎",
    criticality="P0",
    fetcher=lambda: api.taiwan_stock_daily(
        stock_id=TEST_STOCK, start_date=START_DATE, end_date=END_DATE
    ),
))


# --- L1+: 前復權股價（避免 KD/RSI 失真）---
tests.append(run_test(
    name="L1_AdjustedPrice",
    description="前復權 OHLC — 避免除權息日 KD/RSI 計算失真",
    criticality="P1",
    fetcher=lambda: api.taiwan_stock_daily_adj(
        stock_id=TEST_STOCK, start_date=START_DATE, end_date=END_DATE
    ),
))


# --- L2: 法人三大買賣超 ---
tests.append(run_test(
    name="L2_Institutional",
    description="外資/投信/自營商買賣超 — L2 法人方向分",
    criticality="P0",
    fetcher=lambda: api.taiwan_stock_institutional_investors(
        stock_id=TEST_STOCK, start_date=START_DATE, end_date=END_DATE
    ),
))


# --- L3a: 當沖張數 ---
tests.append(run_test(
    name="L3a_DayTrading",
    description="現股當沖張數 — net_volume 計算（chip_ratio 分母）",
    criticality="P0",
    fetcher=lambda: api.taiwan_stock_day_trading(
        stock_id=TEST_STOCK, start_date=START_DATE, end_date=END_DATE
    ),
))


# --- L3b: 融資融券（資券互抵代理）---
tests.append(run_test(
    name="L3b_Margin",
    description="融資融券 — 資券互抵的代理欄位",
    criticality="P1",
    fetcher=lambda: api.taiwan_stock_margin_purchase_short_sale(
        stock_id=TEST_STOCK, start_date=START_DATE, end_date=END_DATE
    ),
))


# --- L3c: 券商分點（最關鍵！免費版通常沒有）---
tests.append(run_test(
    name="L3c_BrokerTrading",
    description="券商買賣超 — L3 七大籌碼來源（前十大/關鍵/官股/地緣）",
    criticality="P0",
    fetcher=lambda: api.taiwan_stock_trading_daily_report(
        stock_id=TEST_STOCK, date=START_DATE
    ) if hasattr(api, "taiwan_stock_trading_daily_report") else
    api.taiwan_stock_broker_top_trading(
        stock_id=TEST_STOCK, date=START_DATE
    ) if hasattr(api, "taiwan_stock_broker_top_trading") else
    (_ for _ in ()).throw(AttributeError("無券商分點 API endpoint，可能為付費功能")),
))


# --- 下市股清單（生存者偏誤關鍵）---
tests.append(run_test(
    name="Delisting",
    description="下市股清單 — 解決生存者偏誤的唯一資料源",
    criticality="P0",
    fetcher=lambda: api.taiwan_stock_delisting()
    if hasattr(api, "taiwan_stock_delisting") else
    (_ for _ in ()).throw(AttributeError("無下市股 API endpoint")),
))


# --- Universe: 上市櫃清單 ---
tests.append(run_test(
    name="Universe_Listed",
    description="當前上市櫃清單 — 標的池基礎",
    criticality="P1",
    fetcher=lambda: api.taiwan_stock_info(),
))


# =====================================================
# 印出每項結果
# =====================================================

print("=" * 70)
print("逐項測試結果")
print("=" * 70)
print()

for t in tests:
    print_result(t)


# =====================================================
# 總結報告
# =====================================================

print("=" * 70)
print("總結報告")
print("=" * 70)

p0_tests = [t for t in tests if t.criticality == "P0"]
p1_tests = [t for t in tests if t.criticality == "P1"]

p0_pass = sum(1 for t in p0_tests if t.ok)
p1_pass = sum(1 for t in p1_tests if t.ok)

print(f"P0（必要）通過: {p0_pass}/{len(p0_tests)}")
print(f"P1（建議）通過: {p1_pass}/{len(p1_tests)}")
print()

# 列出 P0 失敗項
p0_failed = [t for t in p0_tests if not t.ok]
if p0_failed:
    print("⚠️ P0 失敗項（致命）：")
    for t in p0_failed:
        print(f"   - {t.name}: {t.description}")
        print(f"     原因: {t.error}")
    print()


# =====================================================
# 行動建議
# =====================================================

print("=" * 70)
print("行動建議")
print("=" * 70)

has_broker = any(t.ok for t in tests if t.name == "L3c_BrokerTrading")
has_delisting = any(t.ok for t in tests if t.name == "Delisting")
has_basic = (
    any(t.ok for t in tests if t.name == "L1_OHLCV")
    and any(t.ok for t in tests if t.name == "L2_Institutional")
    and any(t.ok for t in tests if t.name == "L3a_DayTrading")
)

if has_broker and has_delisting and has_basic:
    print("✅ FinMind 免費版可支撐完整 IC 測試。")
    print()
    print("下一步：")
    print("  1. 擴大測試到 10–20 檔，確認 API rate limit 是否夠用")
    print("  2. 抓 2015–2024 全 universe，估算總請求數")
    print("  3. 執行 v2.2_ic_test_plan.md 第一階段：資料準備")
    sys.exit(0)

elif has_basic and not (has_broker and has_delisting):
    print("⚠️ 基礎資料可用，但關鍵資料缺失。")
    print()
    missing = []
    if not has_broker:
        missing.append("券商分點（L3 七大籌碼）")
    if not has_delisting:
        missing.append("下市股清單（生存者偏誤）")
    print(f"缺失: {', '.join(missing)}")
    print()
    print("選項：")
    print("  1) Sponsor FinMind 解鎖（先到 finmind.github.io 確認方案內容）")
    print("  2) 直接上 TEJ（含完整下市股 + 券商分點，預算 NT$ 數萬/年）")
    print("  3) 砍策略 L3 維度，從四層改三層（簡化但 Edge 可能消失）")
    print()
    print("建議：先估 TEJ 報價，再決定 sponsor 或升級。")
    sys.exit(1)

else:
    print("❌ 連基礎資料都有問題。")
    print()
    print("排查：")
    print("  1. 網路是否正常？試 ping finmindtrade.com")
    print("  2. FinMind 套件版本是否過舊？pip install -U FinMind")
    print("  3. 是否需要 token？到 finmindtrade.com 註冊取得")
    print("  4. 用 --verbose 重跑看完整錯誤訊息")
    sys.exit(2)
