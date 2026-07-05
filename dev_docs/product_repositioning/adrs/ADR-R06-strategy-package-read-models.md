# ADR-R06: Strategy Package read models drive dynamic research UI

> 狀態: Accepted | 日期: 2026-07-05 | 決策者: refactor 任務

## 背景

現況「新建回測」仍像是對已註冊策略送一包 raw JSON：使用者必須知道
Python config 欄位名，前端也無法依策略差異產生參數表單。策略中心只呈現
策略名與簡單 schema，無法說明策略實際是一個 repo 內 package，包含 alpha
邏輯、runner adapter、research workflow config、測試與文件。

同時，若把瀏覽器做成 Python IDE，會把 sandbox、任意程式碼執行、依賴管理、
版本控制與測試責任全部推進 web console。這不符合個人級 EOD 平台第一階段
要快速把研究 workflow 產品化的定位。

## 決策

策略撰寫留在 repo / AI coding / IDE；web console 不直接編輯或執行任意
Python。策略以 `strategies/<pkg>/` Strategy Package 表達，並透過後端
read model 暴露互動面：

- `GET /strategies` 回傳已註冊策略與 `config_schema`。
- `GET /strategies/{strategy}/asset` 回傳 package descriptor、必要檔案
  present/missing、declared workflows 與互動端點。
- `GET /strategies/{strategy}/optimization-schema` 回傳 `research_config.py`
  的 DOE grid、config schema 與 window/universe 摘要。
- `POST /runs` 接收 guided params 產出的 `params`；raw JSON 僅保留為 advanced
  fallback。
- `POST /research/workflows/doe` 接收 `{strategy, overrides: {grid}}`，HTTP edge
  必須重新驗證 override。

## 後果

- 新增策略不需要改 React；只要 strategy package 註冊並宣告 config/workflow，
  UI 會自動取得可互動面。
- Strategy Hub 從策略名列表升級為策略資產頁，可顯示 package readiness、
  workflow readiness、資料卡與報表入口。
- New Run 的主路徑改為 schema-driven form，降低手寫參數錯誤；raw JSON
  不再是一般使用者的主要入口。
- 未來若接 Codex/Claude Code/Agent SDK，應作為 repo-level branch/PR/job
  workflow，而不是把任意 Python editor 嵌進回測服務。

## 落地

- Spec: [`../specs/SPEC-02-dynamic-strategy-params-and-optimization-ui.md`](../specs/SPEC-02-dynamic-strategy-params-and-optimization-ui.md)
- API: `../06_api_design_specification.md` Strategy Packages section
- Frontend IA: `../17_frontend_information_architecture.md` Strategy Package section
- WBS: `../16_wbs_development_plan.md` WP 11
