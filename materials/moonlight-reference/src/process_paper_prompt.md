# 논문 번역 파이프라인 (Paper Translation Pipeline)

당신은 사용자가 제공한 arXiv 논문을 **한국어로 번역**해 Medium 스타일 HTML로 만드는 작업을 한 건 처리합니다. 사용자가 직접 링크를 준 문서를 그들의 학습용으로 번역하는 것이므로 인용·발췌·번역해도 됩니다.

## 작업 파라미터

작업 정보는 `job.json`에 있습니다(워커가 전달한 경로). 다음 필드를 읽으세요:
- `arxiv_id` — 예: `2501.12948`
- `start_page`, `end_page` — 번역할 페이지 범위 (정수)
- `description` — 어디까지/어떻게 번역할지 (예: "8페이지의 6번 섹션까지만")
- `output_dir` — 결과물을 저장할 디렉터리 (절대경로). 이 안에 `figures/`가 있습니다.

## 진행 상태 표시

각 단계 시작 시 `<output_dir>/stage.txt` 파일에 **한 줄**로 현재 단계를 적으세요(대시보드가 이걸 읽어 사용자에게 보여줍니다). 예:
```
echo "PDF 다운로드 중" > <output_dir>/stage.txt
```
단계 예시: `PDF 다운로드 중` → `본문 읽는 중` → `번역하는 중` → `그림·표 추출 중` → `HTML 빌드 중`.

## 단계

### 1. PDF 다운로드
```
curl -L -o <output_dir>/source.pdf "https://arxiv.org/pdf/<arxiv_id>"
```
`pdfinfo`로 페이지 수/크기를 확인하세요.

### 2. 본문 읽기
`Read` 도구의 `pages` 파라미터로 `<output_dir>/source.pdf`의 `start_page`~`end_page`를 읽습니다(이미지로 렌더됨). `description`이 지정한 종료 지점(예: "6번 섹션까지")을 정확히 지키고, 그 다음 섹션은 번역하지 않습니다.

### 3. 한국어 번역본 작성 → `<output_dir>/paper.md`

**DeepSeek-R1 번역본과 동일한 규칙**을 따르세요:
- 맨 위: `# 한국어 제목` (H1) + 그 아래 `### 영어 원제` (H3, 부제)
- **중요한 주장·수치·용어는 `**볼드**`** 로 강조.
- 문서 순서를 그대로 유지하고, 어떤 문단·문장·수식·표·그림도 누락하지 않음.
- 수식: 디스플레이 수식은 `$$ ... $$`, 인라인은 `$ ... $`. 번호 있는 식은 `\tag{n}` 사용.
- 표:
  - 템플릿/예시류 박스 표는 아래 HTML 박스로:
    ```
    <div class="boxtable">
    <div class="boxtable-caption"><strong>표 N</strong> | 캡션…</div>
    <div class="boxtable-body"> … 내용 (수식은 $..$) … </div>
    </div>
    ```
  - 수치 데이터 표는 **마크다운 표**로 작성(통계적으로 유의한 값 등은 `**볼드**`).
- 그림:
  ```
  ![그림 N](figures/figureN.png)

  <div class="figcaption"><strong>그림 N</strong> | 한국어 캡션…</div>
  ```

**그림·표 배치 규칙 (중요):**
- 각 그림/표는 **본문에서 처음 언급되는 지점 바로 뒤**에 한 번만 배치합니다.
- 본문이 참조하지만 `end_page` 이후(부록 등)에 있는 그림·표도 **PDF에서 발췌**해 포함하고, 캡션 끝에 `<em>(부록에서 발췌)</em>` 표기.

### 4. 그림·표 이미지 추출 → `<output_dir>/figures/`
`pdftoppm -png -r 200 -f <p> -l <p> <output_dir>/source.pdf <output_dir>/figures/p<p>` 로 해당 페이지를 렌더한 뒤, Python(PIL)로 필요한 영역만 crop 해서 `figureN.png` / `tableN.png` 로 저장하세요. crop 좌표는 렌더 이미지를 `Read` 로 확인해 조정합니다(페이지 크기 보통 1654×2339 @200dpi). 작업 후 `p<p>-*.png` 같은 중간 렌더 파일은 삭제.

### 5. HTML 빌드
```
cd <paper_dashboard_base>   # build_paper.py 가 있는 디렉터리
python3 build_paper.py <output_dir>/paper.md <output_dir>/paper.html
```
빌드 후 `paper.html`에 깨진 이미지(존재하지 않는 figures 경로)나 남은 `@@MATH` 플레이스홀더가 없는지 확인하세요.

### 6. 완료 처리
`meta.json`은 **수정하지 마세요**. 특히 **`title`은 원본 영어 제목 그대로 유지**합니다(한국어로 번역하지 말 것). 상태·진행도는 워커가 관리합니다. (단, 본문 `paper.md` 안의 H1 제목은 한국어로 번역해도 됩니다 — 사이드바 표시 제목과는 별개입니다.)

모두 정상 완료되면:
```
echo "완료" > <output_dir>/stage.txt
touch <output_dir>/DONE
```
복구 불가능한 오류면 그 사유를 적고 멈추세요:
```
echo "<짧은 오류 사유>" > <output_dir>/FAILED
```

## 품질 (ultracode)
ultracode 모드라면 번역 완료 후 **검증 워크플로우**(원문 PDF 페이지와 번역본을 대조해 누락·오역·수치 오류 점검)를 한 번 돌리고, 발견된 문제를 반영한 뒤 `DONE`을 쓰세요. 토큰 비용은 신경 쓰지 말고 정확·완전성을 우선합니다.
