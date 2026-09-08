# XLSX_TEMPLATE — 증빙 통합문서 규격 (사용자 결정 2026-09-07: xlsx 필수, 검토자 `Rf_dc`/`Rd_dc` 서식 재현 + par 검증 행)

원천: `Constants.XLSX_REQUIRED / XLSX_TEMPLATE / XLSX_FORMULA_SHEETS / XLSX_SHEETS / XLSX_DC_STYLE / XLSX_DC_BLOCKS / XLSX_COLUMNS`(`graph/step1_graph.py`; 표는 GRAPH_SPEC §10 에 자동 생성). 서식의 출처는 내부 검토자 패키지 `8521_평가보고서 검토자의 검토요구사항_Call Option Valuation_KBI metal_2024.xlsx` 의 `Rf_dc`(B1:TC38)·`Rd_dc`(A1:TD53) 시트를 openpyxl 로 읽어 확인한 값이다(2026-09-07; 원본은 `ref/` 커밋 제외, 셀 값은 fixture C `tests/fixtures/reviewer_curves_20241231.json`).

**2026-09-08 사용자 결정(우선)**: `Rf_dc`/`Rd_dc` 는 검토자 시트를 **그대로 — 살아있는 엑셀 수식 + 원본 서식 —** 재현한다(`XLSX_FORMULA_SHEETS=True`, `io/reviewer_sheet.py`, 명세 `docs/REVIEWER_SHEET_SPEC.md`). par 검증은 그 시트의 MODEL CHECK 행(수식)이다. 적용 조건은 `reviewer_sheet.applicable`(검토자 방식 상수 = 프로필 LINEAR·PCHIP(앱 '보간법' 두 선택지, 국고채 반기·회사채 분기)·REVIEWER_2024 + 주간/월간 격자 + 테너·이표기간이 스텝의 정수배; 마디 YTM 보간은 linear 또는 pchip — REVIEWER_SHEET_SPEC §7). 조건 밖(DEFAULT·PCHIP_TREE, 일간 격자)에서는 아래 §3~§4 의 **값 시트**(XLSX_DC_BLOCKS)를 쓰고 B2 에 사유를 적는다. 나머지 시트(§2)는 두 경우 모두 같다.

## 1. 왜 xlsx 가 필수인가
- 감사인 Q1 "파일/탭/셀 위치와 함께 제출" — `checklist_map.json` 의 위치 문자열 `<file>!<sheet>!<range>` 가 xlsx 시트·셀을 가리킨다.
- 검토자는 2024년에 `Rf_dc`/`Rd_dc` 형식으로 독립 재계산을 했으므로 같은 배치로 내보내면 대조가 셀 단위로 가능하다(C36 독립 재계산 일치).
- 따라서 `XLSX_REQUIRED=True`: openpyxl 이 없어 xlsx 를 못 쓰면 `export_evidence` 엣지 `xlsx누락`(XLSX_MISSING) → fail. CSV/JSON/MD(01~12)는 계속 함께 생성되며 해시 비교(바이트 재현)의 원천이다(xlsx 는 저장 시각 때문에 바이트 결정성이 없음).
- 배포: openpyxl 은 `pyproject.toml` 의 선언 의존성이다. 다른 PC 에서는 `pip install .`(또는 `pip install -r requirements.txt`) 후 실행한다. 표준 라이브러리 원칙의 유일한 예외.

## 2. 통합문서 구조 (`XLSX_SHEETS` 순서 고정)
INPUT_RAW · ROWS_USED · PROVENANCE · CONVENTIONS · **Rf_dc** · **Rd_dc** · PAR_CHECK · FWD_SPOT_CHECK · SENSITIVITY · HEADLINE · FLAGS · APPROVALS · RUN_PATH
- 열 지향 시트(FWD_SPOT_CHECK, RUN_PATH, APPROVALS …)는 `XLSX_COLUMNS` 의 헤더를 1행에 쓴다(basis 라벨 포함). **PAR_CHECK** 는 수식 시트가 적용될 때 검토자 FY25 '검증' 시트의 Par 검증 블록 배치(국고채 6개월·회사채 3개월 표, Rf_dc/Rd_dc 에서 HLOOKUP, REVIEWER_SHEET_SPEC §8)로 쓰고, 아니면 종전 열 지향 표(`XLSX_COLUMNS["PAR_CHECK"]`)로 쓴다.
- `Rf_dc`/`Rd_dc` 는 **행 지향**(검토자 배치): 라벨은 B열, 데이터는 C열부터 오른쪽으로, 블록 사이 빈 행 1개.

## 3. Rf_dc / Rd_dc 값 시트 서식 (`XLSX_DC_STYLE`; 수식 시트 미적용 시에만)
| 항목 | 값 | 검토자 원본 |
|---|---|---|
| 제목 셀 | B1 = "무위험이자율" / "위험이자율" (굵게) | Rf_dc!B1, Rd_dc!B1 |
| 기준일 셀 | D1 = valuation_date | `=Summary!D1` |
| 고시일 셀 | 블록 1 의 라벨 열(B5) = curve_date (mm-dd-yy) | `=Summary!C19` |
| 라벨 열 / 데이터 시작 열 | B / C | 동일 |
| 열 폭 | B 18.7, 데이터 12.7 | 동일 |
| 틀 고정 | E1 | 동일 |
| 블록 제목 | 굵게, 데이터 없음 | r3, r9, r15, r30 |
| 숫자 서식 | 블록 표의 서식 열 그대로(`0.000%`, `0.00000%`, `#,##0.00_ `, `0.00000_ ` 등) | 동일 |

