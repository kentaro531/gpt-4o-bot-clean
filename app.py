import os
import re
import io
import requests
import openai
import pdfplumber
import pandas as pd
import pytesseract
from PIL import Image
from docx import Document
from dotenv import load_dotenv
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

def fix_slack_bold(text):
    text = text.replace('**', '*')
    return re.sub(r'- \*(.+?)\*:', lambda m: f'- *{m.group(1)}*:', text)

def read_pdf(content):
    text = ""
    with pdfplumber.open(io.BytesIO(content)) as pdf:
        for page in pdf.pages:
            text += page.extract_text() or ""
    return text

def read_word(content):
    doc = Document(io.BytesIO(content))
    return "\n".join(p.text for p in doc.paragraphs)

def read_excel(content):
    df = pd.read_excel(io.BytesIO(content), sheet_name=None)
    texts = []
    for name, sheet in df.items():
        texts.append(f"--- シート: {name} ---\n{sheet.head(10).to_string(index=False)}")
    return "\n".join(texts)

def read_image(content):
    image = Image.open(io.BytesIO(content))
    return pytesseract.image_to_string(image, lang='jpn')

def extract_file_text(files):
    text = ""
    for file in files:
        file_url = file['url_private']
        file_type = file.get('filetype')
        headers = {"Authorization": f"Bearer {os.environ['SLACK_BOT_TOKEN']}"}
        response = requests.get(file_url, headers=headers)
        if response.status_code != 200:
            continue
        content = response.content
        if file_type == "pdf":
            text += read_pdf(content)
        elif file_type == "xlsx":
            text += read_excel(content)
        elif file_type in ["jpg", "png"]:
            text += read_image(content)
        elif file_type == "docx":
            text += read_word(content)
    return text

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

@app.event("app_mention")
def handle_app_mention(event, say):
    user_input = event.get("text", "")
    thread_ts = event.get("thread_ts") or event.get("ts")
    files = event.get("files", [])
    file_text = extract_file_text(files) if files else ""

    query_gen = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": "あなたはユーザーの質問に対してWeb検索キーワードを生成するアシスタントです。"},
            {"role": "user", "content": user_input}
        ]
    )
    search_query = query_gen.choices[0].message.content.strip()
    search_text = search_serpapi(search_query) + "\n" + search_google_cse(search_query)

    gpt_messages = [
        {"role": "system", "content": "あなたはSlackのAI税理士アシスタントです。以下の質問とファイル内容、検索結果をもとに、実務的かつ丁寧に構成された回答をしてください。Slackでは *太字* や箇条書きを活用してください。"},
        {"role": "user", "content": f"質問内容：{user_input}\n\n添付資料の内容：{file_text[:3000]}\n\n検索結果：{search_text}"}
    ]

    answer = client.chat.completions.create(
        model="gpt-4o",
        messages=gpt_messages
    )

    final_text = fix_slack_bold(answer.choices[0].message.content)
    say(text=final_text, thread_ts=thread_ts)

if __name__ == "__main__":
    SocketModeHandler(app, os.environ["SLACK_APP_TOKEN"]).start()
