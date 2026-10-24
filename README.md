# 🚄 台灣高鐵票務監控系統

自動監控台灣高鐵票務，當有座位釋出時透過 LINE 即時通知您，並提供直達訂票連結。

## ✨ 功能特色

- 🔍 **自動監控**: 使用 GitHub Actions 定時檢查票務狀態（每 15 分鐘）
- 📱 **LINE 通知**: 發現可用座位時立即透過 LINE 推送訊息
- 🌐 **網頁介面**: 透過 GitHub Pages 提供美觀的監控狀態頁面
- ⚙️ **彈性設定**: 支援多個監控項目、時間區間、特定車次等條件
- 🔗 **直達訂票**: 提供官方訂票網站的直接連結
- 🔒 **安全可靠**: 完全不會自動訂票或保留座位，僅提供查詢功能

## 📋 系統架構

```
GitHub Actions (定時執行)
    ↓
檢查票務 (checker.py)
    ↓
發現可用座位 → 發送 LINE 通知
    ↓
更新結果 (results.json)
    ↓
GitHub Pages 顯示結果 (index.html)
```

## 🚀 快速開始

### 步驟 1: Fork 此儲存庫

點擊右上角的 "Fork" 按鈕，將此儲存庫複製到您的 GitHub 帳號。

### 步驟 2: 設定 LINE 通知

#### 2.1 建立 LINE Official Account

