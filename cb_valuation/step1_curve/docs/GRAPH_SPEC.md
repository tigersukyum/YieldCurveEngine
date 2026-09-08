# GRAPH_SPEC — 1단계 이자율 커브 그래프 (자동 생성: graph/export_spec.py ← graph/step1_graph.py + graph_check.SCENARIOS)

노드 22개 · 엣지 69개 · 승인 노드 3개 · 종단 3개 · 게이트 8개 · 시나리오 55개 · 상수 fingerprint `1c62017129a6…` · spec `26146e2a9624…`(스키마 1.1.0; graph_check 가 spec 다이제스트로 이 문서의 신선도를 검사)

흐름의 유일한 정의는 `graph/step1_graph.py` 의 `EDGES` 배열이다. 이 문서는 그 배열을 사람이 읽기 좋게 펼친 것이며, 불일치가 있으면 코드가 우선한다(`python cb_valuation/step1_curve/graph/export_spec.py` 로 재생성). `python cb_valuation/step1_curve/graph/graph_check.py` 가 불변식·두 갈래 시나리오·노드 쓰기 추적·상수 지문 결정성을 검사한다.

## 1. 노드 (id · 한국어 이름 · 쓰는 접두사 · 알고리즘 요약)

| # | id | 이름 | 쓰는 state 접두사 | 알고리즘 요약(출처: FORMULA_REFERENCE.md) |
|---|---|---|---|---|
| 0 | `load_matrix` | 매트릭스 적재 | `input` | input.*: 원문 보존, sha256, 헤더 셀 단위 비교(TENOR_LABELS), rows 항목 {row_index, label_raw, block, ytm_pct{tenor→float\|None}} (% 원문 유지; ×PCT_TO_DEC 는 select_rows), '-'→None(0 금지), zero_value_cells=[(row_index, tenor_label)] (ZERO_VALUE_CELL 후보), parse_errors. |
| 1 | `record_provenance` | 출처 기록 | `provenance` | provenance.*: data/raw 사본, date_lag_days=(valuation−curve).days, 행 캡처(Q12), 등급 캡처(Q13), instrument, method_choice(사용자가 고른 프로필·chosen_by; interp_method/space 는 C 에서 복사), PROVENANCE_REQUIRED_FIELDS 완전성. |
| 2 | `interpret_labels` | 행 라벨 해석(AI 허용) | `labels` | labels.*: LABEL_GRAMMAR 정규식(기본); parsed 항목 {row_index, kind, rating, block, parser}, rf/rd_candidates 는 parsed 부분집합, unparsed_rows=[row_index]. AI_ENABLED 시 미매칭 행 라벨 문자열만 LLM 에 제안 요청 → 재검증 통과 시 parser='llm'. 숫자 필드 쓰기 금지. |
| 3 | `approve_input` | 입력 승인(필수) | `approval_input` | approval_input.requested_at·snapshot_sha256·flags_seen 만 처음 한 번 기록(멱등). 결정 필드는 set_decision() 전용. |
| 4 | `select_rows` | 행 선택 | `rows` | rows.*: RF/RD 행 = provenance.row_choice(사용자 드롭다운 선택; 앱 기본) 또는 상품 정보(등급+BLOCK_OF_ISSUANCE, BLOCK_FALLBACK 대체 시 사실 기록), 전기 등급·블록 일관성, ytm_pct×PCT_TO_DEC → ytm RateVector(basis nominal_m{RF_FREQ}/nominal_m{RD_FREQ} ∈ BASIS), knot_tenors=C.knot_tenors(curve), missing_knots. |
| 5 | `build_grid` | 격자 생성 | `grid` | grid.*: knots(≤horizon), boot_times(1/m 격자), 산출 격자 = provenance.grid_settings(step∈STEP_MODES, horizon_years=T → N=T/dt; 앱 기본) 또는 상품 만기(TREE_GRID·DAYCOUNT), remaining_years=T, maturity_years(만기일 있을 때만), tree(N,T,dt,event_times). |
| 6 | `interpolate` | 보간 | `interp` | interp.*: method(트리 격자용 INTERP_METHOD)·method_pre(이표격자용 INTERP_METHOD_PRE) 기록, 모드 A 면 이표격자 YTM(ytm_on_coupon_grid) → c_n(COUPON_CONV, par_coupon_on_grid), knot 왕복 검사, 외삽 사용 기록. |
| 7 | `bootstrap` | 부트스트랩(RF·RD) | `bootstrap` | bootstrap.*: 모드 A DF_n=(1−c_nΣDF)/(1+c_n) (BOOT!H/I 동치) / 모드 B knot brent + 중간 이표일 보간(+Gauss-Seidel), df_valid, solver_log. |
| 8 | `verify_par` | 파 검증(핵심 게이트) | `par_check` | par_check.*: 모든 만기 Σ c·DF + DF_n − 목표가격 (RF/RD), max_abs_err, 미사용 knot 잔차 INFO. |
| 9 | `convert_compounding` | 복리 변환 | `conv` | conv.*: annual=expm1(m·log1p(s)), cont=m·log1p(s) ; 왕복 검사 ; basis annual_eff/continuous (§3.7.4.4 구조적 차단). |
| 10 | `map_tree_grid` | 트리 격자 매핑 | `tree` | tree.*: 동일 보간 함수(interp.method/space_grid)로 spot→트리 격자, DF=exp(−r_c t), 유한·범위(DF_RANGE)·단조(TOL_DF_MONOTONE), 격자 보간체의 마디 왕복 오차(knot_roundtrip_max_err), 외삽 스텝 사실 기록(판정 없음), 실제 사용한 method/space(보간체 객체에서) 기록, ytm_on_grid·spot_annual_interp_on_grid(표시용: INTERP_METHOD_PRE YTM 보간, 연복리 현물 선형보간 = 검토자 row11/row12). |
| 11 | `compute_forward` | 선도금리 산출 | `fwd` | fwd.*: f_i=(lnDF_{i−1}−lnDF_i)/dt_i (BM C-FWD), df_step = exp(−f dt)[③] 또는 1/(1+F)[① NODE_DISCOUNT_CONV=1_discrete_fwd], df_step_alt = 다른 쪽(③ 모드에서는 XL BM F열 (1+f)^(−dt)), F_i=expm1(f dt), 연환산, spot_per_step, growth_step=1+F, growth_cum_prev=Π_{j<k}(1+F_j), df_backward=Π_{j≥k}df_step_j, 부트스트랩 격자 선도(boot_fwd_pp/annual), negative_count, max_jump_bp(BP_PER_UNIT), 테너간 선도표(Q10-1). |
| 12 | `verify_fwd_spot` | 선도-현물 정합(Q11) | `fwd_spot_check` | fwd_spot_check.*: \|Σ_{k≤i}(−f_k dt_k) − ln DF_spot(t_i)\| 로그 공간 게이트 + ΠDF−DF 절대차 + Q11 예시. |
| 13 | `run_sensitivity` | 민감도 분석 | `sensitivity` | sensitivity.*: (method×space) + FREQ_SENSITIVITY_SET 변형을 순수 함수로 재실행, DF 상대차표(주 커브 불변) ; EXCEL_REF 면 excel_recon. |
| 14 | `compute_headline` | 헤드라인 산출 | `headline` | headline.*: HEADLINE_RULE 잔여만기(grid.maturity_years) YTM(RF/RD), 후보 진단표, reported_*=instrument.reported_headline 복사, ROUND_HALF_UP·HEADLINE_ROUND_DIGITS 자리 비교 → match_ok(True/False; reported 없으면 None). 만기일 없는 커브 전용 실행에서는 후보 없음·None. |
| 15 | `sanity_check` | 건전성 점검·집계 | `sanity` | sanity.*: 심각도 코드 집계의 유일 지점. 전용 엣지가 처리한 FAIL 은 재평가하지 않는다. sanity.fail = 다중 노드 교차 규칙(INTERP_MISMATCH). |
| 16 | `approve_exception` | 예외 승인(조건부) | `approval_exception` | approval_exception.requested_at·snapshot_sha256·flags_seen 만 처음 한 번 기록(멱등). 결정 필드는 set_decision() 전용. |
| 17 | `approve_curve` | 최종 커브 승인(필수) | `approval_curve` | approval_curve.requested_at·snapshot_sha256·flags_seen 만 처음 한 번 기록(멱등). 결정 필드는 set_decision() 전용. |
| 18 | `export_evidence` | 증빙 내보내기 | `export` | export.*: EVIDENCE_FILES 01~12 + README_conventions.md(CONVENTION_REASONS·PROFILE_DESCRIPTIONS·상수 전부) + xlsx(XLSX_TEMPLATE: XLSX_SHEETS, Rf_dc/Rd_dc 는 XLSX_DC_BLOCKS·XLSX_DC_STYLE, 나머지 XLSX_COLUMNS; xlsx_written/xlsx_path) + checklist(EVIDENCE_REQUIRED_ITEMS 전항목 위치 유효성). XLSX_REQUIRED 인데 미생성 → 엣지 xlsx누락(FAIL); XLSX_REQUIRED=False 일 때만 export.warnings XLSX_SKIPPED. |
| 19 | `done` | 완료 | `result, run` | result.*: approved_state.json 저장(키 valuation_date__curve_set_id), next_step_interface(경로 참조·basis 선언·할인 규약). |
| 20 | `fail` | 실패 | `result, run` | result.*: 실패 노드·엣지·코드(EDGE_CODES)·사유·승인자/코멘트(승인 노드 거절 시) 기록, failed_state.json + 부분 번들. done 으로 가는 엣지 없음. |
| 21 | `wait_for_human` | 사람 대기(정지) | `run` | run.paused_*: 멈춘 자리 기록 + 스냅샷 저장(state/<key>/snapshot__<node>__<n>.json) + exit 3. 재개는 cli resume → set_decision → run(start=paused_at_node). |

