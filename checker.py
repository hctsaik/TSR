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
import re
from datetime import datetime
from typing import Dict, List, Optional, Any
from bs4 import BeautifulSoup

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
    BASE_URL = "https://irs.thsrc.com.tw"
    BOOKING_PAGE_URL = "https://irs.thsrc.com.tw/IMINT/?locale=tw"
    
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "zh-TW,zh;q=0.9,en;q=0.8",
        })
        self.tdx_token = None
        self.ocr = None
        if DDDDOCR_AVAILABLE:
            try:
                self.ocr = ddddocr.DdddOcr(show_ad=False, beta=True)
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
        檢查座位可用性（含真實查詢）
        會先嘗試真實查詢 THSR 網站，失敗則使用 TDX 時刻表
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
            'error': None,
            'check_method': 'unknown'
        }
        
        # 嘗試真實查詢 THSR 官網
        try:
            real_result = self.check_thsr_website(
                origin, destination, travel_date, ticket_count, seat_class, watch
            )
            if real_result['success']:
                result['available_trains'] = real_result['trains']
                result['check_method'] = 'thsr_website'
                print(f"✓ THSR 官網查詢成功，找到 {len(real_result['trains'])} 個可用車次")
                return result
            else:
                print(f"✗ THSR 官網查詢失敗: {real_result.get('error')}")
        except Exception as e:
            print(f"✗ THSR 官網查詢異常: {e}")
        
        # 降級使用 TDX 時刻表
        print("→ 使用 TDX 時刻表進行查詢")
        timetable = self.get_tdx_timetable(travel_date, origin, destination)
        
        if timetable:
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
                
                # 注意: TDX 時刻表無法確認實際座位狀態
                train_info = {
                    'train_number': train_no,
                    'departure_time': depart_time,
                    'arrival_time': arrival_time,
                    'available': 'unknown',  # 無法確認實際座位
                    'booking_url': self.generate_booking_url(
                        travel_date, origin, destination, train_no
                    )
                }
                result['available_trains'].append(train_info)
            
            result['check_method'] = 'tdx_timetable'
            if result['available_trains']:
                result['status'] = 'warning'
                result['error'] = '使用時刻表查詢，無法確認實際座位狀態'
        else:
            result['status'] = 'error'
            result['error'] = '所有查詢方法均失敗'
            result['check_method'] = 'failed'
        
        return result
    
    def check_thsr_website(self, origin: str, destination: str, travel_date: str,
                          ticket_count: int, seat_class: str, watch: Dict) -> Dict:
        """
        查詢 THSR 官網的實際座位可用性
        
        Returns:
            {
                'success': bool,
                'trains': List[Dict],  # 實際有座位的車次
                'error': str
            }
        """
        result = {
            'success': False,
            'trains': [],
            'error': None
        }
        
        # 確認有 OCR 才能處理驗證碼
        if not self.ocr:
            result['error'] = '未安裝 ddddocr，無法辨識驗證碼'
            return result
        
        max_attempts = 3
        for attempt in range(max_attempts):
            try:
                # 1. 取得訂票頁面
                response = self.session.get(self.BOOKING_PAGE_URL, timeout=20)
                if response.status_code != 200:
                    result['error'] = f'無法取得訂票頁面 (HTTP {response.status_code})'
                    time.sleep(2)
                    continue
                
                html_content = response.content
                soup = BeautifulSoup(html_content, 'html.parser')
                
                # 2. 取得驗證碼圖片
                img_tag = soup.find('img', {'id': 'BookingS1Form_homeCaptcha_passCode'})
                if not img_tag:
                    result['error'] = '找不到驗證碼圖片元素'
                    time.sleep(2)
                    continue
                
                img_url = self.BASE_URL + img_tag.get('src')
                img_response = self.session.get(img_url, timeout=10)
                if img_response.status_code != 200:
                    result['error'] = f'無法取得驗證碼圖片 (HTTP {img_response.status_code})'
                    time.sleep(2)
                    continue
                
                # 3. 辨識驗證碼
                captcha_code = self.ocr.classification(img_response.content)
                captcha_code = captcha_code.strip().upper()
                
                if len(captcha_code) < 3:
                    result['error'] = f'驗證碼辨識結果異常: {captcha_code}'
                    time.sleep(2)
                    continue
                
                print(f"  驗證碼辨識: {captcha_code} (嘗試 {attempt + 1}/{max_attempts})")
                
                # 4. 準備表單資料
                form_data = self._prepare_booking_form(
                    soup, origin, destination, travel_date, 
                    ticket_count, seat_class, captcha_code, watch
                )
                
                if not form_data:
                    result['error'] = '無法準備表單資料'
                    time.sleep(2)
                    continue
                
                # 5. 提交表單
                jsessionid = self.session.cookies.get('JSESSIONID')
                if not jsessionid:
                    result['error'] = '無法取得 JSESSIONID'
                    time.sleep(2)
                    continue
                
                submit_url = f"{self.BASE_URL}/IMINT/;jsessionid={jsessionid}?wicket:interface=:0:BookingS1Form::IFormSubmitListener"
                submit_response = self.session.post(submit_url, data=form_data, timeout=20)
                
                if submit_response.status_code != 200:
                    result['error'] = f'提交表單失敗 (HTTP {submit_response.status_code})'
                    time.sleep(2)
                    continue
                
                # 6. 解析可用車次
                trains = self._parse_available_trains(submit_response.content)
                
                if trains:
                    result['success'] = True
                    result['trains'] = trains
                    result['error'] = None
                    return result
                else:
                    # 檢查是否是驗證碼錯誤
                    error_soup = BeautifulSoup(submit_response.content, 'html.parser')
                    error_msg = error_soup.find('span', {'class': 'feedbackPanelERROR'})
                    if error_msg and '驗證碼' in error_msg.get_text():
                        print(f"  驗證碼錯誤，重試...")
                        time.sleep(2)
                        continue
                    else:
                        # 沒有錯誤訊息但也沒有車次 = 真的沒有座位
                        result['success'] = True
                        result['trains'] = []
                        result['error'] = None
                        return result
                
            except requests.exceptions.Timeout:
                result['error'] = 'THSR 網站連線逾時'
                time.sleep(3)
                continue
            except requests.exceptions.ConnectionError:
                result['error'] = 'THSR 網站連線失敗'
                time.sleep(3)
                continue
            except Exception as e:
                result['error'] = f'查詢過程發生錯誤: {str(e)}'
                time.sleep(2)
                continue
        
        return result
    
    def _prepare_booking_form(self, soup: BeautifulSoup, origin: str, destination: str,
                             travel_date: str, ticket_count: int, seat_class: str,
                             captcha_code: str, watch: Dict) -> Optional[Dict]:
        """準備訂票表單資料"""
        try:
            origin_code = STATION_CODES.get(origin)
            dest_code = STATION_CODES.get(destination)
            
            if not origin_code or not dest_code:
                print(f"無效的車站代碼: {origin}, {destination}")
                return None
            
            # 座位等級: 0=標準, 1=商務
            seat_class_code = "1" if seat_class == "商務" else "0"
            
            # 時間選項（預設 09:00）
            time_option = "900A"
            if watch.get('time_range'):
                start_time = watch['time_range'].get('start', '09:00')
                if start_time >= "18:00":
                    time_option = "600P"
                elif start_time >= "15:00":
                    time_option = "300P"
                elif start_time >= "12:00":
                    time_option = "1200N"
                elif start_time >= "09:00":
                    time_option = "900A"
                else:
                    time_option = "600A"
            
            # 解析表單中的預設值
            seat_prefer = soup.find('select', {'name': 'seatCon:seatRadioGroup'})
            if seat_prefer:
                selected = seat_prefer.find('option', {'selected': True})
                if selected:
                    seat_class_code = selected.get('value', seat_class_code)
            
            # 轉換日期格式: YYYY-MM-DD -> YYYY/MM/DD
            if '-' in travel_date:
                travel_date = travel_date.replace('-', '/')
            
            form_data = {
                'selectStartStation': origin_code,
                'selectDestinationStation': dest_code,
                'trainCon:trainRadioGroup': '0',
                'tripCon:typesoftrip': '0',
                'seatCon:seatRadioGroup': seat_class_code,
                'bookingMethod': '0',
                'toTimeInputField': travel_date,
                'toTimeTable': time_option,
                'toTrainIDInputField': '',
                'backTimeInputField': '',
                'backTimeTable': '',
                'backTrainIDInputField': '',
                'ticketPanel:rows:0:ticketAmount': f'{ticket_count}F',
                'ticketPanel:rows:1:ticketAmount': '0H',
                'ticketPanel:rows:2:ticketAmount': '0W',
                'ticketPanel:rows:3:ticketAmount': '0E',
                'ticketPanel:rows:4:ticketAmount': '0P',
                'homeCaptcha:securityCode': captcha_code,
            }
            
            return form_data
        except Exception as e:
            print(f"準備表單資料時發生錯誤: {e}")
            return None
    
    def _parse_available_trains(self, html_content: bytes) -> List[Dict]:
        """解析可用車次（只返回實際有座位的車次）"""
        try:
            soup = BeautifulSoup(html_content, 'html.parser')
            
            # 檢查錯誤訊息
            error_msg = soup.find('span', {'class': 'feedbackPanelERROR'})
            if error_msg:
                return []
            
            # 查找車次標籤
            train_labels = soup.find_all('label', {'class': 'radio'}) or \
                          soup.find_all('label', {'for': lambda x: x and 'TrainRadioGroup' in x})
            
            if not train_labels:
                return []
            
            available_trains = []
            
            for label in train_labels:
                try:
                    # 提取車次編號
                    radio = label.find('input', {'type': 'radio'})
                    if not radio:
                        continue
                    
                    # 從 label 文字中提取資訊
                    text = label.get_text(strip=True)
                    
                    # 嘗試多種方式提取車次編號
                    train_number = None
                    if radio.get('value'):
                        # 從 value 中提取車次號（格式可能是: "TrainNo_813"）
                        value = radio.get('value', '')
                        parts = value.split('_')
                        if len(parts) > 1:
                            train_number = parts[-1]
                    
                    # 如果從 value 取不到，嘗試從文字中解析
                    if not train_number:
                        import re
                        match = re.search(r'\b(\d{3,4})\b', text)
                        if match:
                            train_number = match.group(1)
                    
                    if not train_number:
                        continue
                    
                    # 嘗試提取時間資訊
                    time_match = re.findall(r'(\d{2}:\d{2})', text)
                    depart_time = time_match[0] if len(time_match) > 0 else "未知"
                    arrive_time = time_match[1] if len(time_match) > 1 else "未知"
                    
                    available_trains.append({
                        'train_number': train_number,
                        'departure_time': depart_time,
                        'arrival_time': arrive_time,
                        'available': True,  # 出現在列表中表示有座位
                        'booking_url': self.generate_booking_url(
                            '', '', '', train_number  # 將由前端重新產生完整 URL
                        )
                    })
                except Exception as e:
                    print(f"解析單一車次時發生錯誤: {e}")
                    continue
            
            return available_trains
        except Exception as e:
            print(f"解析可用車次時發生錯誤: {e}")
            return []
    
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
        """執行檢查並發送通知（只在確認有座位時通知）"""
        watches = self.load_watches()
        if not watches:
            print("沒有啟用的監控項目")
            return
        
        print(f"開始檢查 {len(watches)} 個監控項目...")
        
        previous_results = self.load_previous_results()
        previous_trains = {}
        
        # 建立先前可用車次的索引（只記錄確認有座位的）
        for result in previous_results.get('results', []):
            watch_id = result.get('watch_id')
            for train in result.get('available_trains', []):
                if train.get('available') is True:  # 只記錄確認有座位的
                    key = f"{watch_id}_{train.get('train_number')}"
                    previous_trains[key] = train
        
        current_results = []
        new_notifications = []
        
        for watch in watches:
            print(f"\n檢查監控項目: {watch.get('id')}")
            result = self.check_availability_mock(watch)
            current_results.append(result)
            
            # 只處理確認有座位的車次
            confirmed_available_trains = [
                train for train in result.get('available_trains', [])
                if train.get('available') is True
            ]
            
            # 檢查是否有新的可用座位（確認有票的車次）
            for train in confirmed_available_trains:
                key = f"{watch.get('id')}_{train.get('train_number')}"
                
                # 如果是新出現的確認有票車次，發送通知
                if key not in previous_trains:
                    message = (
                        f"🚄 高鐵票務通知\n\n"
                        f"✅ 發現可用座位！\n\n"
                        f"日期: {result.get('travel_date')}\n"
                        f"路線: {result.get('origin')} → {result.get('destination')}\n"
                        f"車次: {train.get('train_number')}\n"
                        f"發車時間: {train.get('departure_time')}\n"
                        f"抵達時間: {train.get('arrival_time')}\n"
                        f"票數: {result.get('ticket_count')} 張\n"
                        f"座位: {result.get('seat_class')}車廂\n\n"
                        f"訂票連結:\n{train.get('booking_url')}\n\n"
                        f"⚠️ 請盡快前往訂票，座位有限！"
                    )
                    new_notifications.append(message)
            
            # 如果使用 TDX 時刻表但無法確認座位，在結果中標註
            if result.get('check_method') == 'tdx_timetable' and result.get('available_trains'):
                unconfirmed_count = len([
                    t for t in result.get('available_trains', [])
                    if t.get('available') == 'unknown'
                ])
                if unconfirmed_count > 0:
                    print(f"  ⚠️ 找到 {unconfirmed_count} 個符合時刻表的車次，但無法確認實際座位狀態")
        
        # 儲存結果
        self.save_results(current_results)
        
        # 發送通知（只發送確認有票的）
        if new_notifications:
            print(f"\n發現 {len(new_notifications)} 個新的可用座位")
            for message in new_notifications:
                self.send_line_notification(message)
                time.sleep(1)  # 避免發送過快
        else:
            print("\n沒有新的確認可用座位")
            
            # 統計未確認的車次
            unconfirmed_total = sum(
                len([t for t in r.get('available_trains', []) if t.get('available') == 'unknown'])
                for r in current_results
            )
            if unconfirmed_total > 0:
                print(f"  註: 有 {unconfirmed_total} 個車次符合條件但無法確認座位狀態")
        
        print("\n檢查完成")

def main():
    monitor = THSRMonitor()
    monitor.check_and_notify()

if __name__ == '__main__':
    main()
