#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
台灣高鐵票務監控系統 - 單元測試
"""

import os
import sys
import json
import yaml
import pytest
from datetime import datetime
from unittest.mock import Mock, patch, mock_open

# 確保可以導入 checker 模組
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from checker import THSRMonitor, STATION_CODES


class TestStationCodes:
    """測試車站代碼對照"""
    
    def test_all_stations_have_codes(self):
        """確認所有車站都有對應的代碼"""
        expected_stations = [
            "南港", "台北", "板橋", "桃園", "新竹", "苗栗",
            "台中", "彰化", "雲林", "嘉義", "台南", "左營"
        ]
        for station in expected_stations:
            assert station in STATION_CODES
            assert len(STATION_CODES[station]) == 3
    
    def test_station_codes_are_unique(self):
        """確認車站代碼不重複"""
        codes = list(STATION_CODES.values())
        assert len(codes) == len(set(codes))


class TestTHSRMonitor:
    """測試 THSRMonitor 類別"""
    
    @pytest.fixture
    def monitor(self):
        """建立測試用的 monitor 實例"""
        return THSRMonitor()
    
    def test_init(self, monitor):
        """測試初始化"""
        assert monitor.session is not None
        assert monitor.tdx_token is None
    
    def test_generate_booking_url_with_train(self, monitor):
        """測試產生訂票網址（含車次）"""
        url = monitor.generate_booking_url(
            "2026-11-01", "台北", "左營", "813"
        )
        assert "https://irs.thsrc.com.tw/IMINT/" in url
        assert "origin=TPE" in url
        assert "destination=ZUY" in url
        assert "date=2026/11/01" in url
        assert "trainNo=813" in url
    
    def test_generate_booking_url_without_train(self, monitor):
        """測試產生訂票網址（不含車次）"""
        url = monitor.generate_booking_url(
            "2026-11-01", "台北", "左營"
        )
        assert "https://irs.thsrc.com.tw/IMINT/" in url
        assert "trainNo" not in url
    
    def test_load_watches_success(self, monitor, tmp_path):
        """測試載入監控設定（成功）"""
        config_file = tmp_path / "watches.yml"
        test_config = {
            'watches': [
                {
                    'id': 'test-1',
                    'enabled': True,
                    'travel_date': '2026-11-01',
                    'origin': '台北',
                    'destination': '左營',
                    'ticket_count': 2,
                    'seat_class': '標準'
                },
                {
                    'id': 'test-2',
                    'enabled': False,
                    'travel_date': '2026-11-02',
                    'origin': '台中',
                    'destination': '台北',
                    'ticket_count': 1,
                    'seat_class': '商務'
                }
            ]
        }
        
        with open(config_file, 'w', encoding='utf-8') as f:
            yaml.dump(test_config, f, allow_unicode=True)
        
        watches = monitor.load_watches(str(config_file))
        
        # 只應載入啟用的項目
        assert len(watches) == 1
        assert watches[0]['id'] == 'test-1'
        assert watches[0]['enabled'] is True
    
    def test_load_watches_file_not_found(self, monitor):
        """測試載入監控設定（檔案不存在）"""
        watches = monitor.load_watches('non_existent_file.yml')
        assert watches == []
    
    def test_load_previous_results_success(self, monitor, tmp_path):
        """測試載入先前結果（成功）"""
        results_file = tmp_path / "results.json"
        test_results = {
            'last_update': '2026-10-24T12:00:00',
            'results': [
                {
                    'watch_id': 'test-1',
                    'available_trains': []
                }
            ]
        }
        
        with open(results_file, 'w', encoding='utf-8') as f:
            json.dump(test_results, f)
        
        results = monitor.load_previous_results(str(results_file))
        
        assert results['last_update'] == '2026-10-24T12:00:00'
        assert len(results['results']) == 1
    
    def test_load_previous_results_file_not_found(self, monitor):
        """測試載入先前結果（檔案不存在）"""
        results = monitor.load_previous_results('non_existent_results.json')
        assert results == {'last_update': None, 'results': []}
    
    def test_save_results(self, monitor, tmp_path):
        """測試儲存結果"""
        results_file = tmp_path / "results.json"
        test_results = [
            {
                'watch_id': 'test-1',
                'available_trains': [
                    {
                        'train_number': '813',
                        'departure_time': '09:00'
                    }
                ]
            }
        ]
        
        monitor.save_results(test_results, str(results_file))
        
        # 驗證檔案已建立並包含正確內容
        assert results_file.exists()
        
        with open(results_file, 'r', encoding='utf-8') as f:
            saved_data = json.load(f)
        
        assert 'last_update' in saved_data
        assert saved_data['results'] == test_results
    
    def test_check_availability_mock(self, monitor):
        """測試座位可用性檢查（模擬模式）"""
        watch = {
            'id': 'test-1',
            'travel_date': '2026-11-01',
            'origin': '台北',
            'destination': '左營',
            'ticket_count': 2,
            'seat_class': '標準',
            'time_range': {
                'start': '09:00',
                'end': '12:00'
            }
        }
        
        result = monitor.check_availability_mock(watch)
        
        assert result['watch_id'] == 'test-1'
        assert result['travel_date'] == '2026-11-01'
        assert result['origin'] == '台北'
        assert result['destination'] == '左營'
        assert 'check_time' in result
        assert 'available_trains' in result
        assert result['status'] in ['success', 'warning', 'error']
    
    @patch('checker.requests.post')
    def test_send_line_notification_success(self, mock_post, monitor, monkeypatch):
        """測試發送 LINE 通知（成功）"""
        # 設定環境變數
        monkeypatch.setenv('LINE_CHANNEL_ACCESS_TOKEN', 'test_token')
        monkeypatch.setenv('LINE_USER_ID', 'U1234567890')
        
        # 模擬成功回應
        mock_response = Mock()
        mock_response.status_code = 200
        mock_post.return_value = mock_response
        
        result = monitor.send_line_notification('測試訊息')
        
        assert result is True
        mock_post.assert_called_once()
    
    @patch('checker.requests.post')
    def test_send_line_notification_failure(self, mock_post, monitor, monkeypatch):
        """測試發送 LINE 通知（失敗）"""
        monkeypatch.setenv('LINE_CHANNEL_ACCESS_TOKEN', 'test_token')
        monkeypatch.setenv('LINE_USER_ID', 'U1234567890')
        
        # 模擬失敗回應
        mock_response = Mock()
        mock_response.status_code = 400
        mock_response.text = 'Bad Request'
        mock_post.return_value = mock_response
        
        result = monitor.send_line_notification('測試訊息')
        
        assert result is False
    
    def test_send_line_notification_no_credentials(self, monitor):
        """測試發送 LINE 通知（無憑證）"""
        result = monitor.send_line_notification('測試訊息')
        assert result is False


class TestWatchesConfig:
    """測試監控設定檔格式"""
    
    def test_watches_yml_exists(self):
        """確認 watches.yml 存在"""
        watches_file = os.path.join(
            os.path.dirname(os.path.dirname(__file__)), 
            'watches.yml'
        )
        assert os.path.exists(watches_file)
    
    def test_watches_yml_valid_yaml(self):
        """確認 watches.yml 是有效的 YAML"""
        watches_file = os.path.join(
            os.path.dirname(os.path.dirname(__file__)), 
            'watches.yml'
        )
        with open(watches_file, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
        
        assert 'watches' in config
        assert isinstance(config['watches'], list)


class TestDateTimeHandling:
    """測試日期時間處理"""
    
    def test_iso_format_parsing(self):
        """測試 ISO 格式日期解析"""
        date_str = "2026-10-24T12:00:00"
        dt = datetime.fromisoformat(date_str)
        assert dt.year == 2026
        assert dt.month == 10
        assert dt.day == 24
    
    def test_date_format_conversion(self):
        """測試日期格式轉換"""
        date_str = "2026-11-01"
        dt = datetime.strptime(date_str, "%Y-%m-%d")
        formatted = dt.strftime("%Y/%m/%d")
        assert formatted == "2026/11/01"


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
