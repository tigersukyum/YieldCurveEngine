# BUILD_PROMPTS — 1단계 앱을 실제로 만들 때 차례로 입력할 프롬프트 (조태호 8단계를 CB에 맞게)

전제: 프로젝트 루트(`프로그램/`)에서 `claude` 실행. 각 단계 후 결과를 **숫자로** 확인하고(완료 메시지 금지) 다음 단계로. 각 단계 끝에 `/graph-check`. 형식은 책 4장의 단계별 프롬프트(파일명·구조·상수 명시)를 따른다.

## 공통 규칙 (모든 단계에 적용)
- **완료 조건(통일)**: ① 실행 출력 **원문** 첨부(요약·반올림 재서술 금지) ② `python cb_valuation/step1_curve/graph/graph_check.py` exit 0 ③ 단계에 적힌 두 갈래 시나리오 id(GRAPH_SPEC §4 = `graph_check.SCENARIOS`, A01~A04·E01~E50)가 기대 마지막 엣지·기대 status 로 끝남. 셋 중 하나라도 빠지면 "완료"라고 쓰지 않는다.
- **숫자**: 임계값·허용오차는 상수명만 인용(TOL_PAR_FAIL, TOL_PAR_WARN, TOL_GOLDEN_ABS.<key>, TOL_EXCEL_RECON, TOL_KNOT_ROUNDTRIP, TOL_ROUNDTRIP_COMP, TOL_FWD_SPOT_FAIL, CROSS_METHOD_DF_WARN, CURVE_DATE_MAX_LAG_DAYS, DENOM_FLOOR, GS_TOL …). 값은 GRAPH_SPEC §11 에만 있고 프롬프트·테스트·문서에 숫자 리터럴로 적지 않는다.
- **프로필 5종**: DEFAULT, EXCEL_KBI, REVIEWER_2024, KICPA_1130, PCHIP_TREE(fixture 매핑 A/B/C/D, PCHIP_TREE 는 A 입력 재사용). 전환은 `Constants.with_profile(name)` 만 쓴다(PROFILE_NAME 이 지문에 포함). 임시 상수 변형은 graph_check 의 `CAP` 처럼 `items()` 전체 복사로 만들고, 상속만 하는 `Constants` 서브클래스는 금지. 재개 시 `Constants.with_profile(state.run.profile)` 로 복원.
- **임포트 규약**: `from cb_valuation.step1_curve.graph import step1_graph`(패키지 `__init__.py` 존재, `sys.path` 조작 금지). 스크립트 직접 실행은 `try/except ImportError` 폴백(graph_check.py 참조).
- **드라이런 정의**(GRAPH_SPEC §6, `/curve-validate`): 하네스가 approve_input 정지에서 `set_decision(approver='dry-run')` 으로 입력 승인만 자동 기록하고 계산을 끝까지 돌린 뒤, approve_exception/approve_curve 정지에서는 재개하지 않고 보고 후 종료한다. `state/` 스냅샷·`approved_state.json` 을 쓰지 않는다(영속화 없음). 실제 승인은 실행 모드 스냅샷에서 `/approve` 로만.
- **git**: 커밋 전 `git status --ignored` 로 `ref/**`, `ref/**(방법론 PDF 포함)`, `state/`, `evidence/`, `data/raw/`, `.env` 가 ignored 목록에 있는지 확인한다(.gitignore). 스냅샷·증빙 파일은 커밋 제외이되 삭제 금지(감사 증빙). 이 폴더는 OneDrive 동기화 폴더이며 아직 git 저장소가 아니다(열린 결정).
- **스크립트·커맨드 대응**(경로는 `cb_valuation/step1_curve/` 기준; 커맨드는 이 스크립트를 호출하고, 없으면 "미구현" 보고):

