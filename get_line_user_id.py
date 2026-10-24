#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LINE User ID 查詢工具
"""

import sys
import requests

def get_user_id(channel_access_token):
    """
    透過 LINE Messaging API 取得追蹤者的 User ID
    
    注意: 您需要先將 LINE Official Account 加為好友
    """
    url = "https://api.line.me/v2/bot/followers/ids"
    headers = {
        "Authorization": f"Bearer {channel_access_token}"
    }
    
    try:
        response = requests.get(url, headers=headers, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            user_ids = data.get('userIds', [])
            
            if user_ids:
                print("✅ 成功取得 User ID！\n")
                print("找到以下 User ID:")
                for i, user_id in enumerate(user_ids, 1):
                    print(f"{i}. {user_id}")
                
                print("\n請將這些 User ID 其中之一設定到 GitHub Secrets 的 LINE_USER_ID")
                print("\n提示: 如果有多個 User ID，通常第一個就是您自己的。")
                return user_ids
            else:
                print("⚠️ 沒有找到任何追蹤者")
                print("\n請確認:")
                print("1. 您已經在手機上將此 Official Account 加為好友")
                print("2. Channel Access Token 正確無誤")
                return []
        else:
            print(f"❌ API 呼叫失敗")
            print(f"狀態碼: {response.status_code}")
            print(f"回應內容: {response.text}")
            
            if response.status_code == 401:
                print("\n可能原因: Channel Access Token 無效或已過期")
                print("請到 LINE Developers Console 重新產生 token")
            
            return None
    
    except requests.exceptions.RequestException as e:
        print(f"❌ 網路請求錯誤: {e}")
        return None

def test_send_message(channel_access_token, user_id):
    """
    測試發送訊息到指定的 User ID
    """
    url = "https://api.line.me/v2/bot/message/push"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {channel_access_token}"
    }
    
    payload = {
        "to": user_id,
        "messages": [
            {
                "type": "text",
                "text": "🚄 台灣高鐵票務監控系統\n\n這是一則測試訊息，如果您收到這則訊息，表示設定成功！"
            }
        ]
    }
    
    try:
        response = requests.post(url, headers=headers, json=payload, timeout=10)
        
        if response.status_code == 200:
            print(f"✅ 測試訊息已發送到 {user_id}")
            print("請檢查您的 LINE 是否收到訊息")
            return True
        else:
            print(f"❌ 發送訊息失敗")
            print(f"狀態碼: {response.status_code}")
            print(f"回應內容: {response.text}")
            return False
    
    except requests.exceptions.RequestException as e:
        print(f"❌ 網路請求錯誤: {e}")
        return False

def main():
    print("=" * 60)
    print("LINE User ID 查詢工具")
    print("台灣高鐵票務監控系統")
    print("=" * 60)
    print()
    
    # 取得 Channel Access Token
    if len(sys.argv) > 1:
        token = sys.argv[1]
    else:
        print("請輸入您的 LINE Channel Access Token:")
        print("(可在 LINE Developers Console 的 Messaging API 分頁中找到)")
        print()
        token = input("Token: ").strip()
    
    if not token:
        print("❌ 錯誤: Token 不能為空")
        sys.exit(1)
    
    print("\n正在查詢 User ID...\n")
    
    # 查詢 User ID
    user_ids = get_user_id(token)
    
    if user_ids:
        print("\n" + "=" * 60)
        print("要測試發送訊息嗎？(y/n)")
        choice = input("> ").strip().lower()
        
        if choice == 'y':
            if len(user_ids) == 1:
                selected_id = user_ids[0]
            else:
                print("\n請選擇要測試的 User ID (輸入編號):")
                try:
                    idx = int(input("> ").strip()) - 1
                    selected_id = user_ids[idx]
                except (ValueError, IndexError):
                    print("無效的選擇")
                    sys.exit(1)
            
            print(f"\n正在發送測試訊息到 {selected_id}...\n")
            test_send_message(token, selected_id)
    
    print("\n" + "=" * 60)
    print("完成！")
    print("=" * 60)

if __name__ == '__main__':
    main()
