# 網站配方大全 (Website Recipes)

> 查表 → 拿配方 → 組裝 → 出網站
> 每種原型包含：積木配方 + Reference 網站 + Lovable 提示詞起手式

---

## 1. Landing Page（行銷著陸頁）

### 一句話定義
單頁面，單一目標，把訪客轉化為潛在客戶或買家。

### 商業目標
流量 → 單一 CTA 轉化（報名/購買/訂閱/諮詢）

### 積木配方

| 模組 | 深度 | 具體功能 |
|------|------|----------|
| Content | L2 | Hero + Feature + Testimonials + FAQ |
| Growth | L2 | SEO + CTA + Email 收集 + Analytics |
| Commerce | L1 | 定價展示 / 購買按鈕（可選） |
| Infra | L1 | 靜態託管 + CDN |

### MVP 最小集合
Hero Section + CTA + 一個表單

### 推薦頁面
`/`（單頁，用 Anchor 導覽）

### Reference 網站
- **Linear** (linear.app) — 極簡科技感，動畫流暢，CTA 明確
- **Notion** (notion.so) — 場景化展示，Social Proof 強
- **Cal.com** (cal.com) — 開源產品 Landing，清晰的 Feature/Pricing

### Lovable 提示詞起手式

```
建立一個現代化的 Landing Page，用於推廣 [你的產品/服務名稱]。

目標受眾：[描述]
核心價值主張：[一句話]
CTA 目標：[報名/購買/訂閱/聯繫]

頁面結構（由上到下）：
1. Hero Section：大標題 + 副標題 + CTA 按鈕 + 產品截圖/插圖
2. Social Proof：客戶 Logo 列 或 用戶數量
3. Feature Section：3-4 個核心功能，圖標 + 標題 + 說明
4. Testimonials：2-3 則用戶評價，含頭像和職稱
5. Pricing（可選）：2-3 個方案卡片
6. FAQ：5-6 個常見問題，手風琴展開
7. Final CTA：重複主要 CTA
8. Footer：Logo + 連結 + 社群 + 版權

設計風格：[簡潔現代 / 溫暖親切 / 科技專業]
主色調：[色值或描述]
響應式：Desktop + Mobile
```

---

## 2. 企業官網 (Corporate Website)

### 一句話定義
多頁面品牌展示站，建立信任、傳遞價值、引導諮詢。

### 商業目標
品牌認知 → 信任建立 → 諮詢/合作轉化

### 積木配方

| 模組 | 深度 | 具體功能 |
|------|------|----------|
| Content | L2 | 首頁 + 關於 + 服務 + Blog + FAQ |
| Growth | L2 | SEO + CTA + 聯絡表單 + Analytics |
| Admin | L1 | 基本內容管理 |
| Infra | L1 | 靜態託管 + CDN |

### MVP 最小集合
首頁 + 關於 + 服務 + 聯絡

### 推薦頁面
`/` `/about` `/services` `/blog` `/contact` `/faq`

### Reference 網站
- **Stripe** (stripe.com) — 企業級但不無聊，動畫精緻
- **Vercel** (vercel.com) — 開發者品牌典範，黑白極簡
- **Basecamp** (basecamp.com) — 有態度的品牌表達

### Lovable 提示詞起手式

```
建立一個專業的企業官網，品牌名稱為 [名稱]。

品牌定位：[描述]
目標受眾：[描述]
核心服務：[1. xxx 2. xxx 3. xxx]

需要以下頁面：
1. 首頁：Hero + 服務概覽 + 客戶見證 + CTA
2. 關於我們：品牌故事 + 團隊介紹 + 使命願景
3. 服務頁：每個服務的詳細介紹 + 流程說明
4. 聯絡我們：聯絡表單 + 地圖 + 聯絡資訊

全站導覽列 + Footer
設計風格：[描述]
主色調：[色值]
響應式：Desktop + Tablet + Mobile
```

---

## 3. Blog / 媒體站

