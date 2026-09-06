# STATE_SCHEMA v1.1.0 — 노드가 함께 쓰는 상태 (= `Constants.STATE_SCHEMA_VERSION`)

원천: `graph/step1_graph.py` 의 `new_state()` 가 이 문서와 1:1 이다. 아래 §1 표는 `new_state()` 출력(JSON 덤프) 전체에서 만들었고 누락 필드는 0개다. 스키마를 바꿀 때는 `new_state()`·이 문서·`graph_check`(노드 쓰기 추적 `ownership_checks`)를 함께 갱신하고 `STATE_SCHEMA_VERSION` 을 올린다(`export_edges_json()` 이 `schema_version` 으로 내보낸다).

그래프 규모·시나리오·상수 값은 생성 문서 `docs/GRAPH_SPEC.md` 를 인용한다 — 노드 §1, 엣지 68개 §2, 두 갈래 시나리오 A01~A04·E01~E50 §4, 심각도 표 §5, 승인 정책 §6, 증빙 규격 §10, 상수 값 §11. 프로필은 5종(DEFAULT, EXCEL_KBI, REVIEWER_2024, KICPA_1130, PCHIP_TREE)이며 `run.profile` 에 기록된다.

## 0. 규칙

- 노드는 **자기 접두사**의 필드만 채운다(`NODES` 등록표의 접두사와 1:1; `graph_check.ownership_checks` 가 쓰기 추적 프록시로 검사). 다음 노드는 정하지 않는다 — 라우팅은 `run()` 의 EDGES 평가뿐이다.
- 다른 접두사는 **읽기만** 한다(예: `record_provenance` 는 `input.file_sha256` 을 읽어 `provenance.complete` 를 계산하고, `sanity_check` 는 계산 접두사 전부를 읽어 `sanity.*` 만 쓴다).
- 승인 결정 필드(`approval_*.decision / approver / timestamp / comment / acknowledged_codes / history`)는 `set_decision()` 만 쓴다. 승인 노드 함수는 `requested_at / snapshot_sha256 / flags_seen` 만 처음 한 번 쓴다(멱등, §4.1).
- 모든 금리 배열은 `RateVector{values, times, basis}` 이며 `basis ∈ Constants.BASIS`. 결측은 `None`(0 금지). DF 는 annual_eff/continuous 에서만 만든다(per_period → exp() 금지).
- `{c: …}` 표기는 `Constants.CURVE_IDS`(RF, RD) 를 키로 하는 dict 이다. 시간 키는 `round(t, T_ROUND_DIGITS)`.
- 임계값·허용오차는 `Constants` 에만 있다. 이 문서는 상수명만 인용하고 값은 GRAPH_SPEC §11 에 있다.
- 심각도 코드 집계는 `sanity_check` 한 곳(`sanity.fail / approval_required / warn`). 단일 노드 FAIL 은 전용 엣지가 처리하고 `result.fail_code` 에 남는다(GRAPH_SPEC §5).
- 그래프가 찍는 시각(`approval_*.requested_at / timestamp`, `run.paused_at`, `run.path` 의 ts)은 `_now()` = `datetime.now(timezone.utc).isoformat()` (ISO, UTC). 입력으로 받아 적는 시각(`provenance.downloaded_at` 등)은 원문 그대로(예: KST 오프셋 포함 ISO).

## 1. 필드 표 (접두사 | 필드 | 타입/의미 | 채우는 노드)

"채우는 노드" 는 `NODES` 등록표의 접두사 소유자다. `run` 은 `run()` 라우터·`wait_for_human`·`done`·`fail`, `result` 는 `done`·`fail`, `approval_*` 의 결정 필드는 `set_decision()` 만, 요청 필드는 승인 노드 함수. "runner/CLI(미구현)" 는 코드에 쓰는 곳이 아직 없고 `new_state()` 초기값(None)만 있는 필드다(`app/cli.py` 는 BUILD_PROMPTS 의 빌드 항목).

