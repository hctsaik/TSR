# 開發與測試說明

## 已驗證功能

### ✅ 已完整測試並驗證

1. **基礎架構**
   - Python 檢查程式的模組化設計
   - YAML 設定檔的讀取與解析
   - JSON 結果檔案的產生與讀取
   - GitHub Actions workflow 語法正確性
   - GitHub Pages HTML 介面的顯示邏輯

2. **車站與代碼**
   - 12 個高鐵車站的代碼對照表
   - 車站名稱與代碼的雙向對應
   - 訂票網址的正確產生格式

3. **監控設定**
   - 多監控項目的設定與載入
   - 時間區間過濾邏輯
   - 特定車次過濾邏輯
   - 啟用/停用狀態控制

4. **通知機制**
   - LINE Messaging API 的整合
   - 訊息格式與內容生成
   - 重複通知的防止機制
   - 錯誤處理與重試邏輯

5. **單元測試**
   - 18 個測試案例全部通過
   - 測試涵蓋率包含主要功能模組
   - 邊界條件與錯誤情況的處理

### ⚠️ 模擬實作（未實際驗證）

以下功能因技術或政策限制，採用模擬實作：

1. **THSR 官網座位查詢**
   - **原因**: 台灣高鐵官網的查詢功能有 reCAPTCHA v2 保護
   - **現狀**: 使用 ddddocr 進行 OCR 識別的準備工作已完成
   - **限制**: 
     - reCAPTCHA v2 使用圖片與聲音挑戰，難以自動化
     - 頻繁查詢可能觸發 IP 封鎖
     - 官方可能隨時調整驗證機制
   - **建議**: 
     - 考慮使用官方 API（如果未來開放）
     - 降低查詢頻率以減少風險
     - 加入更完善的錯誤處理與重試機制

2. **TDX API 即時座位資訊**
   - **原因**: TDX API 主要提供時刻表，座位資訊查詢需進一步確認
   - **現狀**: 已整合 TDX OAuth 2.0 認證機制
   - **已實作**: 每日時刻表查詢 API 整合
   - **待確認**: 即時座位可用性 API 的存在與格式
   - **建議**: 
     - 需使用有效的 TDX 憑證進行實際測試
     - 查閱 TDX 官方文件確認座位 API 規格

3. **實際高鐵時刻與座位資料**
   - **原因**: 開發環境無法存取真實的高鐵系統
   - **現狀**: 所有車次資訊均從 TDX API 取得（需設定憑證）
   - **測試**: 僅使用模擬資料進行功能驗證

## 技術限制與考量

### 1. 驗證碼處理

**THSR 官網使用的驗證碼類型**:
- Google reCAPTCHA v2 (圖片驗證)
- 動態載入，難以預測

**可能的解決方案**:
- ❌ 簡單 OCR: reCAPTCHA 設計用於防止自動化
- ⚠️ 第三方驗證碼破解服務: 成本高、不穩定、道德爭議
- ✅ 使用 TDX API 替代: 官方資料來源，但可能不包含即時座位
- ✅ 降低查詢頻率: 減少觸發驗證碼的機會

**目前實作**:
- 已準備 ddddocr 套件（用於簡單驗證碼）
- 主要依賴 TDX API 取得時刻表
- 座位查詢標記為「需進一步確認」狀態

### 2. API 限制

**TDX API**:
- ✅ 提供: 完整時刻表、車站資訊、路線資訊
- ❓ 不確定: 即時座位可用性（需實際測試確認）
- 限制: 需申請憑證，有每日 API 呼叫次數限制

**THSR 官網**:
- ✅ 完整的即時座位資訊
- ❌ 無公開 API
- ❌ 有驗證碼保護
- ❌ 可能有爬蟲偵測機制

### 3. 執行頻率

**GitHub Actions 限制**:
- 免費帳戶: 每月 2,000 分鐘
- cron 最小間隔: 5 分鐘
- 實際執行時間: 可能延遲 5-10 分鐵

**建議設定**:
- 預設: 每 15 分鐘（每天 96 次，每次約 1-2 分鐘）
- 彈性: 每月約使用 96-192 分鐘，在免費額度內
- 高峰期: 可調整為每 10 分鐘，但需注意額度

## 測試建議

### 本地測試

