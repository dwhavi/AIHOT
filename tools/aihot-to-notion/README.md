# aihot-to-notion

`101 Ai Hot News` Notion 페이지에 AIHOT 분석을 하위 페이지로 누적하는 스크립트.

## 구조

- `lib_notion.py` — 공용 헬퍼 (env 로드, API 호출, 블록 빌더, 자식페이지 제목 조회)
- `aihot_subpage.py` — 메인 (1건 = 1 하위 페이지, `날짜 - 주제` 규칙)
- `/tmp/aihot_to_notion.py` — 구 토글 방식 (deprecated, 참고용)

## 사용법

```bash
python3 aihot_subpage.py "AIHOT 파악 정리"
python3 aihot_subpage.py "AI Hot News와 개발 관련 이슈"
```

- 같은 `날짜 - 주제` 페이지가 이미 있으면 `SKIP` 후 종료 (중복 생성 없음)
- 토큰은 코드에 없음. `~/.hermes/.env`의 `NOTION_API_KEY` 사용

## cron 예시 (일간 누적 시)

```
0 8 * * * /usr/bin/python3 /Users/dwhavi/Projects/aihot-to-notion/aihot_subpage.py "일일 브리핑" >> /tmp/aihot_cron.log 2>&1
```