## 2. EDGES (실행 순서 — 라우터는 위→아래 첫 일치; 코드 열 = result.fail_code)

| # | 현재 노드 | 조건 이름 | 조건 함수 (s=state, C=Constants) | 다음 노드 | 코드 |
|---|---|---|---|---|---|
| 0 | `load_matrix` | 헤더불일치 | `not s.input.header_ok` | `fail` | HEADER_MISMATCH |
| 1 | `load_matrix` | 파싱오류 | `len(s.input.parse_errors) > 0` | `fail` | PARSE_ERROR |
| 2 | `load_matrix` | 행없음 | `s.input.n_rows == 0` | `fail` | MATRIX_EMPTY |
| 3 | `load_matrix` | 적재완료 | `ALWAYS` | `record_provenance` |  |
| 4 | `record_provenance` | 출처불완전 | `not s.provenance.complete` | `fail` | PROVENANCE_INCOMPLETE |
| 5 | `record_provenance` | 프로필불일치 | `s.provenance.method_choice.profile != C.PROFILE_NAME` | `fail` | PROFILE_MISMATCH |
| 6 | `record_provenance` | 기준일역전_또는_지연초과 | `not _fin(s.provenance.date_lag_days) or s.provenance.date_lag_days < 0 or s.provenance.date_lag_days > C.CURVE_DATE_MAX_LAG_DAYS` | `fail` | DATE_LAG_OUT_OF_RANGE |
| 7 | `record_provenance` | 출처기록완료 | `ALWAYS` | `interpret_labels` |  |
| 8 | `interpret_labels` | RF후보없음 | `len(s.labels.rf_candidates) == 0` | `fail` | NO_RF_CANDIDATE |
| 9 | `interpret_labels` | 라벨해석완료 | `ALWAYS` | `approve_input` |  |
| 10 | `approve_input` | 거절 | `s.approval_input.decision == "rejected"` | `fail` | APPROVAL_REJECTED |
| 11 | `approve_input` | 결정선행 | `s[f"approval_{kind}"].decision is not None and s[f"approval_{kind}"].timestamp is not None and \ (s[f"approval_{kind}"].requested_at is None or s[f"approval_{kind}"].timestamp < s[f"approval_{kind}"].requested_at)` | `fail` | DECISION_BEFORE_REQUEST |
| 12 | `approve_input` | 상수변경감지 | `s.approval_input.decision is not None and C.fingerprint() != s.run.constants_fingerprint` | `fail` | CONSTANTS_CHANGED |
| 13 | `approve_input` | 입력변조감지 | `s.approval_input.decision is not None and hash_of(s, C.SNAPSHOT_SCOPE["approve_input"]) != s.approval_input.snapshot_sha256` | `fail` | INPUT_TAMPERED |
| 14 | `approve_input` | 승인 | `s.approval_input.decision == "approved"` | `select_rows` |  |
| 15 | `approve_input` | 대기 | `ALWAYS` | `wait_for_human` |  |
| 16 | `select_rows` | RF행없음 | `s.rows.rf is None` | `fail` | ROW_MISSING_RF |
| 17 | `select_rows` | RD행없음_대체불가 | `s.rows.rd is None` | `fail` | ROW_MISSING_RD |
| 18 | `select_rows` | knot부족 | `min(s.rows.usable_knot_count[c] for c in C.CURVE_IDS) < C.MIN_KNOTS` | `fail` | TOO_FEW_KNOTS |
| 19 | `select_rows` | 행선택완료 | `ALWAYS` | `build_grid` |  |
| 20 | `build_grid` | 잔여만기비유한 | `not (_fin(s.grid.remaining_years) and _fin(s.grid.horizon_years))` | `fail` | MATURITY_NONFINITE |
| 21 | `build_grid` | 만기초과 | `s.grid.remaining_years > s.grid.horizon_years + C.EPS_T` | `fail` | MATURITY_GT_HORIZON |
| 22 | `build_grid` | 격자완료 | `ALWAYS` | `interpolate` |  |
| 23 | `interpolate` | 보간비유한 | `not (s.interp.all_finite and _fin(s.interp.knot_roundtrip_max_err))` | `fail` | INTERP_NONFINITE |
| 24 | `interpolate` | knot왕복불일치 | `s.interp.knot_roundtrip_max_err > C.TOL_KNOT_ROUNDTRIP` | `fail` | KNOT_ROUNDTRIP |
| 25 | `interpolate` | 보간완료 | `ALWAYS` | `bootstrap` |  |
| 26 | `bootstrap` | DF무효_비유한 | `any(s.bootstrap.status[c] == "FAIL_DF_INVALID" or not s.bootstrap.df_valid[c] for c in C.CURVE_IDS)` | `fail` | BOOT_DF_INVALID |
| 27 | `bootstrap` | 분모비양수 | `any(s.bootstrap.status[c] == "FAIL_DENOMINATOR" for c in C.CURVE_IDS)` | `fail` | DENOM_NONPOS |
| 28 | `bootstrap` | 근찾기실패_비수렴 | `any(s.bootstrap.status[c] in ("FAIL_BRACKET", "FAIL_NO_CONVERGENCE") for c in C.CURVE_IDS)` | `fail` | ROOTFIND_FAIL |
| 29 | `bootstrap` | 부트스트랩완료 | `ALWAYS` | `verify_par` |  |
| 30 | `verify_par` | 파잔차비유한 | `not (s.par_check.all_finite and _fin(s.par_check.max_abs_err))` | `fail` | PAR_NONFINITE |
| 31 | `verify_par` | 파검증실패 | `s.par_check.max_abs_err > C.TOL_PAR_FAIL` | `fail` | PAR_RESIDUAL |
| 32 | `verify_par` | 파검증통과 | `ALWAYS` | `convert_compounding` |  |
| 33 | `convert_compounding` | 변환비유한 | `not (s.conv.all_finite and _fin(s.conv.roundtrip_max_err))` | `fail` | COMP_NONFINITE |
| 34 | `convert_compounding` | 왕복변환불일치 | `s.conv.roundtrip_max_err > C.TOL_ROUNDTRIP_COMP` | `fail` | COMP_ROUNDTRIP |
| 35 | `convert_compounding` | 변환완료 | `ALWAYS` | `map_tree_grid` |  |
| 36 | `map_tree_grid` | 트리DF비유한 | `not (s.tree.df_finite and _fin(s.tree.knot_roundtrip_max_err))` | `fail` | TREE_DF_NONFINITE |
| 37 | `map_tree_grid` | 격자knot왕복불일치 | `s.tree.knot_roundtrip_max_err > C.TOL_KNOT_ROUNDTRIP` | `fail` | TREE_KNOT_ROUNDTRIP |
| 38 | `map_tree_grid` | 엑셀제로외삽_정상모드 | `s.tree.excel_zero_used and not C.EXCEL_REPLICATE` | `fail` | EXCEL_ZERO_OUTSIDE_REPLICATE |
| 39 | `map_tree_grid` | DF범위_또는_단조위반 | `not (s.tree.df_range_ok and s.tree.df_monotone_ok)` | `fail` | DF_RANGE_OR_MONOTONE |
| 40 | `map_tree_grid` | 격자매핑완료 | `ALWAYS` | `compute_forward` |  |
| 41 | `compute_forward` | 선도비유한 | `not s.fwd.all_finite` | `fail` | FWD_NONFINITE |
| 42 | `compute_forward` | 선도완료 | `ALWAYS` | `verify_fwd_spot` |  |
| 43 | `verify_fwd_spot` | 정합잔차비유한 | `not (s.fwd_spot_check.all_finite and _fin(s.fwd_spot_check.max_abs_err_log))` | `fail` | FWD_SPOT_NONFINITE |
| 44 | `verify_fwd_spot` | 정합실패 | `s.fwd_spot_check.max_abs_err_log > C.TOL_FWD_SPOT_FAIL` | `fail` | FWD_SPOT_MISMATCH |
| 45 | `verify_fwd_spot` | 정합통과 | `ALWAYS` | `run_sensitivity` |  |
| 46 | `run_sensitivity` | 민감도완료 | `ALWAYS` | `compute_headline` |  |
| 47 | `compute_headline` | 헤드라인미비교 | `(s.headline.reported_rf is not None or s.headline.reported_rd is not None) and s.headline.match_ok is None` | `fail` | HEADLINE_NOT_COMPARED |
| 48 | `compute_headline` | 헤드라인완료 | `ALWAYS` | `sanity_check` |  |
| 49 | `sanity_check` | FAIL플래그존재 | `len(s.sanity.fail) > 0` | `fail` | SANITY_FAIL |
| 50 | `sanity_check` | 승인필요플래그존재 | `len(s.sanity.approval_required) > 0` | `approve_exception` |  |
| 51 | `sanity_check` | 플래그없음 | `ALWAYS` | `approve_curve` |  |
| 52 | `approve_exception` | 거절 | `s.approval_exception.decision == "rejected"` | `fail` | APPROVAL_REJECTED |
| 53 | `approve_exception` | 결정선행 | `s[f"approval_{kind}"].decision is not None and s[f"approval_{kind}"].timestamp is not None and \ (s[f"approval_{kind}"].requested_at is None or s[f"approval_{kind}"].timestamp < s[f"approval_{kind}"].requested_at)` | `fail` | DECISION_BEFORE_REQUEST |
| 54 | `approve_exception` | 상수변경감지 | `s.approval_exception.decision is not None and C.fingerprint() != s.run.constants_fingerprint` | `fail` | CONSTANTS_CHANGED |
| 55 | `approve_exception` | 계산상태변조감지 | `s.approval_exception.decision is not None and hash_of(s, C.SNAPSHOT_SCOPE["approve_exception"]) != s.approval_exception.snapshot_sha256` | `fail` | STATE_TAMPERED |
| 56 | `approve_exception` | 미확인코드잔존 | `s.approval_exception.decision == "approved" and bool({f["code"] for f in s.sanity.approval_required} - set(s.approval_exception.acknowledged_codes))` | `wait_for_human` |  |
| 57 | `approve_exception` | 승인 | `s.approval_exception.decision == "approved"` | `approve_curve` |  |
| 58 | `approve_exception` | 대기 | `ALWAYS` | `wait_for_human` |  |
| 59 | `approve_curve` | 거절 | `s.approval_curve.decision == "rejected"` | `fail` | APPROVAL_REJECTED |
| 60 | `approve_curve` | 결정선행 | `s[f"approval_{kind}"].decision is not None and s[f"approval_{kind}"].timestamp is not None and \ (s[f"approval_{kind}"].requested_at is None or s[f"approval_{kind}"].timestamp < s[f"approval_{kind}"].requested_at)` | `fail` | DECISION_BEFORE_REQUEST |
| 61 | `approve_curve` | 상수변경감지 | `s.approval_curve.decision is not None and C.fingerprint() != s.run.constants_fingerprint` | `fail` | CONSTANTS_CHANGED |
| 62 | `approve_curve` | 계산상태변조감지 | `s.approval_curve.decision is not None and hash_of(s, C.SNAPSHOT_SCOPE["approve_curve"]) != s.approval_curve.snapshot_sha256` | `fail` | STATE_TAMPERED |
| 63 | `approve_curve` | 승인 | `s.approval_curve.decision == "approved"` | `export_evidence` |  |
| 64 | `approve_curve` | 대기 | `ALWAYS` | `wait_for_human` |  |
| 65 | `export_evidence` | 쓰기오류 | `len(s.export.errors) > 0` | `fail` | EXPORT_ERROR |
| 66 | `export_evidence` | xlsx누락 | `C.XLSX_REQUIRED and not s.export.xlsx_written` | `fail` | XLSX_MISSING |
| 67 | `export_evidence` | 증빙불완전 | `not s.export.checklist_all_present` | `fail` | EVIDENCE_INCOMPLETE |
| 68 | `export_evidence` | 내보내기완료 | `ALWAYS` | `done` |  |

