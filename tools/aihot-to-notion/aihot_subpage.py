#!/usr/bin/env python3
"""AIHOT 파악 정리 -> Notion 101 Ai Hot News 하위 페이지로 누적. 중복방지 포함."""
import datetime
import sys

from lib_notion import (
    PARENT_PAGE_ID,
    B,
    BM,
    CODE,
    DIV,
    H3,
    N,
    P,
    Q,
    call,
    delete_block,
    get_child_page_titles,
)


def build_children():
    children = []
    children.append(P('원본: https://github.com/dwhavi/AIHOT (fork from KKKKhazix/AIHOT, Public template, 26 Commits)'))
    children.append(Q('한 줄 정의: "自己找热点、自己写日报的网站框架" — 스스로 핫이슈 수집하고 일보 쓰는 사이트 프레임워크.'))
    children.append(BM('https://github.com/dwhavi/AIHOT'))
    children.append(DIV())
    children.append(H3('1. 개요'))
    children.append(B('실서비스: aihot.news (AI 업계 데모). 이 레포는 실서비스 코드 스냅샷 + 프레임워크화 버전'))
    children.append(B('포함물: 웹사이트, 백오피스, 선별 파이프라인, 클러스터링+열도 알고리즘, 모든 프롬프트 원문과 입선 임계값'))
    children.append(B('기본 내장: 해외 AI 뉴스 RSS 18개 데모 소스 / 진짜 소스·운영 데이터 없음'))
    children.append(B('industry/ 폴더만 갈아끼우면 법률/HR/금융 등 자기 업계 핫스테이션으로 변환 가능'))
    children.append(B('AIHOT 이름·로고는 라이선스 범위 밖. 자기 브랜드로 교체 필요. 코드는 MIT'))
    children.append(H3('2. 동작 방식 (6단계)'))
    children.append(CODE('수집 → 중복제거 → 사전선별 → 2회 독립채점 → 작문 → 클러스터링 → 핫랭킹 → 간행물', 'plain text'))
    children.append(N('수집: 동일 URL·내용 1건만 유지. 제목만 있으면 원문 크롤링'))
    children.append(N('사전선별 (prefilter.md): 이 업계 일인가? 넓게 통과, 명백히 무관한 것만 BLOCK'))
    children.append(N('채점 (selection-score.md): 동일 기준 0~100점 2회 독립 채점. 2회 합 ≥ 2×임계값이면 선별'))
    children.append(B('기본 임계값: T1(공식1차) 60 / T1.5 65 / T2(미디어·개인) 76. 화면 표시는 평균점'))
    children.append(N('작문: 선별 + 아깝게 탈락(understandFloor 50점↑)은 중문 제목·결론우선 요약·추천이유·태그. 원문에 없는 회사는 제목에 금지'))
    children.append(N('구조화 (structure.md): 분류·태그·주체회사·팩트 추출 → 주제페이지·클러스터링 기반'))
    children.append(N('클러스터링 (group-*.md): 서로 다른 출처의 같은 사건 → 1 이벤트로 묶음. 벡터로 최근 2주 후보 → LLM 판정(동일/후속/별개) → 애매하면 타 모델 재확인. 수동 수정분은 덮어쓰지 않음. 묶음 완료(최대 3분) 후 노출로 도배 방지'))
    children.append(N('열도: 글 단위 아님, 이벤트 단위. 48시간 내 독립출처 1곳당 1표, 24시간 지나면 반감. 반복 크롤링·중복보도 가중치 없음. X 토론도 카운트. 6시간 전 대비 급등=上昇, 신규=新'))
    children.append(N('간행: 매일 08:00 일보(전날 08:00~당일 08:00), 매주 월 10:00 주보, 매월 1일 10:30 월보'))
    children.append(H3('3. 기능'))
    children.append(B('6종 소스: RSS / 웹리스트 / JSON / X계정 / 위챗공중계정 / 외부 푸시. 등급제(T1/T1.5/T2/EXCLUDE_MP) +抓取 빈도 자동조절'))
    children.append(B('선별: 사전선별 + 동일기준 2회 채점 + 등급별 임계값. SelectBench로 자标注 샘플 교정'))
    children.append(B('작문/번역/태깅, 이벤트 페이지(综述), 핫랭킹, 일보/주보/월보'))
    children.append(B('주제/검색: 회사·방향·형태 3류 주제페이지'))
    children.append(B('Agent용: RSS(선별/전체/전문/일보), 공개 API, MCP, llms.txt'))
    children.append(B('백오피스(/admin): 소스관리·시험抓取, 콘텐츠진단, 선별평가, 단계별 모델 교체, 예산 차단기, 실행로그·알람'))
    children.append(B('AI 전용 모듈: 모델랭킹보드 + Codex 리셋 모니터 (스위치 OFF 가능)'))
    children.append(H3('4. 아키텍처 (3 프로세스)'))
    children.append(B('api (apps/api, Fastify): 사이트용 /api/site/, 공개 /api/v1/, RSS, MCP, 백오피스, 이미지프록시'))
    children.append(B('worker (apps/worker, pg-boss): 수집, 모델호출, 묶음, 열도, 일보, 알람, 정리'))
    children.append(B('web (apps/web, React Router SSR): DB 직접 접근 금지, HTTP로만 api 호출'))
    children.append(B('불변 규칙: 공개 읽기 단일층 packages/backend/src/publication/ / 페이지 렌더 시 모델 호출 금지 / 유료 호출은 영수증+예산차단기 / 안전밸브 OFF가 개발 기본 / 공개 콘텐츠 익명 / 48시간 지난旧문은 아카이브만 / 全文 표시는 site_fulltext OFF 기본'))
    children.append(H3('5. 기술 스택 / 구조'))
    children.append(B('Node.js 24 / TS / React Router(SSR) / Fastify / PostgreSQL 17 / pg-boss / Tailwind / Docker Compose'))
    children.append(B('industry/: 업계팩 (사이트문구·분류·주제·데모소스·프롬프트·임계값·브랜드·약관) — 커스텀은 여기만'))
    children.append(B('packages/backend/src/: sources / content / editorial / events / publication / reports / providers / notify / operations / admin / leaderboard / monitor'))
    children.append(B('database/migrations: 번호순 증분만 / scripts: init-env, migrate, seed, eval-selection, smoke / tests: 빈 _test/_ci DB, 외부호출 없음'))
    children.append(H3('6. 자기 업계로 바꾸기 (industry/만 수정)'))
    children.append(N('site.ts: 站名, 업계어, 홈문구, mcpPrefix, 크롤러명'))
    children.append(N('taxonomy.ts + topics.json: 카테고리·태그·엔터티·주제 (key/slug는上线 후 변경금지)'))
    children.append(N('sources.json: 최초 임포트용 데모소스. 이후 백오피스 관리'))
    children.append(N('prompts/: 핵심 노하우. 구조(5차원가중·노이즈억제·안전선) 유지, "무엇이 중요/노이즈인가" 예시만 교체'))
    children.append(N('selection.ts: 임계값. 100~200건 라벨링 → scripts/eval-selection.ts 교정'))
    children.append(N('features.ts: leaderboard / codexResetMonitor OFF, brand/, pages/terms·privacy 교체'))
    children.append(H3('7. 실행'))
    children.append(CODE('git clone https://github.com/KKKKhazix/AIHOT.git myhot\ncd myhot\nnode scripts/init-env.ts --llm-key <OpenAI호환 API Key>\ndocker compose up -d --build\n# http://localhost:3000, /admin 비번은 .env ADMIN_PASSWORD', 'bash'))
    children.append(B('컨테이너 5개: db / setup(마이그레이션+시드 후 종료) / api / worker / web'))
    children.append(B('검증: npm run typecheck, npm test(_test DB), node scripts/smoke.ts --base http://localhost:3000'))
    children.append(B('비용: 첫 임포트 152건 ≈ 모델 930회. 이후는 소스更新量 비례. X/공중계정/Jina는 key부터 과금, 상한 차단기 있음'))
    children.append(H3('8. 문서 맵'))
    children.append(B('docs/customize.md: 업계 변환手順 / docs/selection.md: 선별+교정 / docs/sources.md: 6종 소스+외부푸시 POST /api/ingest/items'))
    children.append(B('docs/grouping.md: 이벤트 판정 / docs/deploy.md: Docker·도메인·중국·비용 / docs/architecture.md: 3프로세스·대외出口'))
    children.append(B('docs/leaderboard.md: 모델보드·Codex모니터'))
    children.append(H3('9. 다음 액션'))
    children.append(B('업계 정하기 → 소스 20~30개 → 100~200건 라벨링 후 교정 → 브랜드·도메인·약관 교체 후上线'))
    return children


