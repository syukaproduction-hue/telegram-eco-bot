import os
import requests
from datetime import datetime, timedelta

ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY")
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")
NEWS_API_KEY = os.environ.get("NEWS_API_KEY")


def fetch_news(from_date, to_date):
    all_articles = []

    global_url = "https://newsapi.org/v2/everything"
    global_params = {
        "q": "economy OR stock market OR interest rate OR trade OR inflation",
        "language": "en",
        "from": from_date,
        "to": to_date,
        "sortBy": "popularity",
        "pageSize": 20,
        "apiKey": NEWS_API_KEY,
    }
    global_res = requests.get(global_url, params=global_params)
    if global_res.status_code == 200:
        for a in global_res.json().get("articles", []):
            all_articles.append({
                "title": a.get("title", ""),
                "description": a.get("description", ""),
                "source": a.get("source", {}).get("name", ""),
                "type": "글로벌"
            })

    korea_params = {
        "q": "금리 또는 주식 OR경제 OR 무역 OR 인플레이션",
        "language": "ko",
        "from": from_date,
        "to": to_date,
        "sortBy": "popularity",
        "pageSize": 20,
        "apiKey": NEWS_API_KEY,
    }
    korea_res = requests.get(global_url, params=korea_params)
    if korea_res.status_code == 200:
        for a in korea_res.json().get("articles", []):
            all_articles.append({
                "title": a.get("title", ""),
                "description": a.get("description", ""),
                "source": a.get("source", {}).get("name", ""),
                "type": "금리"
            })

    return all_articles


def get_economic_news():
    today = datetime.now()
    weekday = today.weekday()
    today_str = today.strftime("%Y년 %m월 %d일")

    if weekday == 0:
        from_date = (today - timedelta(days=2)).strftime("%Y-%m-%d")
        to_date = (today - timedelta(days=1)).strftime("%Y-%m-%d")
        saturday = (today - timedelta(days=2)).strftime("%m월 %d일")
        sunday = (today - timedelta(days=1)).strftime("%m월 %d일")
        period = f"{saturday}~{sunday} 주말"
    else:
        from_date = (today - timedelta(days=1)).strftime("%Y-%m-%d")
        to_date = today.strftime("%Y-%m-%d")
        yesterday = (today - timedelta(days=1)).strftime("%m월 %d일")
        period = yesterday

    articles = fetch_news(from_date, to_date)

    news_text = ""
    for a in articles[:40]:
        news_text += f"[{a['type']}] {a['source']}: {a['title']}\n{a['description']}\n\n"

    if not news_text:
        news_text = "죄송합니다 경제 뉴스를 찾을 수 없습니다. 금리, 주식, 무역 관련 뉴스가 없거나 오류가 발생했습니다."

    headers = {
        "Content-Type": "application/json",
        "x-api-key": ANTHROPIC_API_KEY,
        "anthropic-version": "2023-06-01",
    }

    payload = {
        "model": "claude-sonnet-4-5",
        "max_tokens": 2000,
        "messages": [
            {
                "role": "user",
                "content": f"""오늘 {today_str}입니다. {period} 경제 뉴스를 정리하고 분석해주세요. 금리, 주식, 무역 관련 뉴스를 중심으로 분석하세요.

--경제뉴스 분석--
{news_text}
-------------------

🌍 {period} 주요 경제 뉴스
{today_str} 기준

(1 [글로벌] [주요 이슈] [뉴스 제목] [요약]
   [2-3줄 핵심 분석]

(2 [글로벌] [주요 이슈] [뉴스 제목] [요약]
   [2-3줄 핵심 분석]

(...10개 주요 이슈, 순서는 중요도 기준)

💡 국내 경제 뉴스 주요 키워드
[금리 관련] [주식 관련] [무역 관련]

💼 시장 분석
[금리 이슈 분석] [주식 동향] [무역 전망]

💻 해석 및 분석
[2-3줄 요약]

일반 텍스트 형식으로 작성하세요. 별표(*), 언더스코어(_), 대괄호([]), 백틱(`) 등 마크다운 특수문자를 사용하지 마세요.""",
            }
        ],
    }

    response = requests.post(
        "https://api.anthropic.com/v1/messages", headers=headers, json=payload
    )
    response.raise_for_status()

    data = response.json()
    result = ""
    for block in data.get("content", []):
        if block.get("type") == "text":
            result += block.get("text", "")
    return result


def send_telegram_message(text):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": text,
    }
    response = requests.post(url, json=payload)
    response.raise_for_status()
    print("✨ 텔레그램 메시지 전송 완료!")
    return response.json()


def main():
    today = datetime.now()
    weekday = today.weekday()

    if weekday >= 5:
        print("⏸️ 주말이라 뉴스를 전송하지 않습니다.")
        return

    print(f"🌏 경제 뉴스 수집 중입니다 ({today})")
    news = get_economic_news()
    send_telegram_message(news)


if __name__ == "__main__":
    main()