| 커맨드 | 스크립트 | 만드는 단계 |
|---|---|---|
| `/graph-check` | `graph/graph_check.py`(있음) | 0 |
| `/two-branch` | `graph/graph_check.py` + `tests/test_edges_two_branch.py` | 8 |
| `/interp-check` | `reference/test_interp_ref.py`(있음) + `scripts/interp_check.py` | 4a |
| `/par-check` | `scripts/par_check.py` | 4b |
| `/compare-excel` | `scripts/compare_excel.py`(임시 대안 `reference/recompute_boot.py`) | 4b |
| `/fwd-spot-check` | `scripts/fwd_spot_check.py` | 4c |
| `/curve-validate` | `scripts/curve_validate.py --dry-run` | 7 |
| `/approve` | `app/cli.py resume` | 2·7 |
| `/export-evidence` | `scripts/export_evidence.py` + `scripts/evidence_check.py` | 9 |
| `/step1-full` | `scripts/step1_full.py` | 9 |
| (화면) | `app/viewer.html` | 5 |
| (스킬) | `.claude/skills/bond-curve-conventions/SKILL.md`(있음) | 10 |

## 0. 준비 (이미 완료된 것 확인)
```
cb_valuation/step1_curve/ 아래 graph/step1_graph.py(NODES 22·EDGES 68·Constants(프로필 5종)·new_state·run·set_decision·load_state·hash_of), graph/graph_check.py(SCENARIOS A01~A04·E01~E50), graph/export_spec.py, docs/{GRAPH_SPEC(생성 문서 — 편집 금지),STATE_SCHEMA,FORMULA_REFERENCE,INTERPOLATION_METHODS,CROSS_VERIFICATION_GUIDELINES,BUILD_PROMPTS,AUDITOR_QA}.md, PRD_step1.md, tests/fixtures/*, reference/*.py 가 있다.
루트 CLAUDE.md와 step1_curve/CLAUDE.md, tests/CLAUDE.md 를 읽고 내용을 요약해 보여줘. 아직 코드를 쓰지 마.
python cb_valuation/step1_curve/graph/graph_check.py 를 실행해 exit 0 을 확인해줘. 출력에 `GRAPH_SPEC.md 구버전` 이 있으면 python cb_valuation/step1_curve/graph/export_spec.py 를 실행하고 다시 확인해줘.
(선택) git init 후 `git status --ignored` 로 .gitignore(ref/**, ref/**(방법론 PDF 포함), state/, evidence/, data/raw/, .env)가 작동하는지 확인하고 첫 커밋을 해줘. OneDrive 동기화 충돌이 우려되면 .git 을 OneDrive 제외 폴더로 두는 방법을 제안해줘.
```
완료 조건: graph_check 출력 원문(NODES/EDGES/SCENARIOS/fingerprint 줄 포함) + exit 0 + A01~A04·E01~E50 전부 통과(스텁 수준).