## 3. 다이어그램 (mermaid; 승인 노드=스타디움, 종단=이중 사각형)

```mermaid
flowchart TD
  load_matrix[load_matrix<br/>매트릭스 적재]
  record_provenance[record_provenance<br/>출처 기록]
  interpret_labels[interpret_labels<br/>행 라벨 해석(AI 허용)]
  approve_input([approve_input<br/>입력 승인(필수)])
  select_rows[select_rows<br/>행 선택]
  build_grid[build_grid<br/>격자 생성]
  interpolate[interpolate<br/>보간]
  bootstrap[bootstrap<br/>부트스트랩(RF·RD)]
  verify_par[verify_par<br/>파 검증(핵심 게이트)]
  convert_compounding[convert_compounding<br/>복리 변환]
  map_tree_grid[map_tree_grid<br/>트리 격자 매핑]
  compute_forward[compute_forward<br/>선도금리 산출]
  verify_fwd_spot[verify_fwd_spot<br/>선도-현물 정합(Q11)]
  run_sensitivity[run_sensitivity<br/>민감도 분석]
  compute_headline[compute_headline<br/>헤드라인 산출]
  sanity_check[sanity_check<br/>건전성 점검·집계]
  approve_exception([approve_exception<br/>예외 승인(조건부)])
  approve_curve([approve_curve<br/>최종 커브 승인(필수)])
  export_evidence[export_evidence<br/>증빙 내보내기]
  done[[done<br/>완료]]
  fail[[fail<br/>실패]]
  wait_for_human[[wait_for_human<br/>사람 대기(정지)]]
  load_matrix -->|헤더불일치| fail
  load_matrix -->|파싱오류| fail
  load_matrix -->|행없음| fail
  load_matrix -->|적재완료| record_provenance
  record_provenance -->|출처불완전| fail
  record_provenance -->|프로필불일치| fail
  record_provenance -->|기준일역전_또는_지연초과| fail
  record_provenance -->|출처기록완료| interpret_labels
  interpret_labels -->|RF후보없음| fail
  interpret_labels -->|라벨해석완료| approve_input
  approve_input -->|거절| fail
  approve_input -->|결정선행| fail
  approve_input -->|상수변경감지| fail
  approve_input -->|입력변조감지| fail
  approve_input -->|승인| select_rows
  approve_input -->|대기| wait_for_human
  select_rows -->|RF행없음| fail
  select_rows -->|RD행없음_대체불가| fail
  select_rows -->|knot부족| fail
  select_rows -->|행선택완료| build_grid
  build_grid -->|잔여만기비유한| fail
  build_grid -->|만기초과| fail
  build_grid -->|격자완료| interpolate
  interpolate -->|보간비유한| fail
  interpolate -->|knot왕복불일치| fail
  interpolate -->|보간완료| bootstrap
  bootstrap -->|DF무효_비유한| fail
  bootstrap -->|분모비양수| fail
  bootstrap -->|근찾기실패_비수렴| fail
  bootstrap -->|부트스트랩완료| verify_par
  verify_par -->|파잔차비유한| fail
  verify_par -->|파검증실패| fail
  verify_par -->|파검증통과| convert_compounding
  convert_compounding -->|변환비유한| fail
  convert_compounding -->|왕복변환불일치| fail
  convert_compounding -->|변환완료| map_tree_grid
  map_tree_grid -->|트리DF비유한| fail
  map_tree_grid -->|격자knot왕복불일치| fail
  map_tree_grid -->|엑셀제로외삽_정상모드| fail
  map_tree_grid -->|DF범위_또는_단조위반| fail
  map_tree_grid -->|격자매핑완료| compute_forward
  compute_forward -->|선도비유한| fail
  compute_forward -->|선도완료| verify_fwd_spot
  verify_fwd_spot -->|정합잔차비유한| fail
  verify_fwd_spot -->|정합실패| fail
  verify_fwd_spot -->|정합통과| run_sensitivity
  run_sensitivity -->|민감도완료| compute_headline
  compute_headline -->|헤드라인미비교| fail
  compute_headline -->|헤드라인완료| sanity_check
  sanity_check -->|FAIL플래그존재| fail
  sanity_check -->|승인필요플래그존재| approve_exception
  sanity_check -->|플래그없음| approve_curve
  approve_exception -->|거절| fail
  approve_exception -->|결정선행| fail
  approve_exception -->|상수변경감지| fail
  approve_exception -->|계산상태변조감지| fail
  approve_exception -->|미확인코드잔존| wait_for_human
  approve_exception -->|승인| approve_curve
  approve_exception -->|대기| wait_for_human
  approve_curve -->|거절| fail
  approve_curve -->|결정선행| fail
  approve_curve -->|상수변경감지| fail
  approve_curve -->|계산상태변조감지| fail
  approve_curve -->|승인| export_evidence
  approve_curve -->|대기| wait_for_human
  export_evidence -->|쓰기오류| fail
  export_evidence -->|xlsx누락| fail
  export_evidence -->|증빙불완전| fail
  export_evidence -->|내보내기완료| done
```

