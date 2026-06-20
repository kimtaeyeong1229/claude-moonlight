# 🌙 Moonlight

영어를 몰라도 논문을 편하게 읽는 **논문 2단 대조 리더**. arXiv 논문을 한국어로 번역해
**좌측 원문 / 우측 한국어**로 나란히 보여주고, 한쪽 문장에 마우스를 올리면 반대편의
**대응 문장이 형광펜**으로 강조된다. figure·table·수식은 양쪽에 그대로 유지.

- **macOS** → 네이티브 앱(`/Applications/claude-moonlight.app`, WKWebView)
- **Linux / Windows** → 웹 모드(컨테이너 + 브라우저)

> 참조: 기존 `claude-web-papers-kr`(번역 엔진을 그대로 계승). 자세한 설계는 `plans/` 참조.

![Moonlight 메인 화면](docs/screenshot.png)

---

## 사전 준비 (모든 OS 공통)
- **Docker** (Docker Desktop 권장) — 실행 중이어야 함.
- **Claude CLI (`claude`)** — 설치 + 로그인 완료. 번역 워커가 이 인증을 그대로 사용한다.
  - 번역 워커는 **PTY/fork 기반(POSIX 전용)** 이라 호스트가 macOS/Linux 여야 동작한다.
    Windows 는 뷰어(웹)만 바로 쓸 수 있고, 번역까지 쓰려면 **WSL2(Linux)** 에서 설치를 권장.

---

## OS별 설치 & 실행

### 🍎 macOS — 네이티브 앱
```bash
git clone https://github.com/kimtaeyeong1229/claude-moonlight.git
cd claude-moonlight
bash scripts/install.sh          # swiftc 로 네이티브 앱 빌드 → /Applications/claude-moonlight.app
```
**실행**: `/Applications/claude-moonlight.app` 더블클릭.
- 앱이 컨테이너를 자동 기동(없으면 Docker Desktop 도 시작 시도)하고 자체 창에 뷰어를 띄운다.
- 처음 실행 시 "확인되지 않은 개발자" 경고가 나오면 앱 **우클릭 → 열기**로 한 번 허용.
- **앱을 끄면 컨테이너 + 워커가 함께 정지**(완전한 on-demand).

### 🐧 Linux — 웹 모드
```bash
git clone https://github.com/kimtaeyeong1229/claude-moonlight.git
cd claude-moonlight
bash scripts/install.sh          # 앱 메뉴에 'Moonlight' 등록(.desktop) + 웹 런처 준비
```
**실행**: 앱 메뉴의 **Moonlight**, 또는
```bash
bash scripts/moonlight-web.sh    # 컨테이너 기동 + 기본 브라우저로 열기
```
정지: `bash scripts/moonlight-stop.sh`

### 🪟 Windows — 웹 모드
```bat
git clone https://github.com/kimtaeyeong1229/claude-moonlight.git
cd claude-moonlight
scripts\moonlight-web.bat        REM 컨테이너 기동 + 브라우저로 http://127.0.0.1:8090 열기
```
- ⚠️ 번역 워커(PTY)는 Windows 호스트에서 동작하지 않는다. **번역까지 쓰려면 WSL2 안에서**
  위 *Linux* 절차(`bash scripts/install.sh`)로 설치할 것. (그러면 뷰어 + 번역 모두 동작)

> 어느 OS든 백엔드 포트는 `http://127.0.0.1:8090` (localhost 전용). 8080 은 claude-web-terminal 예약.

---

## 동작 방식 (on-demand)
```
실행 (앱 / 웹 런처)
  → scripts/ensure-up.sh
      · docker 데몬 확인 (macOS 앱은 꺼져 있으면 Docker Desktop 기동 시도)
      · 호스트 워커(번역 엔진) 기동 (인증된 claude, 비root)
      · 컨테이너 up (이미 떠 있으면 재사용) → /api/health 대기
  → 뷰어 로드 (macOS=앱 창 / Linux·Windows=브라우저)
```
- **부팅 자동 시작 없음** — 켤 때만 뜬다.
- macOS 앱은 **종료 시 컨테이너 + 워커 정지**. 번역 도중 종료해도 다음 실행 때 자동 재개(`WORKER_REQUEUE`).
- 번역 결과는 레포의 `data/` 에 영속되어 **컨테이너를 껐다 켜도 유지**된다.

