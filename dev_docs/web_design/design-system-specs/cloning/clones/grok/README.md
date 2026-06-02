# Clone Target: grok（忠實還原 — v2 重建）

> **目標**：`https://grok.com`（真正的 Grok web app：深色、單色、極簡 chat 介面）。
> **狀態**：**v2 重建**，取代 v1。v1 誤用 `x.ai/grok`（淺色行銷頁）當代理，與真實 Grok app 不符。

---

## 基本資訊

| 欄位 | 值 |
|------|-----|
| Slug | `grok` |
| Target | `https://grok.com`（Grok app 本體） |
| 擷取方式 | **路徑 2：公開知識重建**（reconstructed from public knowledge） |
| 重建日期 | 2026-06-02 |
| 法律檢查 | [x] 僅依公開可見之 app 外觀；無登入後內容、無資產下載 |

## ⚠️ 為何是「重建」而非「擷取」

- `grok.com` 受 **Cloudflare managed challenge** 保護；headless（Playwright chromium + persistent context + stealth + 久候）三斷點皆卡 `"Just a moment..."`，**無法擷取**。環境無系統 Chrome、無 browser MCP。
- v1 退而用 `x.ai/grok` 行銷頁當代理 → **錯誤**：那是 xAI 淺色行銷頁（白底、大標排版），不是 Grok app。
- 本版依**公開知識**重建 Grok app 的視覺語言。**精確 token（hex / 字型名）標 `TBD`，不瞎掰**；確切值需日後用 DevTools 手動擷取（見 `prompts/01_capture.md` 手動路徑）補正。

## 重建素材（公開）

- Grok app 公開外觀：dark-first、單色（黑/白/灰）、置中大圓角輸入框、左側可收合 sidebar。
- xAI/Grok 單色品牌識別。
- 公開設計編目（dark mode、sidebar 桌機 / drawer 手機、light+dark 雙模式）。
- **排除**：第三方「Grok 風」教學的 purple/gradient 變體（非官方）。

## 輸出範圍

- [x] L0 Foundations（重建，monochrome dark）
- [ ] L1–L4：待精確 token 補正後再展開（不在不確定基礎上堆細節）

## 信心度總表

| 面向 | 信心度 |
|------|--------|
| dark-first / 單色基調 | high |
| 版面（sidebar / 置中輸入框 / 極簡頂列） | high |
| 大圓角 / 細邊框 / 留白 | med–high |
| 精確 hex token | **TBD（需手動擷取補正）** |
| 字型家族 | **TBD** |