| 접두사 | 필드 | 타입/의미 | 채우는 노드 |
|---|---|---|---|
| run | run_id | str\|None — `run_<UTC 시각 YYYYMMDDTHHMMSS>`(`app/runner.prepare_state`). 스냅샷·증빙 디렉터리 키는 `<valuation_date>__<curve_set_id>`(§3.5) | runner |
| run | base_dir | str\|None — 산출물 루트(절대경로). 러너가 기록; export_evidence 가 읽는다(환경변수 사용 금지) | runner |
| run | profile | str — `PROFILES` 키. `new_state(C)` 가 `C.PROFILE_NAME` 을 복사; 재개 시 `Constants.with_profile(run.profile)` 로 복원(§2.4) | new_state(C) |
| run | curve_set_id | str\|None — 커브 세트 식별자(입력값; 기본 "CB1"), 디렉터리 키 `<valuation_date>__<curve_set_id>` 의 일부(§3.5) | runner |
| run | constants_snapshot | dict\|None — 초기값 None. 코드에 채우는 곳·용도 정의가 없다 — 미확인(README_conventions.md 는 `export_evidence` 가 상수 전부를 인쇄하지만 이 필드를 읽는다는 정의는 없다) | runner/CLI(미구현) |
| run | constants_fingerprint | sha256 hex — `C.fingerprint()`, 결정적 직렬화(§2.5) | new_state(C) |
| run | current_node | str\|None — 라우터가 노드 함수를 호출하기 직전에 기록 | run() |
| run | path | list[(from, 조건이름, to, ts_utc, resume_n)] — 지나온 엣지 = 감사조서 경로(§2.2) | run() |
| run | status | "running"\|"paused"\|"done"\|"failed" (§2.1) | run() / wait_for_human / done / fail |
| run | paused_at_node | str\|None — 정지한 승인 노드 id(= `run.path[-1][0]`) | wait_for_human |
| run | snapshot_path | str\|None — 저장된 스냅샷 파일 경로(base_dir 상대, §3.5). `snapshot.save_snapshot` 이 기록(러너 몫) | wait_for_human → runner |
| run | paused_at | ISO 시각(UTC)\|None — 정지 시각 | wait_for_human |
| run | resume_n | int — 재개 회차. `new_state` 0, `run(start=…)` 마다 +1(§2.3) | run() |
| input | raw_text | str\|None — 붙여넣기/파일 원문 불변 보존(러너가 넣고 load_matrix 가 읽는다) | runner |
| input | file_sha256 | str\|None — 원문 해시. PROVENANCE_REQUIRED_FIELDS 항목(`record_provenance` 가 읽음) | load_matrix |
| input | n_rows | int — 행 수(0 → 행없음 → fail) | load_matrix |
| input | header_labels | list[str] — 헤더 셀 원문 | load_matrix |
| input | header_ok | bool — TENOR_LABELS 와 셀 단위 비교(False → 헤더불일치 → fail) | load_matrix |
| input | rows | list[dict] — 행 항목 `{row_index, label_raw, block, ytm_pct{tenor→float\|None}}`(node_load_matrix docstring). 값은 % 원문 유지(×PCT_TO_DEC 변환은 select_rows), MISSING_TOKENS → None(0 금지); 라벨 해석 안 함 | load_matrix |
| input | parse_errors | list[str] — 숫자 아님·열 수 불일치(비어 있지 않으면 파싱오류 → fail) | load_matrix |
| input | zero_value_cells | list[(row_index, tenor_label)] — 0.0 셀(ZERO_VALUE_CELL WARN 후보; node_load_matrix docstring) | load_matrix |
| provenance | source_agency | str\|None — 채권평가사 | runner(입력) → record_provenance(파생) |
| provenance | agencies | list[str] — 사용한 평가사 목록(비어 있으면 `[source_agency]` 로 채움) | record_provenance |
| provenance | averaging | bool — 복수 평가사 평균 사용 여부(초기값 False) | record_provenance |
| provenance | curve_date / valuation_date | ISO date\|None — 고시일 / 평가기준일(입력값) | runner |
| provenance | date_lag_days | int\|None — `(valuation_date − curve_date).days`. 게이트 기준일역전_또는_지연초과(CURVE_DATE_MAX_LAG_DAYS), 코드 DATE_LAG | record_provenance |
| provenance | raw_copy_path / downloaded_at / operator | str / ISO / str (\|None) — data/raw 사본(러너가 저장)·다운로드 시각·담당자(PROVENANCE_REQUIRED_FIELDS) | runner |
| provenance | capture_path | str\|None — 행 렌더링 캡처(감사인 Q12). PROVENANCE_APPROVAL_FIELDS(결측 → CAPTURE_MISSING) | runner |
| provenance | complete | bool — PROVENANCE_REQUIRED_FIELDS 전부 존재(`file_sha256` 는 `input.file_sha256` 에서 읽음). False → 출처불완전 → fail | record_provenance |
| provenance.method_choice | profile / interp_method / interp_space_grid / chosen_by / chosen_at | str\|None ×5 — **사용자가 실행 시 고른 프로필**(PROFILE_SELECTION=required; CLI `--profile`, 화면 목록 PROFILE_DESCRIPTIONS). `profile`·`chosen_by` 는 PROVENANCE_REQUIRED_FIELDS(미선택 → 출처불완전); `profile ≠ C.PROFILE_NAME` → 엣지 프로필불일치; interp_method/space 는 노드가 C 에서 복사 | record_provenance(선택값은 CLI 가 state 에 넣음) |
| provenance.instrument | issuer / cb_name / maturity_date / issuance_type / rating | str\|None ×5 — issuance_type 공모\|사모(BLOCK_OF_ISSUANCE 로 블록 결정); maturity_date 는 PROVENANCE_REQUIRED_FIELDS | runner |
| provenance.instrument | prior_rating_basis / prior_block_basis | str\|None — 전기 등급·블록(RATING_CHANGED·BLOCK_CHANGED 비교 기준, 감사인 Q13) | record_provenance |
| provenance.instrument | event_dates | list — 풋/콜 등 이벤트일(`build_grid` 가 `grid.tree.event_times` 로 매핑). 항목 키 미확인 | record_provenance |
| provenance.instrument.rating_evidence | source_agency / lookup_date / capture_path / rating_valid_from / sha256 | str\|None ×5 — 등급 조회 증빙(감사인 Q13-1); capture_path 는 PROVENANCE_APPROVAL_FIELDS | record_provenance |
| provenance.instrument.reported_headline | rf_pct / rd_pct / source_doc / page / basis_rf / basis_rd | float\|None ×2 / str\|None / int\|str\|None / str ×2(초기값 `f"nominal_m{C.RF_FREQ}"`·`f"nominal_m{C.RD_FREQ}"` — `Constants.BASIS` 라벨, 프로필의 주기를 따른다) — 보고서 기재 헤드라인(%); `compute_headline` 이 읽어 `reported_*`·`match_ok` 를 만든다 | record_provenance |
| labels | parsed | list[dict] — 행별 해석 결과 `{row_index, kind, rating, block, parser}`(node_interpret_labels docstring; `input_stage_flags()` 가 `parser == "llm"` 이면 LLM_PARSER_USED WARN). 숫자 필드 기록 금지 | interpret_labels(AI 허용 유일 지점) |
| labels | rf_candidates / rd_candidates | list[dict] — `parsed` 의 부분집합(같은 키; rf 비어 있으면 RF후보없음 → fail) | interpret_labels |
| labels | unparsed_rows | list[int] — 미해석 행의 `row_index`(UNPARSED_ROWS WARN; node_interpret_labels docstring) | interpret_labels |
| approval_input · approval_exception · approval_curve | requested_at | ISO 시각(UTC)\|None — 승인 요청 시각(처음 한 번, 멱등) | approve_input / approve_exception / approve_curve |
| approval_* | snapshot_sha256 | sha256\|None — `hash_of(state, SNAPSHOT_SCOPE[node])` (§3.3) | 승인 노드 함수 |
| approval_* | flags_seen | list[flag] — 승인자에게 보인 flag(§4.1; flag 구조는 sanity 와 같음) | 승인 노드 함수 |
| approval_* | decision | "approved"\|"rejected"\|None | set_decision() |
| approval_* | approver | str\|None — 비어 있을 수 없음 | set_decision() |
| approval_* | timestamp | ISO 시각(UTC)\|None — 결정 시각(엣지 결정선행 이 requested_at 과 비교, §4.4) | set_decision() |
| approval_* | comment | str\|None | set_decision() |
| approval_* | acknowledged_codes | list[str] — ack 한 코드(⊆ flags_seen 의 code, §4.2) | set_decision() |
| approval_* | history | list[{decision, approver, timestamp, comment, acknowledged_codes, snapshot_sha256, resume_n}] — append-only | set_decision() |
| rows | rf | dict\|None — 선택된 국고채 행. 확인된 키는 `row_index`(graph_check.happy_state)뿐, 나머지 미확인. None → RF행없음 → fail | select_rows |
| rows | rd | dict\|None — 선택된 회사채 행. 확인된 키는 `row_index`·`notch`(graph_check.happy_state, sanity_check)뿐, 나머지(요청/적용 블록·등급 등) 미확인. None → RD행없음_대체불가 → fail; `notch` ≠ NOTCH_DEFAULT 이면 NOTCH_APPLIED(`sanity_check` 가 상수와 비교, threshold=NOTCH_DEFAULT; 값은 GRAPH_SPEC §11) | select_rows |
| rows | rd_fallback_used / rd_fallback_reason | bool / str\|None — BLOCK_FALLBACK 사용 사실(ROW_FALLBACK) | select_rows |
| rows | rating_consistency_ok / block_consistency_ok | bool\|None — 전기 등급·블록 일관성(False → RATING_CHANGED / BLOCK_CHANGED; None = 비교 불가) | select_rows |
| rows | ytm | {c: RateVector\|None} — basis nominal_m2(RF) / nominal_m4(RD), times = TENOR_YEARS, None 보존 | select_rows |
| rows | knot_tenors | {c: list[str]} — `Constants.knot_tenors(c)`(모드·horizon 별 사용 마디) | select_rows |
| rows | missing_knots | {c: list[str]} — 사용 마디 중 결측(KNOT_MISSING) | select_rows |
| rows | usable_knot_count | {c: int} — MIN_KNOTS 게이트(knot부족 → fail) | select_rows |
| grid | knots | {c: list} — 사용 마디(≤ horizon; 시간 키 round(t, T_ROUND_DIGITS)). 항목 키 미확인 | build_grid |
| grid | boot_times | {c: list[float]} — 1/m 이표 격자(년) | build_grid |
| grid | horizon_years | float\|None — CURVE_HORIZON_Y | build_grid |
| grid | remaining_years | float\|None — 잔여만기(DAYCOUNT). 게이트 잔여만기비유한 → 만기초과 | build_grid |
| grid | unused_tenors | {c: list[str]} — 격자에서 제외된 공시 테너(TENOR_DROPPED WARN) | build_grid |
| grid.tree | N / T / dt_mode / dt / times / daycount / event_times | int / 년 / str / list / list / str / list — TREE_GRID 규칙·DAYCOUNT(FORMULA_REFERENCE §5.2), 이벤트일 매핑. event_times 항목 키 미확인 | build_grid |
| interp | method / method_pre / space_pre / space_grid / extrap_left / extrap_right | str\|None ×6 — INTERP_METHOD(트리 격자) / INTERP_METHOD_PRE(이표격자) / INTERP_SPACE_PRE / INTERP_SPACE_GRID / EXTRAP_LEFT / EXTRAP_RIGHT 복사(공시 항목 C37·한공회) | interpolate |
| interp | ytm_on_coupon_grid | {c: RateVector\|None} — 이표격자 위 보간 YTM(basis nominal_m{m}; 증빙 'YTM - YEARLY') | interpolate |
| interp | is_local | bool\|None — `INTERP_TABLE[method][0]` | interpolate |
| interp | par_coupon_on_grid | {c: RateVector}\|None — 모드 A 이표격자 c_n(BOOT!G/V), basis per_period_m2 / m4 | interpolate |
| interp | knot_roundtrip_max_err / all_finite | float\|None / bool — 게이트 보간비유한 → knot왕복불일치(TOL_KNOT_ROUNDTRIP) | interpolate |
| interp | extrapolated_points | {c: list} — 외삽이 쓰인 점(년) | interpolate |
| interp | coupon_grid_extrap_used | bool — 이표격자 외삽 사용(EXTRAP_COUPON_GRID) | interpolate |
| bootstrap | mode / price_mode | str\|None — BOOTSTRAP_MODE / PRICE_MODE 복사 | bootstrap |
| bootstrap | status | {c: "OK"\|"FAIL_DENOMINATOR"\|"FAIL_BRACKET"\|"FAIL_NO_CONVERGENCE"\|"FAIL_DF_INVALID"\|None} — 엣지 DF무효_비유한 / 분모비양수 / 근찾기실패_비수렴 | bootstrap |
| bootstrap | points | {c: list} — 만기별 부트스트랩 점(BOOT!F~I / U~X). 증빙 열은 XLSX_DC_BLOCKS 블록 3(구 XLSX_COLUMNS 의 BOOT 열); state 항목 키는 미확인 | bootstrap |
| bootstrap | spot_pp / df | {c: RateVector\|None} / {c: list} — basis per_period_m2 / m4, times = boot_times(BOOT!H/W, I/X) | bootstrap |
| bootstrap | min_denominator / df_valid | {c: float\|None} / {c: bool} — 분모 최소(DENOM_FLOOR), DF 유효성 | bootstrap |
| bootstrap | solver_log | {c: list} — 모드 B 근찾기 로그(ROOT_*, GS_*). 항목 키 미확인 | bootstrap |
| bootstrap | errors | list[str] | bootstrap |
| par_check | per_maturity | {c: list} — 부트스트랩 격자 만기별 잔차(FORMULA_REFERENCE §6; 가격 1 기준, PAR_FACE 병기). 증빙 열은 XLSX_COLUMNS["PAR_CHECK"]; state 항목 키는 미확인 | verify_par |
| par_check | max_abs_err / all_finite | float\|None / bool — 핵심 게이트 파잔차비유한 → 파검증실패(TOL_PAR_FAIL); TOL_PAR_WARN 초과 구간은 PAR_WARN | verify_par |
| par_check | unused_knot_max_abs_err | float\|None — 미사용 knot(RF 3M/9M 등) 잔차, UNUSED_KNOT_RESIDUAL WARN | verify_par |
| conv | spot_annual / spot_cont | {c: RateVector\|None} — basis annual_eff / continuous(BOOT!M/N) | convert_compounding |
| conv | roundtrip_max_err / all_finite | float\|None / bool — 게이트 변환비유한 → 왕복변환불일치(TOL_ROUNDTRIP_COMP) | convert_compounding |
| tree | spot_annual_on_grid / spot_cont_on_grid | {c: RateVector\|None} — basis annual_eff / continuous, times = grid.tree.times(BM D-SPOT / C-SPOT) | map_tree_grid |
| tree | df_spot_on_grid | {c: list} — DF = exp(−r_c·t) | map_tree_grid |
| tree | df_finite / df_range_ok / df_monotone_ok | bool ×3 — 게이트 사실(트리DF비유한, DF범위_또는_단조위반) | map_tree_grid |
| tree | extrap_left_flat_steps / extrap_left_origin_steps / extrap_right_steps | {c: list[int]} ×3 — 외삽 스텝 index, 사실만. 심각도는 sanity_check: EXTRAP_LEFT_FLAT 은 EXTRAP_LEFT_FLAT_SEVERITY(열린 결정), EXTRAP_LEFT_ORIGIN·EXTRAP_RIGHT_USED 는 APPROVAL_REQUIRED | map_tree_grid |
| tree | excel_zero_used | bool — VBA Empty→0 외삽 사용 사실(EXCEL_REPLICATE 가 아니면 엣지 엑셀제로외삽_정상모드 → fail) | map_tree_grid |
| tree | interp_method_used / interp_space_used | str\|None — 실제 사용한 보간 방법·공간(보간체 객체 CurveOnGrid.method/space 에서 읽음; interp.method / space_grid 와 다르면 INTERP_MISMATCH FAIL) | map_tree_grid |
| tree | knot_roundtrip_max_err | float\|None — 트리 격자 보간체의 마디 재현 오차(게이트 트리DF비유한 → 격자knot왕복불일치, TOL_KNOT_ROUNDTRIP) | map_tree_grid |
| tree | ytm_on_grid | {c: RateVector\|None} — 트리 격자 위 표시용 YTM(INTERP_METHOD_PRE; 검토자 Rf_dc r11) | map_tree_grid |
| fwd | cont_on_grid | {c: RateVector\|None} — 연속복리 선도 f_i(BM C-FWD), basis continuous | compute_forward |
| fwd | disc_per_step / disc_annual_eff | {c: RateVector\|None} — F_i(basis per_step_simple) / 연환산(annual_eff) | compute_forward |
| fwd | df_step / df_step_alt / df_cum | {c: list} ×3 — exp(−f·dt)[③] / (1+f)^(−dt)[① XL BM F열; ③ 과의 차이 ≈ f²dt/2] / Π | compute_forward |
| fwd | spot_per_step / growth_step / growth_cum_prev / df_backward | RateVector(per_step_simple) / list ×3 — (1+z_k)^dt−1 / 1+F_k / Π_{j<k}(1+F_j)(첫 열 1) / Π_{j≥k} df_step_j — 검토자 Rf_dc r32·r33·r34·r38 원천 | compute_forward |
| fwd | boot_fwd_pp / boot_fwd_annual | {c: RateVector} — 부트스트랩 격자 기간 선도 DF_{n−1}/DF_n−1(per_period_m{m}) / (1+F)^m−1(annual_eff) — Rf_dc r26·r27 | compute_forward |
| fwd | negative_count / max_jump_bp | {c: int} / {c: float} — NEG_FWD(APPROVAL_REQUIRED) / SAWTOOTH(FWD_JUMP_WARN_BP, WARN) | compute_forward |
| fwd | all_finite | bool — 게이트 선도비유한 | compute_forward |
| fwd | rule / node_discount_conv / node_discount_reason | str\|None ×3 — TREE_FWD_RULE / NODE_DISCOUNT_CONV / `CONVENTION_REASONS["NODE_DISCOUNT_CONV"]` 복사 | compute_forward |
| fwd | tenor_table | {c: list} — 테너 간 선도표(감사인 Q10-1) | compute_forward |
| fwd_spot_check | max_abs_err_log / max_abs_err_prod | float\|None — 로그 공간 게이트(정합잔차비유한 → 정합실패, TOL_FWD_SPOT_FAIL) / ΠDF−DF 절대차(증빙 병기) | verify_fwd_spot |
| fwd_spot_check | all_finite | bool | verify_fwd_spot |
| fwd_spot_check | sample | dict\|None — 감사인 Q11 예시 1건 = RF 마지막 격자점 `{curve, step, t, prod_df_fwd, df_spot, diff_log, diff_prod}`(08_fwd_spot_sample.md 원천) | verify_fwd_spot |
| fwd_spot_check | rows | {c: list[{step, t, prod_df_fwd, df_spot, diff_log, diff_prod}]} — 전 격자점 잔차(FWD_SPOT_CHECK 시트 원천) | verify_fwd_spot |
| sensitivity | table | list — 교차 방법·공간·주기 DF 상대차표(주 커브 불변). 항목 키 미확인 | run_sensitivity |
| sensitivity | max_rel_df_diff | float\|None — CROSS_METHOD_DF WARN | run_sensitivity |
| sensitivity | freq_alt | dict — FREQ_SENSITIVITY_SET 변형 결과(초기값 빈 `NS()`). 항목 구조 미확인. 비어 있지 않으면 FREQ_SENSITIVITY WARN(value = `dict(freq_alt)`) | run_sensitivity |
| sensitivity | excel_recon | dict\|None — EXCEL_KBI 프로필 전용 엑셀 재조정 결과(TOL_EXCEL_RECON) | run_sensitivity |
| headline | rule | str\|None — HEADLINE_RULE 복사 | compute_headline |
| headline | rf_ytm_remaining / rd_ytm_remaining | float\|None — 잔여만기 YTM(HEADLINE_RULE), basis nominal_m2 / nominal_m4. 단위(% / decimal) 미확인 | compute_headline |
| headline | rf_spot_remaining_annual / rd_spot_remaining_annual | float\|None — 잔여만기 spot, basis annual_eff. 단위 미확인 | compute_headline |
| headline | candidates | list — HEADLINE_DEFS 진단표(AUDITOR_QA C44). 항목 키 미확인 | compute_headline |
| headline | reported_rf / reported_rd | float\|None — `provenance.instrument.reported_headline.rf_pct / rd_pct` 복사 | compute_headline |
| headline | match_ok | bool\|None — ROUND_HALF_UP·HEADLINE_ROUND_DIGITS 자리 비교(사실만). reported 둘 다 None 이면 None; reported 가 있는데 None 이면 엣지 헤드라인미비교 → fail; False → HEADLINE_MISMATCH | compute_headline |
| headline | rating_applied / block_applied | str\|None — 헤드라인에 적용한 등급·블록 | compute_headline |
| sanity | fail / approval_required / warn | list[flag] ×3 — flag = {severity, code, curve, value, threshold, detail}(`input_stage_flags()` 항목은 detail 없음). 심각도 코드 집계의 유일 지점(GRAPH_SPEC §5) | sanity_check |
| export | dir | str\|None — `evidence/<key>/` | export_evidence |
| export | files | list[dict] — 생성 파일 목록(EVIDENCE_FILES 01~12 + README_conventions.md + xlsx, GRAPH_SPEC §10). 확인된 키는 `path`(`export_evidence` 가 checklist 파일 존재 검사에 읽음)뿐, 나머지 미확인 | export_evidence |
| export | errors | list[str] — 비어 있지 않으면 쓰기오류 → fail | export_evidence |
| export | warnings | list[str] — XLSX_SKIPPED(XLSX_REQUIRED=False 로 바꾼 경우에만) 등, sanity_check 이후 발생하므로 export 소속 | export_evidence |
| export | cell_map | dict[item → "<file>!<sheet\|->!<range\|json_path>"] — Q1 위치표(EVIDENCE_REQUIRED_ITEMS 전항목) | export_evidence |
| export | checklist_detail | dict[item → {location, exists}] — 위치 문자열 형식·파일 존재 검사 결과 | export_evidence |
| export | checklist | dict[item → bool] | export_evidence |
| export | checklist_all_present | bool — False → 증빙불완전 → fail | export_evidence |
| export | conventions_statement | str\|None — CONVENTION_REASONS 로 만든 관례 선언문(자유 텍스트 금지) | export_evidence |
| export | xlsx_written / xlsx_path | bool / str\|None — xlsx 통합문서 생성 여부·경로(XLSX_REQUIRED=True 인데 False → 엣지 xlsx누락 → fail; 템플릿 XLSX_TEMPLATE, docs/XLSX_TEMPLATE.md) | export_evidence |
| result | status | "done"\|"failed"\|None | done / fail |
| result | fail_node / fail_edge | str\|None — `run.path[-1]` 의 from·조건이름 | fail |
| result | fail_code | str\|None — `EDGE_CODES[(fail_node, fail_edge)]`(§5.1) | fail |
| result | fail_reason | str\|None — `"<node>:<edge>"` | fail |
| result | fail_detail | dict\|None — §5.2 | fail |
| result | approved_state_path / approved_state_sha256 | str\|None / sha256\|None — approved_state.json 경로(base_dir 상대)·해시. `snapshot.save_terminal` 이 `done` 직후 기록(러너 몫, 노드 아님) | done → runner |
| result | next_step_interface | dict\|None — 2단계 인터페이스, 값 복사가 아닌 경로 참조(§5.3, GRAPH_SPEC §9) | done |

