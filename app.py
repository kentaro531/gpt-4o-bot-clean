import os
from dotenv import load_dotenv
import openai
from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler

# ローカル実行用：.env を読み込む（Renderでは不要）
load_dotenv()

# OpenAIクライアント（プロジェクトキー対応）
client = openai.OpenAI(
    api_key=os.environ["OPENAI_API_KEY"],
    project=os.environ["OPENAI_PROJECT_ID"]
)

# Slackアプリの初期化
app = App(token=os.environ["SLACK_BOT_TOKEN"])

# メンションを検知して応答する関数
@app.event("app_mention")
def handle_mention(event, say, context):
    # メンション部分を削除して質問文だけを取り出す
    user_input = event["text"].replace(f"<@{context['bot_user_id']}>", "").strip()
    thread_ts = event.get("thread_ts") or event["ts"]

    # GPT-4o へ問い合わせ
    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "user", "content": user_input}
        ]
    )

    # スレッドでSlackに返信
    say(text=response.choices[0].message.content, thread_ts=thread_ts)

# Socket Modeで起動
if __name__ == "__main__":
    SocketModeHandler(app, os.environ["SLACK_APP_TOKEN"]).start()