# step1_curve — 1단계 이자율 커브 엔진 세부 규칙 (루트 CLAUDE.md의 공통 규칙에 추가)

## 입력 레이아웃
- 채권평가사 시가평가 기준수익률 매트릭스: 열 `종류|구분|적용대상채권|3M,6M,9M,1Y,1.5Y,2Y,2.5Y,3Y,4Y,5Y,7Y,10Y,15Y,20Y,30Y,50Y`(%, `Constants.TENOR_LABELS`), 행 = 채권 종류/등급, 블록 헤더 행(공모무보증/사모무보증) 상속. 결측 `'-'`(`MISSING_TOKENS`) → None(절대 0 아님).
- RF = 국고채 행(KIS-NET row2). RD = 회사채 + 등급 + 블록(참조 모형: 사모무보증 BB+ row58; 공모 BB+ row42). 대체(BLOCK_FALLBACK)·노칭·전기 등급/블록 불일치는 승인 코드(ROW_FALLBACK·NOTCH_APPLIED·RATING_CHANGED·BLOCK_CHANGED).

## 관례 색인 (값은 `graph/step1_graph.py` Constants; 문서에는 상수명만 — 값 표는 GRAPH_SPEC §11)
RF_FREQ/RD_FREQ, COUPON_CONV, BOOTSTRAP_MODE(A 기본/B 한공회), PRICE_MODE, INTERP_METHOD(linear 기본/pchip 필수), INTERP_SPACE_PRE/GRID, PCHIP_RECOMMENDED_SPACE, EXTRAP_LEFT/RIGHT, EXTRAP_LEFT_FLAT_SEVERITY(열린 결정), CURVE_HORIZON_Y, `Constants.knot_tenors(curve)`(모드별 사용 마디), DAYCOUNT, TREE_GRID, TREE_FWD_RULE, NODE_DISCOUNT_CONV, HEADLINE_RULE, PROFILES 5종 {DEFAULT, EXCEL_REF, REVIEWER_2024, KICPA_1130, PCHIP_TREE} ↔ fixture A/B/C/D(PCHIP_TREE 는 A 입력 재사용).
- **프로필은 실행 시 사용자가 선택한다**(PROFILE_SELECTION=required; CLI `--profile` 필수, 화면 목록 = PROFILES 키 + PROFILE_DESCRIPTIONS). 선택은 `provenance.method_choice` 에 기록되어 PROVENANCE_REQUIRED_FIELDS 로 강제(미선택 → 출처불완전, 실행 상수와 다르면 프로필불일치). 조용한 기본값 없음. 프로필 전환은 `Constants.with_profile(name)` 만 쓴다(PROFILE_NAME 이 지문에 포함). 임시 상수 변경이 필요하면 graph_check 의 `CAP` 처럼 `items()` 전체 복사로 만든다 — 상속만 하는 서브클래스는 금지. 재개 시 `Constants.with_profile(state.run.profile)` 로 복원.

## 노드 22 · 엣지 68 · 게이트 8 · 승인 3 · 종단 3 (전체 표: `docs/GRAPH_SPEC.md` §1~§3, 코드: `graph/step1_graph.py`)
load_matrix → record_provenance → interpret_labels → **approve_input** → select_rows → build_grid → interpolate → bootstrap → verify_par → convert_compounding → map_tree_grid → compute_forward → verify_fwd_spot → run_sensitivity → compute_headline → sanity_check → (**approve_exception**) → **approve_curve** → export_evidence → done | fail | wait_for_human. 게이트(`GATE_NODES`)는 첫 엣지가 반드시 '비유한'.

## 공식 색인 (출처: `docs/FORMULA_REFERENCE.md`)
모드 A: spot_1=c_1, spot_n=((1+c_n)/(1−c_nΣDF))^(1/n)−1 ≡ DF_n=(1−c_nΣDF)/(1+c_n) (BOOT!H/I). 모드 B: 공시 마디 미지수 + 중간 이표일 보간 + brent(+Gauss-Seidel) (한공회 1130). 복리: annual=(1+s)^m−1, cont=m·ln(1+s)=ln(1+annual) (BOOT!M/N). 선도: f_i=(r_i t_i−r_{i−1}t_{i−1})/Δt, DF=exp(−f Δt), F_i=DF_{i−1}/DF_i−1 (BM). 검증: Σc·DF+DF_n=1, Π DF_fwd=DF_spot, knot 왕복, 복리 왕복. PCHIP: `docs/INTERPOLATION_METHODS.md §3`(scipy/SLATEC/MATLAB 동일).

## 심각도 (담당: 전용 엣지 vs sanity_check) — GRAPH_SPEC §5
FAIL → fail(`result.fail_code` = EDGE_CODES; 다중 노드 교차 규칙 INTERP_MISMATCH 만 sanity 소속). APPROVAL_REQUIRED → approve_exception(코드별 `--ack`). WARN → 기록(XLSX_SKIPPED 는 export.warnings). 역전 커브는 정상(NONMONO는 WARN).

