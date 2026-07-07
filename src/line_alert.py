import os
import requests
from dotenv import load_dotenv


class LineAlert:

    def __init__(self):
        load_dotenv()
        self.token = os.getenv("LINE_CHANNEL_ACCESS_TOKEN")
        self.user_id = os.getenv("LINE_USER_ID")

    def send(self, message):
        headers = {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json"
        }

        data = {
            "to": self.user_id,
            "messages": [
                {
                    "type": "text",
                    "text": message
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


def main():
    line = LineAlert()
    line.send("✅ TCP Crypto AI Trader\nLINE Alert class test successful.")


if __name__ == "__main__":
    main()