## 4. 두 갈래 시나리오 (graph_check.SCENARIOS — 문서·프롬프트·fixture E 는 이 표의 id 만 인용)

| id | 설명 | 프로필 | 기대 마지막 엣지 | 기대 status |
|---|---|---|---|---|
| A01 | 정상 입력 → 승인 2곳 → done (EXTRAP_LEFT_FLAT=WARN 기본) | DEFAULT | 내보내기완료 | done |
| A02 | 정상 입력, EXTRAP_LEFT_FLAT_SEVERITY=APPROVAL → approve_exception 경유 후 done | DEFAULT(EXTRAP_LEFT_FLAT=APPROVAL) | 내보내기완료 | done |
| A03 | 결정 없이 approve_input 정지 | DEFAULT | 대기 | paused |
| A04 | PCHIP_TREE 프로필 정상 완주(next_step_interface.space=log_df) | PCHIP_TREE | 내보내기완료 | done |
| E01 | 헤더 불일치 | DEFAULT | 헤더불일치 | failed |
| E02 | 파싱 오류 | DEFAULT | 파싱오류 | failed |
| E03 | 행 0개 | DEFAULT | 행없음 | failed |
| E04 | 출처 불완전(노드 간격 미선택) | DEFAULT | 출처불완전 | failed |
| E05 | curve_date 지연 5일 | DEFAULT | 기준일역전_또는_지연초과 | failed |
| E06 | curve_date 가 평가기준일보다 미래(lag −1) | DEFAULT | 기준일역전_또는_지연초과 | failed |
| E07 | curve_date 지연 1일 → DATE_LAG 승인 후 done | DEFAULT | 내보내기완료 | done |
| E08 | RF 후보 라벨 없음 | DEFAULT | RF후보없음 | failed |
| E09 | 입력 승인 거절 | DEFAULT | 거절 | failed |
| E10 | 입력 승인 결정선행(외부 편집) | DEFAULT | 결정선행 | failed |
| E11 | 입력 승인 후 상수 변경 | DEFAULT | 상수변경감지 | failed |
| E12 | 입력 승인 후 입력 변조 | DEFAULT | 입력변조감지 | failed |
| E13 | RF 행 없음 | DEFAULT | RF행없음 | failed |
| E14 | RD 행 없음·대체 불가 | DEFAULT | RD행없음_대체불가 | failed |
| E15 | knot 부족 | DEFAULT | knot부족 | failed |
| E16 | 잔여만기 미산출(None) | DEFAULT | 잔여만기비유한 | failed |
| E17 | 만기 12Y > horizon | DEFAULT | 만기초과 | failed |
| E18 | 보간 비유한 | DEFAULT | 보간비유한 | failed |
| E19 | knot 왕복 불일치 | DEFAULT | knot왕복불일치 | failed |
| E20 | 부트스트랩 DF 무효 | DEFAULT | DF무효_비유한 | failed |
| E21 | 부트스트랩 분모 ≤ 0 | DEFAULT | 분모비양수 | failed |
| E22 | 근찾기 비수렴 | DEFAULT | 근찾기실패_비수렴 | failed |
| E23 | par 잔차 NaN | DEFAULT | 파잔차비유한 | failed |
| E24 | par 잔차 2×TOL | DEFAULT | 파검증실패 | failed |
| E25 | par 잔차 0.5×TOL 통과 | DEFAULT | 내보내기완료 | done |
| E26 | 복리 변환 비유한 | DEFAULT | 변환비유한 | failed |
| E27 | 복리 왕복 불일치 | DEFAULT | 왕복변환불일치 | failed |
| E28 | 트리 DF 비유한 | DEFAULT | 트리DF비유한 | failed |
| E29 | excel_zero 외삽이 정상 모드에서 발동 | DEFAULT | 엑셀제로외삽_정상모드 | failed |
| E30 | 트리 DF 단조 위반 | DEFAULT | DF범위_또는_단조위반 | failed |
| E31 | 선도 비유한 | DEFAULT | 선도비유한 | failed |
| E32 | 선도-현물 잔차 NaN | DEFAULT | 정합잔차비유한 | failed |
| E33 | 선도-현물 잔차 2×TOL | DEFAULT | 정합실패 | failed |
| E34 | 보고서 헤드라인 있는데 비교 안 됨 | DEFAULT | 헤드라인미비교 | failed |
| E35 | 보간 방법 불일치(트리가 다른 방법 사용) → sanity FAIL | DEFAULT | FAIL플래그존재 | failed |
| E36 | 음의 선도 → approve_exception, 일부 ack → 재정지 | DEFAULT | 미확인코드잔존 | paused |
| E37 | 예외 승인 거절 | DEFAULT | 거절 | failed |
| E38 | 예외 승인 결정선행 | DEFAULT | 결정선행 | failed |
| E39 | 예외 승인 후 상수 변경 | DEFAULT | 상수변경감지 | failed |
| E40 | 예외 승인 후 계산 상태 변조 | DEFAULT | 계산상태변조감지 | failed |
| E41 | 최종 승인 거절 | DEFAULT | 거절 | failed |
| E42 | 최종 승인 결정선행 | DEFAULT | 결정선행 | failed |
| E43 | 최종 승인 후 상수 변경 | DEFAULT | 상수변경감지 | failed |
| E44 | 최종 승인 후 이전 승인 기록 변조 | DEFAULT | 계산상태변조감지 | failed |
| E45 | 증빙 쓰기 오류 | DEFAULT | 쓰기오류 | failed |
| E46 | 증빙 필수 항목 누락(Q11) | DEFAULT | 증빙불완전 | failed |
| E47 | 증빙 위치 문자열 형식 오류 | DEFAULT | 증빙불완전 | failed |
| E48 | 프로필 미선택(method_choice.profile=None) → 출처불완전 | DEFAULT | 출처불완전 | failed |
| E49 | 선택한 프로필 ≠ 실행 상수 프로필 | DEFAULT | 프로필불일치 | failed |
| E50 | xlsx 미생성(XLSX_REQUIRED) | DEFAULT | xlsx누락 | failed |
| E51 | 트리 격자 보간체 knot 왕복 2×TOL | DEFAULT | 격자knot왕복불일치 | failed |

## 5. 심각도 표 (판정 위치 = 전용 엣지 또는 sanity_check 한 곳)

라우터 규칙: (1) 단일 노드로 판정되는 FAIL 은 그 노드의 전용 엣지가 처리하고(§2 표의 코드 열) sanity_check 는 재평가하지 않는다. (2) 다중 노드 교차 규칙(INTERP_MISMATCH)만 `sanity.fail` → `FAIL플래그존재`. (3) APPROVAL_REQUIRED 코드는 sanity_check 만 집계 → approve_exception 정지, 코드별 `--ack` 필수. (4) WARN 은 기록·증빙 인쇄만. (5) 같은 사건이 FAIL·APPROVAL 양쪽이면 FAIL 우선(엣지 순서). (6) 임계 게이트(GATE_NODES)는 [비유한→fail] [초과→fail] [기본→다음]. (7) 임계값은 `Constants` 에만 있고 문서는 상수명만 인용(§11).

| 심각도 | 코드 | 담당 | 비고 |
|---|---|---|---|
| FAIL | §2 표 '코드' 열 전부 | 각 노드 전용 엣지 | `result.fail_code` 에 기록 |
| FAIL | INTERP_MISMATCH (트리 매핑에 쓴 보간 방법/공간 ≠ interp.*) | sanity_check | 다중 노드 교차 규칙 |
| APPROVAL_REQUIRED | DATE_LAG (0<lag≤CURVE_DATE_MAX_LAG_DAYS), CAPTURE_MISSING (PROVENANCE_APPROVAL_FIELDS), NEG_FWD, RD_LT_RF (<RD_MIN_SPREAD), EXTRAP_COUPON_GRID, EXTRAP_LEFT_ORIGIN, EXTRAP_RIGHT_USED, EXTRAP_LEFT_FLAT(EXTRAP_LEFT_FLAT_SEVERITY 가 APPROVAL_REQUIRED 일 때), ROW_FALLBACK, NOTCH_APPLIED, RATING_CHANGED, BLOCK_CHANGED, KNOT_MISSING, HEADLINE_MISMATCH, EXCEL_REPLICATE_ON | sanity_check → approve_exception | DATE_LAG·CAPTURE_MISSING 은 `input_stage_flags()` 로 approve_input.flags_seen 에도 표시 |
| WARN | EXTRAP_LEFT_FLAT(기본), SAWTOOTH (>FWD_JUMP_WARN_BP), PAR_WARN (TOL_PAR_WARN<잔차≤TOL_PAR_FAIL), CROSS_METHOD_DF (>CROSS_METHOD_DF_WARN), FREQ_SENSITIVITY, ZERO_VALUE_CELL, LLM_PARSER_USED, UNPARSED_ROWS, TENOR_DROPPED, UNUSED_KNOT_RESIDUAL, NONMONO_YTM/NONMONO_SPOT(역전 커브 정상; 엔진 이식 후) | sanity_check(기록만) | |
| FAIL | XLSX_MISSING (XLSX_REQUIRED=True 인데 xlsx 미생성) | export_evidence 엣지 `xlsx누락` | 사용자 결정 2026-09-07: xlsx 필수, openpyxl 은 선언 의존성 |
| WARN | XLSX_SKIPPED (XLSX_REQUIRED=False 로 바꾼 경우에만) | export_evidence → `export.warnings` | sanity_check 이후 발생하므로 export 소속 |