## 2. `run` 접두사 상세

### 2.1 `run.status` 값과 기록 주체

| 값 | 기록 주체 | 시점 |
|---|---|---|
| "running" | `new_state()` 초기값, `run()` | 처음 시작·재개 모두 첫 노드 실행 전에 `run()` 이 기록 |
| "paused" | `wait_for_human` 노드 함수 | `paused_at_node`·`paused_at` 과 함께 |
| "done" | `done` 노드 함수 | `result.status = "done"` 과 함께 |
| "failed" | `fail` 노드 함수 | `result.status = "failed"` 과 함께 |

종단 노드(`TERMINAL_NODES` = done, fail, wait_for_human)의 함수가 실행된 직후 `run()` 은 반환한다. 승인 노드가 직접 status 를 바꾸지는 않는다.

### 2.2 `run.path` 항목

- 항목 = `(from, 조건이름, to, ts_utc, resume_n)` 튜플. `run()` 이 EDGES 를 위→아래로 훑어 첫 일치 엣지를 고른 직후 append 한다. `ts_utc` 는 `_now()`, `resume_n` 은 그 시점의 `run.resume_n`.
- 스냅샷 저장 → `load_state()` 후에는 튜플이 리스트로 바뀌지만 정규 JSON 이 같으므로 해시·비교에 영향이 없다.
- RUN_PATH 시트 열은 XLSX_COLUMNS["RUN_PATH"](seq, from, condition, to, ts_utc, resume_n)이며 뒤 5열이 `run.path` 항목과 1:1 이다. `seq` 의 정의(리스트 index 인지 1 기반 순번인지)는 코드·GRAPH_SPEC §10·AUDITOR_QA 에 없다 — 미확인(증빙 구현 시 확정).
- 승인 노드에 `대기` 로 도달한 항목과 재개 후 같은 노드에서 EDGES 를 재평가한 항목(`승인`·`거절`·변조 감지 등)이 모두 남는다 — 지나온 경로가 그대로 감사조서다(GRAPH_SPEC §8).

