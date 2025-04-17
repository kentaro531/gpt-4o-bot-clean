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

# Web検索（SerpAPI）
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
    return "\n".join(snippets[:5])

# Web検索（Google CSE）
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
    return "\n".join(snippets[:5])

# シンプルなリアルタイム系質問の判定（天気・気温など）
def is_realtime_query(text):
    keywords = ["天気", "気温", "今日", "明日", "現在", "ニュース"]
    return any(kw in text.lower() for kw in keywords)

@app.event("app_mention")
def handle_mention(event, say, context):
    channel = event["channel"]
    thread_ts = event.get("thread_ts") or event["ts"]

    # スレッド履歴取得
    response = web_client.conversations_replies(channel=channel, ts=thread_ts)
    messages = response.get("messages", [])

    user_query = messages[-1]["text"]

    # GPTに検索クエリを生成してもらう
    query_gen = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": "あなたはユーザーの質問を検索に適した短いキーワードに変換するアシスタントです。"},
            {"role": "user", "content": user_query}
        ]
    )
    search_query = query_gen.choices[0].message.content.strip()

    # SerpAPI + Google CSE で検索（常に実施）
    serp_result = search_serpapi(search_query)
    cse_result = search_google_cse(search_query)
    combined_result = serp_result + "\n" + cse_result

    # 検索結果を再構成（要点抽出）
    restructure_prompt = [
        {"role": "system", "content": "あなたは検索結果を読み解き、実務に役立つ要点を抜き出す税理士アシスタントです。以下の検索結果から重複を除き、論点を整理してください。"},
        {"role": "user", "content": combined_result}
    ]
    refined_result = client.chat.completions.create(
        model="gpt-4o",
        messages=restructure_prompt
    ).choices[0].message.content

    # 柔軟な回答構成をGPTに指示
    prompt_text = (
        "あなたはLOOK UP ACCOUNTINGのAI税理士アシスタントです。Slackでの質問に対して、検索結果やスレッド文脈を参考に、"
        "丁寧かつプロフェッショナルに回答してください。質問が複雑な場合は、以下の構成で説明してください：\n\n"
        "1. 【導入】質問の意図を簡単に整理\n"
        "2. 【要点】答えを先に明確に\n"
        "3. 【理由・根拠】税務・会計の根拠や制度、条文に触れながら説明\n"
        "4. 【補足】実務上の注意点や現場での対処法\n\n"
        "ただし、質問がシンプルな場合（例：天気、気温、時間など）は、自然な口調で短く端的に答えてください。"
        "Slack上では *太字* を使い、改行・箇条書きを活用して見やすくしてください。"
    )

    gpt_messages = [
        {"role": "system", "content": prompt_text},
        {"role": "user", "content": f"以下の情報をもとに、質問に最適な形で答えてください：\n{refined_result}"}
    ]

    answer = client.chat.completions.create(
        model="gpt-4o",
        messages=gpt_messages
    )
    final_text = answer.choices[0].message.content.replace('**', '*')
    say(text=final_text, thread_ts=thread_ts)

if __name__ == "__main__":
    SocketModeHandler(app, os.environ["SLACK_APP_TOKEN"]).start()