## 6. 사람승인 정책 (엣지에 명시된 정지 3곳)

- **프로필 선택(PROFILE_SELECTION=required, 사용자 결정 2026-09-07)**: 보간법·프로필은 실행 시 사용자가 고른다(CLI `--profile` 필수, 화면 선택 목록 = `PROFILES` 키 + `PROFILE_DESCRIPTIONS`). 선택은 `provenance.method_choice{profile, interp_method, interp_space_grid, chosen_by, chosen_at}` 에 기록되고 PROVENANCE_REQUIRED_FIELDS 에 포함되어 미선택이면 `출처불완전`, 실행 상수의 PROFILE_NAME 과 다르면 `프로필불일치` 로 fail 한다. 조용한 기본값은 없다.
- **approve_input (필수, 계산 전)**: 원시 매트릭스 원문·헤더·provenance(평가사·curve_date·valuation_date·lag·파일 해시·다운로드 시각·담당자·행 캡처·등급 캡처·**method_choice**)·라벨 해석·상품/등급/발행형태를 보고 승인. `flags_seen` = `input_stage_flags()` 결과(DATE_LAG·CAPTURE_MISSING·ZERO_VALUE_CELL·LLM_PARSER_USED·UNPARSED_ROWS) — 판정 규칙은 sanity_check 와 같은 함수 한 곳.
- **approve_exception (조건부)**: `sanity.approval_required` 가 비어있지 않을 때만 도달. `--ack CODE` 로 코드마다 확인해야 하며 하나라도 빠지면 `미확인코드잔존` 이 wait_for_human 으로 되돌린다. ack 단위는 코드(커브 무관).
- **approve_curve (필수, 내보내기 전)**: 05/06/07 표·par 잔차·Q11 예시·헤드라인·관례 요약·전체 flag(APPROVAL+WARN, `flags_seen` 에 기록)를 보고 승인.
- 엣지 순서(`Constants.HUMAN_EDGE_ORDER`, graph_check 가 완전 일치 검사): `[거절→fail] [결정선행→fail] [상수변경감지→fail] [변조감지→fail] [(exception만) 미확인코드잔존→wait_for_human] [승인→다음] [대기(ALWAYS)→wait_for_human]`. decision 이 None 이든 예상 밖 값이든 라우터는 반드시 wait_for_human 으로 간다.
- 정지: 승인 노드 함수는 requested_at·snapshot_sha256(=hash_of(SNAPSHOT_SCOPE[node]))·flags_seen 을 처음 한 번만 쓴다(멱등). wait_for_human 이 `run.status='paused'`, `paused_at_node`, `paused_at` 을 쓰고 스냅샷(`state/<valuation_date>__<curve_set_id>/snapshot__<node>__<n>.json`)을 저장한 뒤 exit code 3.
- 결정: `set_decision()` 만 approval_<kind> 의 decision·approver·timestamp·comment·acknowledged_codes 를 쓰고 `history` 에 append 한다. 조건: 승인 요청 이후(requested_at 존재), `run.status=='paused'` 이고 `run.paused_at_node==approve_<kind>`, approver 비어있지 않음, ack ⊆ flags_seen 코드. 위반은 ValueError. 요청 시각보다 앞선 결정이 스냅샷에 들어 있으면 엣지 `결정선행` 이 fail 로 보낸다.
- 재개: `cli resume --snapshot <path> --decision approved|rejected --approver <이름> --comment "<문장>" [--ack CODE ...]` → `C = Constants.with_profile(state.run.profile)` 복원 → `set_decision()` → `run(state, C, start=run.paused_at_node)`. `start` 는 승인 노드이며 `paused_at_node` 와 같아야 하고(아니면 ValueError), 계산 노드는 재실행되지 않으며 CALC_PREFIXES 필드는 바이트 동일해야 한다(graph_check 재개 검사). 재개마다 `run.resume_n` 증가, `run.path` 항목에 시각·회차 기록.
- 변조 감지: `Constants.fingerprint()`(결정적 직렬화, 프로세스 무관) ≠ `run.constants_fingerprint` → `상수변경감지`; `hash_of(SNAPSHOT_SCOPE)` ≠ `snapshot_sha256` → `입력변조감지`/`계산상태변조감지`. SNAPSHOT_SCOPE 는 approve_exception 에 approval_input 을, approve_curve 에 approval_input·approval_exception 을 포함해 이전 승인 기록의 편집도 잡는다.
- 거절: 어느 승인이든 → fail. `result.fail_reason='<node>:거절'`, `result.fail_detail={node, edge, code, approver, comment, timestamp}`, 부분 번들 저장. 재시도는 새 run_id 로 처음부터.
- 기록: 승인자·ISO 시각·코멘트·flags_seen·acknowledged_codes·snapshot_sha256·history → state, 12_approvals.json, APPROVALS 시트, approved_state.json. 스냅샷·승인 state 는 커밋 제외(.gitignore)이되 삭제 금지. 승인의 진입점은 두 곳뿐이며 둘 다 `set_decision()` 을 호출한다: CLI `resume`, 로컬 앱(`app/server.py` `/api/decision` — viewer.html 의 승인 버튼은 승인자·코멘트·ack 를 그대로 보낼 뿐 판단하지 않는다). AI 는 approval_* 접근이 없다.
- 드라이런(`/curve-validate`): 하네스가 approver='dry-run' 으로 입력 승인만 자동 기록하고 approve_exception/approve_curve 정지에서 보고 후 종료한다. approved_state.json 을 쓰지 않는다.

## 7. AI 의 역할 (해석까지)

허용: (a) `interpret_labels` 노드에서 LABEL_GRAMMAR 정규식 미매칭 행의 **라벨 문자열만** LLM 에 정규화 제안 요청(AI_ENABLED=True + API 키가 있을 때만; 페이로드에 숫자가 있으면 assert). 제안은 정규식 재검증을 통과해야 parser='llm' 으로 채택되고 LLM_PARSER_USED WARN 이 남는다. (b) 증빙·화면의 한국어 설명문(state 값을 문자열로 삽입, 숫자 생성 금지).
금지: YTM 값 읽기·요약, spot/DF/forward 계산, par 통과·심각도·헤드라인 판정, 커브 채택, 승인 필드 쓰기. **앱 초안: `io/label_ai.py` 미구현 — `AI_ENABLED=True` 는 러너 사전 게이트와 `interpret_labels` 가 거부한다(정규식 경로만).** 기본 경로는 정규식이며 API 키 없이 fixture A~E 전부 완주해야 한다. 고객 금리표·식별정보는 외부 LLM 으로 보내지 않는다.

## 8. 화면 (그래프·state 다음에 붙인다)

`app/server.py`(표준 라이브러리 HTTP, 127.0.0.1 전용; `start_app.bat` 또는 `python -m cb_valuation.step1_curve.app.server --open`)가 `app/viewer.html`(외부 라이브러리 없음)을 띄운다. 화면은 `/api/graph`(= `export_edges_json()` + 노드 docstring + PROFILE_DESCRIPTIONS)와 `/api/state`(state JSON)만 읽는다. 왼쪽: 입력(프로필 선택 필수·매트릭스·출처·상품) → 결과(선택 행·마디·부트스트랩 표(basis 헤더)·트리 격자·Q11 예시·헤드라인·flag·민감도) → 승인(flags_seen·코드별 ack·승인자·코멘트) → 증빙(파일·체크리스트) → state JSON. 오른쪽: EDGES 그래프(주 사슬 세로, fail 왼쪽, wait_for_human 오른쪽, done 아래)에 현재 노드·정지 노드·지나온 엣지(run.path)를 색으로 강조하고 조건 이름을 라벨로 붙인다. 화면에 흐름 로직 없음 — 버튼은 `/api/run`(입력 → `run()`)과 `/api/decision`(`set_decision()` → `run(start=paused_at_node)`)을 호출만 한다. 지나온 경로(run.path: from, 조건, to, 시각, 재개 회차)가 그대로 감사조서다.

## 9. 2단계 인터페이스

