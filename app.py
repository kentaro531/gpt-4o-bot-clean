from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler
import openai
import os
from dotenv import load_dotenv

load_dotenv()

app = App(token=os.environ["SLACK_BOT_TOKEN"])
openai.api_key = os.environ["OPENAI_API_KEY"]

@app.event("app_mention")
def handle_mention(event, say):
    text = event["text"]
    thread_ts = event.get("thread_ts") or event["ts"]
    user_input = text.replace("@gpt-4o-bot", "").strip()

    response = openai.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": "あなたは優秀なアシスタントです。"},
            {"role": "user", "content": user_input}
        ]
    )

    say(text=response.choices[0].message.content, thread_ts=thread_ts)

if __name__ == "__main__":
    SocketModeHandler(app, os.environ["SLACK_APP_TOKEN"]).start()