## 4. 값 시트의 블록과 행 (`XLSX_DC_BLOCKS`; `{rate}` = RISK FREE RATE / RISKY RATE, `{period}` = HALF-YEAR(RF_FREQ=2) / QUARTER(RD_FREQ=4 또는 REVIEWER_2024 의 RF))
수식 시트(REVIEWER_SHEET_SPEC §2)는 검토자 원본 행 번호·라벨을 그대로 쓰므로 이 표를 따르지 않는다. cell_map 키(`RF:block1~4`, `RD:block1~5`)는 두 작성기가 같은 이름으로 낸다.
| 블록 | 열 = | 행(라벨 → 원천 접두사) | 검토자 원본 행 |
|---|---|---|---|
| 1 `{rate} - YTM` | 공시 마디(TENOR_LABELS) | WEEKS(테너 주수), TENOR, `{rate} - YTM`(rows), SPOT RATE(bootstrap, 연복리) | r4~r7 |
| 2 `Grid Forward {rate}(INTERPOLATED YTM AND SPOT RATE)` | 트리 격자 스텝(TREE_GRID) | STEP, t (years), `{rate} - YTM`(tree), SPOT RATE(tree), FORWARD RATE(fwd, per_step) | r10~r13 |
| 3 `BOOTSTRAPPING({period})` | 부트스트랩 격자(1/m 년) | `{period}`, WEEKS, YTM - YEARLY, `{period}` PAYMENT RATE(=c), PV OF PRINCIPAL, PV OF BOND(PAR_FACE 또는 관행적 가격), PVF OF SPOT Rate(DF), SUM OF PVF SPOT JUST PRIOR TO(ΣDF), `{period}` SPOT Rate(per_period), SPOT Rate -Yearly(annual_eff), **SPOT Rate -Continuous(conv, 추가)**, FORWARD Rate - `{period}`, FORWARD Rate - Yearly, **MODEL CHECK (PAR REPRICE)**(par_check: Σc·DF+DF_n 을 PAR_FACE 로 환산), **PAR RESIDUAL**(par_check: 잔차, 지수 서식) | r16~r28 (+par 행 2개 추가) |
| 4 `Grid Forward {rate}` | 트리 격자 스텝 | STEP, STEP SPOT RATE(`fwd.spot_per_step` = (1+z_k)^dt−1), FORMULA I(`fwd.growth_step` = 1+F_k — 검토자 r33 = 1+weekly forward), FORMULA II -CUMM(`fwd.growth_cum_prev` = Π_{j<k}(1+F_j), 첫 열 1 — r34), STEP FORWARD RATE(F_k), PVF OF FORWARD RATE(df_step), **MODEL CHECK (PROD DF_FWD - DF_SPOT)**(fwd_spot_check diff_prod, Q11), MODEL CHECK (PV)(`fwd.df_backward` = Π_{j≥k} df_step_j × PAR_FACE — r38 역방향 PV) | r31~r38 (원본 철자 'FOMULA' → FORMULA) |

주의
- 검토자 원본은 RF 도 분기(QUARTER)였다(REVIEWER_2024 프로필). DEFAULT 는 RF 반기이므로 `{period}`=HALF-YEAR 로 치환되고 열 수가 달라진다 — 라벨은 프로필의 RF_FREQ/RD_FREQ 에서 결정하며 하드코딩하지 않는다.
- 블록 2·4 의 열 수 = 트리 격자 스텝 수(보고서 N=234 / 주간 / 엑셀 N=181). 검토자 원본은 520 주(TC 열).
- `Rd_dc` 원본의 "BOOTSTRAPPING(Weekly)" 블록(r39~r45, 주간 부트스트랩)은 REVIEWER_2024 전용 대조 항목이며 기본 템플릿에는 넣지 않는다(SENSITIVITY 시트의 FREQ_SENSITIVITY 로 대체).
- 각 행의 정확한 state 경로는 빌드 9단계(`io/evidence_writer.py`)에서 STATE_SCHEMA 와 함께 확정한다 — 여기서는 접두사까지만 규정.
- 값은 state 의 double 그대로 쓰고 서식만 입힌다(반올림한 값을 쓰지 않는다). 작성기는 **계산하지 않는다** — 파생값(부트스트랩 격자 선도·성장계수·역방향 PV·격자 YTM)은 `compute_forward`/`map_tree_grid`/`interpolate` 노드가 state 에 기록하고, 작성기가 하는 산술은 PAR_FACE 배율과 WEEKS(=t×WEEKS_PER_YEAR) 환산뿐이다. PV OF BOND = PAR_FACE×목표가격, MODEL CHECK (PAR REPRICE) = PAR_FACE×재가격(둘을 구분). 셀 주소는 `checklist_map.json` 이 참조하므로 행 순서를 바꾸면 `Constants.XLSX_DC_BLOCKS` 와 이 문서를 함께 바꾼다.
