# ADR-010: 告警通道改用 Discord（取代 Telegram）

> **狀態：** 已接受 | **日期：** 2026-05-31 | **決策者：** Self
> **Supersedes：** ADR-009 § 3「Telegram 主動告警」部分（雙儀表板分層決策維持不變）
> **Related：** ADR-009（L7 監控架構整體框架）

---

## 1. 背景與問題

- **上下文**：ADR-009 採納「雙儀表板 + Telegram 告警」三層架構，其中告警層使用 Telegram bot。ADR-009 § 4「重新評估觸發」已列出：「Telegram API 停服 / 政策變更 → 切 Discord / LINE Notify」。
- **問題**：實作前重新評估告警通道，發現 Telegram 並非最佳選擇：
  - 決策者（Self）日常已大量使用 Discord，Telegram 僅為「告警專用」會多開一個 app
  - Discord channel 模式可同時保留訊息歷史 + 推播通知 + 多裝置同步，UX 比 Telegram bot 更貼合「個人量化警報」情境
  - Discord embed 對結構化警報（交易訊號、錯誤堆疊）的視覺呈現比 Telegram MarkdownV2 更穩定（無跳脫字元地獄）
- **驅動因素 / 約束**：
  - 告警必須能在「手機 + 桌機」同步推播
  - 必須支援結構化訊息（顏色、欄位、時戳）以便快速分辨警報類型
  - 必須能與 Prefect / cron task 同步呼叫，避免引入 event loop 複雜度
  - 不增加新的 SaaS 月費

---

## 2. 考量的選項

### 選項一：維持 Telegram（ADR-009 原案）
- **描述**：`python-telegram-bot>=21.0`，bot send_message
- **優點**：ADR 已通過、無遷移成本
- **缺點**：
  - 多裝載一個 app 僅為告警
  - MarkdownV2 跳脫繁瑣，結構化警報 UX 受限
  - `python-telegram-bot` 體積大、強制 async（單純發訊用太重）
- **成本/複雜度**：低（不動）

### 選項二：Discord Bot + REST API 直送 ★採納
- **描述**：自建 Discord App，bot token 透過 REST `POST /channels/{id}/messages` 發送，搭配 embed
- **優點**：
  - 與決策者既有工作流融合（不增加 app 切換）
  - Embed 結構化警報視覺穩定、顏色語意化（綠買紅賣）
  - 純 REST 直送無需 `discord.py` event loop，可於 Prefect sync task 直接呼叫
  - 同一 App 未來可擴充斜線指令（如 `/positions` 查倉）— webhook 做不到
  - 免費、無 SaaS 月費
- **缺點**：
  - 需自行管理 bot token 與 OAuth 邀請流程
  - 自實作 rate limit 處理（v1 暫不做，警報量小）
- **成本/複雜度**：低

### 選項三：Discord Webhook
- **描述**：用 channel webhook URL 純 HTTP POST，無 App、無 bot
- **優點**：設定最簡（只要 URL，無 token、無 OAuth）
- **缺點**：
  - send-only，無法擴充互動指令（未來想接 `/positions` 就重做）
  - URL 等同永久 secret，外洩後僅能整支重產
  - 受眾鎖死在一個 channel，無法切 DM
- **成本/複雜度**：極低（但能力上限低）

### 選項四：LINE Notify
- **描述**：ADR-009 觸發條件已列出之備選
- **優點**：台灣使用者基數大、setup 極簡
- **缺點**：
  - **LINE Notify 已於 2025-03-31 終止服務**，遷移到 Messaging API 後個人帳號免費額度僅 200 則/月
  - 結構化訊息支援弱於 Discord embed
  - 不在決策者既有工作流
- **成本/複雜度**：低（但受平台限制）

### 選項五：付費 SaaS（PagerDuty / Opsgenie）
- **描述**：商用告警平台
- **優點**：on-call 排程、escalation 完整
- **缺點**：月費、單人專案大砲打蚊子
- **成本/複雜度**：低開發 / 高運營成本

---

## 3. 決策

**選擇：選項二（Discord Bot + REST API 直送）**

**理由**：
- 與決策者既有 Discord 使用習慣整合，告警通道不增加 context switch
- REST 直送（httpx）比 `python-telegram-bot` 或 `discord.py` 都輕，import 成本低，可在任何 Prefect sync task 中直呼
- Embed 比 MarkdownV2 對結構化警報更友善（顏色 / 欄位 / 時戳原生支援）
- 保留未來擴充斜線指令空間（webhook 路線無此能力）
- ADR-009 § 4「重新評估觸發」已預留此路徑，無需重訂上層架構

### 告警目標模式

