# Y/NK Blog — 自動上傳設定指南

## 整體架構

```
每週排程觸發
    ↓
Cowork 搜尋本週新聞 → 選題 → 寫文章
    ↓
Python 腳本將文章插入 index.html 的 articles 陣列
    ↓
git commit + push 到 GitHub
    ↓
GitHub Pages 自動部署
    ↓
https://你的帳號.github.io/ynk-blog/ 更新完成
```

---

## 一次性設定（只需做一次）

### Step 1：建立 GitHub Repository

1. 到 https://github.com/new 建立新 repo
2. 設定：
   - Repository name：`ynk-blog`
   - 選 **Public**（GitHub Pages 免費方案需要 public）
   - 不要勾選 Add README
3. 點 Create repository

### Step 2：把 blog 資料夾推上 GitHub

打開你電腦的終端機（Terminal / CMD），執行：

```bash
cd /你的blog資料夾路徑/blog

git init
git add index.html banner.jpg logo.jpg add_article.py
git commit -m "Initial commit: Y/NK blog"
git branch -M main
git remote add origin https://github.com/你的帳號/ynk-blog.git
git push -u origin main
```

### Step 3：啟用 GitHub Pages

1. 到 GitHub repo → Settings → Pages
2. Source 選 **Deploy from a branch**
3. Branch 選 **main** / **(root)**
4. 點 Save
5. 等 1-2 分鐘，你的 blog 就上線了

### Step 4：設定 Git 認證（讓自動化腳本能 push）

推薦用 GitHub CLI（gh）來設定認證：

```bash
# 安裝 GitHub CLI（如果還沒有）
# Windows: winget install GitHub.cli
# Mac: brew install gh

# 登入
gh auth login

# 選擇 GitHub.com → HTTPS → Login with a web browser
# 按照提示完成登入
```

或者用 Personal Access Token：

1. GitHub → Settings → Developer settings → Personal access tokens → Tokens (classic)
2. Generate new token → 勾選 `repo` 權限
3. 設定 git 記住密碼：
   ```bash
   git config --global credential.helper store
   ```
4. 下次 push 時輸入帳號和 token，之後就不用再輸入了

### Step 5（可選）：自訂域名

如果你想用 `youngboynotkid.com`：

1. 在 blog 資料夾建立 `CNAME` 檔案，內容只有一行：
   ```
   youngboynotkid.com
   ```
2. 到你的域名 DNS 設定，加入：
   - CNAME 記錄：`www` → `你的帳號.github.io`
   - A 記錄：`@` → `185.199.108.153`（GitHub Pages IP）
3. 在 GitHub Pages 設定中填入 Custom domain

---

## 自動化流程說明

設定完成後，Cowork 的排程任務會每週自動執行：

1. **搜尋新聞**：用 WebSearch 搜尋本週台灣與國際時事
2. **選題撰文**：以 Y/NK 人設寫出 300-500 字的週記
3. **插入文章**：用 `add_article.py` 把新文章加進 `index.html`
4. **Git 推送**：自動 commit 並 push 到 GitHub
5. **自動部署**：GitHub Pages 收到 push 後自動更新網站

你完全不需要手動操作。每週一早上打開 blog 就能看到新文章。

---

## 檔案說明

| 檔案 | 用途 |
|------|------|
| `index.html` | Blog 主頁面，文章資料存在 JS 的 articles 陣列裡 |
| `add_article.py` | 自動插入新文章的 Python 腳本 |
| `banner.jpg` | 首頁 banner 圖片 |
| `logo.jpg` | Logo 圖片 |
| `SETUP-GUIDE.md` | 這份指南（你正在看的） |
