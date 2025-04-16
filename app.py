import os
from dotenv import load_dotenv
import openai
import requests
from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler

load_dotenv()

client = openai.OpenAI(
    api_key=os.environ["OPENAI_API_KEY"],
    project=os.environ["OPENAI_PROJECT_ID"]
)

app = App(token=os.environ["SLACK_BOT_TOKEN"])

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

def search_google_cse(query):
    url = "https://www.googleapis.com/customsearch/v1"
    params = {
        "key": os.environ["GOOGLE_API_KEY"],
        "cx": os.environ["GOOGLE_CSE_CX"],
        "q": query,
        "hl": "ja"
    }
    res = requests.get(url, params=params).json()
    snippets = [item["snippet"] for item in res.get("items", []) if "snippet" in item]
    return "\n".join(snippets[:3])

@app.event("app_mention")
def handle_mention(event, say, context):
    user_input = event["text"].replace(f"<@{context['bot_user_id']}>", "").strip()
    thread_ts = event.get("thread_ts") or event["ts"]

    # Try SerpAPI first
    search_result = search_serpapi(user_input)
    if search_result:
        source = "SerpAPI（汎用検索）"
    else:
        search_result = search_google_cse(user_input)
        source = "Google CSE（専門サイト検索）"

    if not search_result:
        search_result = "検索結果が見つかりませんでした。"

    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {
                "role": "system",
                "content": "あなたはChatGPTとして、親しみやすく、丁寧でプロフェッショナルな口調でユーザーに回答します。"
            },
            {
                "role": "user",
                "content": f"以下の検索結果をもとに、質問に答えてください：\n\n{search_result}"
            }
        ]
    )

    say(
        text=f"🔍 使用検索エンジン: *{source}*\n\n{response.choices[0].message.content}",
        thread_ts=thread_ts
    )

if __name__ == "__main__":
    SocketModeHandler(app, os.environ["SLACK_APP_TOKEN"]).start()