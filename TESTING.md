# 테스트 가이드

## 실행 명령어

```bash
# 단위 테스트 (mock, 빠름, API 키 불필요)
docker compose exec backend python -m pytest tests/ -v --ignore=tests/test_e2e.py

# E2E 테스트 (실제 API, 느림, API 키 필요)
docker compose exec backend python -m pytest tests/test_e2e.py -v

# 특정 파일
docker compose exec backend python -m pytest tests/test_sourcer.py -v
```

## 테스트 파일 매핑

| Phase | 테스트 파일 | 테스트 내용 |
|-------|-----------|-----------|
| Phase 2 | `tests/test_api.py` | 구독자 CRUD API |
| Phase 3 | `tests/test_sourcer.py` | RSS 수집, 중복 제거, 24시간 필터 |
| Phase 4 | `tests/test_curator.py` | LLM 선별 (mock), 스코어링, JSON 파싱 |
| Phase 5 | `tests/test_translator.py` | 번역 (mock), 한국어 패스스루, 병렬 처리 |
| Phase 6 | `tests/test_editor.py` | 리포트 생성 (mock), 마크다운/HTML 출력 |
| Phase 7 | `tests/test_publisher.py` | 발송 (mock), API 키 없을 때 스킵 |
| Phase 8 | `tests/test_pipeline.py` | 전체 파이프라인 E2E (mock) |
| Phase 9 | `tests/test_api.py` 확장 | 리포트 API, 파이프라인 트리거 |
| Phase 11 | `tests/test_e2e.py` | 실제 API 키로 통합 테스트 |

## mock 전략

외부 API는 항상 mock:

```python
# OpenAI mock
@patch("app.pipeline.curator.OpenAI")
def test_curator_select(mock_openai):
    mock_openai.return_value.chat.completions.create.return_value = ...

# RSS mock (로컬 fixture)
@patch("app.pipeline.sourcer.feedparser.parse")
def test_sourcer_collect(mock_parse):
    mock_parse.return_value = load_fixture("rss_sample.xml")
```

## E2E 테스트 (Phase 11)

스크립트 E2E — Python에서 실제 API 키로 백엔드 순차 호출:

```python
# tests/test_e2e.py
async def test_full_pipeline():
    # 1. 구독자 등록
    sub = await client.post("/api/subscribers", json={
        "email": "test@test.com", "name": "Test", "sectors": ["macro", "tech"]
    })
    assert sub.status_code == 201

    # 2. 파이프라인 실행 (실제 RSS + OpenAI 호출)
    run = await client.post("/api/pipeline/run")
    assert run.status_code == 200

    # 3. 리포트 생성 확인
    reports = await client.get("/api/reports")
    assert len(reports.json()) > 0

    # 4. 리포트에 기사 포함 확인
    report = await client.get(f"/api/reports/{reports.json()[0]['id']}")
    assert len(report.json()["articles"]) >= 3

    # 5. 이메일 발송 확인 (RESEND_API_KEY 있을 때만)
```