## 승인·스냅샷 — GRAPH_SPEC §6
정지: `state/<valuation_date>__<curve_set_id>/snapshot__<node>__<n>.json`, exit 3. 결정은 `set_decision()` 만(요청 이후·정지 중·같은 노드·승인자 필수·ack ⊆ flags_seen). 재개 `cli resume --snapshot --decision --approver --comment [--ack]` → `load_state()` → `with_profile(run.profile)` → `run(start=paused_at_node)`; 승인 노드 엣지 순서는 `HUMAN_EDGE_ORDER`(거절·결정선행·상수변경·변조·[미확인코드]·승인·대기). 재개 후 CALC_PREFIXES 바이트 동일.

## fixture · 골든 · 테스트
`tests/fixtures/README.md`. 골든값 원천은 `tests/fixtures/golden/<fixture_id>.json`(FORMULA_REFERENCE §9 는 표시용 인용). 두 갈래 시나리오 id 는 `graph_check.SCENARIOS`(= GRAPH_SPEC §4, A01~A04·E01~E50)만 인용. 러너 `python -m unittest discover -s cb_valuation/step1_curve/tests -v`(stdlib). 그래프 검사 `python cb_valuation/step1_curve/graph/graph_check.py`(exit 0 = 정적 불변식·전 엣지 커버·노드 쓰기 추적·지문 결정성). 참조 구현 `reference/`(interp_ref.py는 scipy 대조 검증됨 — 이식하되 공식은 바꾸지 말 것; recompute_boot.py 는 `reference/xl_BOOT.txt`·`xl_KIS-NET.txt` 사용).

## 증빙 번들 — GRAPH_SPEC §10, FORMULA_REFERENCE §8, `docs/AUDITOR_QA.md`(질의 원문)
`evidence/<key>/` EVIDENCE_FILES(01~12) + README_conventions.md + **xlsx(필수, XLSX_REQUIRED; `Rf_dc`/`Rd_dc` 는 검토자 시트 그대로 살아있는 수식+원본 서식(XLSX_FORMULA_SHEETS, `io/reviewer_sheet.py`, `docs/REVIEWER_SHEET_SPEC.md`; 적용 조건 `reviewer_sheet.applicable` = REVIEWER_2024 방식 + 주간/월간 격자, 아니면 값 시트 XLSX_DC_BLOCKS/XLSX_DC_STYLE `docs/XLSX_TEMPLATE.md`), PAR_CHECK 는 검토자 FY25 검증 시트의 Par 검증 블록(국고채 6개월·회사채 3개월 표, Rf_dc/Rd_dc 에서 HLOOKUP 수식; REVIEWER_SHEET_SPEC §8), 그 밖의 열 지향 시트는 XLSX_COLUMNS; 미생성 → 엣지 xlsx누락 FAIL)** + checklist_map.json(EVIDENCE_REQUIRED_ITEMS 전항목, 위치 문자열 `<file>!<sheet|->!<range|json_path>`) + 12_approvals.json. Q9·C42·C45~C47 은 STEP2_EVIDENCE_ITEMS(2단계). openpyxl 은 pyproject 선언 의존성(표준 라이브러리 원칙의 유일한 예외).

## 참조 엑셀 결함 (수치·셀은 FORMULA_REFERENCE §3.1·§5.1·§9; 재현은 EXCEL_REF 프로필에서만, 정상 모드에서는 수정)
BOOT!G/V stale 하드코딩, L10 live + L11 stale 점프, MF_INTERPOL 좌측 원점 앵커·우측 Empty(0), R24:R25 '-'→0, 9M 미사용·3M 시드(RF_SEED_3M), 헤드라인 ceil_tenor(stale 5Y knot).

