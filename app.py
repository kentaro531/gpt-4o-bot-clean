import os
from dotenv import load_dotenv
import openai
from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler

# 環境変数の読み込み（ローカル用）
load_dotenv()

# 新しいOpenAIクライアント（プロジェクト対応）
client = openai.OpenAI(
    api_key=os.environ["OPENAI_API_KEY"],
    project=os.environ["OPENAI_PROJECT_ID"]
)

# Slack Appの初期化
app = App(token=os.environ["SLACK_BOT_TOKEN"])

# メンションイベントを処理
@app.event("app_mention")
def handle_mention(event, say):
    user_input = event["text"].replace(f"<@{event['bot_id']}>", "").strip()
    thread_ts = event.get("thread_ts") or event["ts"]

    # GPT-4oへ問い合わせ
    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "user", "content": user_input}
        ]
    )

    # Slackへ返答
    say(text=response.choices[0].message.content, thread_ts=thread_ts)

# SocketModeで実行
if __name__ == "__main__":
    SocketModeHandler(app, os.environ["SLACK_APP_TOKEN"]).start()