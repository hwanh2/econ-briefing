# Econ Briefing — 구현 체크리스트

> 프로젝트 규칙/스택/워크플로우는 CLAUDE.md 참조

## 진행 상태

- [x] Phase 1: 프로젝트 셋업 + Docker ✅
- [x] Phase 2: DB 모델 + 구독자 API ✅
- [ ] Phase 3: Sourcer 에이전트 (RSS 수집)
- [ ] Phase 4: Curator 에이전트 (LLM 선별)
- [ ] Phase 5: Translator 에이전트 (LLM 번역)
- [ ] Phase 6: Editor 에이전트 (리포트 구성)
- [ ] Phase 7: Publisher 에이전트 (이메일 발송)
- [ ] Phase 8: 파이프라인 오케스트레이터
- [ ] Phase 9: Backend API 완성
- [ ] Phase 10: Frontend
- [ ] Phase 11: 통합 테스트 + 스케줄러

---

## ~~Phase 1: 프로젝트 셋업 + Docker 기반~~ ✅

### 작업
- [ ] 디렉토리 구조 생성
- [ ] Docker Compose (postgres, backend, frontend)
- [ ] backend Dockerfile + requirements.txt
- [ ] frontend Dockerfile + package.json
- [ ] .env.example

### 디렉토리 구조
```
econ-briefing/
├── docker-compose.yml
├── .env.example
├── backend/
│   ├── Dockerfile
│   ├── requirements.txt
│   ├── app/
│   │   ├── main.py          # FastAPI entry
│   │   ├── config.py        # 환경변수 로드
│   │   ├── models.py        # SQLAlchemy 모델
│   │   ├── database.py      # DB 연결
│   │   ├── routers/
│   │   │   ├── subscribers.py
│   │   │   └── reports.py
│   │   └── pipeline/
│   │       ├── orchestrator.py
│   │       ├── sourcer.py
│   │       ├── curator.py
│   │       ├── translator.py
│   │       ├── editor.py
│   │       └── publisher.py
│   └── tests/
│       ├── test_sourcer.py
│       ├── test_pipeline.py
│       └── test_api.py
├── frontend/
│   ├── Dockerfile
│   ├── package.json
│   ├── app/
│   │   ├── page.tsx          # 구독 등록
│   │   ├── reports/
│   │   │   └── page.tsx      # 리포트 목록
│   │   └── reports/[id]/
│   │       └── page.tsx      # 리포트 상세
│   └── components/
│       ├── SubscribeForm.tsx
│       └── ReportCard.tsx
└── PLAN.md
```

### 검증
```bash
docker compose up -d
docker compose ps  # 3개 컨테이너 모두 healthy
curl http://localhost:8000/health  # {"status": "ok"}
curl http://localhost:3000  # Next.js 페이지 렌더
```

### 통과 기준
- [ ] `docker compose ps` → postgres, backend, frontend 모두 Up
- [ ] `curl localhost:8000/health` → 200 OK
- [ ] `curl localhost:3000` → HTML 응답

---

## Phase 2: DB 모델 + 구독자 API

### 작업
- [ ] SQLAlchemy 모델 정의 (subscribers, reports, report_articles, delivery_logs)
- [ ] Alembic 마이그레이션 (또는 create_all)
- [ ] 구독자 CRUD API (POST/GET/PUT/DELETE)
- [ ] Pydantic 스키마

### DB 스키마
```sql
subscribers:
  id          SERIAL PK
  email       VARCHAR UNIQUE NOT NULL
  name        VARCHAR
  sectors     TEXT[]          -- ['macro', 'tech', 'energy', ...]
  active      BOOLEAN DEFAULT true
  created_at  TIMESTAMP

reports:
  id          SERIAL PK
  date        DATE UNIQUE
  title       VARCHAR
  content_md  TEXT
  content_html TEXT
  created_at  TIMESTAMP

report_articles:
  id            SERIAL PK
  report_id     FK → reports
  title         VARCHAR
  source        VARCHAR
  original_url  VARCHAR
  summary_ko    TEXT
  translation   TEXT
  score         FLOAT
  sector        VARCHAR

delivery_logs:
  id            SERIAL PK
  subscriber_id FK → subscribers
  report_id     FK → reports
  sent_at       TIMESTAMP
  status        VARCHAR  -- 'sent', 'failed', 'skipped'
```