## 앱 초안 구조 (2026-09-07; 실행: `start_app.bat` 또는 `python -m cb_valuation.step1_curve.app.server --open`)
- `nodes/` 노드 구현(자기 접두사만) → `nodes.NODES_IMPL` 을 `run(state, C, nodes=NODES_IMPL)` 에 넘긴다. `graph/step1_graph.NODES` 는 스텁(graph_check 전용)이며 EDGES 는 하나다. 승인·sanity_check·done·fail·wait_for_human 은 step1_graph 함수 그대로.
- `curve/` 순수 함수(interp = reference/interp_ref 재사용, bootstrap 모드 A, compounding, gridmap.CurveOnGrid(공간·외삽), forward). `io/` 매트릭스 파서·정규식 라벨(블록은 등급 순서 재시작으로 분할)·증빙 작성기(evidence_writer; Rf_dc/Rd_dc 는 `io/reviewer_sheet.py` 수식 시트 우선, 폴백 XLSX_DC_BLOCKS)·검토자 시트 자원(`io/reviewer_dc_layout.json`·`io/reviewer_theme1.xml` = 서식·라벨만, 값 없음; 재추출 `reference/extract_reviewer_layout.py <원본>`; Excel 대조 `reference/verify_reviewer_sheet.py <원본>`).
- `app/runner.py` 가 CLI(`app/cli.py`)·서버(`app/server.py` + `viewer.html`)·브라우저 브리지(`app/browser_api.py` — Pyodide 정적 배포, 같은 /api/* 경로를 함수로; `tools/build_web.py` 가 web/ 를 만들고 `.github/workflows/pages.yml` 이 Pages 에 올림; E2E `tools/e2e_web.py`) 공용: prepare_state(입력 접두사 채움; 프로필 필수) → advance(run + 스냅샷/최종 저장, `graph/snapshot.py`) → decide_and_resume(set_decision → run(start)). 번들 루트는 `run.base_dir`(러너가 기록; 노드는 환경변수를 읽지 않는다 — graph_check 가 검사).
- 앱 입력(커브 전용 모드): 매트릭스 업로드(csv/tsv/xlsx → io/matrix_parser.read_matrix_bytes) → `provenance.row_choice`(RF/RD 행 드롭다운) + `provenance.grid_settings`(노드 간격 STEP_MODES 월간/주간/일간, 산출 기간 ≤ CURVE_HORIZON_Y) (캡처 업로드 칸은 2026-09-08 화면에서 제거, PROVENANCE_APPROVAL_FIELDS=() 로 CAPTURE_MISSING 승인 절차도 제거; /api/upload kind=capture 는 유지). 화면 탭은 1 입력·2 결과 두 개(승인 확인·증빙 경로는 결과 탭 안; 검증·플래그 표는 화면에 없고 evidence/09_flags.csv 에만). 상품 정보(instrument)는 선택 입력이며 없으면 헤드라인·등급 캡처를 요구하지 않는다. 결과 화면·`/api/export` 는 io/evidence_writer.dc_blocks 를 공용으로 쓴다(REVIEWER_2024+주간/월간이면 검토자 시트 행 그대로 `orient: rows`, 아니면 값 4블록).
- 구현 범위: 앱 화면은 **보간법 두 선택지 = 프로필 LINEAR("선형 보간")·PCHIP**(`PROFILES_UI`; 검토자 방식 piecewise_quarter_step·1_discrete_fwd·linear×log_df 격자 + RF_FREQ 2·RD_FREQ 4 기본값, 마디 YTM 보간 INTERP_METHOD_PRE 만 linear/pchip — REVIEWER_SHEET_SPEC §7). CLI 전용: DEFAULT·PCHIP_TREE(continuous_from_spot)·REVIEWER_2024(RF·RD 분기, 검토자 원본 fixture C 대조). KICPA_1130(모드 B)·EXCEL_REF 는 `Constants.PROFILES_IMPLEMENTED` 밖 → 화면에 "초안 미구현", `runner.prepare_state` 가 `nodes.unsupported(C)` 사전 게이트로 NotImplementedError(노드 안의 raise 는 도달 불가 방어).
- 검토 반영(2026-09-07): 판단값은 전부 Constants(EPS_T·TOL_DF_MONOTONE·DF_RANGE·INTERP_METHOD_PRE·BLOCK_OF_ISSUANCE·RATING_ORDER·SENSITIVITY_COMBOS·PROFILES_IMPLEMENTED·BP_PER_UNIT·WEEKS_PER_YEAR); 증빙 작성기는 state 복사만(파생값은 노드가 기록); 격자 보간체 knot 왕복 게이트(엣지 `격자knot왕복불일치`); `run()` 은 승인·종단·sanity 노드 함수 항등을 검사; graph_check 가 실제 노드 구현(NODES_IMPL)의 쓰기 접두사도 추적; approved_state.json 해시는 사이드카 `.sha256`(파일 바이트 원상).
- 엔진 테스트 `tests/test_app_pipeline.py`(fixture A done 경로·게이트 허용오차·프로필 필수·결정성·PCHIP_TREE). 실측(fixture A DEFAULT): RF spot_annual 0.5Y 0.0240934 / 10Y 0.0343360, RD 10Y 0.1585730 = recompute_boot live 와 일치.

## 금지 목록
노드 내 라우팅, 타 노드 필드 쓰기, per_period→exp(), 결측 0 대입, 상수 하드코딩, 테스트 안 숫자 리터럴(상수 참조), constants 안 테스트 훅, Constants 상속 서브클래스(with_profile/items() 복사만), EXCEL_REF 밖 엑셀 결함 재현, 출처 없는 공식, 완료 메시지만 있는 보고.
