import os
import requests
from datetime import datetime

# ✅ 여기에 본인 키 입력
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "여기에_API_키_입력")
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "여기에_봇_토큰_입력")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID", "여기에_채팅ID_입력")


def get_economic_news():
    """Claude API로 세계 경제 이슈 Top 10 생성"""
    today = datetime.now().strftime("%Y년 %m월 %d일")

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
                "content": f"""오늘({today}) 기준 최신 세계 경제 이슈 Top 10을 웹 검색해서 아래 형식으로 정리해줘.

형식:
📊 *이번 주 세계 경제 이슈 Top 10*
_{today} 기준_

1️⃣ *[제목]*
→ [2-3줄 핵심 요약]

2️⃣ *[제목]*
→ [2-3줄 핵심 요약]

(... 10개까지)

💡 *한 줄 총평*
[이번 주 경제 흐름 한 줄 정리]

텔레그램 Markdown 형식으로 작성해줘.""",
            }
        ],
    }

    response = requests.post(
        "https://api.anthropic.com/v1/messages", headers=headers, json=payload
    )
    response.raise_for_status()

    data = response.json()
    # content 블록 중 text만 추출
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
    print(f"🚀 경제 뉴스 봇 실행 중... ({datetime.now()})")
    news = get_economic_news()
    send_telegram_message(news)


if __name__ == "__main__":
    main()
