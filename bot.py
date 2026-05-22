import os
import requests
from datetime import datetime, timedelta

ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY")
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")
NEWS_API_KEY = os.environ.get("NEWS_API_KEY")

TELEGRAM_MAX_LEN = 4000


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
        "q": "금리 OR 주식 OR 경제 OR 무역 OR 인플레이션",
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
                "type": "한국"
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
        news_text += f"[{a['type']}] {a['title']}\n{a['description']}\n\n"

    if not news_text:
        news_text = "경제 뉴스를 찾을 수 없습니다."

    headers = {
        "Content-Type": "application/json",
        "x-api-key": ANTHROPIC_API_KEY,
        "anthropic-version": "2023-06-01",
    }

    payload = {
        "model": "claude-sonnet-4-6",
        "max_tokens": 1200,
        "messages": [
            {
                "role": "user",
                "content": f"""오늘 {today_str}입니다. {period} 경제 뉴스 Top 10을 정리해주세요.

반드시 지킬 규칙:
- 전체 응답은 2000자 이내
- 별표(*), 언더스코어(_), 백틱(`), 샵(#) 등 마크다운 특수문자 사용 금지
- 이모지 사용 가능
- 일반 텍스트로만 작성

출력 형식 (반드시 이 형식 그대로):
📅 {today_str} 경제 뉴스 Top 10

1️⃣ 뉴스 제목 🌍
→ 핵심 내용을 1~2문장으로 요약. 마침표로 구분.

2️⃣ 뉴스 제목 🇰🇷
→ 핵심 내용을 1~2문장으로 요약. 마침표로 구분.

(글로벌 뉴스는 🌍, 한국 뉴스는 🇰🇷 사용. 총 10개, 중요도 순)

💡 한 줄 총평
전체 경제 흐름을 1~2문장으로 요약.

---경제뉴스 원문---
{news_text}
-------------------""",
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

    # 연속 빈 줄 정리
    while "\n\n\n" in result:
        result = result.replace("\n\n\n", "\n\n")

    return result.strip()


def send_telegram_message(text):
    """4000자 단위로 분할 전송 (Telegram 4096자 제한 대응)"""
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"

    chunks = []
    while len(text) > TELEGRAM_MAX_LEN:
        split_pos = text.rfind("\n", 0, TELEGRAM_MAX_LEN)
        if split_pos == -1:
            split_pos = TELEGRAM_MAX_LEN
        chunks.append(text[:split_pos])
        text = text[split_pos:].lstrip("\n")
    if text:
        chunks.append(text)

    for i, chunk in enumerate(chunks, 1):
        payload = {"chat_id": TELEGRAM_CHAT_ID, "text": chunk}
        try:
            response = requests.post(url, json=payload)
            response.raise_for_status()
            if len(chunks) > 1:
                print(f"✅ 메시지 {i}/{len(chunks)} 전송 완료")
        except Exception as e:
            print(f"⚠️ 메시지 {i}/{len(chunks)} 전송 실패: {e}")
            raise

    print("✨ 텔레그램 메시지 전송 완료!")


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
