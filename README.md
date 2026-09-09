# cb_valuation — 전환사채(CB) 평가 프로그램 (1단계: 이자율 커브 엔진)

회계법인 평가 실무용. 채권평가사 YTM 매트릭스에서 무위험(국고채)·위험(회사채 등급) 커브를 부트스트래핑·보간해 현물/선도 이자율과 DF 를 만들고, par 검증·사람 승인·감사 증빙(CSV/JSON + xlsx)까지 자동화한다. 흐름은 `cb_valuation/step1_curve/graph/step1_graph.py` 의 `EDGES` 배열 하나로 정의된다(그래프 엔지니어링).

## 설치 (다른 PC 에서도 동일)
```
python -m venv .venv && .venv\Scripts\activate      # Windows
pip install .                                        # openpyxl 이 함께 설치됨(xlsx 증빙 필수)
```
Python 3.12 이상. 그 외 의존성 없음(numpy/scipy 불필요).

## 검사 (설치 확인)
```
python cb_valuation/step1_curve/graph/graph_check.py          # 그래프 불변식·두 갈래 시나리오 → exit 0
python cb_valuation/step1_curve/reference/test_interp_ref.py  # 보간 참조 구현(PCHIP) → TOTAL FAILURES: 0
python -m unittest discover -s cb_valuation/step1_curve/tests -v
```

## 앱 실행 (링크를 열면 화면이 뜬다)
```
start_app.bat                                          # 더블클릭 → 옛 서버 정리 → 로컬 서버 + 브라우저 http://127.0.0.1:8765 (viewer.html 파일을 직접 열면 동작하지 않음)
python -m cb_valuation.step1_curve.app.server --open   # 같은 것(포트 변경: --port 8888)
```
왼쪽 화면 순서: ① **YTM 매트릭스 업로드**(파일 선택 버튼 또는 드래그 앤 드롭 — 평가사 xlsx/xlsm 또는 CSV/TSV; 표를 복사해 붙여넣을 수도 있음) → ② **커브 설정**(**보간법: 선형 보간 / PCHIP** 필수 선택 — 둘 다 검토자 방식 Rf_dc/Rd_dc 수식 시트, 부트스트래핑은 국고채 6개월·회사채 3개월 이표, **노드 간격 월간/주간/일간**, 산출 기간(년), 무위험/위험 **행 드롭다운**(매트릭스에서 읽어 채움), 평가기준일·고시일, 평가사, 담당자) → 실행 → **결과 탭**에서 확인(입력 확인 → 계산 → 최종 확인; 예외 코드가 있을 때만 예외 확인) → 표·엑셀·증빙 경로. 오른쪽에는 `EDGES` 그래프에서 **현재 노드·지나온 엣지가 색으로 표시**된다(정지 = 노란 승인 노드).

결과 탭은 검토자 형식(`Rf_dc`/`Rd_dc`)을 화면에 표로 보여주고 **"엑셀 내려받기"** 로 같은 형식의 xlsx 를 즉시 내보낸다(`exports/`). 보간법 선택(LINEAR·PCHIP; REVIEWER_2024 도) + 주간/월간 격자에서는 검토자 시트를 **행 번호·라벨·서식까지 그대로, 살아있는 엑셀 수식**으로 만든다(입력은 테너 주수·YTM·고시일뿐, 엑셀이 다시 계산; par 검증 = MODEL CHECK 행; 명세 `cb_valuation/step1_curve/docs/REVIEWER_SHEET_SPEC.md`). 다른 프로필·일간 격자에서는 같은 배치의 값 시트(4블록)가 나온다. 최종 승인까지 마치면 감사 증빙 번들(`evidence/`)이 별도로 생성된다. 상품(만기·등급·발행형태) 정보는 이 단계의 앱 화면에서 받지 않는다(2단계용 선택 입력으로만 남아 있음).

화면의 보간법 선택지는 프로필 LINEAR(선형 보간)·PCHIP 두 개다(`Constants.PROFILES_UI`; 사용자 결정 2026-09-08). DEFAULT·PCHIP_TREE·REVIEWER_2024 는 명령행(`--profile`)에서만 쓴다. KICPA_1130·EXCEL_REF 는 미구현. 서버는 127.0.0.1 전용이며 금리표는 PC 밖으로 나가지 않는다.