## 1. 연습용 데이터 — 기준선 양쪽
```
tests/fixtures/ 의 4종(kisnet_matrix_20251231 = A, boot_cached_20251231 = B, reviewer_curves_20241231 = C, kicpa_case1130_20230503 = D; 매핑 표는 tests/fixtures/README.md)을 읽고,
tests/fixtures/golden/<fixture_id>.json (fixture_id = A|B|C|D, 파일 4개)을 만들어줘. 골든값은 docs/FORMULA_REFERENCE.md §9(표시용 인용) 와 reference/recompute_boot.py, reference/curve_demo.py 출력에서만 가져오고, 값마다 source(셀/페이지/스크립트 출력 줄)·tolerance(Constants.TOL_GOLDEN_ABS 의 키: A, B, C_spot, C_fwd_weekly, C_pi, D) 키를 적어라. 이후 테스트는 이 JSON 만 골든 원천으로 읽는다(골든 변경은 출처 첨부 없이 금지).
fixture C(검토자)의 헤드라인은 골든이 아니라 '재계산 회귀값'으로 표기하라(2.765/11.854 는 엑셀 stale 5Y knot 이며 fixture B 전용).
tests/fixtures/E_corrupted/<scenario_id>.json 을 만들되 scenario_id 는 graph_check.SCENARIOS(= docs/GRAPH_SPEC.md §4)의 id 만 쓴다: 오염 케이스 E01~E50 은 파일 하나씩, 정상 케이스 A01~A04 는 fixture A 입력 + 프로필/결정만 다르므로 파일 없이 SCENARIOS 의 설정을 그대로 재사용한다. 각 파일에 scenario_id, expected_last_edge(기대 엣지 이름), expected_status, profile, decisions, hooks 를 SCENARIOS 에서 복사하고(테스트가 SCENARIOS 와 동일성을 assert), 입력 파일로 만들 수 있는 오염(헤더 오타 E01, 파싱 오류 E02, 행 0개 E03, 만기일 없음 E04, curve_date 이동 E05~E07·E36~E40(lag 1일 = DATE_LAG 로 approve_exception 도달), RF 라벨 없음 E08, 만기 12Y E17)은 매트릭스/메타 수준으로, 승인 결정·재개 직전 변조(E09~E12·E36~E44)는 SCENARIOS 의 decisions/hooks 열 그대로, 그 밖의 계산 상태 오염(E13~E16·E18~E35·E45~E47, E36 의 fwd.negative_count 포함)은 tests 안 monkeypatch 훅 이름으로 적어라(Constants 에 훅 금지).
SCENARIOS 에 id 가 없는 오염 — '-'가 0으로 들어간 행(ZERO_VALUE_CELL, WARN)·RD<RF 행(RD_LT_RF, APPROVAL_REQUIRED)·lag = CURVE_DATE_MAX_LAG_DAYS 및 그 +1 의 경계 — 는 E_corrupted/ 파일을 만들지 않는다(파일명을 붙일 id 가 없다). 코드 집계는 GRAPH_SPEC §5 표대로 `input_stage_flags()`·sanity_check 의 unittest(state 수준)로 검증하고, 경계 시나리오가 필요하면 먼저 graph_check.SCENARIOS 에 id 를 추가하고 export_spec.py 로 GRAPH_SPEC §4 를 재생성한 뒤에만 파일을 만든다(추가 여부 열린 결정).
양쪽이 모두 있어야 한다(id 는 SCENARIOS): par 통과 E25/실패 E24(TOL_PAR_FAIL 양쪽), 잔여만기 3.47y(fixture A 기준일 2025-12-31 → 만기 2029-06-21; graph_check.happy_state 의 remaining_years, XL DATA!A4 = FORMULA_REFERENCE §5.2 — RPT 의 4.47y 는 2024-12-31 기준일(fixture C vintage) 값)/12y(E17 만기초과), lag 0(A01)·1일(E07·E36~E40)·초과(E05)·−1(E06), 승인/거절(A01 vs E09·E37·E41), 정상-역전 커브(fixture A vs fixture D — 역전은 NONMONO WARN 만, 통과해야 함). RD>RF/RD<RF 와 CURVE_DATE_MAX_LAG_DAYS 경계값 양쪽은 위 규칙대로 파일 없이 unittest 로 검증한다.
```
완료 조건: golden 4개·E_corrupted 50개 파일 목록 원문 + `python -m json.tool` 로 전부 파싱됨 + graph_check exit 0(시나리오 표 변경 없음: A01~A04·E01~E50).

## 2. 노드와 엣지 — 화면보다 먼저 (이미 선언됨; 러너·스냅샷·CLI 분리)

**프로필 선택은 필수 입력**(사용자 결정 2026-09-07, `Constants.PROFILE_SELECTION="required"`): `cli run` 은 `--profile` 이 없으면 `PROFILE_DESCRIPTIONS` 목록을 출력하고 종료한다(조용한 기본값 금지). 선택값은 `provenance.method_choice{profile, chosen_by=operator, chosen_at}` 로 state 에 넣고, `record_provenance` 가 interp_method/space 를 C 에서 복사한다. 미선택 → `출처불완전`, `C.PROFILE_NAME` 과 불일치 → `프로필불일치`(시나리오 E48·E49). 화면(5단계)의 선택 목록도 같은 상수를 읽는다.
```
graph/step1_graph.py 의 EDGES 배열을 유일한 흐름 정의로 유지하고 run·set_decision·load_state·hash_of·Constants·NODES 도 그 파일에 남긴 채(graph_check.py 와 테스트가 `from cb_valuation.step1_curve.graph import step1_graph` 로 임포트한다), 스냅샷 파일 저장/로드(경로 규칙·exit 3)만 graph/snapshot.py 로, 명령행은 app/cli.py 로 분리해줘.
app/cli.py 서브커맨드: `run --matrix <path> --valuation-date <YYYY-MM-DD> --profile DEFAULT|PCHIP_TREE|KICPA_1130|REVIEWER_2024|EXCEL_KBI (필수)` 와 `resume --snapshot <path> --decision approved|rejected --approver <이름> --comment "<문장>" [--ack CODE ...]`. wait_for_human 도달 시 state/<valuation_date>__<curve_set_id>/snapshot__<node>__<n>.json 저장 후 exit code 3. resume 순서는 고정: `load_state(json)` → `C = Constants.with_profile(state.run.profile)` → `set_decision(state, kind, decision, approver, comment, acknowledged_codes)` → `run(state, C, start=state.run.paused_at_node)`. 승인 필드는 set_decision() 만 쓴다.
graph_check.py 가 여전히 exit 0 이어야 한다. 노드는 아직 스텁이다.
```
완료 조건: `python -m cb_valuation.step1_curve.app.cli run …`(fixture A) 이 approve_input 에서 exit 3 으로 멈춘 출력 원문과 스냅샷 경로 + graph_check exit 0 + A03(대기 → paused) 통과.

