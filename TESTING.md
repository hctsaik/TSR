# 測試與驗證報告

## 執行日期

2026-10-24

## 測試環境

- Python 版本: 3.12.3
- 作業系統: Linux
- 執行環境: GitHub Actions (模擬)

## 測試項目與結果

### 1. 單元測試 ✅

**執行結果**: 18/18 測試通過

```
tests/test_checker.py::TestStationCodes::test_all_stations_have_codes PASSED
tests/test_checker.py::TestStationCodes::test_station_codes_are_unique PASSED
tests/test_checker.py::TestTHSRMonitor::test_init PASSED
tests/test_checker.py::TestTHSRMonitor::test_generate_booking_url_with_train PASSED
tests/test_checker.py::TestTHSRMonitor::test_generate_booking_url_without_train PASSED
tests/test_checker.py::TestTHSRMonitor::test_load_watches_success PASSED
tests/test_checker.py::TestTHSRMonitor::test_load_watches_file_not_found PASSED
tests/test_checker.py::TestTHSRMonitor::test_load_previous_results_success PASSED
tests/test_checker.py::TestTHSRMonitor::test_load_previous_results_file_not_found PASSED
tests/test_checker.py::TestTHSRMonitor::test_save_results PASSED
tests/test_checker.py::TestTHSRMonitor::test_check_availability_mock PASSED
tests/test_checker.py::TestTHSRMonitor::test_send_line_notification_success PASSED
tests/test_checker.py::TestTHSRMonitor::test_send_line_notification_failure PASSED
tests/test_checker.py::TestTHSRMonitor::test_send_line_notification_no_credentials PASSED
tests/test_checker.py::TestWatchesConfig::test_watches_yml_exists PASSED
tests/test_checker.py::TestWatchesConfig::test_watches_yml_valid_yaml PASSED
tests/test_checker.py::TestDateTimeHandling::test_iso_format_parsing PASSED
tests/test_checker.py::TestDateTimeHandling::test_date_format_conversion PASSED
```

**測試覆蓋範圍**:
- 車站代碼對照
- YAML 設定檔讀取
- JSON 結果檔案處理
- LINE 訊息發送
- 訂票網址產生
- 日期時間處理

### 2. 功能測試 ✅

#### 2.1 程式執行測試

**測試指令**:
```bash
python3 checker.py
```

**執行結果**: ✅ 成功
- 程式正常啟動
- 成功載入設定檔 (watches.yml)
- 成功產生結果檔 (results.json)
- 無執行時錯誤

**輸出訊息**:
```
開始檢查 1 個監控項目...
檢查監控項目: watch-1
警告: 未設定 TDX API 憑證，將無法使用 TDX API
結果已儲存至 results.json
沒有新的可用車次
檢查完成
```

#### 2.2 設定檔解析測試

**測試項目**: watches.yml 解析
**結果**: ✅ 成功
- YAML 格式正確
- 所有必要欄位存在
- 資料型別正確
- 啟用/停用控制正常

#### 2.3 結果檔案產生測試

**測試項目**: results.json 產生
**結果**: ✅ 成功

產生的 JSON 結構:
```json
{
  "last_update": "2026-10-24T12:48:36.512338",
  "results": [
    {
      "watch_id": "watch-1",
      "check_time": "2026-10-24T12:48:36.512318",
      "travel_date": "2026-11-01",
      "origin": "南港",
      "destination": "左營",
      "ticket_count": 2,
      "seat_class": "標準",
      "available_trains": [],
      "status": "warning",
      "error": "無法取得時刻表資料"
    }
  ]
}
```

### 3. 整合測試

#### 3.1 訂票網址產生 ✅

**測試案例**:
- 台北 → 左營 (2026-11-01, 車次 813)

**產生的網址**:
```
https://irs.thsrc.com.tw/IMINT/?origin=TPE&destination=ZUY&date=2026/11/01&trainNo=813
```

**驗證結果**: ✅ 格式正確
- 包含正確的車站代碼
- 日期格式轉換正確
- 車次參數正確

#### 3.2 LINE 訊息格式 ✅

**測試項目**: 通知訊息格式
**結果**: ✅ 格式正確

**訊息範例**:
```
🚄 高鐵票務通知

日期: 2026-11-01
路線: 台北 → 左營
車次: 813
發車時間: 09:00
抵達時間: 11:45
票數: 2 張
座位: 標準車廂

訂票連結:
https://irs.thsrc.com.tw/IMINT/?origin=TPE&destination=ZUY&date=2026/11/01&trainNo=813
```

### 4. 未實際驗證的功能 ⚠️

以下功能因環境或政策限制，未進行實際驗證：

#### 4.1 THSR 官網座位查詢 ⚠️

**未驗證原因**:
- 台灣高鐵官網使用 reCAPTCHA v2 驗證
- 驗證碼機制無法在自動化測試中繁 bypass
- 頻繁查詢可能導致 IP 被封鎖