### 검증
```bash
# 컨테이너 안에서 테스트
docker compose exec backend python -m pytest tests/test_api.py -v

# API 수동 테스트
curl -X POST localhost:8000/api/subscribers \
  -H "Content-Type: application/json" \
  -d '{"email":"test@test.com","name":"Test","sectors":["macro","tech"]}'
# → 201 Created

curl localhost:8000/api/subscribers
# → [{"id":1,"email":"test@test.com",...}]
```

### 통과 기준
- [ ] 테이블 4개 생성됨
- [ ] POST /api/subscribers → 201
- [ ] GET /api/subscribers → 구독자 목록 반환
- [ ] PUT /api/subscribers/{id} → 섹터 변경 가능
- [ ] DELETE /api/subscribers/{id} → 삭제 가능

---

## Phase 3: Sourcer 에이전트 (RSS 수집)

### 작업
- [ ] RSS 피드 목록 설정 (config)
- [ ] feedparser로 기사 수집
- [ ] 중복 제거 (URL 기반)
- [ ] 24시간 이내 기사만 필터링
- [ ] 출력: raw_articles 리스트

### RSS 피드 목록
```python
FEEDS = {
    "reuters": "https://www.reuters.com/arc/outboundfeeds/v3/all/rss.xml",
    "cnbc_economy": "https://search.cnbc.com/rs/search/combinedcms/view.xml?partnerId=wrss01&id=20910258",
    "marketwatch": "https://feeds.marketwatch.com/marketwatch/topstories",
    "hankyung": "https://www.hankyung.com/feed/economy",
    "mk": "https://www.mk.co.kr/rss/30100041/",
}
```

### 검증
```bash
docker compose exec backend python -c "
from app.pipeline.sourcer import Sourcer
import asyncio
articles = asyncio.run(Sourcer().collect())
print(f'수집된 기사: {len(articles)}개')
for a in articles[:3]:
    print(f'  - [{a[\"source\"]}] {a[\"title\"][:50]}')
"
```

### 통과 기준
- [ ] 최소 10개 이상 기사 수집
- [ ] 각 기사에 title, url, source, published, snippet 포함
- [ ] 중복 URL 없음
- [ ] 24시간 이내 기사만 포함

---

## Phase 4: Curator 에이전트 (LLM 선별)

### 작업
- [ ] OpenAI API 클라이언트 래퍼
- [ ] 구독자 프로필(섹터) 기반 프롬프트 설계
- [ ] 기사 스코어링 (1-10) + 선정 이유
- [ ] 상위 5~8개 선별
- [ ] 출력: curated_articles 리스트

### 프롬프트 설계
```
System: 당신은 경제 뉴스 에디터입니다.
구독자 관심 섹터: {sectors}

아래 기사 목록에서 읽을 가치가 높은 순서대로 5~8개를 선별하세요.
각 기사에 1-10 스코어와 선정 이유를 달아주세요.

JSON 출력: [{"index": 0, "score": 9, "reason": "..."}, ...]
```

### 검증
```bash
docker compose exec backend python -c "
from app.pipeline.curator import Curator
from app.pipeline.sourcer import Sourcer
import asyncio

async def test():
    articles = await Sourcer().collect()
    curated = await Curator().select(articles, sectors=['macro', 'tech'])
    print(f'선별: {len(curated)}개')
    for a in curated:
        print(f'  [{a[\"score\"]}] {a[\"title\"][:50]}')
        print(f'       이유: {a[\"reason\"]}')

asyncio.run(test())
"
```

### 통과 기준
- [ ] 5~8개 기사 선별됨
- [ ] 각 기사에 score (1-10)와 reason 포함
- [ ] sectors와 관련 없는 기사는 제외됨
- [ ] JSON 파싱 에러 없음

---

## Phase 5: Translator 에이전트 (LLM 번역)

### 작업
- [ ] 영문 기사 → 한국어 번역
- [ ] 경제 용어 glossary 시스템 프롬프트
- [ ] 한국어 기사는 스킵 (passthrough)
- [ ] 병렬 번역 (asyncio.gather)
- [ ] 출력: translated_articles 리스트

### 검증
```bash
docker compose exec backend python -c "
from app.pipeline.translator import Translator
import asyncio

async def test():
    sample = {'title': 'Fed holds rates steady amid inflation concerns',
              'snippet': 'The Federal Reserve kept its benchmark rate unchanged...'}
    result = await Translator().translate(sample)
    print(f'제목: {result[\"title_ko\"]}')
    print(f'본문: {result[\"content_ko\"][:100]}')

asyncio.run(test())
"
```

