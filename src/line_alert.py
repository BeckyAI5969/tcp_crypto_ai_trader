import os
import requests
from dotenv import load_dotenv


load_dotenv()

token = os.getenv("LINE_CHANNEL_ACCESS_TOKEN")
user_id = os.getenv("LINE_USER_ID")

headers = {
    "Authorization": f"Bearer {token}",
    "Content-Type": "application/json"
}

data = {
    "to": user_id,
    "messages": [
        {
            "type": "text",
            "text": "✅ TCP Crypto AI Trader\nPush Message test successful."
        }
    ]
}

response = requests.post(
    "https://api.line.me/v2/bot/message/push",
    headers=headers,
    json=data
)

print(response.status_code)
print(response.text)