1. 前往 [LINE Developers Console](https://developers.line.biz/console/)
2. 使用您的 LINE 帳號登入
3. 點擊「Create a new provider」建立提供者
   - Provider name: 輸入任意名稱（例如：高鐵監控）
4. 點擊「Create a Messaging API channel」
   - Channel name: 輸入頻道名稱（例如：高鐵票務通知）
   - Channel description: 輸入描述
   - Category: 選擇適當的類別
   - Subcategory: 選擇子類別
   - 勾選同意條款
   - 點擊「Create」

#### 2.2 取得 Channel Access Token

1. 進入剛建立的頻道
2. 點擊「Messaging API」分頁
3. 在「Channel access token」區域點擊「Issue」
4. 複製產生的 token（格式類似：`xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx...`）
5. **重要**: 將此 token 妥善保管，不要公開

#### 2.3 取得您的 User ID

方法一：使用官方工具
1. 在手機上加入您的 LINE Official Account 為好友
2. 傳送任意訊息給您的 Official Account
3. 在 LINE Developers Console 中，點擊「Messaging API」分頁
4. 點擊「Webhook」區域的「Verify」或使用以下 Python 腳本：

```python
# get_user_id.py
import requests
import os

token = "YOUR_CHANNEL_ACCESS_TOKEN"
url = "https://api.line.me/v2/bot/followers/ids"
headers = {"Authorization": f"Bearer {token}"}

response = requests.get(url, headers=headers)
print(response.json())
```

方法二：使用簡單的 webhook
1. 設定暫時的 webhook URL (可使用 [webhook.site](https://webhook.site))
2. 在 LINE Developers Console 設定 webhook URL
3. 在手機上傳送訊息給您的 Official Account
4. 在 webhook.site 查看收到的 JSON，找到 `source.userId`

您的 User ID 格式類似：`Uxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx`

### 步驟 3: 設定 GitHub Secrets

1. 在您 Fork 的儲存庫中，點擊「Settings」
2. 在左側選單點擊「Secrets and variables」→「Actions」
3. 點擊「New repository secret」，新增以下 secrets：

| Secret 名稱 | 說明 | 範例 |
|------------|------|------|
| `LINE_CHANNEL_ACCESS_TOKEN` | LINE Messaging API 的 Channel Access Token | `xxxxxxxxxxx...` |
| `LINE_USER_ID` | 您的 LINE User ID | `Uxxxxxxxxx...` |
| `TDX_CLIENT_ID` | (選用) TDX API 的 Client ID | `abc123-xxx` |
| `TDX_CLIENT_SECRET` | (選用) TDX API 的 Client Secret | `1234567890` |

**TDX API 憑證** (選用，但強烈建議設定以取得即時時刻表):
1. 前往 [TDX 運輸資料流通服務平台](https://tdx.transportdata.tw/)
2. 註冊並登入
3. 點擊右上角的使用者名稱 → API Key
4. 建立新的 Client ID 和 Secret
5. 將這兩個值加入 GitHub Secrets

### 步驟 4: 啟用 GitHub Pages

1. 在儲存庫中點擊「Settings」
2. 在左側選單點擊「Pages」
3. 在「Source」選擇「Deploy from a branch」
4. 在「Branch」選擇「main」分支，目錄選擇「/ (root)」
5. 點擊「Save」
6. 等待幾分鐘後，頁面會顯示您的網站 URL（格式：`https://username.github.io/repo-name/`）

### 步驟 5: 設定監控項目

編輯 `watches.yml` 檔案，設定您想監控的車票：

```yaml
watches:
  # 範例 1: 監控時間區間
  - id: taipei-kaohsiung-morning
    enabled: true
    travel_date: "2026-11-01"
    origin: "台北"
    destination: "左營"
    time_range:
      start: "09:00"
      end: "12:00"
    ticket_count: 2
    seat_class: "標準"
  
  # 範例 2: 監控特定車次
  - id: specific-trains
    enabled: true
    travel_date: "2026-11-01"
    origin: "台北"
    destination: "左營"
    train_numbers:
      - "813"
      - "815"
    ticket_count: 1
    seat_class: "商務"
```

**可用車站**:
- 南港、台北、板橋、桃園、新竹、苗栗、台中、彰化、雲林、嘉義、台南、左營

**座位等級**:
- `標準`: 標準車廂
- `商務`: 商務車廂

### 步驟 6: 測試執行

提交 `watches.yml` 的變更後：

1. 前往「Actions」分頁
2. 點擊左側的「高鐵票務監控」workflow
3. 點擊右側的「Run workflow」按鈕手動執行
4. 等待執行完成（約 1-2 分鐘）
5. 檢查 LINE 是否收到測試通知
6. 前往您的 GitHub Pages 網站查看結果

## 📖 設定檔說明

### watches.yml 參數詳解

| 參數 | 必填 | 說明 | 範例 |
|------|------|------|------|
| `id` | ✓ | 監控項目的唯一識別碼 | `watch-1` |
| `enabled` | ✓ | 是否啟用此監控項目 | `true` / `false` |
| `travel_date` | ✓ | 乘車日期 (YYYY-MM-DD) | `2026-11-01` |
| `origin` | ✓ | 起始車站 | `台北` |
| `destination` | ✓ | 目的地車站 | `左營` |
| `time_range` |  | 發車時間範圍 | `{start: "09:00", end: "12:00"}` |
| `train_numbers` |  | 特定車次列表 | `["813", "815"]` |
| `ticket_count` | ✓ | 需要的票數 | `2` |
| `seat_class` | ✓ | 座位等級 | `標準` / `商務` |

**注意**: `time_range` 和 `train_numbers` 二選一，或兩者都不設定（監控全天所有車次）。

## 🔧 進階設定

### 調整檢查頻率

編輯 `.github/workflows/monitor.yml`，修改 cron 表達式：

```yaml
schedule:
  # 每 15 分鐘: */15 * * * *
  # 每 10 分鐘: */10 * * * *
  # 每小時: 0 * * * *
  - cron: '*/15 * * * *'
```

**注意**: GitHub Actions 的 cron 可能會延遲 5-10 分鐘執行。

### 停用監控項目

在 `watches.yml` 中將 `enabled` 設為 `false`:

```yaml
- id: my-watch
  enabled: false
  # ... 其他設定
```

## 🛠️ 技術細節

### 資料來源

1. **TDX 運輸資料流通服務平台**
   - 提供高鐵即時時刻表
   - 需要申請 API 金鑰（免費）
   - 資料更新頻率：即時

2. **台灣高鐵官方網站**
   - 訂票連結產生
   - 注意：查詢功能有驗證碼保護

### 通知機制

系統會記錄上次檢查的結果，只有在以下情況才會發送通知：
- 首次發現符合條件的車次
- 之前無票，現在有票的車次

這可以避免重複通知相同的車次。

### 限制與注意事項

1. **不會自動訂票**: 本系統僅提供查詢和通知功能，不會執行任何訂票操作
2. **需手動訂票**: 收到通知後，請點擊連結前往官方網站手動訂票
3. **驗證碼限制**: 高鐵官網的查詢功能有驗證碼保護，可能影響自動查詢的準確性
4. **TDX 資料限制**: TDX API 主要提供時刻表，即時座位資訊可能有限
5. **執行頻率**: GitHub Actions 的免費額度為每月 2,000 分鐘，請合理設定檢查頻率
6. **時區**: 所有時間均使用台灣時區 (UTC+8)

## 🧪 測試

執行單元測試：

```bash
python -m pytest tests/ -v
```

## 📊 查看結果

### 網頁介面

前往您的 GitHub Pages 網址（例如：`https://username.github.io/repo-name/`）查看：
- 目前啟用的監控項目
- 最新檢查結果
- 可用車次與訂票連結

### 原始資料

檢查 `results.json` 檔案查看詳細的 JSON 格式結果。

## ❓ 常見問題

### Q: 為什麼沒有收到 LINE 通知？

A: 請檢查：
1. LINE Channel Access Token 是否正確設定在 GitHub Secrets
2. LINE User ID 是否正確
3. 是否已將 Official Account 加為好友
4. 檢查 GitHub Actions 的執行記錄是否有錯誤

### Q: 如何確認 User ID 是否正確？

A: 可以使用以下 Python 腳本測試：

```python
import requests

token = "YOUR_CHANNEL_ACCESS_TOKEN"
user_id = "YOUR_USER_ID"

url = "https://api.line.me/v2/bot/message/push"
headers = {
    "Content-Type": "application/json",
    "Authorization": f"Bearer {token}"
}
payload = {
    "to": user_id,
    "messages": [{"type": "text", "text": "測試訊息"}]
}

response = requests.post(url, headers=headers, json=payload)
print(f"Status: {response.status_code}")
print(f"Response: {response.text}")
```

### Q: 可以監控多個日期嗎？

A: 可以，只需在 `watches.yml` 中新增多個監控項目，每個項目設定不同的日期即可。

### Q: GitHub Actions 的執行時間準確嗎？

A: GitHub Actions 的 cron 執行可能會延遲，建議設定較短的時間間隔以確保及時性。

### Q: 需要付費嗎？

A: 完全免費！GitHub Actions、GitHub Pages、LINE Messaging API 都提供免費方案，足夠個人使用。

## 🤝 貢獻

歡迎提交 Issue 或 Pull Request！

## 📄 授權

MIT License

## ⚠️ 免責聲明

本專案僅供個人學習與使用，請勿用於商業用途。使用本系統時請遵守台灣高鐵官方網站的使用條款。本專案不對任何因使用本系統而產生的損失負責。

## 🔗 相關連結

- [台灣高鐵官方網站](https://www.thsrc.com.tw/)
- [TDX 運輸資料流通服務](https://tdx.transportdata.tw/)
- [LINE Developers](https://developers.line.biz/)
- [GitHub Actions 文件](https://docs.github.com/en/actions)
- [GitHub Pages 文件](https://docs.github.com/en/pages)

---

如有任何問題或建議，歡迎開 Issue 討論！
