# 참조 레포 정리 — claude-web-papers-kr (구 "Moonlight" 대시보드)

> 원본 코드는 `materials/moonlight-reference/src/` 에 그대로 복사해 둠.
> (app.py · worker.py · build_paper.py · process_paper_prompt.md · static/index.html · README.md · CLAUDE.md · requirements.txt)

## 한 줄 정의
arXiv 논문을 **한국어 Medium 스타일 HTML**로 번역해 한곳에 모아 읽는 **로컬 웹 대시보드**.
macOS/Linux 전용(PTY+fork).

## 아키텍처 — 2개의 독립 프로세스 + 파일시스템 통신
```
[브라우저] 추가 폼
  → app.py  : papers/<id>/meta.json(status=queued) + jobs/pending/<id>.json 생성
              (arXiv API 로 제목/학회/연도 조회 → en_title.txt)
  → worker.py: 잡 클레임(원자적 rename) → PTY 로 인터랙티브 claude 스폰 → /effort ultracode
              → process_paper_prompt.md 지침대로 PDF 다운로드·읽기·번역·그림/표 추출·HTML 빌드
              → <output_dir>/DONE (실패 시 FAILED)
  → app.py  : status=done → 사이드바에서 클릭해 열람
```
`app.py` 와 `worker.py` 는 서로를 모르고, **`jobs/` 큐 + `papers/<id>/` 산출물**로만 소통한다.
→ 서버를 재시작해도 진행 중 번역이 안 깨진다.

## 파일별 역할
| 파일 | 역할 | 핵심 |
|---|---|---|
| `app.py` (372줄) | aiohttp 대시보드 서버 | 목록/추가/상태/태그 API, arXiv 메타 조회, HTML·그림 정적 서빙, 라이브 ETA |
| `worker.py` (326줄) | PTY 워커 | 잡 큐 감시 → 잡마다 **인터랙티브 claude(PTY)** 스폰. `-p` 미사용. 병렬(스레드) |
| `process_paper_prompt.md` | 파이프라인 지침 | 인터랙티브 claude 에게 주는 번역 절차서 |
| `build_paper.py` (154줄) | md→HTML | MathJax 보호, 표 래핑, Medium 스타일 템플릿 |
| `static/index.html` (552줄) | 프런트엔드 | 사이드바·ETA·태그·검색·정렬·필터·뷰어 |

## 재사용 가치가 큰 핵심 패턴 (Moonlight 신규 프로젝트로 가져갈 것)

### 1. PTY 인터랙티브 claude 워커 (worker.py 의 정수)
- `pty.openpty()` + `os.fork()` + `os.execvpe()` 로 **인터랙티브 REPL** 을 띄움. `claude -p`(헤드리스) **절대 금지**(제품 요구).
- env/argv 를 **부모에서 미리 구성** → fork 직후 자식이 거의 일 안 하고 바로 exec (스레드에서 fork 하므로 중요).
- **제출 버그 회피 (`submit`)**: claude TUI 는 붙여넣기+CR 을 한 덩어리로 삼켜 제출이 안 됨.
  그래서 **텍스트 입력 → 짧게 대기(settle) → `\r` 을 별도로** 전송. ("optimize" 하지 말 것.)
  ```python
  def submit(fd, logf, text, settle=1.5):
      send(fd, text)
      drain(fd, logf, settle)
      send(fd, "\r")
  ```
- `/effort ultracode` 자동 설정 후 ESC 로 슬래시 메뉴 정리.
- 완료 감지는 **파일 sentinel**(`DONE`/`FAILED`) 폴링 + 자식 프로세스 사망 감지 + 타임아웃.
- 병렬: `WORKER_CONCURRENCY` 개의 스레드가 각자 `claim_next()`.

### 2. 파일시스템 잡 큐 (crash-safe)
- `jobs/{pending,processing,done,failed}/` 디렉터리.
- 클레임은 **원자적 `rename`**(`pending → processing`). 여러 워커가 경쟁해도 안전.
- `claim_next()` 는 glob 와 stat 사이에 파일이 사라질 수 있음을 **관용**(skip, 크래시 금지).
- 시작 시 `processing/` 잔여 잡을 `pending/` 으로 복구(`WORKER_REQUEUE`).