## 3. 판단을 조건 함수에
```
모든 게이트(헤더, lag 범위, knot 수, 만기>horizon, knot 왕복, 분모/근찾기/DF 무효, par 잔차, 복리 왕복, excel_zero, DF 범위/단조, 선도-현물, 승인 거절/결정선행/변조/상수변경/ack, 증빙 완전성)가 Constants 상수 + EDGES 람다로만 구현되어 있는지 확인하고, 노드 안에서 다음 노드를 정하거나 프롬프트에 의존하는 판단이 있으면 제거해줘.
tests/test_graph_invariants.py 를 만들어 graph_check.static_checks()/dynamic_checks() 를 unittest 로 감싸라(러너 `python -m unittest discover -s cb_valuation/step1_curve/tests -v`). YTM 은 매트릭스 셀에서 직접 읽고 AI 가 추측하지 않게 하라.
```
완료 조건: unittest 출력 원문(OK) + graph_check exit 0 + A01~A04·E01~E50 전부(스텁 수준, 미커버 엣지 0). 검토자: @agent-graph-structure-auditor.

## 4. 노드가 함께 쓰는 상태 + 엔진 이식 (4a → 4b → 4c 순서; 소단계마다 검사·검토자 호출)
공통: curve/ 패키지에 reference/interp_ref.py(pchip·linear·loglinear_df·natural_cubic; scipy 대조 검증됨 — 공식은 바꾸지 말 것)와 reference/recompute_boot.py(모드 A 폐형식·엑셀 재현)를 이식한다. nodes/ 는 1파일 1노드로 step1_graph.py 의 스텁을 실제 구현으로 교체하되 각 노드는 docs/STATE_SCHEMA.md 의 자기 접두사만 쓴다(쓰기 추적 프록시). graph_check 의 그래프 수준(스텁) 검사는 빌드 후에도 돌아야 한다(`/two-branch` 1단계). 수치는 fsum/log1p/expm1 을 쓰고 (1+s)^m−1 을 직접 계산하지 마라. 모든 금리 배열은 RateVector(values, times, basis), basis ∈ Constants.BASIS. 격자·이표일 키는 round(t, T_ROUND_DIGITS).

### 4a. 보간 플러그인 (선행: 입력→격자 노드·자료형)
```
선행 골격: compounding.py 의 자료형만(RateVector+Basis, basis 검증; 변환 노드는 4c), daycount.py(ACT/365, 30/360, 잔여만기·트리 격자·이벤트일), io/matrix_loader.py('-'→None(0 금지), 0.0 셀 기록, sha256, 헤더 셀 단위 비교), io/label_regex.py(LABEL_GRAMMAR; AI 경로는 6단계), nodes/{load_matrix, record_provenance, interpret_labels, select_rows, build_grid}.py.
보간: interp.py 에 INTERP_TABLE 플러그인(linear·pchip 필수, is_local 플래그 선언; interp_ref.py 의 PCHIP 기울기 규칙 그대로), spaces.py(ytm|spot_annual|spot_continuous|log_df), extrap.py(EXTRAP_LEFT/RIGHT 규칙, excel_zero 는 EXCEL_REPLICATE 전용), nodes/interpolate.py(모드 A 면 이표격자 c_n 을 COUPON_CONV 로, knot 왕복 검사 → interp.knot_roundtrip_max_err, 외삽 사용 기록). 같은 플러그인 객체를 뒤의 부트스트랩 내부(모드 B, 4b)와 트리 격자 매핑(4c)에 쓴다.
scripts/interp_check.py: `--method`·`--space` 옵션(비우면 전수) — knot 왕복(TOL_KNOT_ROUNDTRIP 판정), PCHIP 기울기 MATLAB 예제(INTERPOLATION_METHODS §7; x=−3..3, y=[−1,−1,−1,0,1,1,1] → d=[0,0,0,1,0,0,0]), 교차 방법·공간 DF 상대차표(CROSS_METHOD_DF_WARN), 외삽 플래그(EXTRAP_LEFT_FLAT/EXTRAP_RIGHT_USED) 출력.
```
검사: `python cb_valuation/step1_curve/reference/test_interp_ref.py`(TOTAL FAILURES 0) → `/interp-check`(= scripts/interp_check.py 전수) → `/graph-check`.
완료 조건: 두 출력 원문 + graph_check exit 0 + A04(PCHIP_TREE, next_step_interface.space=log_df)·E01~E08·E13~E19 통과(E19 = TOL_KNOT_ROUNDTRIP 초과). 검토자: @agent-bond-math-verifier(INTERPOLATION_METHODS §3 대조), @agent-qa-test-engineer.