採 **channel 模式**（`DISCORD_ALERT_TARGET=channel`）：
- 訊息有歷史可回溯（DM 也有，但 channel 更利於未來分享給協作者）
- 桌機 + 手機跨裝置同步、可加 emoji reaction 做手動標記
- 若日後決策者轉為純獨自監看，可改 `dm` 模式無需改 code

### 告警等級與顏色映射

承襲 ADR-009 § 3「Telegram 告警等級」三等級分類，重新對應 Discord embed color：

| 等級 | 觸發條件 | Embed Color |
|:--|:--|:--|
| Critical | 實盤下單失敗、Shioaji 斷線、熔斷觸發 | `0xB71C1C` (deep red) |
| High | ETL 失敗、訊號缺漏、部位偏離 > 5%、FinLab 流量 < 500MB | `0xFFA000` (amber) |
| Info / Buy | 收盤摘要、買進訊號 | `0x00C853` (green) |
| Info / Sell | 賣出訊號 | `0xD32F2F` (red) |

### 權限最小化

OAuth2 邀請 URL 僅授予 `Send Messages` (2048) + `Embed Links` (16384) = **18432**。
**禁用** Administrator (8) — 警報用途不需要管理員權限。

---

## 4. 後果

- **正面**：
  - 與決策者既有工具鏈整合，降低告警被忽略風險
  - REST + httpx 實作 ~180 LOC，比 `python-telegram-bot` 方案輕量
  - Embed 結構化呈現提升警報資訊密度
  - 保留未來擴充互動指令的路徑
- **負面**：
  - Bot token 為高敏感 secret，需嚴格管理（.env gitignore + Developer Portal Reset Token 流程）
  - Discord 對台灣 IP 偶有連線不穩，需於 ETL 排程加入告警重送 / fallback 紀錄（本 ADR 不處理，留 v2）
  - 若 Discord 服務中斷，告警會靜默漏失 — 緩解：critical 級警報同步寫入 TimescaleDB `alert_log` table，dashboard E 面板可回放
- **影響範圍**：
  - `backtest_platform/.env.example`：`TELEGRAM_BOT_TOKEN` / `TELEGRAM_CHAT_ID` → `DISCORD_BOT_TOKEN` / `DISCORD_GUILD_ID` / `DISCORD_CHANNEL_ID` / `DISCORD_USER_ID` / `DISCORD_ALERT_TARGET`
  - `backtest_platform/pyproject.toml` `[monitoring]` extras：移除 `python-telegram-bot>=21.0`，新增 `httpx>=0.27`
  - `backtest_platform/src/backtest_platform/monitoring/discord_notifier.py`：新增 ~180 LOC（`DiscordSettings` / `DiscordEmbed` / `DiscordNotifier` + 三個 high-level helper）
  - `backtest_platform/src/backtest_platform/monitoring/__init__.py`：公開 API 匯出
  - `backtest_platform/tests/monitoring/test_discord_notifier.py`：12 個單元測試（httpx MockTransport 攔截，零外網）
  - ADR-009 § 3 表格與 § 4「重新評估觸發」「Telegram」字樣 → 加 superseded 註記指向本 ADR
  - 未來 `monitoring/alerter.py`（M4 W3 排程）改 import `notify_critical` / `notify_high` / `notify_info` 自本模組
- **重新評估觸發**：
  - Discord 1 週內推播失敗率 > 5% → 評估補 webhook fallback 或回頭用 LINE Messaging API
  - 個人告警量超過 Discord rate limit（5 msg / 5 sec per channel）→ 補實作 token bucket
  - Discord 政策變更影響 bot 使用 → 切 Slack 或自架 ntfy.sh

---

## 5. 執行計畫

1. **已完成（本 PR）**：
   - `.env.example` / `.env` 變數遷移
   - `monitoring/discord_notifier.py` + `__init__.py` 模組實作
   - `pyproject.toml` monitoring extras 換 dep
   - 12 個單元測試全綠（`pytest tests/monitoring/test_discord_notifier.py -p no:asyncio`）
2. **下一步（本 PR 後續 commit）**：
   - ADR-009 加 superseded 標記指向本 ADR
   - 重新產生 Discord OAuth2 URL（permissions=18432），文件記錄正確邀請流程
   - **Reset Bot Token**（原 token 已於對話外洩，必須在 Discord Developer Portal 重置）
3. **M4 W3**：`monitoring/alerter.py` 改 import 本模組 helper，串接 ADR-009 三等級告警規則
4. **M4 W4**：三層聯動測試（手動觸發 ETL 失敗 → Grafana 紅燈 + **Discord** High 推播）
5. **M5 W1**：Discord embed timestamp 接 Shioaji 實盤 fill 時間，drift 監控

---

| 日期 | 審核人 | 備註 |
| :--- | :--- | :--- |
| 2026-05-31 | Self | 初版 — 取代 ADR-009 § 3 告警通道部分 |
