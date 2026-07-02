# ADR-031: Standalone Auth 裁決 — localhost-only 綁定取代未實作的 Bearer 承諾

> **狀態：** 已接受 | **日期：** 2026-07-02 | **決策者：** Self（使用者裁定）
> **修正（amends）：** [ADR-021](./ADR-021-unify-rest-contract-into-single-doc-and-openapi.md)（§ single-user static Bearer 承諾）— 本 ADR 把「M3.0 起全端點 static Bearer」的承諾降為 **M5 遠端存取時重議**。
> **相關：** [platform_full_audit_2026-07-02](../platform_full_audit_2026-07-02.md) §3 缺陷 #20（auth 三方矛盾）、[02 PRD v4.0](../02_project_brief_and_prd.md) §2.3（standalone 部署假設正式化）、`rules/security.md`（秘密管理）。

---

## 1. 背景（Context）

審查（缺陷 #20）證實 auth 承諾**三方矛盾**：

| 面向 | 現況（實地覆核 2026-07-02）|
| :--- | :--- |
| **doc 25 §4** | 宣告「單人自託管平台，M3.0 起所有非 `/health` 端點要求 static Bearer，缺/錯 → 401」 |
| **後端 `api/`** | 全目錄**零** Authorization 檢查、無 `HTTPBearer` dependency、無 CORS（`grep Authorization api/` 空）|
| **前端 `services/http.ts`** | 硬編碼 fallback `const TOKEN = import.meta.env.VITE_API_TOKEN ?? 'dev-token'`，且每個請求都送 `Authorization: Bearer ${TOKEN}` |

也就是說：**契約承諾了、後端沒做、前端硬塞了一個沒人檢查的 token**。此外 `.env.example` 的絕對 URL 會繞過 vite proxy 直撞無 CORS 後端。

[PRD v4.0](../02_project_brief_and_prd.md) §2.3 把部署假設正式化：**單機自託管、內網 localhost、無多人協作、無合規審批**。auth 決策必須據此假設一次裁定，不能繼續懸置。

**核心觀察**：「承諾了沒做」比「決定不做」更傷文件可信度——它讓讀者以為有一道防線，實際上沒有；也讓每個 client（前端 / curl / CLI / 未來 daemon）都要攜帶一個無意義的 header。

---

## 2. 選項（Options）

### 選項 A — 補實作 ~20 行 static Bearer dependency（兌現 doc 25 承諾）

- 後端加一個 FastAPI dependency：讀環境變數 `API_TOKEN`，比對 `Authorization: Bearer`，缺/錯回 401；`/health` 豁免。
- 前端維持現有 header slot、把 `VITE_API_TOKEN` 接真。
- **成本**：每個 client（含 curl、CLI、未來排程器）都要攜帶並管理 token；多一份 secret 要輪換；`.env` 一致性要維護。
- **收益（在 localhost 假設下）**：趨近於零——能存取 `127.0.0.1` 的行為者已擁有這台機器（可讀 `.env`、可讀 token、可直接跑 process）。static Bearer 對「同機」威脅模型不增加實質防線。

### 選項 B — localhost-only 綁定宣告 + 移除 doc 25 的 Bearer 承諾（推薦）

- 明文宣告：API **MUST 綁 `127.0.0.1`**（loopback），前端走 vite proxy 同機存取，無公網暴露。**綁定本身即安全邊界**。
- doc 25 §4 移除「M3.0 static Bearer」承諾，降為「M5 遠端存取時重議」。
- 前端 `http.ts` 的 `dev-token` 變為無害殘留（後端不檢查、也不授予任何權限）——可保留 header slot 供 M5，或移除。
- 秘密（`FINLAB_API_TOKEN` / `DISCORD_*` / `INFLUX_*`）**不受影響**，仍僅後端持有、絕不出 bundle（`rules/security.md` 不放鬆）。

---

## 3. 決策（Decision）

**採選項 B。**

1. **loopback bind 為唯一安全邊界**：後端 API 在 standalone 模式 MUST 綁 `127.0.0.1`。此為 [PRD v4.0](../02_project_brief_and_prd.md) §2.3「內網 localhost」假設的直接落地。
2. **移除 doc 25 的 Bearer 承諾**：doc 25 §4 改寫為「standalone = localhost-only 綁定；不承諾未實作的 auth」，Bearer 降為 M5 遠端存取觸發時重開的決策（reverse-proxy guard 或 static Bearer dependency）。
3. **前端 `dev-token` 標記為無害殘留**：不檢查即不構成「洩漏的 secret」（它不授予任何東西）。保留與否為前端清理 follow-up，非 auth 前置。
4. **秘密管理不放鬆**：所有第三方 token 仍後端獨佔、遮罩回應、絕不進 bundle。

**裁決理由（一句話）**：20 行 static Bearer 對 localhost 威脅模型不增加實質安全、卻增加每個 client 的摩擦；loopback bind 才是真正的邊界。誠實地「決定不做」勝過「承諾了沒做」。

---

## 4. 後果（Consequences）

**正面：**
- 三方矛盾一次消解——契約、後端、前端對齊為同一個誠實現實（無 app 層 auth、邊界是 loopback）。
- 每個 client 零 header 摩擦（curl / CLI / 排程器直接打）。
- 前端 `dev-token` 不再是「看似洩漏的 secret」的誤導性告警來源。
- 文件可信度回升：不再宣稱一道不存在的防線。

**負面 / 已接受成本：**
- **無 defense-in-depth**：若 loopback 假設被違反（使用者手動綁 `0.0.0.0`、或經 reverse proxy 對外曝露而未自行加 guard），則無 app 層防線。→ 緩解：於運維文件明文「standalone MUST bind 127.0.0.1」、M5 遠端存取時強制重開 auth 決策。
- **M5 需回補**：跨機/遠端存取時，選項 A 的 static Bearer（或 reverse-proxy guard）需在 M5 重新評估並實作。本 ADR 不預先實作，避免 gold-plating。

**Follow-up（非本 ADR 阻塞項）：**
- doc 25 §4 auth 段同步改寫（本 PR 一併處理）。
- 前端 `http.ts` 的 `dev-token` 與 header slot 清理（前端 worktree 決定去留）。
- 運維文件（14/23）補「loopback bind MUST」宣告——留待架構文件償還 sweep（audit 路線圖 Phase 3）。
