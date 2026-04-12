# Econ Briefing

뉴스 자동 큐레이션 + 번역 + 리포트 생성 파이프라인.

## 기술 스택

| 컴포넌트 | 기술 |
|----------|------|
| Pipeline | Python 3.12, OpenAI SDK (직접 호출, 프레임워크 없음) |
| LLM 모델 | gpt-4o-mini (번역), gpt-4o (큐레이션/편집) |
| Backend | FastAPI, SQLAlchemy, PostgreSQL |
| Frontend | Next.js 15, Tailwind CSS, shadcn/ui |
| Infra | Docker Compose (로컬) |
| Email | Resend (옵셔널) |

## 문서 참조

| 파일 | 내용 |
|------|------|
| **PLAN.md** | 구현 체크리스트 (Phase별 작업 + 검증 + 통과 기준) |
| **SESSION_LOG.md** | Phase 완료 시 맥락 요약 (/clear 후 복구용) |
| **DESIGN.md** | 프론트엔드 디자인 명세 |
| **TESTING.md** | 테스트 가이드 (mock 전략, E2E, 파일 매핑) |

## GitHub

- **Repo**: https://github.com/hwanh2/econ-briefing
- **기본 브랜치**: main — 직접 push 금지, PR로만 머지
- **커밋**: `feat:` / `fix:` / `test:` / `docs:` / `chore:`

### Phase별 워크플로우
```
/start-feature → 이슈 + 피처 브랜치
    ↓
Agent(model="sonnet") → 구현 + 테스트
    ↓
검증 통과 → PLAN.md 체크 + SESSION_LOG.md 기록
    ↓
/finish-feature → push + PR + merge
```

## 디렉토리 구조

```
backend/app/
├── main.py, config.py, database.py, models.py, schemas.py
├── routers/        → subscribers.py, reports.py
└── pipeline/       → orchestrator.py, sourcer.py, curator.py, translator.py, editor.py, publisher.py
backend/tests/      → test_sourcer.py, test_curator.py, ...
frontend/app/       → page.tsx, reports/, components/
```

## 파이프라인 인터페이스

```
Sourcer → [RawArticle] → Curator → [CuratedArticle] → Translator → [TranslatedArticle] → Editor → [Report] → Publisher
```

### 스키마
```
RawArticle:        title, url, source, published, snippet
CuratedArticle:    + score, reason, sector
TranslatedArticle: + title_ko, content_ko
Report:            title, date, summary, content_md, content_html, articles[]
```

### 섹터 (8개)
```
macro: 매크로 (금리/환율/GDP)
finance: 금융/증시
tech: 테크
ai: AI/머신러닝
energy: 에너지/원자재
realestate: 부동산
politics: 글로벌 정치/지정학
startup: 스타트업/VC
```

### RSS 피드 (10개)
reuters, cnbc, marketwatch, hankyung, mk, techcrunch, theverge, hackernews, bbc, platum
> URL은 PLAN.md Phase 3에 명시

## 서브에이전트 전략

- **메인 (Opus)**: 계획, 검증, Phase 전환만
- **서브에이전트 (Sonnet)**: 코드 구현 전담
- Phase 3~7 병렬 가능, Phase 9+10 병렬 가능

### 규칙
- 메인에서 코드 파일 직접 읽기/쓰기 **금지** (서브에이전트에 위임)
- 긴 출력은 `| tail -5` 등으로 제한
- 테스트 통과 후에만 `/finish-feature`

## 컨텍스트 관리

- **매 2~3 Phase마다 `/clear`**
- `/clear` 후 복구: CLAUDE.md(자동) → PLAN.md(체크박스) → SESSION_LOG.md(맥락) → git branch
- Phase 완료 시 SESSION_LOG.md 업데이트 **필수**

### SESSION_LOG 작성 포맷
```markdown
## Phase N: 이름 (완료)
- 주요 결정: ...
- 이슈/우회: ...
- 다음 Phase 참고: ...
```

## Docker

```bash
docker compose up -d            # 시작
docker compose up -d --build    # 재빌드
docker compose logs -f backend  # 로그
```

## 환경변수 (.env)

```
OPENAI_API_KEY=sk-...     # 필수
RESEND_API_KEY=re_...     # 옵셔널
DATABASE_URL=postgresql://briefing:briefing@postgres:5432/briefing
```