### 一句話定義
以內容為核心的流量引擎，用優質文章吸引並留住讀者。

### 商業目標
SEO 流量 → 內容消費 → Email 訂閱 / 廣告 / 導購

### 積木配方

| 模組 | 深度 | 具體功能 |
|------|------|----------|
| Content | L3 | CMS + 分類標籤 + 搜尋 + RSS |
| Growth | L2 | SEO + Newsletter + 社群分享 + Analytics |
| Community | L1 | 留言系統 |
| Admin | L2 | 文章管理 + 數據報表 |
| Identity | L1 | 作者/訂閱者帳號 |
| Infra | L1 | CDN + 快取 |

### MVP 最小集合
文章列表 + 文章頁 + 分類 + Newsletter 表單

### 推薦頁面
`/` `/blog` `/blog/[slug]` `/category/[name]` `/about` `/subscribe`

### Reference 網站
- **Smashing Magazine** (smashingmagazine.com) — 內容優先的排版典範
- **The Verge** (theverge.com) — 視覺強烈的媒體站
- **Paul Graham Essays** (paulgraham.com/articles.html) — 極簡文字導向

### Lovable 提示詞起手式

```
建立一個現代化的 Blog 網站，主題為 [你的主題]。

內容類型：[技術文章 / 商業洞察 / 生活分享]
目標讀者：[描述]

頁面結構：
1. 首頁：最新文章列表（卡片式）+ 精選文章 + Newsletter 訂閱
2. 文章頁：標題 + 作者 + 日期 + 正文（Markdown 渲染）+ 社群分享按鈕 + 相關文章推薦
3. 分類頁：按標籤/分類篩選文章
4. 關於頁：作者介紹

側邊欄（Desktop）：分類列表 + 熱門文章 + Newsletter
響應式：Desktop + Mobile
SEO 優化：語意化 HTML + Meta tags
```

---

## 4. 個人作品集 (Portfolio)

### 一句話定義
展示個人能力和作品的名片式網站。

### 商業目標
展示能力 → 獲取工作/合作機會

### 積木配方

| 模組 | 深度 | 具體功能 |
|------|------|----------|
| Content | L2 | 首頁 + 作品 Gallery + 關於 |
| Growth | L1 | 基本 SEO + 社群連結 |
| Infra | L1 | 靜態託管 |

### MVP 最小集合
首頁 + 作品列表 + 聯絡方式

### 推薦頁面
`/` `/work` `/work/[slug]` `/about` `/contact`

### Reference 網站
- **Brittany Chiang** (brittanychiang.com) — 開發者作品集標竿
- **Lapa Ninja** (lapa.ninja) — 設計師作品集靈感庫
- **Minimal Portfolio** 風格 — 黑白極簡，作品說話

### Lovable 提示詞起手式

```
建立一個極簡風格的個人作品集網站。

姓名：[名字]
職業：[職稱]
專長：[1. xxx 2. xxx 3. xxx]

頁面結構：
1. 首頁：大字名稱 + 一句話介紹 + 精選作品（3-4 個）+ 聯絡 CTA
2. 作品頁：作品 Grid（圖片 + 標題 + 簡述），點擊進入詳情
3. 作品詳情：大圖 + 專案描述 + 我的角色 + 成果
4. 關於：照片 + 自我介紹 + 技能列表 + 經歷時間軸

設計：黑白為主，作品圖片是唯一色彩來源
動畫：微妙的滾動淡入
```

---

## 5. 活動/課程報名頁

### 一句話定義
製造急迫感，將有興趣的人轉化為報名者。

### 商業目標
認知 → 急迫感 → 報名轉化

### 積木配方

| 模組 | 深度 | 具體功能 |
|------|------|----------|
| Content | L1 | 活動介紹 + 講師 + 議程 |
| Commerce | L2 | 報名表單 + 金流 + 發票 |
| Growth | L2 | Countdown + CTA + Email 確認 |
| Identity | L1 | 報名者帳號（可選） |
| Delivery | L1 | 報名確認信 + 行前通知 |
| Admin | L1 | 報名管理 |
| Infra | L1 | 靜態託管 + 表單後端 |

