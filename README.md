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

## 실행 (앱 본체는 BUILD_PROMPTS 단계로 구현 중)
```
python -m cb_valuation.step1_curve.app.cli run --matrix <kisnet.csv> --valuation-date YYYY-MM-DD --profile <DEFAULT|PCHIP_TREE|KICPA_1130|REVIEWER_2024|EXCEL_KBI>
python -m cb_valuation.step1_curve.app.cli resume --snapshot state/<key>/snapshot__<node>__<n>.json --decision approved --approver <이름> --comment "<문장>" [--ack CODE ...]
```
`--profile` 은 필수다(보간법·프로필은 실행 시 사용자가 선택; 선택은 provenance 에 기록되고 입력 승인 화면에 표시된다).

## 문서
- 공통 규칙 `CLAUDE.md`, 1단계 세부 `cb_valuation/step1_curve/CLAUDE.md`, PRD `cb_valuation/step1_curve/PRD_step1.md`
- 그래프 스펙(자동 생성) `cb_valuation/step1_curve/docs/GRAPH_SPEC.md`, 상태 스키마 `docs/STATE_SCHEMA.md`, 공식 `docs/FORMULA_REFERENCE.md`, 보간법 `docs/INTERPOLATION_METHODS.md`, 증빙 xlsx 규격 `docs/XLSX_TEMPLATE.md`, 감사인 질의 `docs/AUDITOR_QA.md`, 빌드 순서 `docs/BUILD_PROMPTS.md`

## 데이터 취급
`ref/`(고객 자료·저작물), `data/raw/`, `state/`, `evidence/` 는 커밋 제외. `tests/fixtures/`·`reference/xl_*.txt` 는 참조 모형의 금리표를 담고 있어 **회사 내부 비공개 저장소에서만** 사용한다(.gitignore 주석 참조). 금리표·식별정보를 외부 LLM 으로 보내지 않는다.
