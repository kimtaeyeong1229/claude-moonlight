# 논문 번역 파이프라인 — Moonlight (문장 정렬 paper.json)

당신은 사용자가 제공한 arXiv 논문을 **한국어로 문장 단위 정렬 번역**해, 2단 대조 뷰어가 읽을
`paper.json` 으로 만드는 작업을 한 건 처리합니다. 사용자가 직접 링크를 준 문서를 학습용으로 번역하는 것이므로 인용·발췌·번역해도 됩니다.

> 번역 엔진/절차는 참조 레포(claude-web-papers-kr)를 그대로 따릅니다. **유일한 차이는 산출물이
> `paper.html` 이 아니라 문장 정렬 `paper.json` 이라는 점**입니다.

## 작업 파라미터
`job.json`(워커가 전달한 경로)에서 읽으세요:
- `arxiv_id` (예: `2501.12948`), `start_page`, `end_page`, `description`, `output_dir`(절대경로, 안에 `figures/`).

## 진행 상태
각 단계 시작 시 `<output_dir>/stage.txt` 에 한 줄로 현재 단계를 적으세요(대시보드가 표시).
예: `PDF 다운로드 중` → `본문 읽는 중` → `번역·정렬 중` → `그림·표 추출 중` → `검증 중`.

## 단계

### 1. PDF 다운로드
```
curl -L -o <output_dir>/source.pdf "https://arxiv.org/pdf/<arxiv_id>"
```
`pdfinfo` 로 페이지 수/크기 확인.

### 2. 본문 읽기
`Read` 도구의 `pages` 로 `<output_dir>/source.pdf` 의 `start_page`~`end_page` 를 읽습니다(이미지 렌더).
`description` 이 지정한 종료 지점(예: "6번 섹션까지")을 정확히 지키고 그 다음 섹션은 번역하지 않습니다.

### 3. 문장 정렬 번역 → `<output_dir>/paper.json`
아래 스키마로 **문장 단위로 영문 원문과 한국어 번역을 1:1 매핑**해 작성합니다.
```json
{
  "id": "<job.id>",
  "titleEn": "원문 영어 제목",
  "titleKo": "한국어 번역 제목",
  "meta": "저자 · 학회/연도 · arXiv:<id>",
  "blocks": [
    {"type":"h2","sid":"h-1","secId":"sec-1","en":"1. Introduction","ko":"1. 서론"},
    {"type":"p","pass":"read","ss":[
      {"sid":"s1","en":"<원문 한 문장>","ko":"<그 문장의 한국어 번역>",
       "wp":[["term","용어"],["key phrase","핵심 구"]]},
      {"sid":"s2","en":"...","ko":"..."}
    ]},
    {"type":"eq","pass":"deep","tex":"$$ ... $$"},
    {"type":"figure","id":"fig-1","img":"figures/fig-1.png","capEn":"Figure 1 | ...","capKo":"그림 1 | ..."},
    {"type":"table","id":"tbl-1","capEn":"Table 1 | ...","capKo":"표 1 | ...","head":["...","..."],"rows":[["...","..."]]}
  ]
}
```
**정렬 규칙 (가장 중요):**
- `ss` 의 각 항목은 **원문 한 문장 = `en`, 그 번역 = `ko`**. 한 문장을 둘로 쪼개거나 합치지 말 것
  (불가피하면 같은 sid 안에서 자연스럽게 처리하되 1:1 을 우선).
- `sid` 는 문서 전체에서 **유일**하고 좌/우(원문·번역)가 **동일**해야 합니다(hover 연동의 키).
- **어떤 문단·문장·수식·표·그림도 누락하지 않음.** 문서 순서 그대로.
- `pass`: 분류용 메타(`core`/`read`/`deep`). 생략 시 `"read"`. (현재 뷰어는 전체를 표시.)
- **`wp` (단어쌍, 권장)**: 그 문장 안의 **주요 단어/구**에 대한 영↔한 대응 목록 `[[영어, 한국어], ...]`.
  - 사용자가 문장 위에서 단어를 더블클릭하면, 그 단어와 한국어 대응어가 양쪽에서 더 밝게 강조됨(단어 뜻 학습용).
  - 내용어(명사·전문용어·동사 등) 위주로 가능한 한 많이. 한국어 쪽은 **조사 없이 깔끔한 형태**(예: "어텐션") 로.
  - 영어 `en` 은 문장에 실제로 등장하는 표기 그대로(대소문자 무관 매칭).
- 수식: `eq` 블록의 `tex` 에 `$$...$$`(또는 인라인은 문장 안에서 `$...$`). 번호식은 `\tag{n}`.
- figure/table 은 **번역하지 않고 원본 이미지 유지**, 캡션만 `capEn`/`capKo` 로 영/한 둘 다.
  표의 수치 데이터는 `head`/`rows` 로(유의값은 `<b>..</b>`).

**그림/표 배치:** 각 그림/표 블록은 본문에서 **처음 언급되는 지점 바로 뒤**에 한 번 배치.
본문이 참조하지만 `end_page` 이후(부록)에 있는 것도 발췌해 포함하고 캡션 끝에 `(부록에서 발췌)` 표기.

### 4. 그림·표 이미지 추출 → `<output_dir>/figures/`
`pdftoppm -png -r 200 -f <p> -l <p> <output_dir>/source.pdf <output_dir>/figures/p<p>` 로 렌더 후,
Python(PIL)로 필요한 영역만 crop 해 `fig-N.png` / `tbl-N.png` 로 저장(`paper.json` 의 `img` 와 파일명 일치).
crop 좌표는 렌더 이미지를 `Read` 로 확인해 조정(200dpi 보통 1654×2339). 중간 `p<p>-*.png` 는 삭제.
> 그림이 사진/도식이 아니라 수치표면 `table` 블록으로 직접 옮기고 이미지를 만들지 않아도 됩니다.

### 5. 검증
```
python3 <pipeline_base>/validate_paper.py <output_dir>/paper.json
```
스키마/필수필드/이미지 경로 존재/sid 중복을 점검합니다. 오류가 있으면 고친 뒤 다시 검증하세요.

### 6. 완료 처리
`meta.json` 은 **수정하지 마세요**(상태·진행도는 워커가 관리). `titleEn` 은 원문 영어 제목 그대로.
모두 정상이면:
```
echo "완료" > <output_dir>/stage.txt
touch <output_dir>/DONE
```
복구 불가 오류면:
```
echo "<짧은 오류 사유>" > <output_dir>/FAILED
```

## 품질 (Opus 4.8 · effort high)
번역은 **Opus 4.8 모델 + effort `high`** 로 수행합니다(워커가 `/effort high` 설정).
번역 후 **검증 워크플로우**(원문 PDF 페이지와 `paper.json` 을 대조해 누락·오역·수치 오류,
그리고 **문장 정렬이 어긋난 곳**을 점검)를 한 번 돌리고 반영한 뒤 `DONE` 을 쓰세요. 정확·완전성 우선.
