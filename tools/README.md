# tools/

AIHOT 프레임워크와 별도로 동작하는 운영 도구 모음.

- `aihot-to-notion/` — `101 Ai Hot News` Notion 페이지에 일일 브리핑 하위 페이지 누적 (06:10 크론). 중복방지 + 100블록 분할. 상세: 해당 폴더 README 참조.
- `ai-news-radar/` — RSS 수집→AI 분류→배달 파이프라인에서 모델 교체된 파일만 발췌 (process.py / ai_classify.py: ZAI glm / NIM → command-code muse-spark-1.3-contributor). 전체 파이프라인 아카이브 아님.