### MVP 最小集合
活動介紹 + 倒數計時 + 報名表單 + 付款

### 推薦頁面
`/`（單頁為主）或 `/` + `/register` + `/confirmation`

### Reference 網站
- **WWDC** (developer.apple.com/wwdc) — 頂級活動頁面設計
- **Web Summit** (websummit.com) — 大型活動的轉化頁面
- **Accupass** (accupass.com) 活動頁 — 台灣在地的活動報名範本

### Lovable 提示詞起手式

```
建立一個課程/活動報名頁面。

活動名稱：[名稱]
日期：[日期]
地點：[地點/線上]
票價：[金額]
限額：[人數]

頁面結構（單頁）：
1. Hero：活動名稱 + 日期地點 + 倒數計時器 + 報名按鈕
2. 活動亮點：3-4 個你會學到的重點
3. 講師介紹：照片 + 經歷 + 一段話
4. 詳細議程：時間軸式排列
5. 學員見證：2-3 則過往學員評價
6. 票種與價格：早鳥/原價/雙人票
7. FAQ：5-6 個常見問題
8. Final CTA：倒數 + 剩餘名額 + 報名按鈕

設計重點：急迫感（倒計時 + 剩餘名額）
```

---

## 6. SaaS 產品

### 一句話定義
軟體即服務，用戶登入後使用核心功能，按月/年訂閱。

### 商業目標
註冊 → 試用 → 付費訂閱 → 留存

### 積木配方

| 模組 | 深度 | 具體功能 |
|------|------|----------|
| Identity | L3 | 註冊/登入 + RBAC + 組織管理 |
| Content | L1 | Landing Page + Docs |
| Commerce | L2 | 訂閱制 + Pricing + 帳務 |
| Delivery | L3 | 核心 Dashboard + 配額控制 + Feature Flag |
| Community | L1 | Changelog + Feedback |
| Growth | L2 | 試用引導 + Email 自動化 |
| Admin | L2 | 用戶管理 + 數據報表 |
| Infra | L3 | 完整後端 + DB + Cache + Queue + 監控 |

### MVP 最小集合
Landing + 註冊登入 + 一個核心功能 + Pricing

### 推薦頁面
**Public:** `/` `/pricing` `/docs` `/login` `/signup`
**App:** `/dashboard` `/settings` `/billing`
**Admin:** `/admin/users` `/admin/analytics`

### Reference 網站
- **Linear** (linear.app) — SaaS 設計標竿
- **Notion** (notion.so) — 產品導向增長典範
- **Supabase** (supabase.com) — 開發者 SaaS 最佳實踐

### Lovable 提示詞起手式

```
建立一個 SaaS 產品的 Landing Page + 基礎 App 框架。

產品名稱：[名稱]
一句話描述：[做什麼用的]
目標用戶：[描述]
核心功能：[1. xxx 2. xxx 3. xxx]

需要以下部分：

A. Landing Page（公開）：
   - Hero + Feature + Pricing (Free/Pro/Enterprise) + CTA

B. App 框架（登入後）：
   - 側邊欄導覽 + 頂部 Header（用戶頭像 + 通知）
   - Dashboard 首頁（關鍵指標卡片 + 最近活動）
   - [核心功能頁面]
   - Settings（個人設定 + 帳務）

認證：Email + Google OAuth
設計：簡潔專業，側邊欄深色
```

---

## 7. 電商

### 一句話定義
展示商品、促進購買、處理訂單的線上商店。

### 商業目標
瀏覽 → 加入購物車 → 結帳 → 復購

### 積木配方