### 4b. 부트스트랩 모드 A·B + par 검증 + PRICE_MODE
```
cashflows.py(만기 역산 1/m 이표 스케줄, 단수기간 stub, COUPON_CONV 적용 위치 한 곳), pricing.py(PRICE_MODE: par | kicpa_conventional — 3M 국채 10,080.6 재현), bootstrap_closed.py(모드 A: DF_n=(1−c_nΣDF)/(1+c_n), 분모 ≤ DENOM_FLOOR → FAIL_DENOMINATOR), bootstrap_rootfind.py(모드 B 한공회 1130: knot brent 브래킷 확장 ROOT_XTOL/ROOT_MAX_ITER/ROOT_BRACKET_STEP/ROOT_BRACKET_EXPANSIONS + 중간 이표일 보간 + is_local=False 면 Gauss-Seidel GS_TOL/GS_MAX_SWEEPS, solver_log; 비수렴 → FAIL_NO_CONVERGENCE), excel_compat.py 의 부트스트랩 부분(3M 시드 RF_SEED_3M, 중점 재격자 RF_REGRID_RULE, stale G/V 주입 — EXCEL_KBI 전용).
nodes/bootstrap.py(bootstrap.status·df_valid·min_denominator·solver_log), nodes/verify_par.py(모든 만기 Σ c·DF + DF_n − 목표가격, RF/RD 둘 다, max_abs_err, 미사용 knot 잔차 INFO).
scripts/par_check.py(`--curve RF|RD|ALL [--state <json>]`; 만기별 잔차·PAR_FACE 환산 열·max|잔차|·미사용 knot INFO, TOL_PAR_FAIL/TOL_PAR_WARN 판정)와 scripts/compare_excel.py(`--vintage stale|live`; fixture B 열별 max|diff| ≤ TOL_EXCEL_RECON, MF_INTERPOL 프로브, stale/live 차이 공시 문구).
tests/test_fixtures_golden.py 의 부트스트랩 항목(fixture A TOL_GOLDEN_ABS.A, B .B EXCEL_KBI 프로필, D .D KICPA_1130 의 spot/DF)을 통과시키고 max|diff| 원문을 붙여라.
```
검사: `/par-check ALL` → `/compare-excel stale` → `/graph-check`.
완료 조건: 세 출력 원문 + graph_check exit 0 + E20~E25 통과(E24/E25 = TOL_PAR_FAIL 양쪽). 검토자: @agent-bond-math-verifier(FORMULA_REFERENCE §3·§6), @agent-qa-test-engineer.