화면 디자인은 `ref/design/DESIGN-dell-1996.md`(디자인 토큰: 검은 페이지 프레임, 평면 색블록 리본 카드, Arial Black 제목·Helvetica 굵은 UI 라벨·Times 본문, 모서리 0, 그림자 없음)를 따른다. 탭은 **1 입력 · 2 결과** 두 개다(승인 확인·증빙 경로·중단 사유는 결과 탭 안에 나온다). 노란 "지금 여기" 스티커가 state 만 보고 볼 탭을 가리킨다. 캡처 승인 절차(CAPTURE_MISSING)는 2026-09-08 사용자 결정으로 없앴다(PROVENANCE_APPROVAL_FIELDS=()). 보라색 블록은 페이지당 하나(실행)이며, 상단 배너 오른쪽 연보라 글씨가 현재 상태다(사용자 결정: 빨강 대신 보라 계열).

## 링크로 실행 (GitHub Pages — 설치 없이 브라우저 안에서 계산)
`start_app.bat` 없이도 링크만 열면 앱이 뜨게 하는 방식이다. 서버를 어디에 두는 것이 아니라, **브라우저 안에서 파이썬 엔진을 그대로 돌린다**(Pyodide = WebAssembly 파이썬). 화면 코드는 로컬 서버 모드와 같고, `fetch("/api/…")` 만 브라우저 안의 파이썬 호출(`app/browser_api.py`)로 바꿔친다.
- **데이터는 PC 를 떠나지 않는다**: 매트릭스·산출물은 브라우저 메모리 파일시스템(`/work`)에만 있다. 외부에서 받는 것은 코드뿐(Pyodide 는 jsDelivr CDN, openpyxl 은 PyPI 휠). 탭을 닫으면 사라지므로 xlsx 와 증빙 zip 은 화면의 버튼으로 저장한다.
- **배포본에는 금리표·고객 자료가 없다**: `tools/build_web.py` 가 `tests/fixtures`, `reference/xl_*.txt`, `docs/`, `ref/` 를 제외하고 패키지를 zip 으로 묶는다(포함되면 빌드가 실패한다).

준비 순서
- **공개 저장소인 경우(현재 `tigersukyum/YieldCurveEngine`)**: `main` 에 push 하면 워크플로가 테스트 → `python tools/build_web.py`(배포본에 금리표·고객 파일이 없는지 `--check` 로 재확인) → 이 저장소의 GitHub Pages 로 배포한다. 저장소 Settings → Pages → Build and deployment → Source 가 **GitHub Actions** 여야 한다(워크플로의 `configure-pages` 가 자동으로 켜 보지만, 404 가 나면 손으로 한 번 설정). 링크: **https://tigersukyum.github.io/YieldCurveEngine/** (2026-09-09 배포 확인).
- **주의**: 공개 저장소에는 `tests/fixtures/`(KIS-NET 매트릭스·검토자 패키지 값)·`reference/xl_*.txt`·`docs/CROSS_CHECK_REF_*.md`(고객 파일명·셀 값) 가 그대로 노출된다. 사용자 결정(2026-09-07)은 '비공개 저장소에서만 커밋' 이었으므로, 공개로 두려면 그 파일들을 저장소와 커밋 이력에서 제거하거나, 저장소를 다시 비공개로 돌리고 아래 방식으로 배포한다.
- **비공개 저장소인 경우**(무료 플랜은 비공개 저장소의 Pages 를 켤 수 없다): 배포본만 별도의 공개 저장소로 보낸다.
  1. 배포용 공개 저장소를 하나 만든다(예 `YieldCurveEngine-site`, 빈 저장소). 여기에는 `index.html`·`cb_valuation.zip`·`.nojekyll` 만 올라간다.
  2. 토큰: 프로필 → Settings → Developer settings → Personal access tokens → **Fine-grained tokens** → Generate. Repository access = *Only select repositories* 로 배포용 저장소만, Permissions → **Contents: Read and write**.
  3. 코드 저장소 Settings → **Secrets and variables → Actions**: Secrets 에 `SITE_REPO_TOKEN` = 토큰, Variables 에 `SITE_REPO` = `계정/배포용저장소이름`. 이 변수가 있으면 워크플로는 직접 Pages 배포 대신 이 저장소로 push 한다.
  4. 배포용 저장소 Settings → Pages → Source **Deploy from a branch**, Branch **main / (root)**. 링크: `https://<계정>.github.io/<배포용저장소이름>/`.
