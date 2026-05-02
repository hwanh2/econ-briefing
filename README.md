# Econ Briefing

경제 뉴스 자동 큐레이션 + 번역 + 리포트 생성 파이프라인

## 프로젝트 개요

Econ Briefing은 해외 경제 뉴스를 자동으로 수집, 선별, 번역하여 매일 아침 한국어 브리핑 리포트를 생성하고 이메일로 발송하는 풀스택 서비스입니다.

이 프로젝트는 **"문서 중심 자동 코드 생성(Document-Driven Code Generation)"** 해커톤의 결과물입니다. 먼저 구현 계획(PLAN.md)과 설계 문서를 작성한 후, AI 서브에이전트가 이 문서를 바탕으로 자동으로 코드를 생성하고 테스트까지 완료하는 방식으로 개발되었습니다.

- 배포: `docker compose up -d`
- 프론트엔드: http://localhost:3000
- API: http://localhost:8000
- API 문서: http://localhost:8000/docs

---

## 기술 스택

| 구성 요소 | 기술 |
|----------|------|
| 파이프라인 | Python 3.12, OpenAI SDK (직접 호출, 별도 프레임워크 없음) |
| LLM 모델 | gpt-4o-mini (번역), gpt-4o (큐레이션/편집) |
| 백엔드 | FastAPI, SQLAlchemy, PostgreSQL |
| 프론트엔드 | Next.js 15, Tailwind CSS, shadcn/ui |
| 인프라 | Docker Compose (로컬) |
| 이메일 | Resend (옵셔널) |

---

## 아키텍처

```
┌──────────────────────────────────────────────────────────────┐
│  Frontend (Next.js 15 + Tailwind)                          │
│  ├── /           → 구독 등록 폼 (섹터 8개 체크박스)        │
│  ├── /reports    → 리포트 목록                             │
│  ├── /reports/[id] → 리포트 상세 (HTML 렌더링)            │
│  └── /unsubscribe  → 구독 해지                            │
└────────────────────┬─────────────────────────────────────────┘
                     │ API (FastAPI)
                     ▼
┌──────────────────────────────────────────────────────────────┐
│  Backend (FastAPI + SQLAlchemy + PostgreSQL)                 │
│  Routers: /api/subscribers, /api/reports, /api/pipeline      │
│  Scheduler: APScheduler @ 매일 06:00 cron                    │
└────────────────────┬─────────────────────────────────────────┘
                     │
                     ▼
┌──────────────────────────────────────────────────────────────┐
│  Pipeline (async 순차 실행)                                  │
│  Sourcer → Curator → Translator → Editor → Publisher         │
│  각 단계 결과 저장: output/{date}/ (JSON + md + html)       │
└──────────────────────────────────────────────────────────────┘
```

### 파이프라인 상세

| 단계 | 에이전트 | LLM 모델 | 역할 |
|------|----------|----------|------|
| 1 | **Sourcer** | - | 5개 RSS 피드 비동기 수집 (feedparser + httpx) |
| 2 | **Curator** | gpt-4o | 기사 스코어링 + 섹터 분류 (JSON response_format) |
| 3 | **Translator** | gpt-4o-mini | 영문→한국어 번역, 한국어 소스는 passthrough |
| 4 | **Editor** | gpt-4o | 마크다운 리포트 + HTML 변환 + "오늘의 핵심" |
| 5 | **Publisher** | - | Resend 이메일 발송 (API 키 없으면 skip) |

---

## 하네스 엔지니어링(Harness Engineering)

이 프로젝트의 핵심 개발 방법론은 **"문서를 먼저 쓰고, 문서를 읽는 AI 에이전트가 코드를 생성"**하는 것입니다.

### 방법론

1. **명세 우선(Spec-First)**: 코드를 직접 작성하기 전에 `PLAN.md`에 Phase별 구현 체크리스트, API 스키마, DB 스키마, 검증 명령어, 통과 기준을 모두 문서화합니다.
2. **설계 문서(Design Doc)**: 프론트엔드 디자인은 `DESIGN.md`에 컴포넌트 구조와 스타일 가이드를 정의합니다.
3. **자동 생성(Auto-Generation)**: 문서가 완성되면 AI 서브에이전트가 문서를 읽고, 체크리스트를 따라 코드를 생성하고, 문서에 명시된 검증 명령어를 실행하여 통과 기준을 확인합니다.
4. **문서 버전 관리**: `SESSION_LOG.md`에 Phase마다 주요 결정과 우회 방법을 기록하여 세션 간 맥락을 유지합니다.

이 방식의 장점:
- 사람이 코드를 직접 치는 시간 대비 문서 품질로 성능이 결정됨
- 구현과 검증이 한 사이클 내에서 완결됨
- `/clear` 후에도 문서만 있으면 복구 가능

---

## 서브에이전트 전략

이 프로젝트는 **멀티-에이전트 오케스트레이션(Multi-Agent Orchestration)**을 통해 개발되었습니다.

### 역할 분리

