# AI 工業化設計完整戰法

> Pencil + Figma MCP + Claude Code = 設計即程式碼的工業級流水線
> 從設計到程式碼，零資訊損失、可版本管理、可規模化。

---

## 目錄

1. [戰法總覽：三大工具如何協作](#1-戰法總覽)
2. [工具介紹與定位](#2-工具介紹與定位)
3. [環境搭建](#3-環境搭建)
4. [核心工作流程](#4-核心工作流程)
5. [Pencil 詳細使用手冊](#5-pencil-詳細使用手冊)
6. [Figma MCP 詳細使用手冊](#6-figma-mcp-詳細使用手冊)
7. [Claude Code 整合使用手冊](#7-claude-code-整合使用手冊)
8. [工業化 Pipeline 架構](#8-工業化-pipeline-架構)
9. [Design Token 自動化流程](#9-design-token-自動化流程)
10. [團隊協作與規模化](#10-團隊協作與規模化)
11. [與現有 Pipeline 的整合](#11-與現有-pipeline-的整合)

---

## 1. 戰法總覽

### 一句話結論

```
Pencil 產出設計 (.pen) → Git 管理設計版本 → Claude Code 讀 .pen 轉程式碼
Figma 管理 Design System → Figma MCP 讓 AI 讀取 → Claude Code 生成一致的程式碼
兩者相輔相成：Pencil 做速度，Figma 做系統，Claude Code 做產出。
```

### 三角戰法圖

```
                    ┌──────────────┐
                    │  設計意圖     │
                    │ (Human)      │
                    └──────┬───────┘
                           │
              ┌────────────┼────────────┐
              ▼            ▼            ▼
      ┌──────────┐  ┌───────────┐  ┌──────────┐
      │ Pencil   │  │ Figma     │  │ Claude   │
      │ .pen     │  │ Library   │  │ Code     │
      │          │  │           │  │          │
      │ 快速設計 │  │ 系統管理  │  │ 程式產出  │
      │ + Git    │  │ + Tokens  │  │ + 整合   │
      └────┬─────┘  └─────┬─────┘  └────┬─────┘
           │              │              │
           │  ┌───────────┘              │
           │  │  Figma MCP               │
           │  │  (設計→AI 橋接)           │
           ▼  ▼                          ▼
      ┌────────────────────────────────────┐
      │         Production Code            │
      │    React / Next.js / HTML/CSS      │
      │    (Git 版本管理)                   │
      └────────────────────────────────────┘
```

### 角色分工

| 工具 | 角色 | 強項 | 弱項 |
|------|------|------|------|
| **Pencil** | 快速設計引擎 | IDE 內設計、AI 多代理並行生成、.pen 可 Git 管理、即時生成 React 程式碼 | 不適合管理大型 Design System |
| **Figma** | 設計系統管理中心 | Variables、Components Library、Design Token 管理、團隊協作、Dev Mode | 設計→程式碼需要額外工具 |
| **Figma MCP** | 設計→AI 橋接器 | 結構化讀取 Figma 設計、Code Connect、Code-to-Canvas 回寫 | 有 API 限制（Starter plan 每月 6 次） |
| **Claude Code** | 程式碼生產者 | 讀取 .pen + Figma MCP 產出一致程式碼、多 MCP 同時使用 | 需要設計規格才能產出好結果 |

---

## 2. 工具介紹與定位

### 2.1 Pencil (pencil.dev)

**是什麼**：Agent-driven 向量設計工具，直接在 IDE 內設計，設計即程式碼。

**核心特色**：
- 在 VS Code / Cursor 內有無限畫布
- 自然語言 prompt → AI 產出設計稿
- 多代理並行（最多 6 個 AI agent 同時設計不同區塊）
- 內建 Shadcn UI / Lunaris / Halo / Nitro 設計套件
- .pen 格式：JSON-based、Git-friendly、可 diff/merge
- 雙向同步：Design ↔ Code

**定價**：
- Pencil 本身免費（Early Access）
- 需要 Claude Code 訂閱（$20/月起）做 AI 功能

**官方文件**：
- 主站：https://www.pencil.dev/
- 文件：https://docs.pencil.dev/

### 2.2 Figma MCP Server

**是什麼**：Figma 官方的 Model Context Protocol 服務，讓 AI 能結構化讀取 Figma 設計。

**核心特色**：
- 13 個工具（get_design_context、get_variable_defs、get_screenshot 等）
- Code Connect：Figma 元件 ↔ 程式碼元件 1:1 對應
- Code-to-Canvas：把程式碼跑的 UI 反向生成 Figma 圖層
- 支援 Claude Code、VS Code、Cursor、Codex 等

**部署方式**：
- Remote（推薦）：`https://mcp.figma.com/mcp`
- Desktop（本機）：`http://127.0.0.1:3845/mcp`

**限制**：
- Starter plan：每月 6 次工具呼叫
- Code Connect 需 Organization / Enterprise plan
- Desktop server 不支援 Code-to-Canvas

**官方文件**：
- 開發者文件：https://developers.figma.com/docs/figma-mcp-server/
- GitHub 指南：https://github.com/figma/mcp-server-guide

### 2.3 Claude Code

**是什麼**：Anthropic 官方 CLI，可以連接多個 MCP Server 進行 AI 輔助開發。

**在此戰法中的角色**：
- 同時連接 Pencil MCP + Figma MCP
- 讀取 .pen 設計檔 → 生成 React/HTML 程式碼
- 讀取 Figma Design System → 確保程式碼符合 token 規範
- 自動化設計→程式碼→驗證的全流程

---

## 3. 環境搭建

### 3.1 安裝 Pencil

1. 從 [pencil.dev](https://pencil.dev) 下載 Desktop App（Mac / Linux / Windows）
2. 開啟 App，執行 `File → Install pencil command into PATH`
3. 重開 terminal 驗證：

```bash
pencil --help
pencil --agent-config config.json
```

> Pencil CLI 是 Desktop App 內建功能，**不在 npm registry**，請勿使用 `npm install`。

### 3.2 設定 Figma MCP

```bash
# 方法 A：Plugin 安裝（推薦）
claude plugin install figma@claude-plugins-official

# 方法 B：手動設定
claude mcp add --transport http figma https://mcp.figma.com/mcp

# 加 --scope user 讓所有專案都能用
claude mcp add --transport http --scope user figma https://mcp.figma.com/mcp
```

**認證**：
1. 啟動 Claude Code
2. 輸入 `/mcp` → 選擇 `figma` → Authenticate
3. 瀏覽器中點擊 "Allow Access"
4. 回到 Claude Code 確認 "Authentication successful"

### 3.3 設定 Pencil MCP

MCP server 應寫在 `~/.claude.json`（user-level）或專案根的 `.mcp.json`（project-level），**不是** `.claude/settings.json`。

若 Pencil 提供 stdio MCP 子指令，使用：

```bash
claude mcp add pencil -- pencil <子指令>
```

或在 `.mcp.json` 手動配置：

```json
{
  "mcpServers": {
    "pencil": {
      "command": "pencil",
      "args": ["<子指令>"]
    }
  }
}
```

> Pencil MCP integration 仍處於 early stage，官方未公開固定的子指令名稱。先以 `pencil --help` 確認當前版本支援的子指令再填入。若不支援，改走 §4 的 `.pen` 檔案流程。

### 3.4 驗證設定

```bash
claude mcp list
# figma:  connected (remote)
# pencil: connected (local)   ← 視 Pencil 版本支援度
```

### 3.5 專案結構建議

```
your-project/
├── .claude/
│   └── settings.json          ← MCP Server 設定
├── design/
│   ├── pages/                 ← .pen 設計檔（Git 管理）
│   │   ├── dashboard.pen
│   │   ├── settings.pen
│   │   └── landing.pen
│   ├── tokens/
│   │   └── tokens.json        ← Design Token 定義
│   └── rules/
│       └── design-rules.md    ← AI 設計規則
├── src/
│   ├── components/            ← 元件程式碼
│   ├── pages/                 ← 頁面程式碼
│   └── styles/
│       └── tokens.css         ← Token → CSS Variables
├── design-system-specs/       ← 本專案的規格文件
│   ├── 00_foundations_spec.md
│   ├── 01_components_spec.md
│   ├── 02_patterns_spec.md
│   ├── 03_templates_spec.md
│   └── 99_documentation_spec.md
└── package.json
```

---

## 4. 核心工作流程

### 4.1 Flow A：Pencil 快速設計 → 程式碼（速度優先）

```
適用：新頁面 / 原型 / MVP / 快速迭代

Step 1: 在 Pencil 中用自然語言描述設計
  Prompt: "Build a dashboard page with 4 stat cards,
           a line chart, and a recent orders table.
           Use Shadcn UI components."

Step 2: AI 多代理同時產出（Hero + Stats + Chart + Table）

Step 3: 在 Pencil 畫布上微調（拖拉、調間距、改文案）

Step 4: .pen 檔自動存在專案目錄中

Step 5: 在 Claude Code 中：
  Prompt: "Read the dashboard.pen file and generate
           a Next.js page component using Tailwind CSS.
           Follow the design tokens in tokens.json."

Step 6: Claude Code 讀 .pen（精確的向量座標 + token 值）→ 產出程式碼

Step 7: Git commit（.pen + code 一起版本管理）
```

### 4.2 Flow B：Figma Design System → 程式碼（一致性優先）

```
適用：已有 Design System / 團隊協作 / 品質要求高

Step 1: 在 Figma 中定義好 Variables、Components、Styles

Step 2: 設定 Code Connect（Figma Node ↔ React Component mapping）

Step 3: 複製 Figma Frame/Layer 的 URL

Step 4: 在 Claude Code 中：
  Prompt: "Implement this Figma design:
           [paste Figma URL]
           Use our existing component library in src/components.
           Follow the design tokens."

Step 5: Figma MCP 呼叫 get_design_context + get_variable_defs
         → 取得結構化設計資料

Step 6: Claude Code 根據設計資料 + Code Connect mapping
         → 產出使用既有元件的程式碼

Step 7: 如果是新增的 UI，用 Code-to-Canvas 回寫到 Figma
  Prompt: "Capture the running UI at localhost:3000/dashboard
           and send it to my Figma file."
```

### 4.3 Flow C：雙向整合流程（工業化）

```
完整流程：

  ┌─────────────────────────────────────────────────┐
  │ Phase 1: Design System 定義（Figma）            │
  │                                                 │
  │  Figma Variables → tokens.json → CSS Variables  │
  │  Figma Components → Code Connect → React Comps  │
  └───────────────────────┬─────────────────────────┘
                          │
  ┌───────────────────────▼─────────────────────────┐
  │ Phase 2: 頁面設計（Pencil 或 Figma）            │
  │                                                 │
  │  Option A: Pencil prompt → .pen file            │
  │  Option B: Figma design → MCP 讀取              │
  └───────────────────────┬─────────────────────────┘
                          │
  ┌───────────────────────▼─────────────────────────┐
  │ Phase 3: 程式碼生成（Claude Code）              │
  │                                                 │
  │  讀 .pen / Figma MCP                            │
  │  → 套用 Design Tokens                           │
  │  → 使用既有 Components                          │
  │  → 產出 Page Component                          │
  └───────────────────────┬─────────────────────────┘
                          │
  ┌───────────────────────▼─────────────────────────┐
  │ Phase 4: 驗證與回饋                             │
  │                                                 │
  │  Code-to-Canvas（程式碼→Figma）驗證視覺         │
  │  Design QA Checklist 檢核                       │
  │  Git commit（.pen + code 一起管理）             │
  └─────────────────────────────────────────────────┘
```

---

## 5. Pencil 詳細使用手冊

### 5.1 .pen 檔案格式

```json
{
  "version": "1.0",
  "canvas": {
    "width": 1440,
    "height": 900
  },
  "objects": [
    {
      "id": "frame-1",
      "type": "frame",
      "x": 0,
      "y": 0,
      "width": 1440,
      "height": 900,
      "layout": "vertical",
      "children": [
        {
          "id": "text-1",
          "type": "text",
          "content": "Dashboard",
          "fontSize": 30,
          "fontWeight": 700,
          "fill": "#111827"
        },
        {
          "id": "rect-1",
          "type": "rectangle",
          "width": 300,
          "height": 120,
          "fill": "#F9FAFB",
          "cornerRadius": 8,
          "children": [...]
        }
      ]
    }
  ]
}
```

**Git 管理重點**：
- .pen 是 JSON，可以 `git diff` 看設計變更
- 多人同時改不同 frame → Git merge 無衝突
- 建議 `.pen` 檔案加入 `.gitattributes` 強制 merge 策略

```gitattributes
*.pen merge=union
```

### 5.2 Pencil MCP 工具

| 工具 | 功能 | 用法 |
|------|------|------|
| `read_canvas` | 讀取整個畫布 | AI 了解當前設計全貌 |
| `get_selected_frame` | 讀取選中的 frame | 針對特定區塊生成程式碼 |
| `get_style_guide` | 讀取樣式指南 | 確保 AI 遵循設計規範 |
| `update_frame` | 修改 frame 屬性 | AI 調整設計 |
| `add_component` | 新增元件 | AI 在畫布上新增設計元素 |

### 5.3 常用 Prompt 範例

**快速生成頁面**：
```
Build a SaaS pricing page with 3 tiers (Free, Pro, Enterprise).
Use Shadcn UI cards. Include a toggle for monthly/yearly pricing.
Feature comparison table below the cards.
```

**從設計稿生成程式碼**：
```
Read the design in dashboard.pen and generate a React component.
Use Tailwind CSS for styling. Import existing components from
@/components. Follow the design tokens in tokens.json.
```

**設計微調**：
```
In the current canvas, increase the padding of all cards to 24px
and change the heading font weight to 600.
```

### 5.4 Pencil ↔ Figma 互通

```
Pencil → Figma：
  1. 在 Figma 安裝 "Pencil.dev / .pen file import" plugin
  2. 匯出 .pen 檔
  3. 在 Figma 中匯入 → 生成 Figma 圖層

  或使用 "Pencil to Figma" plugin 直接複製貼上

Figma → Pencil：
  1. 在 Figma 中選取 frame
  2. Copy (Cmd+C)
  3. 在 Pencil 畫布中 Paste
  4. 保留 layout、styles、spacing、layer hierarchy
```

---

## 6. Figma MCP 詳細使用手冊

### 6.1 13 個工具一覽

| 工具 | 功能 | 常用場景 |
|------|------|---------|
| `get_design_context` | 取得結構化設計資料（預設 React + Tailwind） | 設計→程式碼 |
| `get_variable_defs` | 取得 Design Token 定義 | Token 同步 |
| `get_screenshot` | 截圖 | 視覺參考 |
| `get_metadata` | 取得 XML 結構（輕量） | 大型設計檔 |
| `get_code_connect_map` | 取得元件↔程式碼 mapping | 使用既有元件 |
| `get_code_connect_suggestions` | AI 建議 Code Connect mapping | 初次設定 |
| `add_code_connect_map` | 新增 Code Connect mapping | 維護 mapping |
| `send_code_connect_mappings` | 確認 mapping | 批次設定 |
| `generate_figma_design` | 程式碼→Figma 圖層（Code-to-Canvas） | 反向同步 |
| `generate_diagram` | Mermaid → FigJam 圖表 | 文件製作 |
| `create_design_system_rules` | 生成設計規則檔 | AI 行為規範 |
| `get_figjam` | 讀取 FigJam 資料 | 腦力激盪結果讀取 |
| `whoami` | 取得認證用戶資訊 | 驗證連線 |

### 6.2 常用 Prompt 範例

**從 Figma 生成程式碼**：
```
Implement this Figma design as a React component:
https://www.figma.com/design/xxx/file?node-id=123

Use our component library in src/components/.
Apply design tokens from our tokens.json.
Generate responsive code for desktop and mobile.
```

**取得 Design Tokens**：
```
Get all design variables from my Figma file:
https://www.figma.com/design/xxx/file

Export them as a tokens.json file in W3C Design Token format.
```

**Code-to-Canvas（程式碼→Figma）**：
```
Capture the running UI at http://localhost:3000/settings
and create Figma frames for it in my file:
https://www.figma.com/design/xxx/file
```

**建立 Design System Rules**：
```
Scan my codebase and Figma file to create design system rules.
Include token definitions, component mappings, and naming conventions.
Save the rules file at design/rules/design-rules.md.
```

### 6.3 Code Connect 設定

```
Step 1: 取得建議 mapping
  Claude Code: "Get Code Connect suggestions for my Figma file:
               https://www.figma.com/design/xxx/file"

Step 2: 確認 mapping
  Figma Button → src/components/Button.tsx
  Figma Card → src/components/Card.tsx
  Figma Table → src/components/DataTable.tsx

Step 3: 建立 mapping
  Claude Code: "Add these Code Connect mappings to my Figma file..."

效果：
  - Figma Dev Mode 中直接顯示對應的 React 程式碼
  - AI 生成程式碼時自動使用正確的元件
  - 不再生成 generic HTML，而是使用你的元件庫
```

### 6.4 最佳實踐

```
1. Figma 檔案結構
   - 使用 Auto Layout（不用絕對定位）
   - 使用 Variables（不用 hard-coded 值）
   - Frame 有語意命名（"header-nav" 而非 "Frame 432"）
   - 元件用 Library instances（不要 detach）

2. Prompt 撰寫
   - 指定框架：「使用 React + Tailwind」
   - 指定元件庫路徑：「元件在 src/components/」
   - 指定 Token 檔：「Token 在 tokens.json」
   - 拆解大設計：一個 Frame 一個 prompt（而非整頁）

3. 效能優化
   - 大型設計先用 get_metadata（輕量），再用 get_design_context（詳細）
   - 拆成小 Frame 處理
   - 使用 get_screenshot 做視覺參考
```

---

## 7. Claude Code 整合使用手冊

### 7.1 同時使用 Pencil MCP + Figma MCP

```bash
# .claude/settings.json
{
  "mcpServers": {
    "figma": {
      "url": "https://mcp.figma.com/mcp"
    },
    "pencil": {
      "command": "pencil",
      "args": ["mcp"]
    }
  }
}
```

**使用場景**：
```
Claude Code Prompt:
"Read my dashboard design from dashboard.pen (Pencil),
 and also read the design tokens from my Figma file:
 https://www.figma.com/design/xxx/file

 Generate a React component that:
 1. Follows the layout from the .pen file
 2. Uses tokens from Figma Variables
 3. Uses components from src/components/"
```

### 7.2 搭配規格文件的 Prompt 策略

```
最佳 Prompt 結構：

"Context:
 - Design System: [reference to 00_foundations_spec.md tokens]
 - Component Library: [reference to 01_components_spec.md]
 - Pattern: [reference to 02_patterns_spec.md - Data Table Pattern]
 - Template: [reference to 03_templates_spec.md - List Page Template]

 Task:
 Implement the user list page using the List Page Template.
 Include search, filter, and pagination per our Data Table Pattern.

 Source:
 - Figma: [paste Figma URL]
 - Or: Read users-list.pen

 Output:
 - React component at src/pages/UserList.tsx
 - Use Tailwind CSS with our design tokens
 - All states: loading, empty, error, populated"
```

### 7.3 批量生產 Prompt

```
當你需要快速產出多個頁面：

"Based on our design system specs in design-system-specs/,
 generate the following pages:

 1. Dashboard (03_templates - Dashboard Template)
 2. User List (03_templates - List Page Template)
 3. User Detail (03_templates - Detail Page Template)
 4. Settings (03_templates - Settings Page Template)

 For each page:
 - Create a React component in src/pages/
 - Include all states (loading/empty/error)
 - Follow 02_patterns for interactions
 - Use components from src/components/
 - Apply tokens from tokens.json"
```

---

## 8. 工業化 Pipeline 架構

### 8.1 完整 Pipeline

```
┌─────────────────────────────────────────────────────────┐
│                  DESIGN PIPELINE                        │
│                                                         │
│  Input                                                  │
│  ├── PRD / User Story                                   │
│  ├── wireframe sketch (optional)                        │
│  └── existing Design System (Figma)                     │
│                                                         │
│  Phase 1: Token & System Setup (一次性)                 │
│  ├── Figma Variables → tokens.json                      │
│  ├── Code Connect mapping                               │
│  ├── design-rules.md (AI 規則檔)                        │
│  └── 00-99 規格文件定義                                  │
│                                                         │
│  Phase 2: Design (每個功能/頁面)                        │
│  ├── Option A: Pencil prompt → .pen → Git               │
│  ├── Option B: Figma design → MCP 讀取                  │
│  └── Option C: 直接用 spec prompt（無設計稿）            │
│                                                         │
│  Phase 3: Code Generation                               │
│  ├── Claude Code reads design source                    │
│  ├── Applies tokens + components + patterns             │
│  ├── Generates React/Next.js components                 │
│  └── Includes all states + RWD + a11y                   │
│                                                         │
│  Phase 4: Verification                                  │
│  ├── Design QA checklist (99_documentation_spec.md)     │
│  ├── Code-to-Canvas 回寫 Figma 驗證                     │
│  ├── Storybook 視覺驗證                                  │
│  └── Automated tests                                    │
│                                                         │
│  Phase 5: Version & Ship                                │
│  ├── Git commit (.pen + code + tokens)                  │
│  ├── PR review                                          │
│  ├── Change log update                                  │
│  └── Deploy                                             │
│                                                         │
│  Output                                                 │
│  ├── Production React components                        │
│  ├── Figma Library (synced)                             │
│  ├── Design tokens (synced)                             │
│  └── Change log                                         │
└─────────────────────────────────────────────────────────┘
```

### 8.2 速度指標

| 任務 | 傳統 | AI Pipeline | 加速倍數 |
|------|------|------------|---------|
| 新頁面設計 | 4-8 小時 | 20-40 分鐘 | 6-12x |
| 設計→程式碼 | 1-2 天 | 10-30 分鐘 | 24-48x |
| Design System 初始化 | 2-4 週 | 2-3 天 | 5-10x |
| 新元件（設計+程式碼） | 4-8 小時 | 30-60 分鐘 | 4-8x |
| Token 同步 | 手動 2-4 小時 | 自動（即時） | ∞ |

---

## 9. Design Token 自動化流程

### 9.1 Token 生命週期

```
Define (Figma)
  → Export (Token Studio plugin)
  → Transform (Style Dictionary)
  → Consume (CSS / Tailwind / React)
  → Verify (CI/CD)
  → Update (repeat)
```

### 9.2 Token 格式（W3C Design Token）

```json
{
  "color": {
    "brand": {
      "primary": {
        "$type": "color",
        "$value": "#2563EB",
        "$description": "Primary brand color for CTA buttons"
      }
    },
    "text": {
      "primary": {
        "$type": "color",
        "$value": "{color.neutral.900}",
        "$description": "Main text color"
      }
    }
  },
  "space": {
    "4": {
      "$type": "dimension",
      "$value": "16px",
      "$description": "Standard component spacing"
    }
  }
}
```

### 9.3 自動化腳本

```bash
# Token 同步腳本（加入 CI/CD 或 Git hooks）

# 1. 從 Figma 拉取最新 tokens
claude code "Use Figma MCP to get_variable_defs from
  https://www.figma.com/design/xxx/file
  and save as design/tokens/tokens.json"

# 2. 用 Style Dictionary 轉換
npx style-dictionary build

# 3. 輸出
#    → src/styles/tokens.css (CSS Variables)
#    → tailwind.config.js (Tailwind theme)
#    → src/tokens/index.ts (TypeScript constants)
```

---

## 10. 團隊協作與規模化

### 10.1 角色與工具對應

| 角色 | 主要工具 | 工作流 |
|------|---------|--------|
| 設計師 | Figma + Pencil | 定義 Design System → 設計頁面 → 產出 .pen / Figma frame |
| 前端工程師 | Claude Code + Figma MCP | 讀取設計 → 生成程式碼 → 驗收 |
| 產品經理 | Pencil（快速原型） | 用自然語言描述需求 → 快速生成原型 → 討論 |
| QA | Design QA Checklist | 對照設計稿驗收 → Code-to-Canvas 回寫驗證 |

### 10.2 Git 工作流

```
main
├── feature/user-list
│   ├── design/pages/user-list.pen    ← 設計（.pen 可 diff）
│   ├── src/pages/UserList.tsx        ← 程式碼
│   └── CHANGELOG.md                  ← 變更紀錄
│
├── design-system/add-date-picker
│   ├── design/tokens/tokens.json     ← Token 更新
│   ├── src/components/DatePicker.tsx  ← 新元件
│   └── 01_components_spec.md         ← 規格更新
```

### 10.3 CI/CD 整合

```yaml
# .github/workflows/design-sync.yml
name: Design Token Sync

on:
  push:
    paths:
      - 'design/tokens/**'

jobs:
  sync:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Build tokens
        run: npx style-dictionary build
      - name: Check token diff
        run: git diff --exit-code src/styles/tokens.css
      - name: Alert if tokens changed
        if: failure()
        run: echo "::warning::Design tokens have been updated!"
```

---

## 11. 與現有 Pipeline 的整合

### 本專案結構的對應關係

```
現有 Pipeline                    ↔  AI 工業化工具
─────────────────────────────────────────────────────
global/BASE_DESIGN_SYSTEM.md     ↔  Figma Variables + tokens.json
global/SYSTEM_DOCUMENT_SPEC.md   ↔  00_foundations_spec.md（詳細版）
modules/MODULE_REGISTRY.md       ↔  01_components_spec.md + 02_patterns_spec.md
pages/page_template.md           ↔  03_templates_spec.md
assembly/PIPELINE_ORCHESTRATOR   ↔  Claude Code + MCP prompt
guides/quality_checklist.md      ↔  99_documentation_spec.md（QA 部分）
references/website_recipes.md    ↔  03_templates_spec.md（Template Selection）
```

### 升級路徑

```
Phase 1（立即可做）：
  ✅ 把 00-99 規格文件放入專案
  ✅ 安裝 Figma MCP
  ✅ 用 Claude Code 讀規格文件 + Figma 設計生成程式碼

Phase 2（團隊準備好後）：
  ✅ 安裝 Pencil，建立 .pen 工作流
  ✅ 設定 Token Studio → Style Dictionary pipeline
  ✅ 建立 Code Connect mapping

Phase 3（規模化）：
  ✅ CI/CD token sync
  ✅ Design QA 自動化
  ✅ 多人協作 Git workflow
```

---

## 附：第三方替代工具

| 類別 | 工具 | 定位 |
|------|------|------|
| Design-to-Code | Locofy.ai | Figma → React/Vue/Flutter |
| Design-to-Code | Builder.io | 視覺編輯器 + 程式碼生成 |
| UI 生成 | Vercel v0 | 文字 → React + Tailwind |
| Design System 平台 | Supernova.io | Design System 管理 + MCP |
| Token 管理 | Tokens Studio | Figma Token 管理 + sync |
| 設計 AI | Uizard | 手繪 → 原型 |
| 網頁→Figma | html.to.design | 網頁截圖 → Figma 圖層 |
| 開源替代 | OpenPencil | MIT license Pencil 替代 |
| Community MCP | claude-talk-to-figma | 雙向讀寫 Figma（免費帳號可用） |

---

## 速查口訣

```
一個系統：Design Token（貫穿一切的血液）
兩個引擎：Pencil（速度）+ Figma（系統）
三個橋：Pencil MCP + Figma MCP + Code Connect
四個流程：定義→設計→生成→驗證
五層規格：00 Foundations → 01 Components → 02 Patterns → 03 Templates → 99 Documentation
```

---

**版本**：v1.0
**最後更新**：2026-03-17
**相關文件**：所有 `design-system-specs/` 下的規格文件
