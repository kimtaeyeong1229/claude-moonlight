# 기존 Moonlight 대시보드의 기능 목록

> `static/index.html`(552줄) + `README.md` 기준. 신규 앱에서 무엇을 계승/폐기/변형할지 판단용.

## A. 논문 추가 / 파이프라인
- **새 논문 추가 폼**: arXiv 링크 + 시작/종료 페이지 + 자유 서술 설명("8페이지의 6번 섹션까지만").
- **메타 자동 조회**: arXiv API 로 제목·게재 학회(NeurIPS/ICML/… 사전 매칭)·연도 자동 채움.
  제목은 **영어 원제 유지**(`en_title.txt`).
- 백그라운드 워커(PTY 인터랙티브 claude, ultracode)가 번역 → 그림/표 추출 → HTML 빌드.
- **병렬 처리**: `WORKER_CONCURRENCY` 로 여러 논문 동시 번역.

## B. 진행 상태 표시 (사이드바)
- 상태 배지: `대기 중(queued)` / `번역 중(processing)` / `완료(done)` / `실패(failed)`.
- **ETA 진행바**: 페이지 수 기반 추정(`ETA_SECONDS_PER_PAGE=75` + base 60s).
  서버가 경과시간으로 progress 하한을 계산(최대 95%까지 시간 기반 채움).
- **라이브 stage 텍스트**: 파이프라인이 `stage.txt` 에 쓴 현재 단계("PDF 다운로드 중" 등) 표시.
- **완료되면 자동으로 열림**.

## C. 목록 탐색 / 정리
- **제목 검색창**.
- **정렬 토글**: 게재순 / 제목순 / 추가순.
- **커스텀 태그**: 5색, 최대 10개. 카드의 `+` 버튼으로 부착(`tags.json`, 대시보드만 씀).
- **태그 필터 패널**: 태그 클릭으로 필터, "전체" 칩.

## D. 뷰어 / 레이아웃
- **사이드바 접기**(`☰` / `«`) → 본문 전체 폭 읽기.
- 본문은 `build_paper.py` 가 만든 단일 **Medium 스타일 HTML**(MathJax, Noto Serif/Sans KR).
- 카드 클릭 → iframe/패널로 해당 `paper.html` 열람.

## E. 산출물 구조 (papers/<id>/)
`paper.md` · `paper.html` · `figures/*.png` · `meta.json` · `stage.txt` · `tags.json` · `en_title.txt` · `source.pdf` · `worker.log` · `job.json` · `DONE`/`FAILED`.

## F. 운영 / 배포
- aiohttp 서버 `127.0.0.1:8090`. 정적 서빙으로 papers/ 그림·HTML 제공.
- macOS 런처(.app, Chrome app 모드) + launchd 자동 시작 스크립트(`scripts/`).
- favicon / PWA manifest.

---

## 신규 Moonlight(2단 대조 뷰어) 관점의 계승/변형 판단

| 기존 기능 | 신규 앱에서 | 비고 |
|---|---|---|
| PTY 인터랙티브 claude 워커 | **계승** | 검증된 핵심. `-p` 금지 유지 |
| 파일시스템 잡 큐 (atomic rename) | **계승** | crash-safe |
| 상태 파일 분리 (meta/stage/tags/en_title) | **계승** | 새 기능은 새 sidecar |
| PDF 다운·페이지 읽기·figure crop 추출 | **계승** | figure 는 양쪽 패널 공용 |
| 단일 paper.html 산출 | **변형** | 원문/번역 2벌 + **문장 정렬 id** 가 필요 |
| build_paper.py (md→HTML) | **변형** | 문장 단위 `<span data-sid>` 래핑, 좌우 동일 구조 |
| Medium 단일 컬럼 뷰 | **변형** | 2-pane side-by-side + scroll-sync + hover 연동 |
| 라이브러리/태그/검색/정렬 | **후순위(v0.2+)** | v0.1 은 단일 논문 정독에 집중 |
| ETA 진행바, 자동 열림 | **계승(축소)** | 단순화 가능 |

## 신규 앱에 새로 필요한 것 (기존엔 없음)
1. **문장 단위 원문↔번역 정렬**(공통 id) — 핵심 신규 데이터.
2. **2-pane 동기 스크롤** + **hover 시 양쪽 동일 문장 파란 형광펜** 하이라이트.
3. figure/table 의 **좌우 위치 정렬**(공통 `fig-N`/`tbl-N` id).
4. (리서치 권고) Focus 모드, 3-pass 뷰, 용어 툴팁, 테마(light/sepia/dark) 등 — `03-reading-ux-research.md` 참조.
