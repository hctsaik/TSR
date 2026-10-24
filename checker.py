#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
台灣高鐵票務監控系統 - 主要檢查程式
"""

import os
import json
import yaml
import requests
import time
from datetime import datetime
from typing import Dict, List, Optional, Any
import io
import base64

try:
    import ddddocr
    DDDDOCR_AVAILABLE = True
except ImportError:
    DDDDOCR_AVAILABLE = False
    print("警告: ddddocr 未安裝，驗證碼辨識功能將無法使用")

# 台灣高鐵車站代碼對照表
STATION_CODES = {
    "南港": "NAG",
    "台北": "TPE",
    "板橋": "BAC",
    "桃園": "TYU",
    "新竹": "HSC",
    "苗栗": "MIL",
    "台中": "TAC",
    "彰化": "CHA",
    "雲林": "YUL",
    "嘉義": "CHY",
    "台南": "TNN",
    "左營": "ZUY"
}

# TDX API 設定
TDX_API_BASE = "https://tdx.transportdata.tw/api/basic"
TDX_AUTH_URL = "https://tdx.transportdata.tw/auth/realms/TDXConnect/protocol/openid-connect/token"

# THSR 官方網站
THSR_BOOKING_URL = "https://irs.thsrc.com.tw/IMINT/"
THSR_QUERY_URL = "https://irs.thsrc.com.tw/IMINT/Home/SearchBooking"

class THSRMonitor:
    def __init__(self):
        self.session = requests.Session()
        self.tdx_token = None
        self.ocr = None
        if DDDDOCR_AVAILABLE:
            try:
                self.ocr = ddddocr.DdddOcr(show_ad=False)
            except Exception as e:
                print(f"初始化 OCR 失敗: {e}")
        
    def get_tdx_token(self) -> Optional[str]:
        """取得 TDX API 存取權杖"""
        client_id = os.getenv('TDX_CLIENT_ID')
        client_secret = os.getenv('TDX_CLIENT_SECRET')
        
        if not client_id or not client_secret:
            print("警告: 未設定 TDX API 憑證，將無法使用 TDX API")
            return None
            
        try:
            response = requests.post(
                TDX_AUTH_URL,
                data={
                    'grant_type': 'client_credentials',
                    'client_id': client_id,
                    'client_secret': client_secret
                },
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                self.tdx_token = data.get('access_token')
                return self.tdx_token
            else:
                print(f"取得 TDX 權杖失敗: {response.status_code}")
                return None
        except Exception as e:
            print(f"取得 TDX 權杖時發生錯誤: {e}")
            return None
    
    def get_tdx_timetable(self, date: str, origin: str, destination: str) -> List[Dict]:
        """從 TDX API 取得時刻表"""
        if not self.tdx_token:
            if not self.get_tdx_token():
                return []
        
        origin_code = STATION_CODES.get(origin)
        dest_code = STATION_CODES.get(destination)
        
        if not origin_code or not dest_code:
            print(f"無效的車站名稱: {origin} -> {destination}")
            return []
        
        try:
            # TDX API: 取得每日時刻表
            url = f"{TDX_API_BASE}/v2/Rail/THSR/DailyTimetable/OD/{origin_code}/to/{dest_code}/{date}"
            headers = {
                'Authorization': f'Bearer {self.tdx_token}'
            }
            
            response = requests.get(url, headers=headers, timeout=15)
            
            if response.status_code == 200:
                return response.json()
            else:
                print(f"取得 TDX 時刻表失敗: {response.status_code}")
                return []
        except Exception as e:
            print(f"查詢 TDX 時刻表時發生錯誤: {e}")
            return []
    
    def check_availability_mock(self, watch: Dict) -> Dict[str, Any]:
        """
        模擬查詢座位可用性
        真實實作需要處理 THSR 網站的驗證碼
        """
        travel_date = watch.get('travel_date')
        origin = watch.get('origin')
        destination = watch.get('destination')
        ticket_count = watch.get('ticket_count', 1)
        seat_class = watch.get('seat_class', '標準')
        
        result = {
            'watch_id': watch.get('id'),
            'check_time': datetime.now().isoformat(),
            'travel_date': travel_date,
            'origin': origin,
            'destination': destination,
            'ticket_count': ticket_count,
            'seat_class': seat_class,
            'available_trains': [],
            'status': 'success',
            'error': None
        }
        
        # 嘗試從 TDX 取得時刻表
        timetable = self.get_tdx_timetable(travel_date, origin, destination)
        
        if timetable:
            # 如果有指定時間範圍
            time_range = watch.get('time_range')
            train_numbers = watch.get('train_numbers', [])
            
            for train in timetable:
                train_no = train.get('DailyTrainInfo', {}).get('TrainNo', '')
                depart_time = train.get('OriginStopTime', {}).get('DepartureTime', '')
                arrival_time = train.get('DestinationStopTime', {}).get('ArrivalTime', '')
                
                # 過濾條件
                if train_numbers and train_no not in train_numbers:
                    continue
                    
                if time_range:
                    start_time = time_range.get('start', '00:00')
                    end_time = time_range.get('end', '23:59')
                    if not (start_time <= depart_time <= end_time):
                        continue
                
                # 注意: TDX API 可能不提供即時座位資訊
                # 這裡我們將所有符合條件的車次標記為「需進一步確認」
                train_info = {
                    'train_number': train_no,
                    'departure_time': depart_time,
                    'arrival_time': arrival_time,
                    'available': 'unknown',  # 實際需查詢 THSR 官網
                    'booking_url': self.generate_booking_url(
                        travel_date, origin, destination, train_no
                    )
                }
                result['available_trains'].append(train_info)
        else:
            result['status'] = 'warning'
            result['error'] = '無法取得時刻表資料'
        
        return result
    
    def generate_booking_url(self, date: str, origin: str, destination: str, 
                            train_no: str = "") -> str:
        """產生高鐵訂票網址"""
        origin_code = STATION_CODES.get(origin, "")
        dest_code = STATION_CODES.get(destination, "")
        
        # 將日期格式轉換為 THSR 網站格式
        date_obj = datetime.strptime(date, "%Y-%m-%d")
        date_param = date_obj.strftime("%Y/%m/%d")
        
        base_url = "https://irs.thsrc.com.tw/IMINT/"
        params = f"?origin={origin_code}&destination={dest_code}&date={date_param}"
        if train_no:
            params += f"&trainNo={train_no}"
        
        return base_url + params
    
    def load_watches(self, config_file: str = 'watches.yml') -> List[Dict]:
        """載入監控設定"""
        try:
            with open(config_file, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)
                watches = config.get('watches', [])
                # 只返回已啟用的監控項目
                return [w for w in watches if w.get('enabled', True)]
        except FileNotFoundError:
            print(f"設定檔 {config_file} 不存在")
            return []
        except Exception as e:
            print(f"載入設定檔時發生錯誤: {e}")
            return []
    
    def load_previous_results(self, results_file: str = 'results.json') -> Dict:
        """載入先前的檢查結果"""
        try:
            with open(results_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except FileNotFoundError:
            return {'last_update': None, 'results': []}
        except Exception as e:
            print(f"載入結果檔時發生錯誤: {e}")
            return {'last_update': None, 'results': []}
    
    def save_results(self, results: List[Dict], results_file: str = 'results.json'):
        """儲存檢查結果"""
        output = {
            'last_update': datetime.now().isoformat(),
            'results': results
        }
        
        try:
            with open(results_file, 'w', encoding='utf-8') as f:
                json.dump(output, f, ensure_ascii=False, indent=2)
            print(f"結果已儲存至 {results_file}")
        except Exception as e:
            print(f"儲存結果時發生錯誤: {e}")
    
    def send_line_notification(self, message: str) -> bool:
        """發送 LINE 訊息通知"""
        access_token = os.getenv('LINE_CHANNEL_ACCESS_TOKEN')
        user_id = os.getenv('LINE_USER_ID')
        
        if not access_token or not user_id:
            print("警告: 未設定 LINE 通知憑證")
            return False
        
        url = "https://api.line.me/v2/bot/message/push"
        headers = {
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {access_token}'
        }
        
        payload = {
            'to': user_id,
            'messages': [
                {
                    'type': 'text',
                    'text': message
                }
            ]
        }
        
        try:
            response = requests.post(url, headers=headers, json=payload, timeout=10)
            if response.status_code == 200:
                print("LINE 通知已發送")
                return True
            else:
                print(f"發送 LINE 通知失敗: {response.status_code} - {response.text}")
                return False
        except Exception as e:
            print(f"發送 LINE 通知時發生錯誤: {e}")
            return False
    
    def check_and_notify(self):
        """執行檢查並發送通知"""
        watches = self.load_watches()
        if not watches:
            print("沒有啟用的監控項目")
            return
        
        print(f"開始檢查 {len(watches)} 個監控項目...")
        
        previous_results = self.load_previous_results()
        previous_trains = {}
        
        # 建立先前可用車次的索引
        for result in previous_results.get('results', []):
            watch_id = result.get('watch_id')
            for train in result.get('available_trains', []):
                key = f"{watch_id}_{train.get('train_number')}"
                previous_trains[key] = train
        
        current_results = []
        new_notifications = []
        
        for watch in watches:
            print(f"\n檢查監控項目: {watch.get('id')}")
            result = self.check_availability_mock(watch)
            current_results.append(result)
            
            # 檢查是否有新的可用座位
            for train in result.get('available_trains', []):
                key = f"{watch.get('id')}_{train.get('train_number')}"
                
                # 如果是新出現的車次，或狀態從不可用變為可用
                if key not in previous_trains:
                    message = (
                        f"🚄 高鐵票務通知\n\n"
                        f"日期: {result.get('travel_date')}\n"
                        f"路線: {result.get('origin')} → {result.get('destination')}\n"
                        f"車次: {train.get('train_number')}\n"
                        f"發車時間: {train.get('departure_time')}\n"
                        f"抵達時間: {train.get('arrival_time')}\n"
                        f"票數: {result.get('ticket_count')} 張\n"
                        f"座位: {result.get('seat_class')}車廂\n\n"
                        f"訂票連結:\n{train.get('booking_url')}"
                    )
                    new_notifications.append(message)
        
        # 儲存結果
        self.save_results(current_results)
        
        # 發送通知
        if new_notifications:
            print(f"\n發現 {len(new_notifications)} 個新的可用車次")
            for message in new_notifications:
                self.send_line_notification(message)
                time.sleep(1)  # 避免發送過快
        else:
            print("\n沒有新的可用車次")
        
        print("\n檢查完成")

def main():
    monitor = THSRMonitor()
    monitor.check_and_notify()

if __name__ == '__main__':
    main()