### 2.3 `run.resume_n`

- `new_state()` 0. `run(state, C, start=node)` 는 `start ∈ HUMAN_NODES` 이고 `start == run.paused_at_node` 임을 검증(아니면 ValueError)한 뒤 +1 하고 그 노드부터 EDGES 를 재평가한다. 계산 노드는 재실행되지 않는다.
- `set_decision()` 이 `history` 항목에 적는 `resume_n` 은 `run.resume_n + 1`(그 결정을 적용할 재개 회차)이다.

### 2.4 `run.profile`

- `new_state(C)` 가 `C.PROFILE_NAME` 을 복사한다. `Constants.with_profile(name)` 은 `items()` 전체 복사 + `PROFILES[name]` 오버라이드 + `PROFILE_NAME = name` 인 클래스를 만들며, PROFILE_NAME 이 지문에 포함된다.
- 재개는 `C = Constants.with_profile(state.run.profile)` 로 복원해 호출한다. 처음 시작(`start=None`)에서 `C.fingerprint() != run.constants_fingerprint` 면 ValueError(다른 프로필로 만든 state).

### 2.5 `run.constants_fingerprint` (결정적 직렬화)

- `Constants.fingerprint()` = `sha256(canonical_json(Constants.items()))`. `items()` = 대문자 속성 전부(상속 포함).
- `canonical_json(obj)` = `json.dumps(obj, sort_keys=True, default=_canon, ensure_ascii=False, separators=(",", ":"))`. `_canon`: set/frozenset → `sorted(repr(x))` 리스트, 그 밖의 비직렬화 객체 → `repr`. 프로세스·PYTHONHASHSEED 무관(graph_check 가 서브프로세스로 검사).
- 승인 노드의 엣지 `상수변경감지` 는 decision 이 있을 때 `C.fingerprint()` 와 재비교한다 → CONSTANTS_CHANGED.

