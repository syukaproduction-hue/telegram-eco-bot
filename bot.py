import os
import requests
from datetime import datetime, timedelta

ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY")
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")
NEWS_API_KEY = os.environ.get("NEWS_API_KEY")


def fetch_news(from_date, to_date):
    """NewsAPI에서 한국 + 세계 경제 뉴스 가져오기"""
    all_articles = []

    # 1. 세계 경제 뉴스 (영어)
    global_url = "https://newsapi.org/v2/everything"
    global_params = {
        "q": "economy OR stock market OR interest rate OR trade OR inflation OR GDP",
        "language": "en",
        "from": from_date,
        "to": to_date,
        "sortBy": "popularity",
        "pageSize": 20,
        "apiKey": NEWS_API_KEY,
    }
    global_res = requests.get(global_url, params=global_params)
    if global_res.status_code == 200:
        articles = global_res.json().get("articles", [])
        for a in articles:
            all_articles.append({
                "title": a.get("title", ""),
                "description": a.get("description", ""),
                "source": a.get("source", {}).get("name", ""),
                "type": "글로벌"
            })

    # 2. 한국 경제 뉴스
    korea_url = "https://newsapi.org/v2/everything"
    korea_params = {
        "q": "한국 경제 OR 주식 OR 환율 OR 금리 OR 무역 OR 코스피",
        "language": "ko",
        "from": from_date,
        "to": to_date,
        "sortBy": "popularity",
        "pageSize": 20,
        "apiKey": NEWS_API_KEY,
    }
    korea_res = requests.get(korea_url, params=korea_params)
    if korea_res.status_code == 200:
        articles = korea_res.json().get("articles", [])
        for a in articles:
            all_articles.append({
                "title": a.get("title", ""),
                "description": a.get("description", ""),
                "source": a.get("source", {}).get("name", ""),
                "type": "한국"
            })

    return all_articles


def get_economic_news():
    today = datetime.now()
    weekday = today.weekday()
    today_str = today.strftime("%Y년 %m월 %d일")

    # 날짜 범위 설정
    if weekday == 0:  # 월요일: 주말 뉴스
        from_date = (today - timedelta(days=2)).strftime("%Y-%m-%d")
        to_date = (today - timedelta(days=1)).strftime("%Y-%m-%d")
        saturday = (today - timedelta(days=2)).strftime("%m월 %d일")
        sunday = (today - timedelta(days=1)).strftime("%m월 %d일")
        period = f"{saturday}~{sunday} 주말"
    else:  # 화~금: 전날 뉴스
        from_date = (today - timedelta(days=1)).strftime("%Y-%m-%d")
        to_date = today.strftime("%Y-%m-%d")
        yesterday = (today - timedelta(days=1)).strftime("%m월 %d일")
        period = yesterday

    # 뉴스 가져오기
    articles = fetch_news(from_date, to_date)

    # 뉴스 목록 텍스트로 변환
    news_text = ""
    for i, a in enumerate(articles[:40]):
        news_text += f"[{a['type']}] {a['source']}: {a['title']}\n{a['description']}\n\n"

    if not news_text:
        news_text = "뉴스를 가져오지 못했습니다. Claude 자체 지식으로 정리합니다."

    # Claude API로 정리
    headers = {
        "Content-Type": "application/json",
        "x-api-key": ANTHROPIC_API_KEY,
        "anthropic-version": "2023-06-01",
    }

    payload = {
        "model": "claude-sonnet-4-20250514",
        "max_tokens": 2000,
        "messages": [
            {
                "role": "user",
                "content": f"""오늘은 {today_str}이야. 아래는 {period} 동안의 한국 및 세계 경제 뉴스야.
이 뉴스들을 바탕으로 가장 중요한 이슈 Top 10을 아래 형식으로 정리해줘.
한국 뉴스와 글로벌 뉴스를 적절히 섞어서 선정하고, 모두 한국어로 작성해줘.

--- 뉴스 원문 ---
{news_text}
-----------------

형식:
📊 *{period} 경제 이슈 Top 10*
_{today_str} 아침 브리핑_

1️⃣ *[제목]* [🇰🇷 또는 🌍]
→ [2-3줄 핵심 요약]

2️⃣ *[제목]* [🇰🇷 또는 🌍]
→ [2-3줄 핵심 요약]

(... 10개까지, 🇰🇷=한국, 🌍=글로벌)

💡 *한 줄 총평*
[전체 경제 흐름 한 줄 정리]

텔레그램 Markdown 형식으로 작성해줘.""",
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
        "parse_mode": "Markdown",
    }
    response = requests.post(url, json=payload)
    response.raise_for_status()
    print("✅ 텔레그램 전송 완료!")
    return response.json()


def main():
    today = datetime.now()
    weekday = today.weekday()

    if weekday >= 5:
        print("⏭️ 주말이라 건너뜁니다.")
        return

    print(f"🚀 경제 뉴스 봇 실행 중... ({today})")
    news = get_economic_news()
    send_telegram_message(news)


if __name__ == "__main__":
    main()