### 4c. 복리 변환·트리 격자·선도·Π DF 검증
```
compounding.py 변환 함수(annual=expm1(m·log1p(s)), cont=m·log1p(s); discount_factor 는 annual_eff|continuous 만 수용, per_period 전달 시 TypeError — 한공회 §3.7.4.4), forward.py(TREE_FWD_RULE 두 가지; NODE_DISCOUNT_CONV: df_step=exp(−f·dt) 와 df_step_alt=1/(1+F) 병기), sensitivity.py((method×space)+FREQ_SENSITIVITY_SET 변형을 순수 함수로 재실행, 주 커브 불변), headline.py(HEADLINE_RULE·HEADLINE_DEFS 후보 진단표, 보고서 헤드라인과의 ROUND_HALF_UP 비교 → match_ok; 비교 자릿수는 Constants 에 상수가 없으므로 이 문서에 리터럴로 적지 않는다 — 상수화 여부·이름은 열린 결정, 현행 표기는 STATE_SCHEMA `headline.match_ok` 행·step1_graph `node_compute_headline` docstring·GRAPH_SPEC §1), excel_compat.py 의 격자 부분(MF_INTERPOL 포트 — EXCEL_KBI 전용).
nodes/{convert_compounding, map_tree_grid, compute_forward, verify_fwd_spot, run_sensitivity, compute_headline, sanity_check}.py — map_tree_grid 는 4a 와 같은 플러그인 객체·공간으로 spot→트리 격자(tree.interp_method_used/interp_space_used 기록, 외삽 스텝은 사실만 기록), verify_fwd_spot 은 로그 공간 |Σ(−f_k·dt_k) − ln DF_spot| 게이트 + ΠDF−DF 절대차 + Q11 예시. 심각도 집계는 sanity_check 한 곳(EXTRAP_LEFT_FLAT_SEVERITY(열린 결정) 반영, 역전 커브는 WARN 만).
scripts/fwd_spot_check.py(`--state <json>`; 트리 격자 전 점 로그 잔차·곱 절대차, TOL_FWD_SPOT_FAIL 판정, 마지막 격자점 예시 — fixture C 는 week 520).
tests/test_fixtures_golden.py 를 전 항목으로 확장: A(C-SPOT·PV), B, C(TOL_GOLDEN_ABS.C_spot·C_fwd_weekly·C_pi, REVIEWER_2024 프로필), D. max|diff| 원문을 붙여라.
```
검사: `/fwd-spot-check <state.json>` → `python -m unittest cb_valuation.step1_curve.tests.test_fixtures_golden -v` → `/graph-check`.
완료 조건: 세 출력 원문 + graph_check exit 0 + E26~E36 통과(E27 = TOL_ROUNDTRIP_COMP 초과, E33 = TOL_FWD_SPOT_FAIL 초과, E36 = NEG_FWD → approve_exception 재정지). 검토자: @agent-bond-math-verifier(FORMULA_REFERENCE §4·§5), @agent-graph-structure-auditor(자기 접두사·집계 한 곳), @agent-qa-test-engineer.

## 5. 흐름이 보이는 화면
```
graph/graph_check.py 가 만드는 graph/edges_export.json 을 읽는 app/viewer.html(외부 라이브러리 없음)을 작성해줘. 왼쪽: 매트릭스·선택 행·BOOT/BM 열 순서 결과표(basis 헤더)·par 잔차·Q11 예시·flag 표. 오른쪽: EDGES 그래프에 현재 노드와 지나온 엣지(run.path)를 색으로 강조하고 state JSON 을 보여줘. 화면에는 흐름 로직을 두지 말고 state JSON 과 edges_export.json 만 읽어라. 승인 버튼은 `app/cli.py resume` 명령 문자열을 만들어 보여주기만 한다.
```
완료 조건: fixture A 의 정지 스냅샷(approve_input)과 done state 두 개를 열어 현재 노드·경로가 강조된 화면 캡처(또는 DOM 텍스트 원문) + graph_check exit 0 + A01·A03 통과. 검토자: @agent-graph-structure-auditor(화면에 흐름 로직 없음).

## 6. AI는 해석까지
```
io/label_regex.py(Constants.LABEL_GRAMMAR)를 기본 경로로 두고, io/label_ai.py 는 Constants.AI_ENABLED 와 ANTHROPIC_API_KEY 가 있을 때만 interpret_labels 노드에서 정규식 미매칭 행의 라벨 문자열만 전송(페이로드에 숫자가 있으면 assert)하고, 제안은 정규식 재검증을 통과해야 parser='llm' 으로 반영되게 해줘(LLM_PARSER_USED WARN 기록). 계산·판정·approval_* 필드 접근은 불가(프록시). API 키 없이 fixture A~D 와 E_corrupted 전부 완주함을 보여줘.
```
완료 조건: 실행 목록 원문(API 키 없음, 각 fixture·시나리오의 종단 status) + graph_check exit 0 + A01·E08 통과. 검토자: @agent-graph-structure-auditor(AI 접근 범위).

