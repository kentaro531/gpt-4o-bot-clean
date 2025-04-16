import os
from dotenv import load_dotenv
import openai
import requests
from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler
from slack_sdk import WebClient

load_dotenv()

client = openai.OpenAI(
    api_key=os.environ["OPENAI_API_KEY"],
    project=os.environ["OPENAI_PROJECT_ID"]
)

app = App(token=os.environ["SLACK_BOT_TOKEN"])
web_client = WebClient(token=os.environ["SLACK_BOT_TOKEN"])

@app.event("app_mention")
def handle_mention(event, say, context):
    channel = event["channel"]
    thread_ts = event.get("thread_ts") or event["ts"]

    # スレッド履歴の取得
    response = web_client.conversations_replies(channel=channel, ts=thread_ts)
    messages = response.get("messages", [])

    gpt_messages = []

    # システムプロンプト（性格・トーン）
    gpt_messages.append({
        "role": "system",
        "content": (
            "あなたはLOOK UP GPT 4oというSlack上のAIアシスタントです。"
            "親しみやすく、丁寧でプロフェッショナルな口調で、Slackのスレッドの流れを汲み取りながらユーザーに的確な助言を行います。"
            "必要に応じて太字や箇条書きで視認性を高め、ユーザーの疑問に寄り添った構成で答えてください。"
        )
    })

    # スレッド履歴をOpenAIに渡す形式に整形
    for m in messages:
        role = "assistant" if m.get("bot_id") else "user"
        gpt_messages.append({"role": role, "content": m["text"]})

    # GPT-4o呼び出し
    completion = client.chat.completions.create(
        model="gpt-4o",
        messages=gpt_messages
    )

    # 返答をSlackにスレッド投稿
    say(text=completion.choices[0].message.content, thread_ts=thread_ts)

if __name__ == "__main__":
    SocketModeHandler(app, os.environ["SLACK_APP_TOKEN"]).start()