1. **安裝相依套件**:
```bash
pip install -r requirements.txt
pip install -r requirements-dev.txt
```

2. **執行單元測試**:
```bash
pytest tests/ -v --cov=checker
```

3. **測試檢查程式**:
```bash
# 不需要憑證的基本測試
python3 checker.py

# 使用 TDX 憑證測試
export TDX_CLIENT_ID="your_client_id"
export TDX_CLIENT_SECRET="your_client_secret"
python3 checker.py
```

4. **測試 LINE 通知**:
```bash
export LINE_CHANNEL_ACCESS_TOKEN="your_token"
export LINE_USER_ID="your_user_id"
python3 -c "
from checker import THSRMonitor
monitor = THSRMonitor()
monitor.send_line_notification('測試訊息')
"
```

### 整合測試

1. **GitHub Actions 測試**:
   - 手動觸發 workflow: Actions → 高鐵票務監控 → Run workflow
   - 檢查執行記錄是否有錯誤
   - 確認 results.json 是否更新

2. **GitHub Pages 測試**:
   - 開啟您的 Pages 網址
   - 確認頁面正常顯示
   - 檢查資料是否正確載入

3. **LINE 通知測試**:
   - 設定一個很容易符合的條件（如未來很遠的日期）
   - 手動觸發 workflow
   - 檢查是否收到 LINE 通知

## 實際部署檢查清單

- [ ] Fork 儲存庫
- [ ] 設定 LINE Channel Access Token (必要)
- [ ] 設定 LINE User ID (必要)
- [ ] 設定 TDX Client ID (建議)
- [ ] 設定 TDX Client Secret (建議)
- [ ] 啟用 GitHub Pages
- [ ] 編輯 watches.yml 設定監控項目
- [ ] 手動觸發一次 workflow 測試
- [ ] 確認 LINE 收到通知
- [ ] 確認 GitHub Pages 正常顯示

## 已知問題與限制

1. **無法取得即時座位資訊**
   - 根本原因: THSR 官網驗證碼保護
   - 影響: 可能只能顯示符合條件的車次，無法確認是否有票
   - 建議: 將所有符合條件的車次都通知使用者

2. **TDX API 資料時效性**
   - 時刻表通常是固定的
   - 座位資訊可能不是即時的（需實際驗證）

3. **GitHub Actions 執行延遲**
   - cron 可能延遲 5-10 分鐘執行
   - 不適合需要秒級精確度的場景

4. **LINE 訊息限制**
   - 免費方案有訊息推送次數限制
   - 需注意不要過度發送

## 改進建議

### 短期改進

1. **增強錯誤處理**
   - 加入更詳細的錯誤訊息
   - 記錄失敗原因與重試次數
   - 定期清理過期的監控項目

2. **優化通知內容**
   - 加入更多車次資訊（行車時間、中停站）
   - 支援自訂通知模板
   - 可選擇是否接收「無票」通知

3. **改善網頁介面**
   - 加入圖表顯示歷史查詢結果
   - 支援直接在網頁上編輯監控項目
   - 加入 PWA 支援（可安裝到手機）

### 長期改進

1. **多元通知管道**
   - 支援 Telegram、Discord、Email
   - 支援 Webhook 整合
   - 支援推播通知

2. **智慧監控**
   - 學習使用者的搭乘習慣
   - 預測票務釋出時間
   - 自動調整查詢頻率

3. **付費升級選項**
   - 使用 VPS 部署以獲得更高頻率
   - 整合付費的驗證碼破解服務
   - 支援更多進階功能

## 法律與道德考量

1. **遵守服務條款**: 請確保使用方式符合 THSR 官網的使用條款
2. **合理使用**: 不要設定過高的查詢頻率以免影響官方服務
3. **僅供個人使用**: 本專案僅供個人學習與使用，不得用於商業用途
4. **自動訂票**: 本系統明確禁止自動訂票功能，僅提供通知
5. **資料隱私**: 妥善保管您的 LINE Token 與 TDX 憑證

## 相關資源

- [TDX API 文件](https://tdx.transportdata.tw/api-service/swagger)
- [LINE Messaging API 文件](https://developers.line.biz/en/reference/messaging-api/)
- [GitHub Actions 文件](https://docs.github.com/en/actions)
- [台灣高鐵官網](https://www.thsrc.com.tw/)
