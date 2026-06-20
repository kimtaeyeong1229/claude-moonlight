# 리서치 — 논문 정독 팁 & 집중을 돕는 읽기 UI/UX

> Moonlight(원문 좌 / 한국어 우, 문장 hover → 반대편 파란 형광펜) 설계를 위한 근거 자료.
> 출처 URL 인라인 포함.

---

## TOPIC 1 — 논문을 효과적으로 읽는 법

### 1.1 3-pass 독해법 (S. Keshav)
논문은 처음부터 끝까지 읽지 않고 **목적이 다른 3번의 패스**로 읽는다.
([HKU](https://blog-sc.hku.hk/reading-papers-efficiently-with-the-three-pass-approach/) ·
[overview](https://richardmathewsii.substack.com/p/three-pass-research-literature-review))
- **Pass 1 — 개관 (5~10분)**: 제목·초록·서론, 모든 섹션 제목, 결론, 참고문헌 훑기. 목적: 더 읽을지 결정.
- **Pass 2 — 내용 파악 (~1시간)**: 증명/수식은 건너뛰고 **그림·표·그래프에 집중**. 메모. 목적: 자기 말로 요약 가능.
- **Pass 3 — 정독 (4시간+)**: 모든 가정에 도전, 논증 재구성, 사실상 재현. 목적: 비판·재현 수준 숙달.
- **첫 패스 체크리스트 "5 C's"**: Category, Context, Correctness, Contributions, Clarity.

### 1.2 숙련 연구자의 실제 읽기 순서 (비선형)
교과서처럼 선형으로 읽지 말 것. ([National University](https://resources.nu.edu/researchprocess/readingscientificarticle))

| 섹션 | 읽는 법 | 이유 |
|---|---|---|
| 제목+제목들+그림 | **먼저** 훑어 관련성 판단 | 빠른 분류 |
| 초록 | 일찍 읽기 (자족적 요약) | 왜·어떻게·무엇을 |
| 서론 | 익숙하면 스킵 | 배경+연구질문 |
| **그림/표/결과** | **여기 집중** | 핵심 발견/데이터 |
| 방법 | 엄밀성 평가 아니면 스킵 | 기술적 |
| 논의/결론 | 정독 | 해석+후속연구 |
| 참고문헌 | 마지막 | 다음 읽을거리 지도 |

스킬은 "빨리 읽기"가 아니라 "똑똑하게 읽기": 제목→초록→서론/결론→가장 중요한 그림 1~2개.
([Polygence](https://www.polygence.org/blog/skimming-articles-for-research) ·
[Semantic Reader/arXiv](https://arxiv.org/pdf/2303.14334))

### 1.3 능동적 읽기 (주석·메모·질문)
- **색상 코드 하이라이트(고정 범례)**: 핵심 아이디어 / 모르는 용어 / 중요 예시별 색 분리.
  ([EWU](https://research.ewu.edu/writers_c_read_study_strategies) ·
  [Keiser PDF](https://www.keiseruniversity.edu/pdf/KeiserWrites/Active-Reading-Notetaking-and-Highlighting.pdf))
- **앵커링된 인라인 주석**: 특정 구간에 고정해 요점·논증 전환·자기 반응 기록.
- **읽으며 질문**: 용어 이해? 주장 신뢰 가능? 내 지식과 어떻게 연결? ([National University](https://resources.nu.edu/researchprocess/readingscientificarticle))
- **수집 → 태깅 → 정리** 워크플로우. ([Philosophy Institute](https://philosophy.institute/research-methodology/effective-note-taking-research-strategies/))

### 1.4 초보자·비원어민의 함정
- 선형·전수 독해 → 번아웃. 목적 중심 다중 패스 스키밍으로 해결.
- **비원어민은 원어민의 약 2배 읽기 시간** 소요. ← Moonlight 가 정확히 노리는 페인포인트.
  ([Researcher.Life](https://researcher.life/blog/article/5-key-strategies-to-tackle-research-reading-challenges-for-non-native-english-speakers/))
- 관용구·비문자적 표현·구문 변형이 의미를 뒤집음. 분야별 어휘는 의도적으로 쌓아야.

### 1.5 → Moonlight 설계 권고 (Topic 1)
1. **3-pass 를 UI 로**: Skim / Read / Deep 모드 토글(초록·제목·결론만 / 그림 강조 / 전체).
2. **섹션 아웃라인·점프 패널**(그림·결론·결과로 비선형 이동).
3. **그림을 1급 시민으로**: 그림 갤러리/점프, 양쪽 패널에 그림 인라인 유지.
4. **5 C's 를 메모 템플릿**으로 옵션 제공.
5. **색상 코드 하이라이트+앵커 메모**(문장 정렬이 완벽한 앵커 단위).
6. **비원어민 가치 강조**: 한국어 패널이 2배 시간/관용구 혼란을 직접 공략 + **용어 인라인 툴팁**.

---

## TOPIC 2 — 집중·이해를 돕는 읽기 UI/UX (특히 2단 대역)

### 2.1 가독성 타이포그래피
- **행 길이(measure): 50~75자, 66자 이상적** (WCAG ≤80). CSS `max-width: ~70ch`.
  ([UXPin](https://www.uxpin.com/studio/blog/optimal-line-length-for-readability/) ·
  [Baymard](https://baymard.com/blog/line-length-readability))
- **행간(line-height): 라틴 본문 ≥1.5**, 긴 행은 1.6~1.7. **한국어/CJK 는 ≈1.7** (음절 블록 정보밀도↑).
  ([az-loc](https://www.az-loc.com/best-fonts-for-chinese-japanese-korean-websites/) ·
  [Typotheque CJK](https://www.typotheque.com/articles/typesetting-cjk-text))
- **정렬: 좌측 정렬(우측 래그)** — 매 행 시작점이 일정.
  ([USWDS](https://designsystem.digital.gov/components/typography/))
- **한글+라틴 폰트**: 두 스크립트를 한 가족으로 — **Pretendard**(한국 웹 표준급) 또는 **Noto Sans KR**
  (한글·한자·라틴 커버), Noto Serif KR(세리프 옵션). 페어링은 **평균 글자 무게**로 맞춤.
  ([Noto Sans KR](https://fonts.google.com/noto/specimen/Noto+Sans+KR) ·
  [Google Fonts Korean](https://googlefonts.github.io/korean/))

### 2.2 눈 피로·인지부하 감소
- 행 길이 제한 + 넉넉한 **문단 간격(~2em)** + 덩어리화.
- **테마**: light / **sepia(따뜻)** / **dark** — 긴 세션·어두운 방.
  ([Immersive Reader](https://speechify.com/blog/how-to-use-immersive-reader-in-microsoft-edge/))
- 색 오버레이/틴트는 일부 독자(난독·Irlen)에 도움. ([Helperbird](https://www.helperbird.com/features/overlay/))

### 2.3 읽기 앱의 집중 보조 기능
- **Line Focus**: 1/3/5줄만 남기고 나머지 디밍 (MS Immersive Reader 시그니처).
- **현재 단어/문장 하이라이트**: 읽어주기와 함께 활성 구간 강조(주의 고정).
- **방해 제거 리더 모드**, 크기/간격/색 조절, 품사 색칠.
  ([Speechify Edge](https://speechify.com/blog/how-to-use-immersive-reader-in-microsoft-edge/))

### 2.4 2단 대역(parallel-text) UX
- **레이아웃**: 원문 좌 / 번역 우, 병렬 정렬. "parallel text alignment" = 양쪽 대응 문장 식별.
  ([Parallel text/Wikipedia](https://en.wikipedia.org/wiki/Parallel_text))
- **스크롤 싱크**: **퍼센트 위치 기반**으로 한쪽 스크롤 시 반대편 이동. 트리플클릭으로 해당 행에 점프 정렬.
  ([syncscroll](https://github.com/omnbird/syncscroll) ·
  [Bilingual Reader 확장](https://chromewebstore.google.com/detail/bilingual-reader/ecbgnkobdpgmofceoljghglggimcckab))
- **선택/hover 연동 하이라이트**: 원문 문단 선택 시 번역 대응 문단 강조 ← **Moonlight 핵심과 동일**.
- **정렬 단위**: **문장 단위**가 장문 독해의 스윗스팟. 단어별 interlinear(LingQ/Readlang)는 어학 학습용으로 무겁고 노이즈. 문장쌍은 다국어 ML 정렬로 자동 매칭 가능.
  ([Automatic Translation Alignment](https://ceur-ws.org/Vol-3834/paper128.pdf) ·
  [Readlang](https://blog.readlang.com/2013/02/03/parallel-texts.html))

### 2.5 하이라이트 색 (그리고 파란색)
- **노랑**: 주의 끌기·단기 회상 최고, 그러나 과용 시 과자극·장기 보존 저하.
- **파랑**: **지속 집중·장기 보존**에 유리(빨강 같은 압박 없음). 파랑·초록이 "집중·이해"에 효과적.
  ([Skoodos](https://skoodosbridge.com/blog/color-psychology-note-taking-visual-learning-memory) ·
  [TeacherTutors](https://theteachertutors.com/blog/post-one-1))
- **Moonlight 결론**: 파랑은 **차분한 집중·연결 신호**로 적합(순간적 "이 두 문장이 짝"). **저채도**로 써서 경보가 아닌 부드러운 단서로. 노랑은 **별도의 사용자 주석 하이라이트**에 배정해 의미 분리.
  ([PMC 색-기억 연구](https://www.ncbi.nlm.nih.gov/pmc/articles/PMC4347302/))

### 2.6 그림/표/수식 처리 (Semantic Reader / ScholarPhi 계열)
([Semantic Reader/arXiv](https://arxiv.org/pdf/2303.14334) · [CACM](https://dl.acm.org/doi/full/10.1145/3659096))
- **인라인 인용 카드**(클릭 시 TLDR 팝업), **용어·기호 툴팁**(hover 시 위치별 정의),
  수식 기호 자동 다이어그램, 자동 용어집 → 설명을 **읽기 흐름 안**에 유지.

### 2.7 → Moonlight 설계 권고 (Topic 2)
1. **measure 고정**: 각 패널 ~66자(최대 70). 대화면에서 풀폭 금지.
2. **스크립트별 행간**: 한국어 ~1.7 / 영문·한문 ~1.5~1.6 독립 조정.
3. **폰트**: Pretendard 또는 Noto Sans KR(한글+라틴 통일), Noto Serif KR 옵션. 양쪽 좌측 정렬.
4. **3 테마**: light / sepia / dark.
5. **파란 hover 연동 정제**: **저채도 파랑** wash 를 양쪽 활성 문장에. hover 한 쪽은 약간 진하게, 반대편은 연하게 → 방향성 표시. 노랑은 사용자 주석용으로 분리.
6. **퍼센트 스크롤 싱크** + **문장 클릭→반대편 정렬 점프**(hover 의 명시적 보완).
7. **문장 단위 정렬**(단어별 interlinear 금지). hover 시 **점선 커넥터/여백 마커**로 연결 강조.
8. **Focus 모드(Line-Focus)**: 활성 문장쌍만 남기고 디밍(±1 문장 옵션). 가장 레버리지 큰 이해 기능, hover 모델과 정합.
9. **그림/표/수식 양쪽 인라인 유지**(그림은 언어 무관, 미번역). **용어·수식 기호 hover 툴팁**(= 비원어민 어휘 보조).
10. **읽기 진행 표시**(스크롤 진행 + 아웃라인 섹션 마커).

---

## Top 5 우선순위 (종합)
1. **문장 단위 정렬 + 스크롤 싱크 + hover/클릭 파란 연동** (핵심 가치, 저채도 파랑).
2. **Focus/Line-Focus 모드** (활성 문장쌍만 강조).
3. **절제된 타이포** (66자, 한글1.7/영문1.5, Pretendard/Noto Sans KR, 좌측정렬, sepia+dark).
4. **3-pass 스캐폴딩** (Skim/Read/Deep + 섹션 아웃라인 + 그림 우선 내비).
5. **용어/기호 인라인 툴팁 + 그림 양쪽 인라인** (비원어민 2배 시간 페인 공략).

---
### 주요 출처
- Keshav 3-pass: HKU / richardmathewsii
- 읽기 순서: National University LibGuide · Polygence · Semantic Reader(arXiv 2303.14334)
- 능동 읽기: EWU · Keiser · Humber · Philosophy Institute
- 비원어민: Researcher.Life
- 타이포: UXPin · Baymard · az-loc · Typotheque · USWDS · Noto/Pretendard
- 집중 기능: MS Immersive Reader(Speechify) · Helperbird
- 2단 대역: Parallel text(Wikipedia) · syncscroll · Bilingual Reader 확장 · Readlang · CEUR 정렬 논문
- 색: Skoodos · TeacherTutors · PMC 색-기억 연구
- 그림/수식: Semantic Reader / ScholarPhi(CACM, arXiv)