`result.next_step_interface`(경로 참조): tree.spot_cont_on_grid.{RF,RD}, fwd.cont_on_grid.{RF,RD}, fwd.df_step.{RF,RD}, grid.tree.event_times, spot_lookup{method→interp.method, space→interp.space_grid, basis}, node_discount_conv→fwd.node_discount_conv, profile. 소비 측(트리/BDT/혼합이자율)은 basis 라벨과 할인 규약을 검사한다. 2단계 증빙 예약 항목: `Constants.STEP2_EVIDENCE_ITEMS`.

## 10. 증빙 번들 규격 (Constants.EVIDENCE_FILES / XLSX_SHEETS / XLSX_COLUMNS / EVIDENCE_REQUIRED_ITEMS)

| 번호 | 파일 | 형식 |
|---|---|---|
| 01 | 01_raw_matrix.csv | csv |
| 02 | 02_rows_used.csv | csv |
| 03 | 03_knots.csv | csv |
| 04 | 04_bootstrap.csv | csv |
| 05 | 05_spot_table.csv | csv |
| 06 | 06_tree_grid.csv | csv |
| 07 | 07_par_residuals.csv | csv |
| 08 | 08_fwd_spot_sample.md | md |
| 09 | 09_flags.csv | csv |
| 10 | 10_headline.json | json |
| 11 | 11_sensitivity.csv | csv |
| 12 | 12_approvals.json | json |

xlsx: XLSX_REQUIRED=True(미생성 → 엣지 `xlsx누락`), 템플릿 `reviewer_2024_dc`(docs/XLSX_TEMPLATE.md), 시트 순서: INPUT_RAW, ROWS_USED, PROVENANCE, CONVENTIONS, Rf_dc, Rd_dc, PAR_CHECK, FWD_SPOT_CHECK, SENSITIVITY, HEADLINE, FLAGS, APPROVALS, RUN_PATH

| 열 지향 시트 | 열(basis 라벨 포함) |
|---|---|
| PAR_CHECK | curve, t, n, price, target, residual, residual_x_face |
| FWD_SPOT_CHECK | curve, step, t, prod_df_fwd, df_spot, diff_log, diff_prod |
| RUN_PATH | seq, from, condition, to, ts_utc, resume_n |
| APPROVALS | kind, requested_at, snapshot_sha256, flags_seen, decision, approver, timestamp, comment, acknowledged_codes |

Rf_dc / Rd_dc (행 지향, XLSX_DC_BLOCKS; 서식 XLSX_DC_STYLE = {"label_col": "B", "first_data_col": "C", "freeze_panes": "E1", "width_label": 18.7, "width_data": 12.7, "title_cell": "B1", "date_cell": "D1", "title_bold": true, "block_title_bold": true})

| 블록 | 행 라벨 | 원천 접두사 | 숫자 서식 |
|---|---|---|---|
| {rate} - YTM | WEEKS | rows | `#,##0_ ` |
| {rate} - YTM | TENOR | rows | `@` |
| {rate} - YTM | {rate} - YTM | rows | `0.000%` |
| {rate} - YTM | SPOT RATE | bootstrap | `0.000%` |
| Grid Forward {rate}(INTERPOLATED YTM AND SPOT RATE) | STEP | grid | `#,##0_ ` |
| Grid Forward {rate}(INTERPOLATED YTM AND SPOT RATE) | t (years) | grid | `0.0000_ ` |
| Grid Forward {rate}(INTERPOLATED YTM AND SPOT RATE) | {rate} - YTM | tree | `0.000%` |
| Grid Forward {rate}(INTERPOLATED YTM AND SPOT RATE) | SPOT RATE | tree | `0.000%` |
| Grid Forward {rate}(INTERPOLATED YTM AND SPOT RATE) | FORWARD RATE | fwd | `0.000%` |
| BOOTSTRAPPING({period}) | {period} | bootstrap | `#,##0_ ` |
| BOOTSTRAPPING({period}) | WEEKS | bootstrap | `#,##0_ ` |
| BOOTSTRAPPING({period}) | YTM - YEARLY | bootstrap | `0.000%` |
| BOOTSTRAPPING({period}) | {period} PAYMENT RATE | bootstrap | `0.000%` |
| BOOTSTRAPPING({period}) | PV OF PRINCIPAL | bootstrap | `#,##0.00_ ` |
| BOOTSTRAPPING({period}) | PV OF BOND | par_check | `#,##0.00_ ` |
| BOOTSTRAPPING({period}) | PVF OF SPOT Rate | bootstrap | `0.00000_ ` |
| BOOTSTRAPPING({period}) | SUM OF PVF SPOT JUST PRIOR TO | bootstrap | `#,##0.0000_ ` |
| BOOTSTRAPPING({period}) | {period} SPOT Rate | bootstrap | `0.000%` |
| BOOTSTRAPPING({period}) | SPOT Rate -Yearly | bootstrap | `0.000%` |
| BOOTSTRAPPING({period}) | SPOT Rate -Continuous | conv | `0.000%` |
| BOOTSTRAPPING({period}) | FORWARD Rate - {period} | fwd | `0.000%` |
| BOOTSTRAPPING({period}) | FORWARD Rate - Yearly | fwd | `0.000%` |
| BOOTSTRAPPING({period}) | MODEL CHECK (PAR REPRICE) | par_check | `#,##0.00_ ` |
| BOOTSTRAPPING({period}) | PAR RESIDUAL | par_check | `0.00E+00` |
| Grid Forward {rate} | STEP | grid | `#,##0_ ` |
| Grid Forward {rate} | STEP SPOT RATE | tree | `0.00000%` |
| Grid Forward {rate} | FORMULA I | fwd | `#,##0.0000_ ` |
| Grid Forward {rate} | FORMULA II -CUMM | fwd | `#,##0.0000_ ` |
| Grid Forward {rate} | STEP FORWARD RATE | fwd | `0.00000%` |
| Grid Forward {rate} | PVF OF FORWARD RATE | fwd | `0.00000_ ` |
| Grid Forward {rate} | MODEL CHECK (PROD DF_FWD - DF_SPOT) | fwd_spot_check | `0.00000%` |
| Grid Forward {rate} | MODEL CHECK (PV) | fwd_spot_check | `#,##0.00_ ` |

프로필 선택 목록(PROFILE_DESCRIPTIONS; PROFILE_SELECTION=required)

| 프로필 | 설명 |
|---|---|
| DEFAULT | 모드 A(이표격자 YTM 선형보간 후 폐형식 부트스트랩) + 트리 격자 연복리 현물 선형 — 엑셀 BOOT/BM·검토자 논리 재현(입력만 live 교정) |
| PCHIP_TREE | DEFAULT 와 같은 부트스트랩, 트리 격자 보간만 PCHIP(g=r_c·t, log_df) — 선도곡선 연속·음의 선도 방지(보간법 변경 공시 필요) |
| KICPA_1130 | 모드 B(공시 마디 미지수 근찾기 + 중간 이표일 보간) + 관행적 가격 — 한국공인회계사회 실무사례 1130 준용 |
| REVIEWER_2024 | RF·RD 분기 부트스트랩(c=YTM/4, par 10000), 격자 위 분기 선도 일정(분기 DF 사이 log-linear), 이산 할인 1/(1+F), 표시용 현물은 분기 연복리 현물의 선형보간 — 2024 내부 검토자 Rf_dc/Rd_dc 시트와 같은 원리(수식 시트 출력용) |
| EXCEL_REF | 엑셀 결함 재현(stale 3M 시드·원점 앵커·Empty→0·ceil_tenor) — 재조정(compare-excel) 전용, 증빙 헤드라인 금지 |

필수 증빙 항목(전항목이 `export.cell_map` 에 `<file>!<sheet|->!<range|json_path>` 로 있어야 done 도달): Q1, Q8, Q9_FWD_INPUT, Q10_1, Q10_2, Q11, Q12, Q13, C33, C34, C35, C36, C37, C38, C39, C40, C41, C43, C44, C48, HEADLINE_RF, HEADLINE_RD, HEADLINE_RATING, HEADLINE_BLOCK, KICPA_INTERP_DISCLOSURE, RUN_PATH, APPROVALS

2단계 예약(1단계 checklist 제외): Q9, C42, C45, C46, C47

## 11. 상수 표 (Constants — 값·출처는 코드 주석에서 추출; 문서 인용은 상수명으로)