## 3. 스냅샷·해시

### 3.1 `CALC_PREFIXES`

`("input", "provenance", "labels", "rows", "grid", "interp", "bootstrap", "par_check", "conv", "tree", "fwd", "fwd_spot_check", "sensitivity", "headline", "sanity")` — 15개, 계산·판정 접두사 전부. `run`·`approval_*`·`export`·`result` 는 제외. 재개 후 CALC_PREFIXES 해시가 바이트 동일해야 하며(graph_check `dynamic_checks`), 같은 입력 두 번 → 같은 해시(`tests/CLAUDE.md` 결정성).

### 3.2 `SNAPSHOT_SCOPE` (승인 노드별 해시 범위)

| 노드 | 범위 |
|---|---|
| approve_input | `("input", "provenance", "labels")` |
| approve_exception | `CALC_PREFIXES + ("approval_input",)` |
| approve_curve | `CALC_PREFIXES + ("approval_input", "approval_exception")` |

자기 `approval_*` 는 제외한다(`set_decision()` 이 스냅샷 뒤에 쓰므로). 이전 승인 기록을 포함하므로 앞선 승인의 편집도 `계산상태변조감지` 가 잡는다.

### 3.3 `hash_of(state, prefixes)` (정규 JSON 왕복)

```
payload = json.loads(canonical_json({p: state[p] for p in prefixes}))
return sha256(canonical_json(payload).encode("utf-8")).hexdigest()
```

