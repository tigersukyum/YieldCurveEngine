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
start_app.bat                                          # 더블클릭 → 로컬 서버 + 브라우저 http://127.0.0.1:8765 (viewer.html 파일을 직접 열면 동작하지 않음)
python -m cb_valuation.step1_curve.app.server --open   # 같은 것(포트 변경: --port 8888)
```
왼쪽 화면 순서: ① **YTM 매트릭스 업로드**(파일 선택 버튼 또는 드래그 앤 드롭 — 평가사 xlsx/xlsm 또는 CSV/TSV; 표를 복사해 붙여넣을 수도 있음) → ② **커브 설정**(프로필=보간법 묶음 필수 선택, **노드 간격 월간/주간/일간**, 산출 기간(년), 무위험/위험 **행 드롭다운**(매트릭스에서 읽어 채움), 평가기준일·고시일, 평가사, 담당자) → ③ 출처 증빙(선택: 사용한 행의 화면 캡처 이미지/PDF 업로드 — 감사인 Q12) → 실행 → 승인(입력 확인 → 계산 → 예외/최종 승인) → 결과. 오른쪽에는 `EDGES` 그래프에서 **현재 노드·지나온 엣지가 색으로 표시**된다(정지 = 노란 승인 노드).

결과 탭은 검토자 형식(`Rf_dc`/`Rd_dc` 4블록: 마디 YTM·현물 / 격자 YTM·현물·선도 / 부트스트래핑·par 검증 / 격자 선도·Π DF 검증)을 화면에 표로 보여주고 **"엑셀 내려받기"** 로 같은 형식의 xlsx 를 즉시 내보낸다(`exports/`). 최종 승인까지 마치면 감사 증빙 번들(`evidence/`)이 별도로 생성된다. 상품(만기·등급·발행형태) 정보는 이 단계의 앱 화면에서 받지 않는다(2단계용 선택 입력으로만 남아 있음).

초안 범위: DEFAULT(모드 A + 선형)·PCHIP_TREE(격자 PCHIP/log_df) 프로필. KICPA_1130·REVIEWER_2024·EXCEL_REF 는 화면에 "초안 미구현"으로 표시된다. 서버는 127.0.0.1 전용이며 금리표는 PC 밖으로 나가지 않는다.

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