| 模組 | 深度 | 具體功能 |
|------|------|----------|
| Content | L2 | 商品目錄 + 商品詳情 + Blog |
| Commerce | L3 | 購物車 + 結帳 + 金流 + 發票 + 退款 |
| Identity | L2 | 會員 + 訂單歷史 + 收藏 |
| Delivery | L2 | 出貨追蹤 + 電子商品交付 |
| Growth | L2 | SEO + Email + 推薦 + 折扣碼 |
| Community | L1 | 商品評價 |
| Admin | L2 | 商品管理 + 訂單管理 + 報表 |
| Infra | L2 | DB + CDN + 搜尋引擎 |

### MVP 最小集合
商品列表 + 商品頁 + 購物車 + 結帳

### 推薦頁面
`/` `/products` `/products/[slug]` `/cart` `/checkout` `/account` `/account/orders`

### Reference 網站
- **Apple Store** (apple.com/shop) — 商品展示標竿
- **Shopify Theme Store** — 各類電商模板靈感
- **Pinkoi** (pinkoi.com) — 亞洲設計電商範本

### Lovable 提示詞起手式

```
建立一個電商網站，販售 [商品類型]。

品牌名稱：[名稱]
商品數量：約 [數量] 件
價格範圍：NT$ [範圍]

頁面結構：
1. 首頁：Banner + 推薦商品 + 分類入口 + 新品
2. 商品列表：Grid 排列 + 篩選（分類/價格/排序）
3. 商品詳情：大圖（可切換）+ 名稱 + 價格 + 描述 + 規格選擇 + 加入購物車
4. 購物車：商品清單 + 數量修改 + 小計 + 結帳按鈕
5. 結帳：收件資訊 + 付款方式 + 訂單確認
6. 會員中心：訂單歷史 + 個人資料

響應式：Desktop + Mobile（行動購物優先）
```

---

## 8. EdTech 教育平台

### 一句話定義
線上學習平台，用課程內容交付價值。

### 商業目標
認知 → 試看 → 購課 → 完課 → 復購/推薦

### 積木配方

| 模組 | 深度 | 具體功能 |
|------|------|----------|
| Identity | L2 | 學員帳號 + 講師帳號 |
| Content | L2 | 課程介紹 + Blog + FAQ |
| Commerce | L2 | 課程購買 + 訂閱 + 折扣碼 |
| Delivery | L3 | 影片播放 + 章節進度 + 作業 + 證書 |
| Community | L2 | 討論區 + 互評 |
| Growth | L2 | SEO + Email + 試看 |
| Admin | L2 | 課程上架 + 學員管理 + 營收報表 |
| Infra | L2 | 影片串流 + DB + CDN |

### MVP 最小集合
課程列表 + 課程介紹頁 + 購買 + 學習介面（影片+章節）

### 推薦頁面
**Public:** `/` `/courses` `/courses/[slug]` `/pricing` `/blog`
**App:** `/learn/[course]/[lesson]` `/dashboard` `/certificates`
**Admin:** `/admin/courses` `/admin/students` `/admin/revenue`

### Reference 網站
- **Coursera** (coursera.org) — 課程卡片 + 學習介面
- **Udemy** (udemy.com) — 課程市場模式
- **Hahow** (hahow.in) — 台灣在地 EdTech 範本

### Lovable 提示詞起手式

```
建立一個線上課程平台。

平台名稱：[名稱]
課程主題：[主題領域]
目標學員：[描述]

頁面結構：

A. 公開頁面：
   - 首頁：Hero + 精選課程 + 講師介紹 + 學員見證
   - 課程介紹頁：封面 + 大綱 + 講師 + 評價 + 購買按鈕
   - 課程列表：卡片 Grid + 分類篩選

B. 學習介面（登入後）：
   - 左側：章節列表（含完成狀態勾選）
   - 中央：影片播放器
   - 下方：課程筆記 / 討論區
   - 右上：進度百分比

C. 學員 Dashboard：
   - 進行中的課程 + 已完成的課程 + 證書
```

---

## 9. 社群平台

### 一句話定義
以用戶互動為核心，讓人們連結、分享、討論。