JSON 왕복으로 NS/dict·tuple/list 차이를 없애므로 메모리 state 와 재적재한 스냅샷의 해시가 같다. 사용처: 승인 노드 함수(`snapshot_sha256`), 엣지 `입력변조감지`(INPUT_TAMPERED)·`계산상태변조감지`(STATE_TAMPERED), graph_check 재개·결정성 검사.

### 3.4 `load_state(obj)`

스냅샷 JSON(dict) → NS 재귀 변환: dict → `NS`, list → list(원소 재귀), 그 외 값은 그대로. `run.path` 항목은 리스트로 남는다. CLI `resume` 가 스냅샷을 읽어 쓴다(`load_state()` → `with_profile(run.profile)` → `set_decision()` → `run(start=paused_at_node)`).

### 3.5 스냅샷·상태 파일 경로 규칙 (GRAPH_SPEC §6·§10)

파일 쓰기는 `graph/snapshot.py`(스냅샷 저장/로드, `PAUSE_EXIT_CODE=3`)와 그것을 부르는 `app/runner.py`(CLI·서버 공용) 몫이며 노드는 파일을 만들지 않는다(예외: `export_evidence` 는 증빙 번들을 쓴다).

- key = `<valuation_date>__<curve_set_id>`
- 정지 스냅샷: `state/<key>/snapshot__<node>__<n>.json`, 저장 후 exit code 3. `<n>` = 그 노드의 정지 회차(같은 노드에서 다시 멈추면 2, 3 …; `snapshot.save_snapshot` 이 폴더의 기존 파일 수로 정한다).
- 승인 완료 state: `approved_state.json`(`done`, 키 = key) + 사이드카 `approved_state.json.sha256`. 해시 원상 = 파일 바이트 그대로(파일 안의 `result.approved_state_sha256` 는 null); 메모리 state·API 응답에는 해시가 들어 있다. 검증: `sha256(approved_state.json) == 사이드카 값`. 드라이런은 쓰지 않는다.
- 실패 state: `failed_state.json` + 부분 번들(`fail`).
- 증빙 번들: `evidence/<key>/`(`export.dir`).
- 스냅샷·승인 state·증빙은 커밋 제외(.gitignore)이되 삭제 금지(감사 증빙).

