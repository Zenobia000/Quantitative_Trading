# 網站積木模組檢索矩陣 (Website × Module Matrix)

> 類型只是比例差異。不同網站只是不同模組的深度加權。

**圖例：** ⬜ 不需要 ｜ 🟡 L1 基礎 ｜ 🟠 L2 標準 ｜ 🔴 L3 企業級

---

## 主矩陣

| 網站類型 | Identity | Content | Commerce | Delivery | Community | Growth | Admin | Infra |
|---------|----------|---------|----------|----------|-----------|--------|-------|-------|
| **Landing Page** | ⬜ | 🟠 | 🟡 | ⬜ | ⬜ | 🟠 | ⬜ | 🟡 |
| **企業官網** | ⬜ | 🟠 | ⬜ | ⬜ | ⬜ | 🟠 | 🟡 | 🟡 |
| **Blog / 媒體** | 🟡 | 🔴 | ⬜ | ⬜ | 🟡 | 🟠 | 🟠 | 🟡 |
| **個人作品集** | ⬜ | 🟠 | ⬜ | ⬜ | ⬜ | 🟡 | ⬜ | 🟡 |
| **活動/課程報名** | 🟡 | 🟡 | 🟠 | 🟡 | ⬜ | 🟠 | 🟡 | 🟡 |
| **SaaS 產品** | 🔴 | 🟡 | 🟠 | 🔴 | 🟡 | 🟠 | 🟠 | 🔴 |
| **電商** | 🟠 | 🟠 | 🔴 | 🟠 | 🟡 | 🟠 | 🟠 | 🟠 |
| **EdTech 教育** | 🟠 | 🟠 | 🟠 | 🔴 | 🟠 | 🟠 | 🟠 | 🟠 |
| **社群平台** | 🔴 | 🟠 | 🟡 | 🟡 | 🔴 | 🟠 | 🟠 | 🔴 |
| **Marketplace** | 🔴 | 🟠 | 🔴 | 🟠 | 🟠 | 🟠 | 🔴 | 🔴 |

---

## 複雜度排序（由簡到繁）

| 排名 | 網站類型 | 模組數 | 最高深度 | Vibe Coding 難度 |
|------|---------|--------|---------|-----------------|
| 1 | Landing Page | 3 | L2 | ⭐ 半天可完成 |
| 2 | 個人作品集 | 3 | L2 | ⭐ 半天可完成 |
| 3 | 企業官網 | 4 | L2 | ⭐⭐ 一天可完成 |
| 4 | Blog / 媒體 | 5 | L3 | ⭐⭐ 一天可完成 |
| 5 | 活動/課程報名 | 6 | L2 | ⭐⭐ 一天可完成 |
| 6 | 電商 | 7 | L3 | ⭐⭐⭐ 需多天迭代 |
| 7 | EdTech 教育 | 8 | L3 | ⭐⭐⭐ 需多天迭代 |
| 8 | SaaS 產品 | 7 | L3 | ⭐⭐⭐⭐ 需系統架構 |
| 9 | 社群平台 | 7 | L3 | ⭐⭐⭐⭐ 需系統架構 |
| 10 | Marketplace | 8 | L3 | ⭐⭐⭐⭐⭐ 需工程團隊 |

---

## MVP 最小積木集合

### Tier 1：純展示型（無需後端）

**Landing Page / 作品集 / 企業官網**

```
必要：Content (L2) + Growth (L1-L2) + Infra (L1)
可選：Commerce (L1) — 若需要 CTA 導購
```

### Tier 2：單向交易型（需要收錢或收資料）

**活動報名 / 課程銷售頁**

```
必要：Content (L1) + Commerce (L2) + Growth (L2) + Infra (L1)
可選：Identity (L1) + Delivery (L1) — 若需要登入看內容
```

### Tier 3：雙向互動型（需要後端 + 用戶狀態）

**Blog / 電商 / EdTech**

```
必要：Identity (L2) + Content (L2) + Commerce (L2) + Delivery (L2) + Admin (L2) + Infra (L2)
可選：Community (L1) + Growth (L2)
```

### Tier 4：平台型（需要完整系統架構）

**SaaS / 社群 / Marketplace**

```
必要：全部 8 模組，多數 L2-L3
關鍵：Identity (L3) + Infra (L3) 是基底
差異：SaaS 重 Delivery / 社群重 Community / Marketplace 重 Commerce + Admin
```

---

## 三層架構對照

每種網站都可以用三層來拆解開發順序：

| 層級 | 說明 | 對應模組 |
|------|------|----------|
| **Public Layer（公域層）** | 訪客可見的頁面 | Content + Growth |
| **Conversion Layer（轉換層）** | 讓訪客變用戶/買家 | Identity + Commerce |
| **Product Layer（產品層）** | 用戶登入後的核心體驗 | Delivery + Community + Admin |
| **Infrastructure Layer** | 支撐一切的底層 | Infrastructure |

**Vibe Coding 建議開發順序：** Public → Conversion → Product → Infrastructure

先做看得到的，再做看不到的。先讓訪客進來，再讓他留下。

---

## 使用方式

1. **確認你的網站類型** → 在主矩陣中找到對應列
2. **看哪些模組亮燈** → 🟡🟠🔴 的就是你需要的積木
3. **查 MODULE_REGISTRY.md** → 看每個模組的具體功能清單
4. **決定 MVP 範圍** → 參考 MVP 最小積木集合
5. **去 website_recipes.md** → 取得完整配方和提示詞起手式