def main():
    topic = sys.argv[1] if len(sys.argv) > 1 else "AIHOT 파악 정리"
    today = datetime.date.today().isoformat()
    title = f"{today} - {topic}"
    print("title:", title)

    existing = get_child_page_titles(PARENT_PAGE_ID)
    if title in existing:
        print(f"SKIP: '{title}' already exists ({existing[title][:8]}). No duplicate created.")
        return 0

    children = build_children()
    print("blocks:", len(children))
    res = call("POST", "pages", {
        "parent": {"page_id": PARENT_PAGE_ID},
        "properties": {"title": [{"text": {"content": title}}]},
        "children": children,
    })
    print("subpage_id:", res.get("id"))
    print("subpage_url:", res.get("url"))

    # Legacy cleanup: old toggle-style titles (e.g. "2026-11-03 · AIHOT 파악 정리")
    # best-effort, ignore failures
    try:
        from lib_notion import call as _call
        page_children = _call("GET", f"blocks/{PARENT_PAGE_ID}/children?page_size=100")
        for b in page_children.get("results", []):
            t = b.get("type", "")
            if t in ("heading_2", "heading_3", "toggleable_heading_2"):
                rich = (b.get(t) or {}).get("rich_text", [])
                txt = "".join(x.get("plain_text", "") for x in rich)
                if txt.endswith("· " + topic) or txt == title.replace(" - ", " · "):
                    try:
                        delete_block(b["id"])
                        print("legacy toggle deleted:", txt)
                    except Exception as e:
                        print("legacy delete failed:", str(e)[:200])
    except Exception as e:
        print("legacy cleanup skipped:", str(e)[:200])

    print("DONE")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