### 3. 상태 파일 분리 (동시 쓰기 충돌 방지) — ★ Moonlight 에도 그대로 적용할 설계 원칙
서로 다른 writer 가 절대 같은 파일을 안 건드리도록 per-paper 상태를 쪼갬:
| 파일 | writer | 내용 |
|---|---|---|
| `meta.json` | **worker** (시작/종료) | status / progress / ETA |
| `stage.txt` | 파이프라인(claude) | 현재 사람이 읽을 단계 (대시보드가 표시) |
| `tags.json` | **dashboard** | 사용자 커스텀 태그 |
| `en_title.txt` | add-time | 표시용 영어 원제 (worker 가 덮어쓰면 안 됨) |
> 새 기능은 **새 sidecar 파일**을 만드는 게 원칙(워커가 쓰는 필드에 끼워넣지 말 것).

### 4. build_paper.py (md → 스타일 HTML)
- **수식 보호**: `$$...$$` / `$...$` 를 placeholder 로 빼두고 markdown 변환 후 복원 → MathJax 가 처리.
- 표는 `.table-wrap` 으로 감싸 가로 스크롤. figure 는 `figures/*.png` 상대경로.
- Noto Serif/Sans KR, `--maxw: 720px`, `word-break: keep-all` 등 한국어 가독성 스타일.
- 박스표(`.boxtable`) / 그림 캡션(`.figcaption`) 컨벤션.

### 5. process_paper_prompt.md (번역 파이프라인 지침)
- 단계: PDF 다운(`curl arxiv.org/pdf/<id>`) → `Read` 의 `pages` 로 페이지 읽기 → 한국어 md 작성 →
  `pdftoppm -png -r 200` 로 페이지 렌더 후 PIL crop 으로 figure/table 추출 → build_paper.py → DONE.
- 번역 규칙: 문서 순서 유지, **어떤 문단·문장·수식·표·그림도 누락 금지**, 중요 주장/수치 볼드.
- **그림/표 배치**: 본문 첫 언급 지점 바로 뒤 1회. 부록 그림도 발췌해 포함.
- ultracode 면 번역 후 **검증 워크플로우**(원문 대조 누락·오역·수치 점검) 1회 실행 후 DONE.
- **제목 규칙**: `meta.json` 의 `title`(영어 원제)은 절대 번역/덮어쓰기 금지. 단 본문 H1 은 한국어 가능.

## 하드 제약 (CLAUDE.md) — Moonlight 에서도 유지 권장
- **`claude -p` 금지** — 반드시 PTY 인터랙티브 세션.
- **submit = 텍스트 → 대기 → 별도 `\r`** (TUI 제출 버그).
- macOS/Linux 전용. Windows 가정 추가 금지.
- 기본 포트 8090 (8080 은 claude-web-terminal 예약).

## 환경변수
`DASHBOARD_PORT`(8090) · `ETA_SECONDS_PER_PAGE`(75) · `WORKER_CONCURRENCY`(2) ·
`WORKER_MODEL`(claude-opus-4-8) · `WORKER_ULTRACODE`(1) · `WORKER_JOB_TIMEOUT`(3600) ·
`WORKER_CWD`(상위 dir) · `WORKER_REQUEUE`(1) · `CLAUDE_CMD`(PATH 의 claude)

## Moonlight(신규) 에 시사하는 점
- 위 1~5 패턴은 거의 그대로 재사용 가능. 특히 **PTY 워커 + 잡 큐 + 상태 파일 분리**는 검증된 토대.
- 단, 신규 앱은 "모아 읽기"가 아니라 **원문/번역 2단 대조 + 문장 hover 연동**이 목표 →
  파이프라인 산출물을 단일 `paper.html` 이 아니라 **문장 단위 정렬 정보(공통 id)** 를 가진 구조로 바꿔야 함.
  (예: 원문 문장 `s-12` ↔ 번역 문장 `s-12` 매핑 → 좌우 DOM 에서 같은 id hover 연동.)
- figure/table 은 기존처럼 원본 이미지 추출 그대로, **양쪽 패널 동일 위치**에 배치(공통 id `fig-N`).
