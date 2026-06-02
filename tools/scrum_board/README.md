# Scrum Board — 互動式專案管理看板

拖拉式 Scrum 看板，把 sprint 狀態變更**雙向同步**回 repo 文件，讓 AI 讀檔即知最新狀況。

## 為什麼存在

`dev_docs/16_wbs_development_plan.md` §7 的 sprint 表是專案狀態真相源，但手改 markdown 表格繁瑣。
本工具提供瀏覽器拖拉介面，任何變更自動回寫 `dev_docs/scrum_board.json`（機器可讀真相源）
並重生 WBS §7 表格 — 兩邊永遠一致。

## 架構

```
瀏覽器拖拉卡片
   │  POST /api/board（整份看板 JSON，debounce 500ms）
   ▼
本地 server.py（stdlib http.server，零依賴，僅綁 127.0.0.1）
   │  save_board() 寫檔 + 蓋 updatedAt 時戳
   ▼
dev_docs/scrum_board.json   ◄── 真相源，AI 直接讀
   │  sync_wbs.sync()
   ▼
16_wbs_development_plan.md §7   （只重寫 <!-- SCRUM_BOARD:START/END --> 之間）
```

## 啟動

一鍵腳本（自動定位 repo venv，無需先 activate）：

```bash
./tools/scrum_board/start.sh            # 綁 0.0.0.0:8765（區網可達，會印出本機 IP）
./tools/scrum_board/start.sh 9000       # 換 port
HOST=127.0.0.1 ./tools/scrum_board/start.sh   # 鎖回本機
```

或直接呼叫 server：

```bash
python tools/scrum_board/server.py                    # 預設綁 0.0.0.0:8765
python tools/scrum_board/server.py --host 127.0.0.1   # 僅本機
python tools/scrum_board/server.py --port 9000
```

> ⚠️ 預設綁 `0.0.0.0` 方便遠端 / 容器外瀏覽器存取，代表**同網段其他機器可連入**。
> 此 server 無認證，請只在可信任內網使用，勿暴露公網；要鎖回本機加 `--host 127.0.0.1`。

開瀏覽器 → 拖拉卡片跨欄（Backlog / To Do / In Progress / Review / Done）→ 右上角顯示
「已同步 WBS」即代表 `scrum_board.json` 與 WBS §7 都已寫回。

## 操作

| 動作 | 方式 |
| :--- | :--- |
| 移動 sprint 狀態 | 拖拉卡片到目標欄 |
| 編輯 / 刪除卡片 | 雙擊卡片開 modal |
| 新增卡片 | 工具列「＋ 新增卡片」 |
| 依里程碑篩選 | 工具列 M0/M1/M2/M3 chip |
| 匯出 JSON 備份 | 工具列「匯出 JSON」 |

## 狀態 ↔ emoji 映射（看板欄位 → WBS 前綴）

| 欄位 | WBS 前綴 |
| :--- | :--- |
| Done | ✅ |
| Review | 🔎 |
| In Progress | 🚧 |
| To Do | ⏳ |
| Backlog | （無） |

## 檔案

| 檔案 | 職責 |
| :--- | :--- |
| `start.sh` | 一鍵啟動腳本（自動找 venv python，預設綁 0.0.0.0）|
| `server.py` | 本地 HTTP 伺服器（零依賴）|
| `sync_wbs.py` | 純函式同步引擎（`render_table` / `replace_between_markers` / `sync`）|
| `index.html` / `styles.css` / `app.js` | 前端看板 UI |
| `tests/test_sync_wbs.py` | 同步引擎單元測試（8 cases）|

## 測試

```bash
backtest_platform/.venv/bin/python -m pytest tools/scrum_board/tests/ -q
```

## 注意

- 真相源是 `dev_docs/scrum_board.json`；WBS §7 marker 之間的內容由工具生成，**請勿手改**。
- WBS §1 banner、模組工時表等其他區段**不受工具影響**，仍由人維護。
- 伺服器預設綁 `0.0.0.0`（區網可達、無認證）；僅在可信任內網使用，或加 `--host 127.0.0.1` 鎖回本機。
