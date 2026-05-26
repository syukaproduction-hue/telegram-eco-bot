import os
import re
import time
import requests
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta

ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY")
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")
NEWS_API_KEY = os.environ.get("NEWS_API_KEY")

TELEGRAM_MAX_LEN = 4000

# 경제 섹션 RSS 피드 (연합뉴스·한국경제·매일경제·서울경제·조선비즈)
KOREA_RSS_FEEDS = [
    "https://www.yna.co.kr/rss/economy.xml",
    "https://www.hankyung.com/feed/economy",
    "https://www.mk.co.kr/rss/40300001/",
    "https://www.sedaily.com/RSSFeed/Economy",
    "https://biz.chosun.com/rss/economy.xml",
]


def fetch_korea_rss():
    articles = []
    seen_titles = set()
    headers = {"User-Agent": "Mozilla/5.0"}

    for feed_url in KOREA_RSS_FEEDS:
        try:
            res = requests.get(feed_url, headers=headers, timeout=10)
            if res.status_code != 200:
                continue
            root = ET.fromstring(res.content)
            for item in root.findall(".//item")[:10]:
                title = item.findtext("title", "").strip()
                desc = item.findtext("description", "").strip()
                desc = re.sub(r"<[^>]+>", "", desc).strip()
                if title and title not in seen_titles:
                    seen_titles.add(title)
                    articles.append({
                        "title": title,
                        "description": desc,
                        "type": "한국"
                    })
        except Exception:
            continue

    return articles


def fetch_news(from_date, to_date):
    base_url = "https://newsapi.org/v2/everything"

    global_articles = []
    global_params = {
        "q": "economy OR stock market OR interest rate OR trade OR inflation",
        "language": "en",
        "from": from_date,
        "to": to_date,
        "sortBy": "popularity",
        "pageSize": 20,
        "apiKey": NEWS_API_KEY,
    }
    global_res = requests.get(base_url, params=global_params)
    if global_res.status_code == 200:
        for a in global_res.json().get("articles", []):
            global_articles.append({
                "title": a.get("title", ""),
                "description": a.get("description", ""),
                "type": "글로벌"
            })

    korea_articles = fetch_korea_rss()

    # 글로벌 6개 + 한국 4개 목표, 한국 부족분은 글로벌로 채워 항상 10개 유지
    korea_count = min(len(korea_articles), 4)
    global_count = min(len(global_articles), 10 - korea_count)
    selected = global_articles[:global_count] + korea_articles[:korea_count]
    return selected


def enforce_length(text, max_len=3600):
    if len(text) <= max_len:
        return text

    totalp_text = ""
    for marker in ["💡 한 줄 총평", "💡 한줄 총평", "💡"]:
        pos = text.rfind(marker)
        if pos > 0:
            totalp_text = "\n\n" + text[pos:]
            text = text[:pos].rstrip()
            break

    available = max_len - len(totalp_text)
    if len(text) > available:
        cut = text[:available]
        boundary = cut.rfind("\n\n")
        text = cut[:boundary] if boundary > 0 else cut

    return text.strip() + totalp_text


def get_economic_news():
    now_utc = datetime.utcnow()
    now_kst = now_utc + timedelta(hours=9)
    today_str = now_kst.strftime("%Y년 %m월 %d일")
    from_date = (now_utc - timedelta(days=1)).strftime("%Y-%m-%d")
    to_date = now_utc.strftime("%Y-%m-%d")

    articles = fetch_news(from_date, to_date)

    news_text = ""
    for a in articles:
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
        "max_tokens": 3000,
        "messages": [
            {
                "role": "user",
                "content": f"""오늘 {today_str}입니다. 아래 경제 뉴스 {len(articles)}개를 순서대로 정리해주세요.

반드시 지킬 규칙:
- 아래 원문 {len(articles)}개를 순서 그대로 번호 순으로 정리할 것 (선택하거나 빠뜨리지 말 것)
- 별표(*), 언더스코어(_), 백틱(`), 샵(#) 등 마크다운 특수문자 사용 금지
- 이모지 사용 가능
- 일반 텍스트로만 작성

출력 형식 (이 형식을 그대로 따를 것):
📅 {today_str} 경제 뉴스 Top {len(articles)}

1️⃣ 뉴스 제목 🌍
→ 2~3문장, 마침표로 구분, 합산 60~90자. 예: 핵심 사실. 배경 또는 영향. 전망.

2️⃣ 뉴스 제목 🇰🇷
→ 2~3문장, 마침표로 구분, 합산 60~90자. 예: 핵심 사실. 배경 또는 영향. 전망.

(글로벌 뉴스는 🌍, 한국 뉴스는 🇰🇷)

💡 한 줄 총평
전체 경제 흐름 2문장, 합산 60~80자.

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

    while "\n\n\n" in result:
        result = result.replace("\n\n\n", "\n\n")

    result = enforce_length(result.strip(), max_len=3600)
    return result


def send_telegram_message(text):
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
        response = requests.post(url, json=payload)
        response.raise_for_status()
        if len(chunks) > 1:
            print(f"✅ 메시지 {i}/{len(chunks)} 전송 완료")
            time.sleep(1)

    print("✨ 텔레그램 메시지 전송 완료!")


def main():
    now_utc = datetime.utcnow()
    now_kst = now_utc + timedelta(hours=9)
    weekday = now_kst.weekday()

    if weekday >= 5:
        print("⏸️ 주말이라 뉴스를 전송하지 않습니다.")
        return

    print(f"🌏 경제 뉴스 수집 중입니다 ({now_kst})")
    news = get_economic_news()
    send_telegram_message(news)


if __name__ == "__main__":
    main()
