# design.pen 對齊變更 Brief（user journey + sidebar 三區）

> **用途**：在 Pencil 設計工具裡套用，讓 `pages/design.pen` 與 page specs / IA（`03` §4.7）對齊。
> **產出依據**：對 `design.pen` 全樹勘查（22 頂層 frame、route 已 `/monitor|/research|/system`、Grok 單色 token 化）+ page spec entry_point 比對。
> **現況**：design.pen 已 ~95% 對齊（screens 齊、route 對、配色對）；本 brief 只補**最後一哩：sidebar 三區身分 + journey 連線**。
> **方式**：你在工具內手動套用（不程式化改檔，避免撞掉工具內未存編輯）。逐項打勾。

---

## Part 1 — Sidebar Navigation：三區分組（最高優先）

問題：畫布全樹「monitor」文字命中 **0**；Monitor 四頁是「裸面板」（Panel A/B/C/D），沒有區身分，而 Research/System 有。sidebar 視覺分組因此不齊。

對 `Sidebar Navigation` pattern frame（§4.2）+ 每頁頁面殼內的 sidebar 元件，統一成**三段式分組**（對齊 IA `03` §4.7 / §5.2）：

```
⌘ Cmd-K  ← 全域命令列（頂部，常駐）

▸ RESEARCH（研究 · 主軸）
    策略庫        /research/strategies
    New Run       /research/runs/new
    Runs          /research/runs        ← Run Report/Compare/Sweep 為其子頁，高亮父項
    Compare       /research/compare
    Sweep         /research/sweep
    Validate      /research/validate
    Promote       /research/promote

▸ MONITOR（監控 · live 子視圖）
    A 績效總覽    /monitor/performance
    B 部位狀態    /monitor/positions
    C 訊號日誌    /monitor/signals
    D 風控指標    /monitor/risk

▸ SYSTEM（系統）
    資料管理      /system/data
    告警設定      /system/alerts
```

- [ ] sidebar 出現 **3 個區段標頭**：RESEARCH / MONITOR / SYSTEM（明度/字級分層，單色，不加彩色）
- [ ] Monitor 四項收進 MONITOR 區段（不再平鋪、不再與 Research 同層）
- [ ] 子頁（New Run / Run Report / Compare / Sweep）進入時，sidebar 高亮其**父項或所屬區**，不另開導覽項
- [ ] 區段順序 Research → Monitor → System（研究為主軸置頂，呼應「監控降為子視圖」）

---

## Part 2 — Monitor 面板的區身分（label 對齊）

四個 frame 的標題列 / 頁面 H1 補上 Monitor 區身分，與 `Research · X`、`System · X` 的命名一致：

| 現有 frame 名 | 標題列建議顯示 |
| :--- | :--- |
| `Panel A · Performance Overview` | **Monitor · A · 績效總覽** |
| `Panel B · Positions` | **Monitor · B · 部位狀態** |
| `Panel C · Signal Log` | **Monitor · C · 訊號日誌** |
| `Panel D · Risk Metrics` | **Monitor · D · 風控指標** |

- [ ] 四頁標題列加「Monitor ·」前綴（frame 內部名稱可留，重點是畫面上顯示的區身分）
- [ ] route 字串已正確（`/monitor/*`），無需改

---

## Part 3 — Cmd-K 全域命令列

畫布已有 `Command Palette` / `Chip Command Palette` 元件，但只零星出現。

- [ ] 確認 Cmd-K 入口在**每頁頁面殼**都可見（頂部常駐 chip 或 ⌘K 提示），表達「全域可達任一頁」
- [ ] Cmd-K 動作集涵蓋：切策略 / 跳 run / 開比較 / 新建 run / 跳監控面板 / type-to-run by id（橋接 CLI 子命令名）

---

## Part 4 — Journey 連線（page connectivity，本分支主軸）

在 page frame 之間補**連接線**，讓畫布直接呈現完整研究→實盤旅程 + 迴圈回流。建議用兩種線型區分：