**目前狀態**:
- 已準備 ddddocr 套件（用於簡單驗證碼）
- 實際應用時需要額外處理 reCAPTCHA

**建議**:
- 使用時請降低查詢頻率
- 優先使用 TDX API
- 監控是否觸發驗證碼

#### 4.2 TDX API 即時資料 ⚠️

**未驗證原因**:
- 需要有效的 TDX API 憑證
- 未設定實際的 Client ID 和 Secret

**已實作功能**:
- OAuth 2.0 認證流程
- 每日時刻表查詢 API 呼叫
- 錯誤處理與重試機制

**待驗證項目**:
- 實際 API 回應格式
- 座位可用性資料的存在與格式
- API 呼叫速率限制

**驗證方法**:
1. 至 [TDX 平台](https://tdx.transportdata.tw/) 申請憑證
2. 設定環境變數:
   ```bash
   export TDX_CLIENT_ID="your_client_id"
   export TDX_CLIENT_SECRET="your_client_secret"
   ```
3. 執行程式並檢查輸出

#### 4.3 LINE Messaging API 推送 ⚠️

**未驗證原因**:
- 需要實際的 LINE Channel Access Token
- 需要有效的 LINE User ID

**已實作功能**:
- LINE Messaging API 整合
- Push Message 發送邏輯
- 錯誤處理

**待驗證項目**:
- 實際訊息推送成功率
- 通知延遲時間
- 訊息格式在 LINE 中的顯示效果

**驗證方法**:
1. 依照 README 建立 LINE Official Account
2. 取得 Channel Access Token 和 User ID
3. 設定 GitHub Secrets
4. 手動觸發 workflow 測試

#### 4.4 GitHub Actions 執行 ⚠️

**未驗證原因**:
- 需要實際推送到 GitHub 儲存庫
- 需要設定 GitHub Secrets

**已實作功能**:
- Workflow YAML 語法正確
- 排程設定 (cron)
- 手動觸發支援
- 結果自動提交

**待驗證項目**:
- 實際排程執行
- Secrets 注入
- 結果提交權限

#### 4.5 GitHub Pages 部署 ⚠️

**未驗證原因**:
- 需要實際啟用 GitHub Pages

**已實作功能**:
- 靜態 HTML 頁面
- JavaScript 資料載入
- 響應式設計

**待驗證項目**:
- 實際部署與訪問
- 資料更新顯示
- 跨瀏覽器相容性

## 驗證總結

### ✅ 已完整驗證

1. **核心邏輯**: 所有 Python 程式邏輯經過單元測試驗證
2. **資料處理**: YAML 讀取、JSON 產生、資料格式轉換
3. **URL 產生**: 訂票網址產生邏輯正確
4. **錯誤處理**: 檔案不存在、API 失敗等錯誤情境
5. **程式執行**: 本地執行無錯誤

### ⚠️ 需使用者驗證

1. **LINE 通知**: 需實際設定 LINE 憑證後驗證
2. **TDX API**: 需實際設定 TDX 憑證後驗證
3. **GitHub Actions**: 需推送後驗證排程執行
4. **GitHub Pages**: 需啟用後驗證頁面顯示

### ❌ 已知限制

1. **THSR 官網查詢**: 因驗證碼保護，無法直接自動查詢座位
2. **即時座位資訊**: 取決於 TDX API 是否提供此資訊
3. **查詢頻率**: 受 GitHub Actions 排程限制

## 建議使用流程

### 初次設定

1. Fork 此儲存庫
2. 設定所有必要的 GitHub Secrets
3. 啟用 GitHub Pages
4. 編輯 watches.yml 加入監控項目
5. 手動觸發 workflow 測試
6. 確認 LINE 收到通知
7. 確認 GitHub Pages 正常顯示

### 日常使用

1. 定期檢查 GitHub Pages 查看結果
2. 接收 LINE 通知
3. 點擊連結前往官網訂票
4. 根據需要更新 watches.yml

### 問題排查

1. 檢查 GitHub Actions 執行記錄
2. 查看 results.json 的錯誤訊息
3. 確認 Secrets 設定正確
4. 檢查 LINE 官方帳號狀態

## 結論

本專案的核心功能已經過完整的單元測試與本地驗證，程式邏輯正確且運作穩定。

然而，由於以下外部因素的限制，部分功能需要在實際部署後才能完整驗證：

1. **台灣高鐵官網**的驗證碼保護機制
2. **TDX API** 的實際資料格式與可用性
3. **LINE Messaging API** 的實際推送效果
4. **GitHub Actions** 的排程執行狀況

建議使用者依照 README 的步驟進行設定，並在實際環境中進行測試與驗證。如遇到問題，請參考 DEVELOPMENT.md 的問題排查指南。
