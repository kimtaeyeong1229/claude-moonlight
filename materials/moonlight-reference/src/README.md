# 📄 Paper Dashboard

arXiv 논문을 **한국어 Medium 스타일 HTML**로 번역해 한 곳에서 모아 읽는 웹 대시보드.

사이드바에서 **"+ 새 논문 추가"** → arXiv 링크 / 페이지 범위 / 간단한 설명(예: *"8페이지의 6번 섹션까지만"*)만 넣으면,
백그라운드 워커가 **Claude Code(Opus 4.8 · ultracode)** 를 띄워 번역본을 만들고, 완료되면 클릭해서 읽을 수 있다.

* 번역 생성은 **반드시 인터랙티브 모드의 `claude`** 로 돈다 — `claude -p`(헤드리스) 를 **절대 쓰지 않음**.
  워커가 `claude-web-terminal` 과 동일하게 **PTY(의사 터미널)** 에서 인터랙티브 REPL 을 띄워 작업을 지시한다.
* 여러 논문을 올리면 **병렬**로 처리(동시 실행 수 조절 가능), 그 사이 기존 논문은 계속 읽을 수 있다.
* 카드별 **커스텀 태그**(5색·최대 10개), **제목 검색**, **정렬**(게재순·제목순·추가순), **태그 필터** 지원.

![dashboard](docs/screenshot.png)

---

## 1. 사전 준비 (Prerequisites)

이 프로젝트는 **로컬에 설치·인증된 Claude Code CLI** 를 호출해 번역을 수행한다. macOS / Linux 전용(워커가 `pty`+`fork` 사용 → Windows 미지원).

### (1) Claude Code CLI
```bash
# 설치 (https://docs.claude.com/claude-code)
# 설치 후 로그인 (브라우저 인증)
claude            # 한 번 실행해서 로그인/온보딩 완료해 두기
```
대시보드가 제대로 동작하려면 다음이 갖춰져 있어야 한다:
- `claude` 가 PATH 에 있고 **로그인 완료** 상태일 것 (`which claude` 로 확인).
- 워커는 기본적으로 **`--model claude-opus-4-8`** 로 띄운다. (환경변수 `WORKER_MODEL` 로 변경 가능)
- **ultracode** 품질로 돌리려면 Claude 설정에서 *dynamic workflows* 가 켜져 있어야 한다(`/config`).
  필요 없으면 `WORKER_ULTRACODE=0` 으로 끌 수 있다.

### (2) poppler (PDF → 이미지/페이지)
그림·표 추출과 페이지 읽기에 `pdftoppm` / `pdfinfo` 를 쓴다.
```bash
brew install poppler          # macOS
sudo apt-get install poppler-utils   # Debian/Ubuntu
```

### (3) Python 3.10+
```bash
pip install -r requirements.txt    # aiohttp, markdown, Pillow
```

### (4) (선택) claude-web-terminal
워커가 띄우는 인터랙티브 세션을 브라우저에서 들여다보고 싶다면 사용. 필수는 아니다.

---

## 2. 실행 (Run)

```bash
# 1) 대시보드 웹서버
python3 app.py                       # → http://127.0.0.1:8090

# 2) 워커 (별도 터미널) — 인터랙티브 claude 로 번역 수행
python3 worker.py                    # 기본 동시 2개
# 더 많이 병렬로:
WORKER_CONCURRENCY=10 python3 worker.py
```

브라우저로 **http://127.0.0.1:8090** 접속 → **"+ 새 논문 추가"**.

---

## 3. 웹페이지 사용법

1. **+ 새 논문 추가** → arXiv 링크, 시작/종료 페이지, 간단한 설명 입력 후 *생성 시작*.
   - 제목·게재 학회·연도는 **arXiv 에서 자동**으로 가져온다(제목은 원본 영어 유지).
2. 사이드바에 **ETA 진행바**와 함께 *번역 중* 으로 표시되고, **완료되면 자동으로 열린다**.
3. 카드의 **`+`** 버튼으로 **태그**(5색, 최대 10개)를 달아 분류.
4. 상단 **검색창**(제목), **정렬 토글**(게재순/제목순/추가순), **`# 태그 필터`** 로 빠르게 탐색.
5. 좌상단 **`☰` / `«`** 로 사이드바를 접어 전체 폭으로 읽기.

---

## 4. 동작 원리

```
[브라우저] 추가 폼 제출
  → app.py : papers/<id>/meta.json(status=queued) + jobs/pending/<id>.json 생성
             (arXiv API 로 제목/학회/연도 조회 → en_title.txt)
  → worker.py : 잡 클레임(원자적 rename) → 인터랙티브 claude(PTY) 스폰 → /effort ultracode
                → process_paper_prompt.md 지침대로 PDF 다운로드·본문 읽기·한국어 번역
                  ·그림/표 추출·build_paper.py 로 HTML 빌드
                → <output_dir>/DONE 기록 (실패 시 FAILED)
  → app.py : status=done → 사이드바에서 클릭해 열람
```