- 로컬에서 미리 보기: `python tools/build_web.py` 후 `python -m http.server 8790 --directory web` → `http://127.0.0.1:8790/` (인터넷 필요 — CDN·PyPI).

사용자 쪽에서 보이는 것: 링크를 열면 검은 화면에 "계산 엔진을 불러오는 중…"(처음 10~30초, 이후는 브라우저 캐시로 빨라짐) → 평소와 같은 화면. 확인·계산·엑셀 내려받기·증빙 zip 내려받기가 모두 브라우저 안에서 끝난다. 명령행·Excel COM 검증 도구는 로컬 설치 모드에서만 쓴다.

## 화면이 이상할 때
- 드롭다운이 비어 있거나 오른쪽 그래프가 없거나 파일을 끌어다 놓아도 반응이 없으면 **옛 서버 인스턴스가 응답하는 경우**다(같은 포트에 옛 서버가 남아 있으면 화면은 새 것, API 는 옛 것이 된다). `start_app.bat` 은 시작 전에 옛 서버를 모두 닫고, 서버는 포트 공유를 거부하며 옛 인스턴스를 교체한다. 화면 상단에 빨간 안내가 뜨면 그 지시를 따르고, 헤더의 `viewer <버전>` 배지와 서버 창의 `v<버전>` 이 같은지 확인한다(다르면 Ctrl+F5).
- 브라우저를 **관리자 권한**으로 띄운 경우 Windows 가 탐색기에서의 드래그 앤 드롭을 막는다 — 그때는 "파일 선택" 버튼을 쓰거나 일반 권한 창으로 연다.

## 명령행
```
python -m cb_valuation.step1_curve.app.cli run --matrix <matrix.csv|xlsx> --valuation-date YYYY-MM-DD --profile DEFAULT|PCHIP_TREE --step monthly|weekly|daily --horizon 10 --rf-row 2 --rd-row 58 [--curve-set-id CURVE1 --operator 이름 --capture-path … --downloaded-at …]  # 상품 정보(--maturity-date --rating --issuance …)는 선택
python -m cb_valuation.step1_curve.app.cli resume --snapshot state/<key>/snapshot__<node>__<n>.json --decision approved|rejected --approver <이름> --comment "<문장>" [--ack CODE ...]
```
정지(사람 승인 대기)는 exit code 3 이며 스냅샷 경로를 출력한다. `--profile` 은 필수다(보간법·프로필은 실행 시 사용자가 선택; 선택은 provenance 에 기록되고 입력 승인 화면에 표시된다). 산출물: `state/<평가기준일>__<세트>/`(스냅샷·approved_state.json), `evidence/<…>/`(01~12 + README_conventions.md + checklist_map.json + evidence.xlsx), `data/raw/<고시일>/`(원본 사본).

## 문서
- 공통 규칙 `CLAUDE.md`, 1단계 세부 `cb_valuation/step1_curve/CLAUDE.md`, PRD `cb_valuation/step1_curve/PRD_step1.md`
- 그래프 스펙(자동 생성) `cb_valuation/step1_curve/docs/GRAPH_SPEC.md`, 상태 스키마 `docs/STATE_SCHEMA.md`, 공식 `docs/FORMULA_REFERENCE.md`, 보간법 `docs/INTERPOLATION_METHODS.md`, 증빙 xlsx 규격 `docs/XLSX_TEMPLATE.md`, 감사인 질의 `docs/AUDITOR_QA.md`, 빌드 순서 `docs/BUILD_PROMPTS.md`

## 데이터 취급
`ref/`(고객 자료·저작물), `data/raw/`, `state/`, `evidence/` 는 커밋 제외. `tests/fixtures/`·`reference/xl_*.txt` 는 참조 모형의 금리표를 담고 있어 **회사 내부 비공개 저장소에서만** 사용한다(.gitignore 주석 참조). 금리표·식별정보를 외부 LLM 으로 보내지 않는다.