| 계층 | 모델 | 책임 |
|------|------|------|
| **메인 (오케스트레이터)** | Claude Opus 4.6 | 계획 수립, Phase 전환, 검증, 품질 관리 |
| **서브에이전트** | Claude Sonnet 4.6 | 코드 구현, 테스트 작성, 리팩토링 전담 |

### 워크플로우

```
/start-feature → 이슈 생성 + 피처 브랜치 체크아웃
      ↓
메인 에이전트 (Opus): PLAN.md Phase 해석 + 구현 지시서 작성
      ↓
서브에이전트 (Sonnet): 코드 구현 + 테스트 작성
      ↓
검증 통과 → PLAN.md 체크 + SESSION_LOG.md 기록
      ↓
/finish-feature → git push + PR 생성 + merge
```

### 규칙

- 메인 에이전트는 코드 파일을 **직접 읽거나 수정하지 않음**. 전부 서브에이전트에 위임합니다.
- 서브에이전트는 하나의 Phase를 완료한 후 결과를 보고하고, 메인 에이전트가 다음 Phase를 할당합니다.
- Phase 3~7(파이프라인 에이전트들)은 독립적이라 **병렬 개발**이 가능합니다.
- Phase 9~10(백엔드 API + 프론트엔드) 역시 인터페이스가 명확해 병렬 개발이 가능합니다.

---

## 실행 방법

### 사전 준비

```bash
cp .env.example .env
# .env에 OPENAI_API_KEY 필수 입력
# RESEND_API_KEY 는 옵셔널
```

### Docker Compose로 시작

```bash
docker compose up -d            # 시작
docker compose up -d --build    # 재빌드
docker compose logs -f backend  # 로그
```

### 통합 테스트

```bash
docker compose exec backend python -m pytest tests/ -v
```

### API 수동 테스트

```bash
# 구독자 등록
curl -X POST localhost:8000/api/subscribers \
  -H "Content-Type: application/json" \
  -d '{"email":"test@test.com","name":"Test","sectors":["macro","tech"]}'

# 파이프라인 수동 실행
curl -X POST localhost:8000/api/pipeline/run

# 리포트 확인
curl localhost:8000/api/reports
```

---

## 프로젝트 구조

```
econ-briefing/
├── docker-compose.yml
├── .env.example
├── PLAN.md                # 구현 체크리스트
├── SESSION_LOG.md         # Phase 완료 맥락
├── DESIGN.md              # 프론트엔드 디자인 명세
├── TESTING.md             # 테스트 가이드
├── backend/
│   ├── Dockerfile
│   ├── requirements.txt
│   ├── app/
│   │   ├── main.py          # FastAPI entry
│   │   ├── config.py        # 환경변수 로드
│   │   ├── database.py      # DB 연결
│   │   ├── models.py        # SQLAlchemy 모델
│   │   ├── schemas.py       # Pydantic 스키마
│   │   ├── routers/
│   │   │   ├── subscribers.py
│   │   │   ├── reports.py
│   │   │   └── pipeline.py
│   │   └── pipeline/
│   │       ├── orchestrator.py
│   │       ├── sourcer.py
│   │       ├── curator.py
│   │       ├── translator.py
│   │       ├── editor.py
│   │       └── publisher.py
│   └── tests/
│       ├── test_sourcer.py
│       ├── test_curator.py
│       ├── test_translator.py
│       ├── test_editor.py
│       ├── test_publisher.py
│       ├── test_orchestrator.py
│       ├── test_api.py
│       ├── test_e2e.py
│       └── test_error_handling.py
└── frontend/
    ├── Dockerfile
    ├── package.json
    ├── app/
    │   ├── page.tsx          # 구독 등록
    │   ├── layout.tsx
    │   ├── globals.css
    │   ├── reports/
    │   │   └── page.tsx      # 리포트 목록
    │   ├── reports/[id]/
    │   │   └── page.tsx      # 리포트 상세
    │   └── unsubscribe/
    │       └── page.tsx      # 구독 해지
    └── tailwind.config.ts
```

---

## 테스트

- 총 **74개 테스트** 통과
- **Mock 기반 테스트**: OpenAI API, RSS 피드, Resend 이메일 등 모든 외부 의존성을 mock하여 네트워크 없이 실행 가능
- **E2E 테스트**: 구독 등록 → 파이프라인 실행 → 리포트 생성 → API 확인까지 전체 흐름 검증
- **에러 핸들링 테스트**: RSS 피드 실패, LLM 타임아웃, Publisher 스킵 등 엣지 케이스 13개 추가

---

## 환경변수

| 변수 | 필수 | 설명 |
|------|------|------|
| `OPENAI_API_KEY` | O | OpenAI API 키 (gpt-4o, gpt-4o-mini 호출용) |
| `RESEND_API_KEY` | X | Resend 이메일 발송 키 (없으면 발송 skip) |
| `DATABASE_URL` | O | PostgreSQL 연결 문자열 |

---

## 라이선스

MIT
