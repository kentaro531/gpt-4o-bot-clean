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

# 専門キーワードリスト
TAX_KEYWORDS = [
    "インボイス", "確定申告", "税制改正", "法人税", "消費税", "所得税", "源泉徴収",
    "年末調整", "納税", "税務調査", "税務署", "税理士", "税務会計", "税金還付",
    "電子申告", "e-Tax", "控除", "住民税", "印紙税", "固定資産税", "地方税",
    "税務処理", "税効果会計", "非課税", "課税所得", "免税", "税率", "更正の請求",
    "繰越欠損金", "租税条約", "申告期限", "追徴課税", "課税標準", "納付書",
]

ACCOUNTING_KEYWORDS = [
    "決算", "仕訳", "会計ソフト", "帳簿", "監査",
    "複式簿記", "勘定科目", "会計基準", "日本基準", "IFRS", "J-GAAP",
    "仕訳帳", "総勘定元帳", "貸借対照表", "損益計算書", "キャッシュ・フロー計算書",
    "株主資本等変動計算書", "決算書", "経理", "月次決算", "内部統制", "監査法人",
    "会計士", "税務会計", "法定監査", "内部監査", "外部監査", "減価償却", "資産計上",
    "会計年度", "経理処理", "科目分類", "月次試算表", "勘定合って銭足らず", "BS", "PL", "SS","資産", "負債", "純資産",
]

FINANCE_KEYWORDS = [
    "資金調達", "財務分析", "キャッシュフロー", "経営指標",
    "資金繰り", "銀行融資", "投資家", "投資", "資本政策", "株式発行", "増資",
    "M&A", "リスケジュール", "リスケ", "自己資本比率", "ROE", "ROA", "PER",
    "PBR", "EPS", "有価証券報告書", "財務諸表", "流動比率", "固定比率", "損益分岐点",
    "資本コスト", "WACC", "社債発行", "格付", "CF計画", "DCF法", "NPV", "IRR",
    "レバレッジ", "デットファイナンス", "エクイティファイナンス",
]

FREEE_KEYWORDS = [
    "freee", "フリー会計", "freeeでの登録", "freee 使い方",
    "freee会計", "フリー会計ソフト", "freee 請求書", "freee 経費精算", "freee API",
    "freee 開業届", "freeeの導入", "freee サポート", "freee 連携", "freee 設定",
    "フリー 人事労務", "freee 料金", "freee チュートリアル", "フリー マニュアル",
    "クラウド会計 freee", "freee 確定申告", "freee 固定資産", "freee 領収書 登録",
]

def contains_keyword(text):
    text_lower = text.lower()
    return any(
        kw.lower() in text_lower
        for kw in TAX_KEYWORDS + ACCOUNTING_KEYWORDS + FINANCE_KEYWORDS + FREEE_KEYWORDS
    )

def search_google_cse(query):
    url = "https://www.googleapis.com/customsearch/v1"
    params = {
        "key": os.environ["GOOGLE_API_KEY"],
        "cx": os.environ["GOOGLE_CSE_CX"],
        "q": query,
        "hl": "ja"
    }
    res = requests.get(url, params=params).json()
    snippets = [item["snippet"] for item in res.get("items", [])]
    return "\n".join(snippets[:3]) if snippets else "検索結果が見つかりませんでした。"

def search_serpapi(query):
    url = "https://serpapi.com/search"
    params = {
        "q": query,
        "api_key": os.environ["SERPAPI_KEY"],
        "hl": "ja",
        "gl": "jp"
    }
    res = requests.get(url, params=params).json()
    snippets = []
    for result in res.get("organic_results", []):
        if "snippet" in result:
            snippets.append(result["snippet"])
    return "\n".join(snippets[:3]) if snippets else "検索結果が見つかりませんでした。"

@app.event("app_mention")
def handle_mention(event, say, context):
    user_input = event["text"].replace(f"<@{context['bot_user_id']}>", "").strip()
    thread_ts = event.get("thread_ts") or event["ts"]

    if contains_keyword(user_input):
        search_result = search_google_cse(user_input)
        source = "Google CSE（税務・会計・財務特化）"
    else:
        search_result = search_serpapi(user_input)
        source = "SerpAPI（汎用検索）"

    response = client.chat.completions.create(
    model="gpt-4o",
    messages=[
        {
            "role": "system",
            "content": "あなたはChatGPTとして、親しみやすく、丁寧でプロフェッショナルな口調でユーザーに回答します。"
        },
        {
            "role": "user",
            "content": f"以下の検索結果をもとに、ユーザーの質問に分かりやすく丁寧に答えてください：\n\n{search_result}"
        }
    ]
)

    say(
        text=f"🔍 使用検索エンジン: *{source}*\n\n{response.choices[0].message.content}",
        thread_ts=thread_ts
    )

if __name__ == "__main__":
    SocketModeHandler(app, os.environ["SLACK_APP_TOKEN"]).start()