## 4. `approval_*` 접두사 상세

### 4.1 `flags_seen` 채우기 (승인 노드 함수 `_human(kind)`, `requested_at` 이 None 일 때 한 번만)

| 노드 | flags_seen | 비고 |
|---|---|---|
| approve_input | `input_stage_flags(s, C)` | 순수 함수. `sanity_check` 도 같은 함수를 호출한다(판정 규칙 한 곳). 코드: DATE_LAG(APPROVAL_REQUIRED, 0 < lag ≤ CURVE_DATE_MAX_LAG_DAYS), CAPTURE_MISSING(APPROVAL_REQUIRED, PROVENANCE_APPROVAL_FIELDS 결측마다 1건), ZERO_VALUE_CELL(WARN), LLM_PARSER_USED(WARN), UNPARSED_ROWS(WARN) |
| approve_exception | `list(sanity.approval_required)` | APPROVAL_REQUIRED 만 |
| approve_curve | `list(sanity.approval_required) + list(sanity.warn)` | APPROVAL_REQUIRED + WARN 전부 |

flag 항목 구조는 `sanity.*` 와 같다(§1 sanity 행). 같은 함수·같은 시점에 `snapshot_sha256 = hash_of(s, SNAPSHOT_SCOPE[node])` 와 `requested_at = _now()` 도 기록한다.