## 7. 사람이 끼어드는 자리
```
approve_input / approve_exception / approve_curve 에서 wait_for_human 으로 멈추고 스냅샷이 저장되며, `app/cli.py resume` 로 멈춘 노드에서 이어서 실행되는지 fixture A 로 보여줘. set_decision() 만 승인 필드를 쓰고(다른 필드 쓰기 AssertionError), 거절(E09·E37·E41)은 fail 로 가며 fail_reason 에 노드·승인자·코멘트가 남아야 한다. 재개 후 CALC_PREFIXES 필드 바이트 동일(hash_of), 결정선행(E10·E38·E42)·상수 변경(E11·E39·E43)·입력/계산 상태 변조(E12·E40)·이전 승인 기록 변조(E44)·ack 일부(E36 → 미확인코드잔존 재정지) 에서 fail/재정지 엣지가 작동함을 확인하고 12_approvals.json 을 인쇄해줘.
scripts/curve_validate.py(`--matrix <path> --valuation-date <YYYY-MM-DD> --profile NAME (필수) --dry-run`): 공통 규칙의 드라이런 정의대로 approver='dry-run' 으로 입력 승인만 자동 기록하고, approve_exception/approve_curve 정지에서 심각도 표(코드·커브·값·임계 상수명)·헤드라인·교차 방법 DF 차이·run.path 를 출력하고 종료한다(영속화 없음).
```
완료 조건: 12_approvals.json 원문 + `/curve-validate` 출력 원문 + graph_check exit 0 + A03·E09~E12·E36~E44 통과. 검토자: @agent-graph-structure-auditor.

## 8. 두 갈래 확인
```
tests/test_edges_two_branch.py: graph_check.SCENARIOS(A01~A04·E01~E50)를 스텁 대신 실제 노드로 그대로 돌려 run.path 의 엣지 이름이 기대 마지막 엣지·기대 status 와 일치하는지 확인해줘 — 게이트 8곳(GATE_NODES) 임계값 양쪽·NaN, 승인 3노드 approved/rejected/pending/결정선행, ack 일부/전부, EXTRAP_LEFT_FLAT_SEVERITY(열린 결정) 두 값(A01 = WARN 기본 vs A02 = APPROVAL_REQUIRED, `items()` 전체 복사 방식), 프로필 5종(DEFAULT·EXCEL_KBI·REVIEWER_2024·KICPA_1130·PCHIP_TREE). 기대(GRAPH_SPEC §4 표 그대로): approve_exception 경유 = A02(EXTRAP_LEFT_FLAT ack → done)·E07(DATE_LAG ack → done)·E36(NEG_FWD 만 ack, DATE_LAG 미확인 → 미확인코드잔존 → paused)·E37~E40(lag 1일 DATE_LAG 로 도달한 뒤 각각 거절·결정선행·상수변경감지·계산상태변조감지 → fail); done = A01·A02·A04·E07·E25; paused = A03(approve_input 대기)·E36; 나머지 E 는 전부 fail(기대 엣지 이름은 SCENARIOS 열 그대로). fixture 수준: A/C/D 는 done(D 는 역전 커브라도 WARN 만), B 는 EXCEL_REPLICATE_ON 승인 없이 완료 불가. 이표주기는 DEFAULT 의 RF_FREQ/RD_FREQ 와 REVIEWER_2024(FREQ_SENSITIVITY_SET 의 RF 대안 주기) 둘 다. 미커버 엣지 0 을 엔진 수준에서도 유지하고, 의도대로 될 때까지 수정해줘.
```
검사: `/two-branch`(graph_check "two-branch scenarios" 부분 + `python -m unittest cb_valuation.step1_curve.tests.test_edges_two_branch -v`).
완료 조건: 두 출력 원문 + graph_check exit 0 + A01~A04·E01~E50 전부(id | 기대 엣지/status | 실제 | 판정 표). 검토자: @agent-qa-test-engineer, @agent-graph-structure-auditor.

## 9. 증빙·재조정

