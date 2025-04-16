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

def is_too_shallow(text):
    keywords = ["わかりません", "提供できません", "確認してください", "アクセスできません", "最新情報ではありません"]
    return any(kw in text.lower() for kw in keywords)

def search_serpapi(query):
    url = "https://serpapi.com/search"
    params = {
        "q": query,
        "api_key": os.environ["SERPAPI_KEY"],
        "hl": "ja",
        "gl": "jp"
    }
    res = requests.get(url, params=params).json()
    snippets = [r["snippet"] for r in res.get("organic_results", []) if "snippet" in r]
    return "\n".join(snippets[:3])

@app.event("app_mention")
def handle_mention(event, say, context):
    channel = event["channel"]
    thread_ts = event.get("thread_ts") or event["ts"]

    response = web_client.conversations_replies(channel=channel, ts=thread_ts)
    messages = response.get("messages", [])

    gpt_messages = [
        {
            "role": "system",
            "content": (
                "あなたはLOOK UP GPT 4oというSlack上のAIアシスタントです。"
                "Slackのスレッド履歴をふまえて、親しみやすく丁寧なトーンで名探偵コナン風に回答します。"
                "情報が不足している場合、正確な回答を作るために質問をしてください。"
            )
        }
    ]

    for m in messages:
        role = "assistant" if m.get("bot_id") else "user"
        gpt_messages.append({"role": role, "content": m["text"]})

    completion = client.chat.completions.create(
        model="gpt-4o",
        messages=gpt_messages
    )

    result_text = completion.choices[0].message.content

    if is_too_shallow(result_text):
        query = messages[-1]["text"]
        search_result = search_serpapi(query)
        gpt_messages.append({
            "role": "user",
            "content": f"さっきの質問について、以下の検索結果を参考に、もう一度丁寧に答えてください：\n\n{search_result}"
        })
        completion = client.chat.completions.create(
            model="gpt-4o",
            messages=gpt_messages
        )
        result_text = completion.choices[0].message.content

    say(text=result_text, thread_ts=thread_ts)

if __name__ == "__main__":
    SocketModeHandler(app, os.environ["SLACK_APP_TOKEN"]).start()