| 상수 | 값 | 출처/비고 |
|---|---|---|
| `STATE_SCHEMA_VERSION` | `"1.1.0"` |  |
| `PROFILE_NAME` | `"DEFAULT"` |  |
| `PROFILE_SELECTION` | `"required"` | 사용자 결정 2026-09-07: 보간법·프로필은 실행 시 사용자가 선택(조용한 기본값 없음) — CLI --profile 필수, provenance.method_choice 에 기록·approve_input 화면 표시, 미선택 → 출처불완전, 불일치 → 프로필불일치 |
| `PROFILE_DESCRIPTIONS` | `{` | 앱 선택 화면·증빙 관례 선언문에 그대로 쓰는 설명(자유 텍스트 금지) |
| `TENOR_LABELS` | `["3M", "6M", "9M", "1Y", "1.5Y", "2Y", "2.5Y", "3Y", "4Y", "5Y", "7Y", "10Y", "15Y", "20Y"` | KIS-NET!D1:S1, BOOT!B3:Q3 |
| `TENOR_YEARS` | `{"3M": 0.25, "6M": 0.5, "9M": 0.75, "1Y": 1.0, "1.5Y": 1.5, "2Y": 2.0, "2.5Y": 2.5, "3Y": ` |  |
| `MISSING_TOKENS` | `frozenset({"-", "", "N/A", "n/a", "nan"})` | KIS-NET R58:S58 '-' ; BOOT!R24:R25=0 은 결함 → None (0 금지) |
| `PCT_TO_DEC` | `0.01` | BOOT!B4 ='KIS-NET'!D2/100 |
| `CURVE_IDS` | `("RF", "RD")` | BOOT 행4/행5 |
| `RF_FREQ` | `2` | 한공회 §3.7.3.3(책 p.124) 국고채 반기 ; BOOT!F = E*2 |
| `RD_FREQ` | `4` | 한공회 §3.7.3.4(책 p.124) 회사채 분기 ; BOOT!U = T*4 |
| `FREQ_SENSITIVITY_SET` | `{"RF": [2, 4], "RD": [4]}` | 검토자 Rf_dc(RF 분기 부트스트랩) |
| `COUPON_CONV` | `"nominal_div_m"` | c=YTM/m — 한공회 §3.7.3.5, 검토자 Check list!E35 '연간YTM/4' ; 대안 "effective_root" (감사인 Q10-2 ②) |
| `BOOTSTRAP_MODE` | `"interpolate_then_bootstrap"` | A(엑셀 BOOT·검토자 Rf_dc) \| "bootstrap_with_interpolation" B(한공회 사례1130 §2.2) |
| `PRICE_MODE` | `"par"` | BOOT/검토자 PV OF BOND 10000 \| "kicpa_conventional"(한공회 §3.7.2, 3M 국채 10,080.6) |
| `INTERP_METHOD` | `"linear"` | 검토자 C37 직선보간 ; "pchip" 필수 옵션 ; 비교 전용 natural_cubic/bessel/kruger/smith_wilson |
| `INTERP_SPACE_PRE` | `"ytm"` | 모드 A: knot→이표격자 per-period 선형 (BOOT!G/V 재현 오차 0) |
| `INTERP_METHOD_PRE` | `"linear"` | 모드 A 이표격자 보간법 — XL BOOT!G/V 선형; PCHIP_TREE 도 이표격자는 선형(PROFILE_DESCRIPTIONS "트리 격자 보간만 PCHIP") |
| `INTERP_SPACE_GRID` | `"spot_annual"` | BM MF_INTERPOL 이 BOOT!M(연복리 spot) 선형보간 = 한공회 변형① ; 대안 spot_continuous(②), log_df(④), ytm(③ 재현) |
| `PCHIP_RECOMMENDED_SPACE` | `"log_df"` | 카탈로그 §3: PCHIP 은 g=r_c·t 대상일 때 선도 양수·연속 보장 (PCHIP_TREE 프로필이 명시 지정) |
| `INTERP_TABLE` | `{` | method_id: (is_local, include) — INTERPOLATION_METHODS §1 (include: must\|recommended\|compare_only\|deferred_step2) |
| `EXTRAP_LEFT` | `"flat"` | spot 공간: 현물 평탄(=선도 r_1 상수, 검토자 weeks1-13) ; log_df 공간: (0,0) 마디 포함 정규 구간 ; "origin_anchored" = VBA MF_INTERPOL Case1 (EXCEL_REF 전용) |
| `EXTRAP_RIGHT` | `"flat_forward"` | g(t)=g_n+g'(t_n−)(t−t_n) (카탈로그 §5) \| "flat_spot"(Hagan-West) \| "excel_zero"(VBA Empty→0, EXCEL_REF 전용; 정상 모드 발동 시 FAIL) |
| `EXTRAP_LEFT_FLAT_SEVERITY` | `"WARN"` | 트리 첫 스텝(t<첫 knot)은 구조적으로 항상 해당 → WARN ; "APPROVAL_REQUIRED" 로 되돌릴 수 있음(사용자 결정 2026-09-07: WARN 확정) |
| `CURVE_HORIZON_Y` | `10.0` | BOOT!E29/T49 ; KICPA_1130 프로필 50 |
| `RF_SEED_3M` | `"none"` | \| "excel_ytm_half" (BOOT!L10 = C10/2, EXCEL_REF 전용) |
| `RF_REGRID_RULE` | `"interp"` | \| "excel_midpoint_per_period" (BOOT!L11:L49 중점, EXCEL_REF 전용) |
| `MIN_KNOTS` | `4` | PCHIP 끝점 3점식 요건 + 여유 (열린 결정) |
| `SENSITIVITY_COMBOS` | `[("linear", "spot_annual"), ("pchip", "log_df"), ("linear", "log_df"), ("pchip", "spot_ann` | 교차 민감도 대상(주 조합 제외) — CROSS_METHOD_DF_WARN 비교 모집단 |
| `PROFILES_IMPLEMENTED` | `("DEFAULT", "PCHIP_TREE", "REVIEWER_2024")` | 앱 구현 범위 — 러너 사전 게이트·화면 비활성화 (KICPA_1130 모드 B·EXCEL_REF 결함 재현은 미구현) |
| `BLOCK_OF_ISSUANCE` | `{"사모": "사모무보증", "공모": "공모무보증"}` | 발행형태 → KIS-NET 고시 블록(B39 공모무보증 / B54 사모무보증), 감사인 Q13 |
| `RATING_ORDER` | `["AAA", "AA+", "AA0", "AA-", "A+", "A0", "A-", "BBB+", "BBB0", "BBB-", "BB+", "BB0", "BB-"` | KIS-NET 회사채 등급 서열(블록 분할 기준: 서열이 되돌아가면 새 블록); 부호 없는 등급은 "0" 으로 정규화 |
| `NOTCH_DEFAULT` | `0` | 한공회 §3.9.1 노칭 (≠0 → NOTCH_APPLIED 승인) |
| `DF_RANGE` | `(0.0, 1.0)` | DF 유효 범위(상한 1 = 명목금리 음수 불허 — 열린 결정) ; 부트스트랩 df_valid·트리 df_range_ok |
| `TOL_DF_MONOTONE` | `1e-15` | 트리 DF 비증가 판정 여유(부동소수 반올림) |
| `WEEKS_PER_YEAR` | `52` | 단위 환산(bp, 증빙 WEEKS 행) |
| `BP_PER_UNIT` | `1e4` | 단위 환산(bp, 증빙 WEEKS 행) |
| `BLOCK_FALLBACK` | `{"사모무보증": "공모무보증", "공모무보증": "사모무보증"}` | 요청 블록 결측 시 대체 (감사인 Q13 회신 2025-02-04: 사모 미고시 → 공모 사용) ; 대체 사용 → ROW_FALLBACK 승인 |
| `DAYCOUNT` | `"ACT/365"` | 보고서 T=1633/365 ; "30/360" = 워크시트 함수 YEARFRAC(MAIN_주가!B7,MAIN_주가!B6,0) (XL DATA!A4=3.475, dT=DATA!C4=A4/B4, BM!C3=DATA!$C$4) |
| `STEP_MODES` | `{"monthly": 1.0 / 12.0, "weekly": 1.0 / 52.0, "daily": 1.0 / 365.0}` | 앱 노드 간격(월간/주간/일간) → dt(년, 달력 기준; 영업일 격자는 열린 결정) ; provenance.grid_settings.step |
| `STEP_LABELS` | `{"monthly": "월간", "weekly": "주간", "daily": "일간"}` | 화면 표시 |
| `AGENCIES` | `("KIS", "KAP", "NICE", "FN", "EG")` | 채권평가사 코드(KIS자산평가·한국자산평가·나이스피앤아이·에프앤자산평가·이지자산평가) — 화면 드롭다운 |
| `TREE_GRID` | `{"mode": "report", "N": 234, "dt_weekly": 1.0 / 52.0}` | report: N 고정(보고서 234) \| weekly: dt=1/52(검토자) \| excel: N 고정 (XL DATA!B4=181) |
| `TREE_FWD_RULE` | `"continuous_from_spot"` | BM C-FWD ; \| "piecewise_quarter_step" (검토자 Rf_dc 분기 이산선도→주간) |
| `NODE_DISCOUNT_CONV` | `"3_continuous_fwd"` | 감사인 Q8 ③ exp(−f·dt) = XL BM row9, 한공회 §3.7.4.1 ; ① "1_discrete_fwd"(검토자 Check list!E34), ② "2_quarterly_fwd" |
| `CONVENTION_REASONS` | `{` | 증빙 관례 선언문에 그대로 삽입되는 사유 문장(자유 텍스트 금지) |
| `DENOM_FLOOR` | `1e-12` | 1−c_n·ΣDF ≤ floor → FAIL (BOOT!H 분모) |
| `EPS_T` | `1e-9` | 시간 비교 여유 |
| `T_ROUND_DIGITS` | `8` | 격자·이표일 공통 키 round(t, 8) |
| `ROOT_MAX_ITER` | `200` | 한공회 해찾기 대체(brent) ; KICPA 재현 실험 1e-12 → 채택 1e-14 |
| `ROOT_BRACKET_STEP` | `0.05` | 한공회 해찾기 대체(brent) ; KICPA 재현 실험 1e-12 → 채택 1e-14 |
| `ROOT_BRACKET_EXPANSIONS` | `6` | 한공회 해찾기 대체(brent) ; KICPA 재현 실험 1e-12 → 채택 1e-14 |
| `ROOT_XTOL` | `1e-14` | 한공회 해찾기 대체(brent) ; KICPA 재현 실험 1e-12 → 채택 1e-14 |
| `GS_MAX_SWEEPS` | `100` | 비국소 보간(pchip 등) 모드 B 전역 반복 ; 비수렴 → ROOTFIND_FAIL |
| `GS_TOL` | `1e-14` | 비국소 보간(pchip 등) 모드 B 전역 반복 ; 비수렴 → ROOTFIND_FAIL |
| `TOL_PAR_FAIL` | `1e-10` |  |
| `TOL_PAR_WARN` | `1e-12` |  |
| `TOL_FWD_SPOT_FAIL` | `1e-12` | 로그 공간 \|Σ ln df_step − ln DF_spot\| (검토자 ±2.2e-16) ; 증빙에는 ΠDF−DF 절대차 병기 |
| `TOL_KNOT_ROUNDTRIP` | `1e-12` | BOOT!G knot 재현 0.0 |
| `TOL_ROUNDTRIP_COMP` | `1e-13` | BOOT!M/N 왕복 ≤2.2e-16 |
| `TOL_EXCEL_RECON` | `1e-12` | recompute_boot.py max\|err\| 2e-15 |
| `TOL_GOLDEN_ABS` | `{"A": 1e-10, "B": 1e-12, "C_spot": 1e-9, "C_fwd_weekly": 5e-9, "C_pi": 1e-7, "D": 5e-6}` | 골든 원천은 fixture JSON double |
| `CROSS_METHOD_DF_WARN` | `1e-3` | 교차 보간법 DF 상대차 (한공회 사례 §2.3 ≤0.07%) |
| `FWD_JUMP_WARN_BP` | `100.0` | 인접 스텝 연속선도 점프 (검토자 수용 톱니 RF 35bp/RD 250bp — 열린 결정) |
| `RD_MIN_SPREAD` | `0.0` | RD_spot − RF_spot < 0 → RD_LT_RF 승인 |
| `CURVE_DATE_MAX_LAG_DAYS` | `3` | 2024-12-31 휴장 vs 12-30 고시 (사용자 결정 2026-09-07: 3일) ; lag<0 또는 >3 → FAIL, 0<lag≤3 → DATE_LAG 승인 |
| `HEADLINE_RULE` | `"interp_linear_ytm"` | 검토자 Check list!E44 직선보간 (사용자 결정 2026-09-07 확정) ; \| "ceil_tenor" (EXCEL_REF: stale 5Y knot 2.765/11.854, T∈(4,5] 기준) |
| `HEADLINE_DEFS` | `["interp_linear_ytm", "ceil_tenor", "nearest_tenor", "spot_annual_at_T", "spot_cont_at_T"]` | 진단표 전용 |
| `HEADLINE_ROUND_DIGITS` | `3` | 사용자 결정 2026-09-07: 보고서 표기(2.765/11.854)와 같은 % 소수 3자리 ROUND_HALF_UP 비교 |
| `PAR_FACE` | `10000` | 검토자 PV OF BOND 10000 |
| `EXCEL_REPLICATE` | `False` |  |
| `AI_ENABLED` | `False` | TTimes 6단계: API 키 없이 완결 |
| `BASIS` | `("nominal_m2", "nominal_m4", "per_period_m2", "per_period_m4", "annual_eff", "continuous",` | 한공회 §3.7.4.4 |
| `LABEL_GRAMMAR` | `{"RF": r"^\s*국고채", "RD": r"회사채\s*(AAA\|AA[+\-0]?\|A[+\-0]?\|BBB[+\-0]?\|BB[+\-0]?\|B[+\-0]` |  |
| `PROVENANCE_REQUIRED_FIELDS` | `("source_agency", "curve_date", "valuation_date", "file_sha256", "raw_copy_path", "downloa` |  |
| `PROVENANCE_APPROVAL_FIELDS` | `("capture_path",)` | 감사인 Q12-2 사용 행 캡처(이미지/PDF) ; 누락 → CAPTURE_MISSING 승인 |
| `PROVENANCE_APPROVAL_FIELDS_PRODUCT` | `("instrument.rating_evidence.capture_path",)` | 감사인 Q13-1 등급 캡처 — 상품(등급) 정보가 입력된 경우에만 요구 |
| `HUMAN_NODES` | `("approve_input", "approve_exception", "approve_curve")` |  |
| `TERMINAL_NODES` | `("done", "fail", "wait_for_human")` |  |
| `HUMAN_EDGE_ORDER` | `{` | graph_check 가 이름 시퀀스 완전 일치를 검사 |
| `CALC_PREFIXES` | `("input", "provenance", "labels", "rows", "grid", "interp", "bootstrap", "par_check", "con` |  |
| `SNAPSHOT_SCOPE` | `{"approve_input": ("input", "provenance", "labels"),` | 자기 approval_* 는 set_decision 이 스냅샷 뒤에 쓰므로 제외 |
| `EVIDENCE_REQUIRED_ITEMS` | `["Q1", "Q8", "Q9_FWD_INPUT", "Q10_1", "Q10_2", "Q11", "Q12", "Q13", "C33", "C34", "C35", "` |  |
| `STEP2_EVIDENCE_ITEMS` | `["Q9", "C42", "C45", "C46", "C47"]` | 2단계(트리·일반사채 PV·풋) 산출물 — 1단계 checklist 에 포함하지 않음 |
| `EVIDENCE_FILES` | `{"01": ("raw_matrix", "csv"), "02": ("rows_used", "csv"), "03": ("knots", "csv"), "04": ("` |  |
| `XLSX_REQUIRED` | `True` | 사용자 결정 2026-09-07: xlsx 는 필수 증빙 — 없으면 export 엣지 'xlsx누락' → fail ; openpyxl 은 pyproject 선언 의존성(배포 PC 는 pip install .) |
| `XLSX_TEMPLATE` | `"reviewer_2024_dc"` | REV 8521 검토요구사항 xlsx 의 Rf_dc/Rd_dc 시트 서식 재현 + par 검증 행 추가 (docs/XLSX_TEMPLATE.md) |
| `XLSX_FORMULA_SHEETS` | `True` | 사용자 결정 2026-09-08: Rf_dc/Rd_dc 는 검토자 시트 그대로 **살아있는 수식 + 원본 서식**(io/reviewer_sheet, docs/REVIEWER_SHEET_SPEC.md). 적용 조건은 reviewer_sheet.applicable(검토자 방식 상수 + 주간/월간 격자); 불가하면 값 시트(XLSX_DC_BLOCKS) |
| `XLSX_SHEETS` | `("INPUT_RAW", "ROWS_USED", "PROVENANCE", "CONVENTIONS", "Rf_dc", "Rd_dc", "PAR_CHECK",` |  |
| `XLSX_DC_STYLE` | `{"label_col": "B", "first_data_col": "C", "freeze_panes": "E1", "width_label": 18.7, "widt` |  |
| `XLSX_DC_BLOCKS` | `[` | (블록 제목, [(행 라벨, 원천 state 접두사, 숫자 서식)]) — 열 = 마디(블록 1·3) 또는 격자 스텝(블록 2·4) ; 라벨·서식은 REV Rf_dc r3~r38 원문({…} 커브별 치환: rate=RISK FREE RATE\|RISKY RATE, period=HALF-YEAR\|QUARTER) |
| `XLSX_COLUMNS` | `{"PAR_CHECK": ["curve", "t", "n", "price", "target", "residual", "residual_x_face"],` | 검토자 MODEL CHECK |
| `PROFILES` | `{` | 상수 오버라이드 dict 일 뿐 판단 로직 없음. fixture 매핑: A=DEFAULT, B=EXCEL_REF, C=REVIEWER_2024, D=KICPA_1130, PCHIP_TREE=A 입력 재사용 |
| `NODES_` | `nodes or NODES` |  |
