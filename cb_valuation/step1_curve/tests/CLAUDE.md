# tests — 테스트 규칙 (1단계)

- 러너: 프로젝트 루트에서 `python -m unittest discover -s cb_valuation/step1_curve/tests -v` (표준 라이브러리). pytest가 있어도 같은 파일이 돌아야 한다. 임포트는 `from cb_valuation.step1_curve.graph import step1_graph`(패키지 `__init__.py` 존재; `sys.path` 조작 금지).
- fixture는 결정적(난수·현재시각 없음). 골든값은 `fixtures/golden/<fixture_id>.json`(A·B·C·D)에서만 로드하고 각 값에 `source`·`tolerance`(Constants.TOL_GOLDEN_ABS 키) 필수. 오염 케이스는 `fixtures/E_corrupted/<scenario_id>.json`(id = GRAPH_SPEC §4 / `graph_check.SCENARIOS`). 골든 변경은 출처(셀/페이지/재계산 스크립트) 첨부 없이는 금지.
- 모든 실행 테스트는 프로필을 명시한다(`Constants.with_profile(name)` + `provenance.method_choice.profile == name`; PROFILE_SELECTION=required 이므로 미선택 state 는 `출처불완전` 으로 가야 정상 — 시나리오 E48·E49). xlsx 는 필수(XLSX_REQUIRED): 엔진 테스트의 export 는 `export.xlsx_written=True` 를 실제 파일 존재로 assert 하고, openpyxl 이 없는 환경은 `xlsx누락` 시나리오(E50)만 통과한다.
- 허용오차·임계값은 `Constants` 참조(테스트 안 숫자 리터럴 금지). 테스트 훅(DF 교란 등)은 tests 안 monkeypatch로만 — `Constants`에 넣지 않는다. 상수 변형은 `Constants.with_profile()` 또는 `items()` 전체 복사(graph_check `CAP` 방식)로만.
- 두 갈래: 시나리오 id·기대 마지막 엣지·기대 status 는 `graph_check.SCENARIOS`를 그대로 재사용한다(엔진 테스트는 스텁 대신 실제 노드로 같은 표를 돈다). 게이트 8곳 임계값 양쪽 + NaN; 승인 3노드 approved/rejected/pending/결정선행; ack 일부/전부; 변조·상수 변경; 프로필 5종. 기대값은 `run.path`의 **엣지 이름**으로 assert. graph_check 의 커버리지 불변식(미커버 엣지 0)을 엔진 수준에서도 유지한다.
- 승인 노드는 하네스가 `set_decision()`으로 자동 승인하되 먼저 `wait_for_human 도달·run.status=paused·paused_at_node·스냅샷 존재`를 assert. 재개 후 CALC_PREFIXES 필드 바이트 동일(`hash_of`).
- 결정성: 같은 입력 두 번 → `hash_of(state, CALC_PREFIXES)` 동일 + `result.next_step_interface` 동일(approved_state.json 전체는 승인 시각이 달라 비교 대상이 아님). 저장→`load_state()` 재적재 후 해시 동일. CSV/JSON 재생성 바이트 동일(xlsx는 docProps 제외).
- 판정은 완료 메시지가 아니라 수치 비교(max|diff|, 잔차)로. 실패 보고는 테스트명 | 기대 경로 | 실제 run.path | 의심 노드.
- 관례 중복 기재(스킬 비표시 대비): RateVector basis 필수(`Constants.BASIS`), DF는 annual_eff/continuous만, fsum/log1p/expm1, 격자 키 round(t, T_ROUND_DIGITS), 플러그인 추가 시 is_local 선언 + knot 왕복·MATLAB pchip 예제 테스트.