## 번역 엔진 (참조 레포 계승)
- **컨테이너 = 대시보드/뷰어 서버**, **호스트 = 번역 워커**(하이브리드).
  - 컨테이너 안 claude 는 root·인증 문제로 부적합 → 워커는 호스트의 **인증된 비root claude** 로 구동.
- 워커는 **PTY 인터랙티브 `claude`** 로 번역. **`claude -p`(헤드리스) 금지.** 모델 **Opus 4.8 · effort `high`**.
- 파이프라인: PDF 다운 → 페이지 읽기 → **문장 정렬 `paper.json`**(+단어쌍 `wp`) 작성 →
  figure/table 추출(poppler) → 검증 → `DONE`.

## 화면 사용법

### 사이드바 (왼쪽)
| 요소 | 동작 |
|---|---|
| **+ 새 논문 추가** | arXiv 링크·페이지 범위·설명 입력 → 번역 잡 생성(워커가 처리, 진행바 표시) |
| **논문 카드** | 클릭하면 뷰어로 열림. 🗑(hover) 로 삭제 |

### 상단 컨트롤
| 컨트롤 | 사용법 |
|---|---|
| **☰** | 사이드바 접기/펴기 |
| **보기** | 반반(원문＋번역) / 원문 / 번역 |
| **🎯 집중** | 가리킨 문장쌍만 또렷, 나머지는 흐리게 |
| **🔗 싱크** | 좌우 스크롤 동기화 on/off |
| **테마** | 밝게 / 어둡게 |
| **형광색** | hover 형광펜 색 6종 선택 |

### 본문에서
| 동작 | 결과 |
|---|---|
| 문장에 **hover** | 양쪽 같은 문장이 형광펜으로 강조(가리킨 쪽 진하게) |
| 문장 **클릭** | 양쪽 패널을 그 문장으로 정렬 점프 |
| 단어 **더블클릭** | 그 단어와 한국어 대응어가 양쪽에서 **밝은 노랑**으로 강조 + 뜻 툴팁(`영어 → 한국어`) |
| 그림·표 **더블클릭** | 해당 이미지/표만 **확대(라이트박스)** — 클릭/Esc 로 닫기 |
| 커서를 **오른쪽 끝**으로 | **목차** 패널이 슬라이드-인(Notion 식), 벗어나면 숨김 |
| **점선 밑줄 용어** hover | 용어 설명 툴팁 |

## 구조
| 경로 | 역할 |
|---|---|
| `app/server.py` | aiohttp 서버(목록/추가/상태/정적, 샘플 프리로드) |
| `app/worker.py` | PTY 인터랙티브 claude 워커(번역 엔진; **호스트에서 실행**) |
| `app/process_paper_prompt.md` | 파이프라인 지침(문장 정렬 + 단어쌍 paper.json) |
| `app/validate_paper.py` | paper.json 스키마 검증 |
| `app/static/index.html` | 2단 대조 뷰어(형광펜·단어쌍·집중·테마·목차·싱크·라이트박스) |
| `app/sample/paper.json` | 즉시 데모용 정렬 샘플 |
| `app/native/MoonlightApp.swift` | macOS 네이티브 앱 창(WKWebView) |
| `Dockerfile`·`docker-compose.yml` | 컨테이너(서버 + poppler) |
| `scripts/` | `install.sh`(OS 분기)·`make-app.sh`(macOS)·`moonlight-web.sh`/`.bat`(Linux·Windows)·`ensure-up.sh`·`moonlight-stop.sh`·`docker-entrypoint.sh` |
| `plans/` | v0.1~v0.4 설계 문서 · `materials/` 리서치·프로토타입·참조 코드 |

## 로컬 검증 (Docker 없이 뷰어만)
```bash
python3 -m venv .venv && ./.venv/bin/pip install -r requirements.txt
MOONLIGHT_DATA=./data ./.venv/bin/python app/server.py   # http://127.0.0.1:8090
```
서버만 띄워 뷰어/샘플을 확인할 수 있다(실제 번역은 claude + PTY 워커 필요).

## 한계
- 번역 워커는 **macOS/Linux(POSIX)** 전용. Windows 는 WSL2 권장.
- 이전에 번역된 논문은 단어쌍(`wp`)이 없을 수 있다(기능 추가 이후 번역분부터 포함).
- `data/` 는 제3자 논문 발췌/그림을 포함하므로 git 에 포함하지 않는다.

## 라이선스
[MIT](LICENSE) © 2026 kimtaeyeong1229

생성되는 번역본·그림은 원 논문(arXiv 등)의 저작물에서 파생된 것으로 **개인 학습/열람용**이다.