### 4.2 ack 규칙 (단위 = 코드)

- ack 단위는 **코드**(커브 무관). `set_decision(..., acknowledged_codes)` 는 `{f["code"] for f in flags_seen}` 밖의 코드가 하나라도 있으면 ValueError 를 낸다.
- `approve_exception` 의 엣지 `미확인코드잔존` 은 `decision == "approved"` 이고 `{code ∈ sanity.approval_required} − acknowledged_codes` 가 비어 있지 않으면 wait_for_human 으로 되돌린다(같은 노드에서 다시 정지, `requested_at`·`snapshot_sha256` 은 멱등이라 유지). 재정지 후 다시 `set_decision()` 할 수 있고 `history` 에 누적된다.
- approve_input·approve_curve 는 ack 를 검증만 하고(flags_seen ⊇), 라우팅 조건에는 쓰지 않는다.

### 4.3 `set_decision(state, kind, decision, approver, comment, acknowledged_codes)` 전제 조건 (위반 = ValueError)

`kind ∈ {input, exception, curve}`, `decision ∈ {approved, rejected}`, `approver` 비어 있지 않음, `requested_at`·`snapshot_sha256` 존재(요청 전 금지), `run.status == "paused"` 이고 `run.paused_at_node == "approve_<kind>"`(정지 중인 바로 그 노드), ack ⊆ flags_seen 코드. 기록: `decision, approver, timestamp(_now()), comment, acknowledged_codes(list)` + `history.append({decision, approver, timestamp, comment, acknowledged_codes, snapshot_sha256, resume_n: run.resume_n + 1})`.

### 4.4 엣지 `결정선행` (`_pre(kind)`)

`decision`·`timestamp` 가 있고 (`requested_at` 이 없거나 `timestamp < requested_at`) → fail(DECISION_BEFORE_REQUEST). 요청 시각보다 앞선 결정이 스냅샷에 들어 있는 외부 편집을 잡는다. 승인 노드 엣지 순서는 `HUMAN_EDGE_ORDER`(GRAPH_SPEC §6).

## 5. `result` 구조

### 5.1 `result.fail_code`

`EDGE_CODES.get((fail_node, fail_edge))` — GRAPH_SPEC §2 표의 '코드' 열. `sanity_check` 의 `FAIL플래그존재` 는 SANITY_FAIL 이고 세부 코드(INTERP_MISMATCH)는 `sanity.fail` 에 남는다.

### 5.2 `result.fail_detail`

`{node, edge, code}`; `fail_node ∈ HUMAN_NODES` 이면 `approval_<kind>` 에서 `approver, comment, timestamp` 를 더한다(거절·변조 감지 시 승인자 추적). `fail_reason = "<node>:<edge>"`.

### 5.3 `result.next_step_interface` (`done`)

```
{ "rf_spot_cont": "tree.spot_cont_on_grid.RF", "rd_spot_cont": "tree.spot_cont_on_grid.RD",
  "rf_fwd_cont":  "fwd.cont_on_grid.RF",       "rd_fwd_cont":  "fwd.cont_on_grid.RD",
  "rf_df_step":   "fwd.df_step.RF",            "rd_df_step":   "fwd.df_step.RD",
  "event_times":  "grid.tree.event_times",
  "spot_lookup":  { "method": "interp.method", "space": "interp.space_grid", "basis": <basis> },
  "node_discount_conv": "fwd.node_discount_conv",
  "profile": run.profile }
```

값 복사가 아닌 **경로 참조** 이며 `basis` 만 값이다: `interp.space_grid ∈ {log_df, spot_continuous}` 이면 "continuous", 아니면 "annual_eff". 소비 측(2단계 트리/BDT/혼합이자율)은 basis 라벨과 할인 규약을 검사한다(GRAPH_SPEC §9). 저장 → `load_state()` 후에도 동일해야 한다(graph_check).

## 6. 버전 이력

- 현재 판 = `Constants.STATE_SCHEMA_VERSION` 1.1.0(`export_edges_json()` 의 `schema_version`). 이 문서는 `new_state()` 전체 JSON 덤프를 기준으로 작성했다(§1).
- v1.0.0 → v1.1.0 의 필드 추가·변경 목록: v1.0.0 STATE_SCHEMA 원본이 저장소·백업·다른 문서 어디에도 남아 있지 않아(이 폴더는 아직 git 저장소가 아님 — 열린 결정) 대조 불가 — **미확인**. 이전 판과의 차이를 적으려면 원본 파일이 필요하다.
- 이 판의 표기 규칙: sanity flag 항목에 `severity` 포함; `approval_*` 세 접두사는 구조가 같아 한 블록으로 기재; 채우는 노드 열에 `run()` / `set_decision()` / runner·CLI(미구현) 를 구분; 코드·fixture·타 문서에서 확인되지 않는 하위 구조 키는 "미확인" 으로 남긴다.
