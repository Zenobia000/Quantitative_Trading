# Research Scripts

策略研究階段的 POC / 驗證腳本。

## finmind_poc.py

驗證 FinMind 免費版能否支撐四層共振戰法的 IC 測試。

### 執行

```bash
pip install FinMind pandas
python finmind_poc.py

# 看完整 traceback
python finmind_poc.py --verbose
```

### 退出碼

| 碼 | 意義 | 下一步 |
| :---: | :--- | :--- |
| 0 | 全部資料就位 | 進入 v2.2_ic_test_plan.md 第一階段 |
| 1 | 基礎可用、關鍵缺失 | 評估 sponsor / TEJ / 砍 L3 |
| 2 | 基礎都有問題 | 檢查 token / 網路 / 套件版本 |

### Token 設定

部分 API 需要 FinMind 免費 token：

1. 到 https://finmindtrade.com 註冊
2. 取得 API token
3. 編輯 `finmind_poc.py` 設定 `TOKEN = "your_token_here"`

### 測試項目

對應 v2.md Part 2.3 四層計分系統：

| 測試 | 對應 v2.md | 重要性 |
| :--- | :--- | :---: |
| L1_OHLCV | 結構分基礎 | P0 |
| L1_AdjustedPrice | KD/RSI 復權 | P1 |
| L2_Institutional | L2 法人方向 | P0 |
| L3a_DayTrading | net_volume 分母 | P0 |
| L3b_Margin | 資券互抵代理 | P1 |
| L3c_BrokerTrading | L3 七大籌碼 | **P0（最關鍵）** |
| Delisting | 生存者偏誤 | **P0（最關鍵）** |
| Universe_Listed | 標的池 | P1 |

### 已知問題

- FinMind API 方法名稱可能因版本不同而異，腳本用 `hasattr` 防禦
- 免費版 rate limit 約 600 請求/小時（依方案）
- 券商分點通常為付費功能，免費版預期 FAIL（這是預期結果，不是 bug）