**主流程（實線箭頭）**：
- [ ] `System · Data Management` → `Research · New Run Config`（標：bundle_ref 快照回饋）
- [ ] `Research · Strategy Library` → `Research · New Run Config`（新建 / 衍生變體）
- [ ] `Research · New Run Config` → `Research · Run Report`（提交 → 結果）
- [ ] `Research · Run Report` → `Research · Runs Table`（返回工作台）
- [ ] `Research · Runs Table` ⇄ `Research · Compare`（多選比較）
- [ ] `Research · Runs Table` ⇄ `Research · Sweep`（參數掃描）
- [ ] `Research · Compare` / `Run Report` → `Research · Validate Gate`（選穩健高原送驗證）
- [ ] `Research · Validate Gate` → `Research · Promote`（核准解鎖）
- [ ] `Research · Promote` → `Panel A`（部署 Live → 交監控）

**迴圈回流（虛線 / loss 色箭頭，標失敗原因）**：
- [ ] `Research · Validate Gate` --IS/OOS FAIL--> `Research · New Run Config`（回 M0 重設進場，ADR-017 現況）
- [ ] `Research · Promote` --Paper 退化--> `Research · New Run Config`（打回 Draft）
- [ ] `Panel D · Risk Metrics` --結構性退化(Cmd-K)--> `Research · Validate Gate` / `Runs Table`（triage 回研究迴圈）

**監控/告警串接（實線）**：
- [ ] `Panel A` → `Panel C`（equity 某日 drill-down 訊號）
- [ ] `Panel A` → `Panel B`（KPI 下鑽部位）
- [ ] `Panel B` → `Panel C`（部位 → 訊號歷史）
- [ ] `Panel D` / Grafana F–I → `System · Alerts`（事件來源）
- [ ] `System · Alerts` --Critical deep-link--> `Panel D` / `Panel C`（告警跳對應面板）

> 收口檢查：旅程應形成**閉環**（…→Promote→Monitor→triage→回 Research），無孤兒頁、無死胡同。

---

## Part 5 — 一致性驗證（順手核對）

- [ ] 斷點：四個 Monitor 面板若沿用舊斷點表（Desktop ≥1024 / Tablet 1023 等），對齊研究頁標準 **Desktop ≥1280 / Tablet 768–1279 / sidebar→drawer @<1024**
- [ ] sidebar 收合一律**兩態**（展開 ↔ drawer @<1024），不用 icon-rail 中間態（已從 monitor_c spec 移除）
- [ ] 配色：sidebar 區段標頭 / 連接線一律單色（`$color.text.*` / `$color.border.*`），journey 失敗回流線可用 `$color.loss`（唯一彩色例外，呼應漲跌語義）
- [ ] First-run 空狀態（FirstRunEmptyState）在 Strategy Library / Runs Table / Data 三頁的 CLI 引導卡呈現一致

---

## 對應的 docs 變更（已同步，供對照）

本 brief 與以下 page spec 變更同批，確保 docs ↔ design.pen 一致：

- `pages/monitor_a~d_*.md` entry_point：統一「側邊導覽『Monitor → X』」+ 補 Cmd-K（取代「主導覽列 / 左側 Sidebar / 主儀表板側邊導航」等不一致用語）
- `pages/monitor_c_signals.md` RWD：sidebar 三態 icon-rail → 兩態 drawer
- IA 真相源：`03_uiux_benchmark_and_reinforcement_plan.md` §4.7（sitemap）/ §5.2（三區 IA）

---

## 驗收（套用後自檢）

- [ ] sidebar 三區分組在所有 14 頁一致呈現，Monitor 取得區身分
- [ ] Cmd-K 全域常駐
- [ ] journey 連線閉環、含 3 條回流邊（Validate FAIL / Paper 退化 / 監控退化）
- [ ] 全畫布仍單色 Grok（連接線/區標頭無新增彩色，回流線僅 loss 色例外）
- [ ] design.pen 與 page specs 的 route / 區身分 / 旅程描述零矛盾
