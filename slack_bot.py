import os
from dotenv import load_dotenv
import openai
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError

load_dotenv()

SLACK_BOT_TOKEN = os.getenv("SLACK_BOT_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
CHANNEL_NAME = "#oss"

client = WebClient(token=SLACK_BOT_TOKEN)
openai.api_key = OPENAI_API_KEY

def generate_gpt_message(prompt: str) -> str:
    completion = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",
        messages=[{"role": "user", "content": prompt}]
    )
    return completion.choices[0].message["content"]

def send_slack_message(channel: str, text: str) -> None:
    try:
        response = client.chat_postMessage(channel=channel, text=text)
        print(f"메시지 전송 완료! (timestamp: {response['ts']})")
    except SlackApiError as e:
        error_msg = e.response.get("error", "Unknown error")
        print(f"메시지 전송 실패: {error_msg}")

if __name__ == "__main__":
    prompt = "oss에 대한 tmi를 하나 던져줘."
    message = generate_gpt_message(prompt)
    send_slack_message(CHANNEL_NAME, message)