### 통과 기준
- [ ] 영문 → 한국어 번역 정상 동작
- [ ] 경제 용어 자연스러움 (예: "Fed" → "연준", "rate hike" → "금리 인상")
- [ ] 한국어 기사 입력 시 원문 그대로 반환
- [ ] 병렬 처리 시 에러 없음

---

## Phase 6: Editor 에이전트 (리포트 구성)

### 작업
- [ ] 마크다운 리포트 생성
- [ ] 기사별 핵심 요약 (1~2줄)
- [ ] 기사 간 맥락 연결
- [ ] 시장 영향도 태깅 (HIGH/MEDIUM/LOW)
- [ ] HTML 변환 (이메일용)
- [ ] 출력: report.md + report.html

### 리포트 포맷
```markdown
# 📊 경제 브리핑 — 2025.01.15

## 오늘의 핵심
> 연준이 기준금리를 동결했습니다. 시장은 3월 인하 가능성에 주목하고 있습니다.

---

## 1. [HIGH] 연준 기준금리 동결, 3월 인하 시사
**출처**: Reuters | [원문 보기](...)

연준이 기준금리를 5.25-5.50%로 유지했습니다...

**핵심**: 파월 의장은 "데이터 의존적" 접근을 재확인하면서도...

---

## 2. [MEDIUM] 삼성전자 4분기 실적 서프라이즈
...
```

### 검증
```bash
docker compose exec backend python -c "
from app.pipeline.editor import Editor
import asyncio

async def test():
    sample_articles = [...]  # Phase 5 출력 사용
    report = await Editor().compose(sample_articles)
    print(report['content_md'][:500])
    print('---')
    print(f'HTML 길이: {len(report[\"content_html\"])}')

asyncio.run(test())
"
```

### 통과 기준
- [ ] 마크다운 리포트 생성됨
- [ ] "오늘의 핵심" 섹션 포함
- [ ] 각 기사에 영향도 태그 (HIGH/MEDIUM/LOW) 있음
- [ ] HTML 변환 정상
- [ ] 원문 링크 포함

---

## Phase 7: Publisher 에이전트 (이메일 발송)

### 작업
- [ ] Resend SDK 연동
- [ ] HTML 이메일 템플릿
- [ ] 구독자별 발송
- [ ] 발송 로그 기록 (delivery_logs)
- [ ] RESEND_API_KEY 없으면 skip (로그만 남김)

### 검증
```bash
# RESEND_API_KEY 없이 — 스킵 모드 확인
docker compose exec backend python -c "
from app.pipeline.publisher import Publisher
import asyncio

async def test():
    result = await Publisher().send(
        report_html='<h1>테스트</h1>',
        subscribers=[{'email': 'test@test.com', 'name': 'Test'}]
    )
    print(f'결과: {result}')  # {'skipped': 1, 'reason': 'no_api_key'}

asyncio.run(test())
"

# RESEND_API_KEY 있으면 — 실제 발송
# curl 또는 Resend 대시보드에서 발송 확인
```

### 통과 기준
- [ ] API 키 없을 때: 에러 없이 스킵, 로그 남김
- [ ] API 키 있을 때: 이메일 발송 성공
- [ ] delivery_logs 테이블에 기록됨

---

## Phase 8: 파이프라인 오케스트레이터

### 작업
- [ ] 5개 에이전트 순차 실행
- [ ] 중간 결과 파일 저장 (output/{date}/)
- [ ] 에러 발생 시 해당 단계부터 재실행 가능
- [ ] 전체 실행 로그
- [ ] DB에 리포트 저장

### 검증
```bash
# 전체 파이프라인 실행
docker compose exec backend python -m app.pipeline.orchestrator

# 결과 확인
docker compose exec backend ls output/$(date +%Y-%m-%d)/
# → raw_articles.json, curated_articles.json, translated_articles.json, report.md, report.html

# DB 확인
docker compose exec backend python -c "
from app.database import get_db
from app.models import Report
db = next(get_db())
report = db.query(Report).order_by(Report.id.desc()).first()
print(f'리포트: {report.title}')
print(f'날짜: {report.date}')
"
```

