# KODEX 경제이슈 Top10 봇 — 작업 맥락

## 프로젝트 개요

텔레그램 채널 "KODEX 경제이슈 Top10"에 평일 오전 9시(KST)마다 경제 뉴스 Top 10을 자동 발송하는 봇.

- **저장소**: https://github.com/syukaproduction-hue/telegram-eco-bot
- **봇 파일**: `bot.py`
- **워크플로우**: `.github/workflows/daily_bot.yml`

---

## 실행 구조

```
cron-job.org (매 평일 오전 9시 KST)
    → GitHub API로 workflow_dispatch 트리거
        → GitHub Actions (ubuntu-latest)
            → bot.py 실행
                → 뉴스 수집 → Claude API → 텔레그램 전송
```

### 중요 규칙: 코드 수정 후 workflow_dispatch 자동 트리거 금지

봇이 오전 9시 기준 12시간 윈도우에서만 유효한 데이터를 수집하므로,
다른 시간대에 실행하면 "뉴스 없음" 안내가 텔레그램 채널 구독자에게 발송됨.
**코드 수정 → push만 하고 끝낼 것. 테스트 실행은 사용자가 직접 GitHub Actions에서 "Run workflow" 버튼으로 진행.**

---

## GitHub Actions Secrets (GitHub 서버에 저장됨)

| 시크릿 이름 | 용도 |
|---|---|
| `ANTHROPIC_API_KEY` | Claude API 호출 |
| `TELEGRAM_BOT_TOKEN` | 텔레그램 봇 토큰 |
| `TELEGRAM_CHAT_ID` | 텔레그램 채널 ID |
| `NEWS_API_KEY` | NewsAPI (글로벌 뉴스용) |

---

## 코드 구조 (bot.py)

### 1. 뉴스 수집 (`fetch_news` + `fetch_korea_rss`)

**글로벌 뉴스**: NewsAPI `/v2/everything`
- 영어, popularity순, 최대 20개
- 쿼리: `economy OR stock market OR interest rate OR trade OR inflation`

**한국 뉴스**: RSS 피드 직접 파싱 (NewsAPI 사용 안 함)
- 연합뉴스 경제, 한국경제 경제, 매일경제 경제, 서울경제 경제, 조선비즈 경제
- `xml.etree.ElementTree` (Python 내장, 추가 패키지 불필요)
- 이유: NewsAPI로 한국어 기사 검색 시 경제 무관 기사가 섞임

**선별**: 글로벌 상위 6개 + 한국 상위 4개 = 총 10개
- 한국 기사 4개 미만이면 글로벌로 채워 항상 10개 유지

### 2. 시간 처리

GitHub Actions는 UTC로 실행되므로 `datetime.utcnow()` 사용.
`now_kst = now_utc + timedelta(hours=9)` 로 KST 변환.
주말 판단도 KST 기준으로 처리.

NewsAPI 무료 플랜은 24시간 인덱싱 지연이 있으므로 날짜만 사용 (시간 필터 금지).
- `from_date = 어제 날짜`
- `to_date = 오늘 날짜`

### 3. Claude API 호출

- 모델: `claude-sonnet-4-6`
- `max_tokens`: 3000 (한국어 약 2.5 토큰/글자이므로 넉넉하게)
- 프롬프트에서 기사 수를 동적으로 전달 (`{len(articles)}개`)
- Claude에게 선택권 없이 주어진 기사를 순서대로 포맷팅만 시킴 (거부 방지)
- 마크다운 특수문자 사용 금지 (텔레그램 parse_mode 없음)

### 4. 길이 제어 (`enforce_length`)

- 3600자 초과 시 본문을 잘라내되 `💡 한 줄 총평` 섹션은 반드시 보존
- 텔레그램 한도는 4096자지만 여유 확보를 위해 4000자 단위로 분할 전송

---

## 과거에 발생했던 버그와 해결법

| 버그 | 원인 | 해결 |
|---|---|---|
| 오전 2:35에 중복 실행 | `schedule:` cron이 workflow에 남아있었음 | `workflow_dispatch`만 남기고 삭제 |
| 텔레그램 400 Bad Request | `parse_mode: "Markdown"` + 마크다운 특수문자 | parse_mode 제거, 프롬프트에서 특수문자 금지 |
| 내용이 8~9번에서 잘림 | max_tokens=700~1500으로 부족 | 3000으로 증가 + enforce_length 추가 |
| "뉴스 없음" 메시지 발송 | `datetime.now()` 사용으로 UTC/KST 혼용 | `datetime.utcnow()` + KST 변환으로 교체 |
| NewsAPI 시간 필터 결과 0건 | 무료 플랜 24시간 인덱싱 지연 | 시간 제거, 날짜만 사용 |
| 한국 기사 누락 (8번 이후 없음) | NewsAPI 한국어 기사 부족 | RSS 피드로 교체 |
| Claude가 포맷 거부 | "반드시 한국 5개" 강제 시 품질 미달 기사로 거부 | 코드에서 선별 후 Claude는 포맷팅만 |
| 총평 잘림 | enforce_length에서 총평 위치 못 찾음 | 여러 마커 패턴으로 탐색 (`💡 한 줄 총평`, `💡 한줄 총평`, `💡`) |

---

## 출력 형식 (텔레그램 메시지)

```
📅 2026년 05월 29일 경제 뉴스 Top 10

1️⃣ 뉴스 제목 🌍
→ 핵심 사실. 배경 또는 영향. 전망.

2️⃣ 뉴스 제목 🇰🇷
→ 핵심 사실. 배경 또는 영향. 전망.

... (총 10개)

💡 한 줄 총평
전체 경제 흐름 요약 2문장.
```

- 글로벌 뉴스: 🌍, 한국 뉴스: 🇰🇷
- 마크다운 없는 순수 텍스트

---

## 코드 수정 시 주의사항

1. `push` 후 자동 트리거 하지 말 것 (구독자에게 이상한 메시지 발송됨)
2. 테스트는 GitHub Actions 페이지에서 "Run workflow" 버튼으로 직접 실행
3. `sortBy=popularity` 유지할 것 — `publishedAt`으로 바꾸면 한국 기사 품질 급락
4. `parse_mode` 텔레그램 전송 시 절대 추가하지 말 것 — 400 에러 발생
5. max_tokens 3000 미만으로 낮추지 말 것 — 내용 잘림 발생
