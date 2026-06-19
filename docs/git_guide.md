# Git 操作指南

本專案採用 GitHub 為主開發平台，GitLab（NTU）作為備份與鏡像同步。

## 一、開發者初始設定（只需做一次）

### 1. clone 專案
```bash
git clone https://github.com/tofudoctor/Intelligent-Invoice-Management-and-Automated-Reconciliation-System.git
cd Intelligent-Invoice-Management-and-Automated-Reconciliation-System
```

### 2. 設定你的 Git 使用者資訊(local)：

```bash
git config user.email "你的學校信箱"
```

### 3. 在 GitHub 加入學校信箱

請到 GitHub 設定：

Settings → Emails → Add email
![image](/docs/images/email_setting.png)

加入你的學校信箱，確保 commit 作者正確顯示

## 二、日常開發流程

### 1. 從 main 開新分支

```bash
git checkout main
git pull origin main
git checkout -b 分支名稱
```
若有舊分支：
```bash
git checkout 分支名稱
```

### 2. 開發並提交

```bash
git add .
git commit -m "描述你的修改"
```

### 3. 推送到 GitHub

```bash
git push origin 分支名稱
```

### 4. 開 Pull Request(PR) & 合併(Merge)

到 GitHub：

* 建立 PR（分支 → main）
* Code Review
* 在 GitHub 上完成 merge

### 5. 更新本地 main

```bash
git checkout main
git pull origin main
```

### 6. 刪除分支

PR merge 成功後：

* 在 GitHub 上：點擊 Delete branch

或在本地：

```bash
git branch -d 分支名稱
git push origin --delete 分支名稱
```

### 7. 同步

當 PR merge 後：
* GitHub 會自動同步到 GitLab  
* 無需手動操作 GitLab

## 三、重要規範

### 禁止直接操作 GitLab

禁止：

* 在 GitLab commit
* 在 GitLab merge
* 在 GitLab 建 branch

GitLab 是鏡像(mirror)，不是主 repo


### 禁止直接 push main

請務必使用：

* Pull Request

### Git Branch 命名規範

格式：
```
type/description
```

- feature/xxx：新功能
- bugfix/xxx：修 bug
- refactor/xxx：重構
- docs/xxx：文件

範例：  
- feature/login-api  
- bugfix/login-crash  
- refactor/auth-service  
- docs/readme-update


### Git Commit 命名規範

格式：
```
[type] description
```

- feat: 新功能
- fix: 修 bug
- refactor: 重構
- docs: 文件
- test: 測試
- chore: 雜項

範例：  
- [feat] add login API  
- [fix] handle null user  
- [refactor] simplify auth flow  
- [docs] update README setup guide  
- [test] add login unit tests  
- [chore] update dependencies  


## 四、常見錯誤

### GitLab 顯示不是你的名字

原因：email 不一致

解法：

```bash
git config user.email "你的學校信箱"
```

### push 被拒絕

先更新：

```bash
git pull origin main
```

### merge 衝突

```bash
git pull origin main
git merge main
```
手動解決後再 commit

### 當 main 有更新時（同步分支）

若開發中的分支需要最新 main 的內容：

```bash
git checkout 分支名稱
git pull origin main
git merge main
git push origin 分支名稱
```