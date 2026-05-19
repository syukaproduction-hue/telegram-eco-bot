import os
import requests
from datetime import datetime, timedelta

# ✅ 환경변수에서 키 불러오기
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY")
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")


def get_economic_news():
    """요일에 따라 다른 프롬프트로 Claude API 호출"""
    today = datetime.now()
    weekday = today.weekday()  # 0=월, 1=화, 2=수, 3=목, 4=금, 5=토, 6=일
    today_str = today.strftime("%Y년 %m월 %d일")

    # 월요일: 주말(토~일) 이슈
    if weekday == 0:
        saturday = (today - timedelta(days=2)).strftime("%m월 %d일")
        sunday = (today - timedelta(days=1)).strftime("%m월 %d일")
        period = f"{saturday}~{sunday} 주말"
        period_desc = f"{saturday}부터 {sunday} 주말 동안"
    # 화~금요일: 전날 이슈
    else:
        yesterday = (today - timedelta(days=1)).strftime("%m월 %d일")
        period = f"{yesterday}"
        period_desc = f"{yesterday} 하루 동안"

    headers = {
        "Content-Type": "application/json",
        "x-api-key": ANTHROPIC_API_KEY,
        "anthropic-version": "2023-06-01",
    }

    payload = {
        "model": "claude-sonnet-4-20250514",
        "max_tokens": 2000,
        "tools": [{"type": "web_search_20250305", "name": "web_search"}],
        "messages": [
            {
                "role": "user",
                "content": f"""오늘은 {today_str}이야. {period_desc} 발생한 세계 경제 이슈 Top 10을 웹 검색해서 아래 형식으로 정리해줘.

형식:
📊 *{period} 세계 경제 이슈 Top 10*
_{today_str} 아침 브리핑_

1️⃣ *[제목]*
→ [2-3줄 핵심 요약]

2️⃣ *[제목]*
→ [2-3줄 핵심 요약]

(... 10개까지)

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
    """텔레그램으로 메시지 전송"""
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

    # 토요일(5), 일요일(6)은 실행 안 함
    if weekday >= 5:
        print("⏭️ 주말이라 건너뜁니다.")
        return

    print(f"🚀 경제 뉴스 봇 실행 중... ({today})")
    news = get_economic_news()
    send_telegram_message(news)


if __name__ == "__main__":
    main()
