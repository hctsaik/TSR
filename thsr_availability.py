#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
台灣高鐵座位可用性檢查器 - 實際查詢 THSR 官網
"""

import io
import json
import time
import requests
from datetime import datetime, date
from typing import Dict, List, Optional, Tuple
from PIL import Image
from bs4 import BeautifulSoup

try:
    import ddddocr
    DDDDOCR_AVAILABLE = True
except ImportError:
    DDDDOCR_AVAILABLE = False

# THSR 車站代碼對照表
STATION_CODES = {
    "南港": "1",
    "台北": "2",
    "板橋": "3",
    "桃園": "4",
    "新竹": "5",
    "苗栗": "6",
    "台中": "7",
    "彰化": "8",
    "雲林": "9",
    "嘉義": "10",
    "台南": "11",
    "左營": "12"
}

# 時間選項對照
TIME_OPTIONS = {
    "00:00": "1201A",
    "06:00": "600A",
    "09:00": "900A",
    "12:00": "1200N",
    "15:00": "300P",
    "18:00": "600P",
    "21:00": "900P",
}

class THSRAvailabilityChecker:
    """台灣高鐵座位可用性檢查器"""
    
    BASE_URL = "https://irs.thsrc.com.tw"
    BOOKING_PAGE_URL = "https://irs.thsrc.com.tw/IMINT/?locale=tw"
    
    def __init__(self, max_retries: int = 3):
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Accept-Language": "zh-TW,zh;q=0.9,en-US;q=0.8,en;q=0.7",
            "Accept-Encoding": "gzip, deflate, br",
        })
        self.max_retries = max_retries
        self.ocr = None
        if DDDDOCR_AVAILABLE:
            try:
                self.ocr = ddddocr.DdddOcr(show_ad=False, beta=True)
            except Exception as e:
                print(f"初始化 OCR 失敗: {e}")
    
    def get_booking_page(self) -> Tuple[Optional[bytes], Optional[str]]:
        """取得訂票頁面"""
        try:
            response = self.session.get(self.BOOKING_PAGE_URL, timeout=15)
            if response.status_code == 200:
                return response.content, response.text
            else:
                print(f"取得訂票頁面失敗: {response.status_code}")
                return None, None
        except Exception as e:
            print(f"取得訂票頁面時發生錯誤: {e}")
            return None, None
    
    def get_captcha_image(self, html_content: bytes) -> Optional[bytes]:
        """從頁面中取得驗證碼圖片"""
        try:
            soup = BeautifulSoup(html_content, 'html.parser')
            img_tag = soup.find('img', {'id': 'BookingS1Form_homeCaptcha_passCode'})
            if not img_tag:
                print("找不到驗證碼圖片元素")
                return None
            
            img_url = self.BASE_URL + img_tag.get('src')
            response = self.session.get(img_url, timeout=10)
            if response.status_code == 200:
                return response.content
            else:
                print(f"取得驗證碼圖片失敗: {response.status_code}")
                return None
        except Exception as e:
            print(f"取得驗證碼圖片時發生錯誤: {e}")
            return None
    
    def recognize_captcha(self, img_bytes: bytes, save_path: Optional[str] = None) -> Optional[str]:
        """辨識驗證碼"""
        if not self.ocr:
            print("OCR 未初始化")
            return None
        
        try:
            # 儲存圖片以便檢查（除錯用）
            if save_path:
                with open(save_path, 'wb') as f:
                    f.write(img_bytes)
            
            # 使用 ddddocr 辨識
            result = self.ocr.classification(img_bytes)
            
            # 清理結果（移除空格、轉大寫）
            result = result.strip().upper()
            
            # 驗證結果長度（THSR 驗證碼通常是 4-6 位）
            if len(result) < 3 or len(result) > 8:
                print(f"驗證碼辨識結果長度異常: {result}")
                return None
            
            return result
        except Exception as e:
            print(f"辨識驗證碼時發生錯誤: {e}")
            return None
    
    def parse_form_data(self, html_text: str) -> Dict[str, str]:
        """解析表單中的隱藏欄位"""
        soup = BeautifulSoup(html_text, 'html.parser')
        form_data = {}
        
        # 取得座位偏好
        seat_prefer = soup.find('select', {'name': 'seatCon:seatRadioGroup'})
        if seat_prefer:
            selected = seat_prefer.find('option', {'selected': True})
            if selected:
                form_data['seatCon:seatRadioGroup'] = selected.get('value', '0')
        
        # 取得行程類型
        trip_type = soup.find('select', {'name': 'tripCon:typesoftrip'})
        if trip_type:
            selected = trip_type.find('option', {'selected': True})
            if selected:
                form_data['tripCon:typesoftrip'] = selected.get('value', '0')
        
        # 取得搜尋方式
        search_by = soup.find('input', {'name': 'bookingMethod', 'checked': True})
        if search_by:
            form_data['bookingMethod'] = search_by.get('value', '0')
        
        return form_data
    
    def submit_booking_form(self, origin: str, destination: str, travel_date: str,
                           time_option: str, ticket_count: int, seat_class: str,
                           captcha_code: str, form_data: Dict[str, str]) -> Optional[bytes]:
        """提交訂票表單"""
        try:
            # 取得 JSESSIONID
            jsessionid = self.session.cookies.get('JSESSIONID')
            if not jsessionid:
                print("無法取得 JSESSIONID")
                return None
            
            # 建構表單資料
            origin_code = STATION_CODES.get(origin)
            dest_code = STATION_CODES.get(destination)
            
            if not origin_code or not dest_code:
                print(f"無效的車站: {origin}, {destination}")
                return None
            
            # 座位等級: 0=標準, 1=商務
            seat_class_code = "1" if seat_class == "商務" else "0"
            
            params = {
                'selectStartStation': origin_code,
                'selectDestinationStation': dest_code,
                'trainCon:trainRadioGroup': '0',  # 單程票
                'tripCon:typesoftrip': form_data.get('tripCon:typesoftrip', '0'),
                'seatCon:seatRadioGroup': seat_class_code,
                'bookingMethod': form_data.get('bookingMethod', '0'),
                'toTimeInputField': travel_date,
                'toTimeTable': time_option,
                'toTrainIDInputField': '',
                'backTimeInputField': '',
                'backTimeTable': '',
                'backTrainIDInputField': '',
                'ticketPanel:rows:0:ticketAmount': f'{ticket_count}F',  # F=全票
                'ticketPanel:rows:1:ticketAmount': '0H',  # 孩童
                'ticketPanel:rows:2:ticketAmount': '0W',  # 敬老
                'ticketPanel:rows:3:ticketAmount': '0E',  # 愛心
                'ticketPanel:rows:4:ticketAmount': '0P',  # 大學生
                'homeCaptcha:securityCode': captcha_code,
            }
            
            # 提交表單
            submit_url = f"{self.BASE_URL}/IMINT/;jsessionid={jsessionid}?wicket:interface=:0:BookingS1Form::IFormSubmitListener"
            
            response = self.session.post(submit_url, data=params, timeout=15, allow_redirects=True)
            
            if response.status_code == 200:
                return response.content
            else:
                print(f"提交表單失敗: {response.status_code}")
                return None
        except Exception as e:
            print(f"提交表單時發生錯誤: {e}")
            return None
    
    def parse_available_trains(self, html_content: bytes) -> List[Dict]:
        """解析可用車次"""
        try:
            soup = BeautifulSoup(html_content, 'html.parser')
            
            # 檢查是否有錯誤訊息
            error_msg = soup.find('span', {'class': 'feedbackPanelERROR'})
            if error_msg:
                error_text = error_msg.get_text(strip=True)
                print(f"查詢錯誤: {error_text}")
                return []
            
            # 查找所有車次選項
            train_labels = soup.find_all('label', {'class': 'radio'})
            
            if not train_labels:
                print("沒有找到可用車次")
                return []
            
            available_trains = []
            
            for label in train_labels:
                try:
                    # 提取車次編號
                    train_id_elem = label.find('span', {'class': 'train-number'})
                    if not train_id_elem:
                        continue
                    train_id = train_id_elem.get_text(strip=True)
                    
                    # 提取發車時間
                    depart_elem = label.find('span', {'class': 'departure-time'})
                    depart_time = depart_elem.get_text(strip=True) if depart_elem else "未知"
                    
                    # 提取抵達時間
                    arrive_elem = label.find('span', {'class': 'arrival-time'})
                    arrive_time = arrive_elem.get_text(strip=True) if arrive_elem else "未知"
                    
                    # 提取行駛時間
                    duration_elem = label.find('span', {'class': 'duration'})
                    duration = duration_elem.get_text(strip=True) if duration_elem else "未知"
                    
                    # 取得表單值（用於選擇車次）
                    radio_input = label.find('input', {'type': 'radio'})
                    form_value = radio_input.get('value', '') if radio_input else ''
                    
                    # 檢查是否有折扣標記
                    discount_info = []
                    early_bird = label.find('span', string=lambda text: text and '早鳥' in text)
                    if early_bird:
                        discount_info.append(early_bird.get_text(strip=True))
                    
                    available_trains.append({
                        'train_number': train_id,
                        'departure_time': depart_time,
                        'arrival_time': arrive_time,
                        'duration': duration,
                        'discount': ', '.join(discount_info) if discount_info else '',
                        'form_value': form_value,
                        'available': True  # 出現在列表中表示有座位
                    })
                except Exception as e:
                    print(f"解析車次資訊時發生錯誤: {e}")
                    continue
            
            return available_trains
        except Exception as e:
            print(f"解析可用車次時發生錯誤: {e}")
            return []
    
    def check_availability(self, origin: str, destination: str, travel_date: str,
                          time_option: str = "900A", ticket_count: int = 1,
                          seat_class: str = "標準", save_captcha: bool = False) -> Dict:
        """
        檢查座位可用性
        
        Args:
            origin: 起始站
            destination: 目的地站
            travel_date: 乘車日期 (YYYY/MM/DD)
            time_option: 時間選項
            ticket_count: 票數
            seat_class: 座位等級
            save_captcha: 是否儲存驗證碼圖片
        
        Returns:
            包含可用車次資訊的字典
        """
        result = {
            'success': False,
            'available_trains': [],
            'error': None,
            'captcha_recognized': None
        }
        
        for attempt in range(self.max_retries):
            try:
                print(f"\n=== 嘗試 {attempt + 1}/{self.max_retries} ===")
                
                # 1. 取得訂票頁面
                print("正在取得訂票頁面...")
                html_content, html_text = self.get_booking_page()
                if not html_content:
                    result['error'] = "無法取得訂票頁面"
                    time.sleep(2)
                    continue
                
                # 2. 取得驗證碼圖片
                print("正在取得驗證碼...")
                captcha_img = self.get_captcha_image(html_content)
                if not captcha_img:
                    result['error'] = "無法取得驗證碼圖片"
                    time.sleep(2)
                    continue
                
                # 3. 辨識驗證碼
                print("正在辨識驗證碼...")
                captcha_path = f"/tmp/captcha_{int(time.time())}.png" if save_captcha else None
                captcha_code = self.recognize_captcha(captcha_img, captcha_path)
                
                if not captcha_code:
                    result['error'] = "驗證碼辨識失敗"
                    time.sleep(2)
                    continue
                
                print(f"驗證碼辨識結果: {captcha_code}")
                result['captcha_recognized'] = captcha_code
                
                # 4. 解析表單資料
                form_data = self.parse_form_data(html_text)
                
                # 5. 提交表單
                print(f"正在查詢 {origin} → {destination} ({travel_date})...")
                response_html = self.submit_booking_form(
                    origin, destination, travel_date, time_option,
                    ticket_count, seat_class, captcha_code, form_data
                )
                
                if not response_html:
                    result['error'] = "提交表單失敗"
                    time.sleep(2)
                    continue
                
                # 6. 解析可用車次
                print("正在解析車次資訊...")
                available_trains = self.parse_available_trains(response_html)
                
                if available_trains:
                    result['success'] = True
                    result['available_trains'] = available_trains
                    result['error'] = None
                    print(f"✓ 找到 {len(available_trains)} 個可用車次")
                    return result
                else:
                    # 檢查是否是驗證碼錯誤
                    soup = BeautifulSoup(response_html, 'html.parser')
                    error_span = soup.find('span', {'class': 'feedbackPanelERROR'})
                    if error_span and '驗證碼' in error_span.get_text():
                        print("驗證碼錯誤，重試...")
                        result['error'] = "驗證碼錯誤"
                        time.sleep(2)
                        continue
                    else:
                        result['success'] = True
                        result['available_trains'] = []
                        result['error'] = "目前沒有可用車次"
                        return result
                
            except Exception as e:
                print(f"檢查過程發生錯誤: {e}")
                result['error'] = str(e)
                time.sleep(2)
                continue
        
        return result


def test_real_query():
    """測試真實查詢"""
    checker = THSRAvailabilityChecker()
    
    # 使用明天的日期進行測試
    tomorrow = date.today()
    # tomorrow = tomorrow.replace(day=tomorrow.day + 1)
    test_date = tomorrow.strftime("%Y/%m/%d")
    
    print(f"測試查詢: 台北 → 左營, 日期: {test_date}")
    
    result = checker.check_availability(
        origin="台北",
        destination="左營",
        travel_date=test_date,
        time_option="900A",
        ticket_count=1,
        seat_class="標準",
        save_captcha=True
    )
    
    print("\n" + "="*60)
    print("查詢結果:")
    print("="*60)
    print(f"成功: {result['success']}")
    print(f"錯誤: {result['error']}")
    print(f"辨識的驗證碼: {result['captcha_recognized']}")
    print(f"可用車次數: {len(result['available_trains'])}")
    
    if result['available_trains']:
        print("\n可用車次:")
        for train in result['available_trains'][:5]:  # 只顯示前5個
            print(f"  車次 {train['train_number']}: {train['departure_time']} → {train['arrival_time']} ({train['duration']})")
    
    return result


if __name__ == '__main__':
    test_real_query()