**xlsx 는 필수**(사용자 결정 2026-09-07, `Constants.XLSX_REQUIRED`): `io/evidence_writer.py` 는 `docs/XLSX_TEMPLATE.md`(= `XLSX_SHEETS`·`XLSX_DC_STYLE`·`XLSX_DC_BLOCKS`·`XLSX_COLUMNS`) 대로 검토자 `Rf_dc`/`Rd_dc` 배치(라벨 B열·데이터 C열부터·틀 고정 E1·열 폭·숫자 서식)를 재현하고 블록 3 에 par 검증 행(MODEL CHECK (PAR REPRICE)·PAR RESIDUAL)을 넣는다. 생성 후 `export.xlsx_written=True`·`xlsx_path` 를 기록하고, openpyxl 이 없으면 기록하지 않아 엣지 `xlsx누락` 이 fail 로 보낸다(시나리오 E50). openpyxl 은 `pyproject.toml` 의 선언 의존성이며 README 의 `pip install .` 로 설치된다 — 다른 PC 에서의 동작 확인(`python -c "import openpyxl"` + 번들 생성 + `checklist_map.json` 의 `evidence.xlsx!Rf_dc!<cell>` 참조가 실제 셀과 일치)을 완료 조건에 넣는다.
```
io/evidence_writer.py 와 nodes/export_evidence.py, scripts/export_evidence.py(`--valuation-date <YYYY-MM-DD> [--curve-set-id <id>]`; 승인된 state 로 번들 재생성), scripts/evidence_check.py(`evidence/<key>`; 체크리스트 검증): EVIDENCE_FILES 01~12 CSV/JSON·README_conventions.md(CONVENTION_REASONS·상수 전부·허용오차(상수명+값)·프로필·fingerprint·'참조 모델 내부 불일치' 공시)·xlsx(XLSX_SHEETS/XLSX_COLUMNS 고정 셀, openpyxl 없으면 export.warnings XLSX_SKIPPED)·checklist_map.json(위치 문자열 `<file>!<sheet|->!<range|json_path>`)·12_approvals.json. EVIDENCE_REQUIRED_ITEMS 전항목이 cell_map 에 있어야 export 통과(GRAPH_SPEC §10). CSV/JSON 재생성 바이트 동일 테스트(xlsx 는 docProps 제외).
scripts/compare_excel.py 로 fixture B ≤ TOL_EXCEL_RECON 및 stale/live 차이 disclosure 문구, scripts/interp_check.py 로 교차 방법·Gauss-Seidel 로그를 출력해줘. scripts/step1_full.py 를 만들어 /step1-full 의 순서(graph_check → test_interp_ref → unittest → compare_excel stale/live·interp_check → curve_validate --dry-run·evidence_check → 요약표)를 fail-fast 로 실행하게 해줘. scripts/ 8종(par_check, fwd_spot_check, interp_check, compare_excel, curve_validate, export_evidence, evidence_check, step1_full)이 모두 있고 커맨드 10개가 "미구현" 없이 돌아야 한다.
```
검사: `/export-evidence <valuation_date>` → `/step1-full` → `git status --ignored`(evidence/·state/ 가 ignored 목록에 있음).
완료 조건: evidence_check 체크리스트 표·step1_full 요약표 원문 + graph_check exit 0 + A01(done, 증빙 전항목)·E45~E47 통과. 검토자: @agent-audit-evidence-reviewer, @agent-qa-test-engineer.

## 10. 에이전트·커맨드·스킬로 검토 루프 돌리기
```
.claude/agents/ 5개(bond-math-verifier, graph-structure-auditor, audit-evidence-reviewer, qa-test-engineer, curve-fixer)와 .claude/commands/ 10개, .claude/skills/bond-curve-conventions/SKILL.md 가 이미 있다. 각 파일을 열어 tools·model 줄과 커맨드가 호출하는 스크립트 경로(공통 규칙의 대응표)를 확인해줘. 재시작 → /help → /step1-full → @agent-bond-math-verifier, @agent-graph-structure-auditor, @agent-audit-evidence-reviewer 병렬 검토(읽기 전용; curve-fixer 와 동시 실행 금지) → `git status --ignored` 확인 후 백업/커밋 → @agent-curve-fixer 로 번호 매겨진 지적 사항만 수정 → @agent-qa-test-engineer 재검증 → 사람 확인 → /export-evidence 로 실제 평가기준일 번들 생성 → audit-evidence-reviewer 최종('감사인 제출 가능 여부').
```
완료 조건: /step1-full 요약표 원문(ERROR 0) + graph_check exit 0 + A01~A04·E01~E50 전부 + done 도달 조건(par 양쪽 통과·승인·증빙 체크리스트 전항목).