### 통과 기준
- [ ] 5개 에이전트 순차 실행 완료
- [ ] output/{date}/ 에 중간 결과물 5개 존재
- [ ] reports 테이블에 리포트 저장됨
- [ ] report_articles 테이블에 기사 저장됨
- [ ] 실행 로그에 각 단계 소요시간 출력

---

## Phase 9: Backend API 완성

### 작업
- [ ] GET /api/reports — 리포트 목록
- [ ] GET /api/reports/{id} — 리포트 상세
- [ ] POST /api/pipeline/run — 수동 파이프라인 실행
- [ ] GET /api/pipeline/status — 파이프라인 상태
- [ ] APScheduler 스케줄러 (매일 06:00)

### 검증
```bash
# 리포트 API
curl localhost:8000/api/reports
# → [{"id": 1, "date": "2025-01-15", "title": "..."}]

curl localhost:8000/api/reports/1
# → {"id": 1, "content_html": "...", "articles": [...]}

# 수동 실행
curl -X POST localhost:8000/api/pipeline/run
# → {"status": "started", "job_id": "..."}

# 스케줄러 확인
curl localhost:8000/api/pipeline/status
# → {"next_run": "2025-01-16T06:00:00", "last_run": "..."}
```

### 통과 기준
- [ ] 리포트 CRUD API 동작
- [ ] 파이프라인 수동 트리거 가능
- [ ] 스케줄러 등록됨 (06:00 매일)
- [ ] 에러 시 적절한 HTTP 코드 반환

---

## Phase 10: Frontend

### 작업
- [ ] 구독 등록 페이지 (이메일, 이름, 섹터 선택)
- [ ] 리포트 목록 페이지
- [ ] 리포트 상세 페이지 (마크다운 렌더링)
- [ ] 구독 해지 페이지
- [ ] 반응형 디자인

### 화면 목록
```
/                    → 구독 등록 폼
/reports             → 리포트 목록 (날짜별)
/reports/[id]        → 리포트 상세
/unsubscribe/[token] → 구독 해지
```

### 검증
```bash
# 브라우저에서 확인
open http://localhost:3000

# 또는 curl
curl localhost:3000 | grep "구독"
curl localhost:3000/reports | grep "브리핑"
```

### 통과 기준
- [ ] 구독 폼 → 제출 → DB에 저장됨
- [ ] 섹터 체크박스 동작
- [ ] 리포트 목록 표시
- [ ] 리포트 상세 마크다운 렌더링
- [ ] 모바일 반응형

---

## Phase 11: 통합 테스트 + 스케줄러

### 작업
- [ ] E2E: 구독 등록 → 파이프라인 실행 → 리포트 생성 → 웹 확인
- [ ] 스케줄러 동작 확인
- [ ] 에러 핸들링 (RSS 실패, LLM 타임아웃)
- [ ] 로그 정리

### 검증
```bash
# E2E 테스트
docker compose exec backend python -m pytest tests/ -v

# 전체 흐름 수동 테스트
curl -X POST localhost:8000/api/subscribers \
  -H "Content-Type: application/json" \
  -d '{"email":"harry@test.com","name":"Harry","sectors":["macro","tech"]}'

curl -X POST localhost:8000/api/pipeline/run

# 30초 대기 후
curl localhost:8000/api/reports | python -m json.tool
```

### 통과 기준
- [ ] 전체 파이프라인 E2E 성공
- [ ] 리포트가 웹에서 확인 가능
- [ ] 스케줄러 등록 확인
- [ ] `docker compose logs` 에 에러 없음

---

## 실행 순서 요약

```
Phase 1  → docker compose up 성공
Phase 2  → 구독자 API 동작
Phase 3  → RSS 기사 수집 성공
Phase 4  → LLM 기사 선별 성공        ← OPENAI_API_KEY 필요
Phase 5  → LLM 번역 성공
Phase 6  → 리포트 생성 성공
Phase 7  → 이메일 발송 (또는 스킵)    ← RESEND_API_KEY 옵셔널
Phase 8  → 전체 파이프라인 E2E
Phase 9  → Backend API 완성
Phase 10 → Frontend 완성
Phase 11 → 통합 테스트 + 스케줄러 ON → 자고 일어나면 리포트 확인
```

## 체크포인트 규칙

1. 각 Phase 완료 후 **검증 명령어 실행**
2. 통과 기준 **전부 체크**되어야 다음 Phase
3. 실패 시 **해당 Phase만 수정** 후 재검증
4. 절대 검증 없이 다음 Phase로 넘어가지 않음