### 商業目標
註冊 → 互動 → 黏著 → 網路效應

### 積木配方

| 模組 | 深度 | 具體功能 |
|------|------|----------|
| Identity | L3 | 個人檔案 + 追蹤/好友 + 權限 |
| Content | L2 | 動態牆 + 文章 + 多媒體 |
| Community | L3 | 討論 + 私訊 + 通知 + 聲望 + UGC |
| Growth | L2 | 推薦演算法 + 通知 + 分享 |
| Commerce | L1 | 付費會員（可選） |
| Delivery | L1 | 會員專屬內容 |
| Admin | L2 | 內容審核 + 用戶管理 |
| Infra | L3 | WebSocket + Queue + Cache + 搜尋 |

### MVP 最小集合
註冊 + 個人頁 + 發文 + 動態牆 + 留言

### Reference 網站
- **Discord** (discord.com) — 社群互動典範
- **Product Hunt** (producthunt.com) — 討論+投票社群
- **Threads** (threads.net) — 極簡社群

### Lovable 提示詞起手式

```
建立一個 [主題] 社群平台的 MVP。

社群主題：[描述]
核心互動：[發文/討論/投票/分享]

頁面結構：
1. 首頁/動態牆：最新貼文 Feed + 發文按鈕
2. 發文介面：文字 + 圖片上傳 + 標籤
3. 貼文詳情：內容 + 按讚 + 留言串
4. 個人頁面：頭像 + 自介 + 我的貼文
5. 通知：互動通知列表

認證：Email + OAuth
即時更新：新留言/按讚即時顯示
```

---

## 10. Marketplace 市集

### 一句話定義
連接買家與賣家的雙邊平台。

### 商業目標
供給 → 需求匹配 → 交易 → 平台抽成

### 積木配方

| 模組 | 深度 | 具體功能 |
|------|------|----------|
| Identity | L3 | 買家帳號 + 賣家帳號 + 驗證 |
| Content | L2 | 商品/服務目錄 + 搜尋 |
| Commerce | L3 | 交易 + 金流 + 平台抽成 + 退款 |
| Delivery | L2 | 訂單追蹤 + 評價 |
| Community | L2 | 買賣家溝通 + 評價系統 |
| Growth | L2 | SEO + 推薦 + 分類 |
| Admin | L3 | 雙邊管理 + 爭議處理 + 營收 |
| Infra | L3 | 完整後端 + 搜尋引擎 + 支付閘道 |

### MVP 最小集合
商品列表 + 搜尋 + 商品頁 + 下單 + 賣家上架

### Reference 網站
- **Airbnb** (airbnb.com) — 雙邊市集設計標竿
- **Fiverr** (fiverr.com) — 服務型市集
- **蝦皮** (shopee.tw) — 亞洲 C2C 市集

### Lovable 提示詞起手式

```
建立一個 [類型] 市集平台的 MVP。

平台名稱：[名稱]
交易類型：[商品/服務/數位內容]
買家是：[描述]
賣家是：[描述]

頁面結構：

A. 公開：
   - 首頁：搜尋框 + 分類 + 推薦列表
   - 搜尋結果：篩選 + 排序 + 列表/Grid 切換
   - 商品/服務詳情：圖片 + 描述 + 價格 + 賣家資訊 + 評價 + 購買

B. 買家：
   - 訂單列表 + 訊息

C. 賣家：
   - 上架管理 + 訂單管理 + 收入報表

D. Admin：
   - 用戶管理 + 爭議處理
```

---

## 使用指南

1. **找到你的類型** → 上面 10 種選最接近的
2. **看積木配方** → 確認需要哪些模組和深度
3. **查 Reference** → 打開參考網站，截圖你喜歡的部分
4. **複製提示詞起手式** → 填入你的具體資訊
5. **搭配 Global Design System** → 確保視覺一致性
6. **逐頁展開** → 用 `pages/page_template.md` 定義每個頁面細節