### 파일 구성
| 파일 | 역할 |
|---|---|
| `app.py` | 대시보드 서버(aiohttp). 목록/추가/상태/태그 API, 논문 HTML·그림 서빙, arXiv 메타 조회 |
| `worker.py` | 잡 큐 감시 → 잡마다 **인터랙티브 claude**(PTY) 스폰해 처리. **`-p` 미사용**, 병렬 지원 |
| `process_paper_prompt.md` | 인터랙티브 claude 에게 주는 번역 파이프라인 지침 |
| `build_paper.py` | `paper.md` → Medium 스타일 `paper.html`(MathJax) 변환 |
| `static/index.html` | 프런트엔드(사이드바 리스트·ETA·태그·검색·정렬·필터·뷰어) |
| `papers/<id>/` | 논문별 결과물(`paper.md`, `paper.html`, `figures/`, `meta.json`, `tags.json`, `en_title.txt`) — *git 미포함(런타임)* |
| `jobs/{pending,processing,done,failed}/` | 잡 큐 — *git 미포함(런타임)* |

> **설계 메모 — 상태 충돌 방지**: 워커가 쓰는 `meta.json`(상태/진행도)과 사용자가 만지는 데이터를
> 파일 단위로 분리했다. 태그는 `tags.json`, 진행 단계는 `stage.txt`, 표시용 영어 제목은 `en_title.txt`.
> 덕분에 번역이 도는 중에도 태그를 달거나 UI 를 바꿔도 진행 중인 작업이 깨지지 않는다.

---

## 5. 환경변수

| 변수 | 기본값 | 설명 |
|---|---|---|
| `DASHBOARD_PORT` | `8090` | 대시보드 포트 |
| `ETA_SECONDS_PER_PAGE` | `75` | 페이지당 ETA 추정(초) |
| `WORKER_CONCURRENCY` | `2` | 동시 처리 잡 수(병렬 슬롯) |
| `WORKER_MODEL` | `claude-opus-4-8` | 워커가 띄우는 모델 |
| `WORKER_ULTRACODE` | `1` | `/effort ultracode` 자동 설정(0이면 끔) |
| `WORKER_JOB_TIMEOUT` | `3600` | 잡당 최대 시간(초) |
| `WORKER_CWD` | 상위 디렉터리 | claude 를 띄울 (신뢰된) 작업 디렉터리 |
| `WORKER_REQUEUE` | `1` | 시작 시 `processing/` 잔여 잡을 `pending/` 으로 복구(라이브 풀에 합류할 땐 `0`) |
| `CLAUDE_CMD` | (PATH 의 `claude`) | claude 실행 파일 경로 |

---

## 6. 트러블슈팅

- **잡이 "번역 중"에서 멈춤** → `papers/<id>/worker.log` 확인. `claude` 로그인이 안 됐거나 모델 설정 문제일 수 있음.
- **그림이 안 나옴** → `poppler`(`pdftoppm`) 설치 확인.
- **프롬프트가 제출 안 됨** → claude TUI 는 붙여넣기+Enter 를 한 덩어리로 처리해 제출이 안 되는 버그가 있어,
  워커는 *텍스트 입력 → 잠시 대기 → Enter 별도 전송* 방식으로 처리한다(`worker.submit`).
- **포트 충돌** → `DASHBOARD_PORT` 변경. (claude-web-terminal 이 8080 이라 대시보드는 8090 기본)

---

## 7. 데스크톱 바로가기 & 자동 시작 (macOS)

### 바로가기 (앱 아이콘)
```bash
./scripts/make-launcher.sh        # → ~/Desktop/Paper Dashboard.app 생성 (커스텀 아이콘)
```
더블클릭하면 대시보드가 **앱 창(Chrome app 모드)** 으로 열린다. 서비스가 꺼져 있으면 자동 시작도 시도한다.
(브라우저에서 *Chrome ⋮ → 캐스트·저장·공유 → 페이지를 앱으로 설치* / Safari *공유 → Dock에 추가* 로도 favicon 아이콘의 앱을 만들 수 있다.)

### 부팅 시 자동 시작 (전원 껐다 켜도)
```bash
WORKER_CONCURRENCY=4 ./scripts/install-autostart.sh
```
`~/Library/LaunchAgents` 에 두 개의 LaunchAgent(대시보드·워커)를 설치한다.
**다음 로그인/재부팅부터** 자동으로 켜지고, 죽으면 launchd 가 다시 살린다.

지금 바로 켜려면(수동 실행 중인 app/worker 를 먼저 끄고):
```bash
launchctl bootstrap gui/$(id -u) ~/Library/LaunchAgents/com.paperdashboard.dashboard.plist
launchctl bootstrap gui/$(id -u) ~/Library/LaunchAgents/com.paperdashboard.worker.plist
```
해제: `./scripts/uninstall-autostart.sh` · 동시 처리 수는 `WORKER_CONCURRENCY` 로 조절(plist 의 값 수정 후 재부팅 또는 재-bootstrap).

## 8. 면책

생성되는 번역본·그림은 원 논문(arXiv 등)의 저작물에서 파생된 것으로, **개인 학습/열람용**이다.
`papers/` 디렉터리는 git 에 포함하지 않는다(제3자 저작물 발췌 포함).
