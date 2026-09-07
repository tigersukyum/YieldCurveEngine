# PRD — 전환사채 평가 프로그램 1단계: 이자율 커브 엔진 (YTM 매트릭스 → 부트스트래핑 → 보간 → 현물/선도 → par 검증)

## Why
- 회계법인 평가 실무에서 CB(전환사채) 공정가치 평가의 첫 입력은 무위험(국고채)·위험(회사채 등급) 이자율 기간구조다. 현재는 엑셀(KBI메탈 모형 `KIS-NET→BOOT→BM`)로 만들며, 보간 입력값이 하드코딩된 stale 값이고 VBA `MF_INTERPOL`이 범위 밖에서 0을 반환하는 등 결함이 있다(FORMULA_REFERENCE §3.1, §5.1).
- 감사인(Q1, Q8~Q13)·내부 검토자(체크리스트 C33~C48)·한국공인회계사회 실무사례(사례 1130, §3.7)의 요구를 **재현 가능하고 증빙이 자동 생성되는** 프로그램으로 충족한다.
- 그래프 엔지니어링으로 만들어 바이브코딩 유지보수(노드 단위 수정, 코드 밖 에이전트 검토)를 가능하게 한다.

## Who
- 사용자: 평가 담당 회계사(입력·승인·증빙 제출). 검토자: 내부 검토 회계사·감사인.
- 에이전트(코드 밖 검토, `.claude/agents/`): `bond-math-verifier`(공식·복리·보간 검증), `graph-structure-auditor`(EDGES·state 규칙), `qa-test-engineer`(fixture·두 갈래·골든), `audit-evidence-reviewer`(감사 증빙 완전성), `curve-fixer`(유일한 수정자).

## What (범위)
입력: 채권평가사 시가평가 기준수익률 매트릭스(3M…50Y 16테너, %, '-' 결측; 파일 업로드 csv/tsv/xlsx), 평가기준일·커브 기준일, 사용할 RF/RD 행(드롭다운), 노드 간격(월간/주간/일간)과 산출 기간(년). 상품 정보(발행형태, 신용등급, 만기, 풋/콜일, 보고서 헤드라인)는 1단계 앱 화면에서 제외하고 선택 입력(2단계용)으로만 둔다.
출력: (1) RF·RD 커브 — 부트스트랩 격자의 기간·연복리·연속복리 현물, 트리 격자의 현물·연속/이산 선도·스텝 DF; (2) 검증 — par 재가격 잔차, Π DF_fwd=DF_spot, knot 왕복, 복리 왕복, 민감도(교차 보간법·주기); (3) 승인 기록 3곳; (4) 증빙 번들(CSV/JSON/xlsx, 관례 선언문, Q1 위치표); (5) `approved_state.json` — 2단계(트리/BDT/혼합이자율) 입력 계약.
범위 밖: 이항트리·BDT·옵션 평가(2단계 이후), 실제 이표일·휴일 조정(2단계 확장), 다중 평가사 평균 노드(인터페이스만 예약).

## When / Where
- 평가기준일마다(반기·기말·발행일) 1회 실행; 승인 정지 후 재개 가능. 로컬 Windows, Python 3.12+ 표준 라이브러리 + openpyxl(필수 — xlsx 증빙 필수, `pyproject.toml` 선언; 다른 PC 는 `pip install .`). API 키 없이 완결. 고객 금리표는 외부 전송 금지.

## How (그래프 제약 — 강제는 코드)
1. 흐름은 `graph/step1_graph.py`의 `EDGES` 하나. 22노드·68엣지·승인 3곳·종단 3개·임계 게이트 8곳(`docs/GRAPH_SPEC.md`).
2. 노드는 자기 접두사 필드만 채운다(`docs/STATE_SCHEMA.md`). 판단은 `Constants` + 엣지 람다.
3. 이표주기 RF_FREQ=2, RD_FREQ=4; 이표율 c=YTM/m(COUPON_CONV); 부트스트랩 모드 A(엑셀·검토자 재현, 기본)/B(한공회 1130 근찾기); 가격 par/kicpa_conventional.
4. 보간: `INTERP_METHOD ∈ {linear(기본), pchip(필수)}` × `INTERP_SPACE_GRID ∈ {spot_annual(기본, KICPA①), spot_continuous(②), log_df(④), ytm(재현)}`; PCHIP 권장 공간은 log_df(PCHIP_RECOMMENDED_SPACE; PCHIP_TREE 프로필이 명시 지정). **보간법·프로필은 실행 시 사용자가 선택한다**(PROFILE_SELECTION=required; CLI `--profile` 필수, 화면 목록 PROFILE_DESCRIPTIONS; `provenance.method_choice` 에 기록·입력 승인 화면 표시; 미선택/불일치는 fail). 비교 전용: natural_cubic, bessel, kruger, smith_wilson. 부트스트랩 내부(모드 B)와 트리 격자 매핑에 같은 보간 함수. 외삽: 좌 flat / 우 flat_forward, 엑셀 결함 재현은 EXCEL_REF 프로필에서만.
5. 복리 변환(한공회 §3.7.4.4 준용): 기간 s(주기 m) → 연복리 (1+s)^m−1 → 연속복리 m·ln(1+s); DF는 annual_eff/continuous에서만; per_period → exp() 구조적 차단.
6. 선도 f_i=(r_i t_i − r_{i−1} t_{i−1})/Δt (연속), F_i=DF_{i−1}/DF_i−1 (이산) 둘 다 출력; Π DF_fwd = DF_spot 검증(Q11).
7. 사람승인: 입력(필수) → 예외(조건부, 코드별 ack) → 최종 커브(필수). wait_for_human 정지·스냅샷·resume.
8. AI: interpret_labels 라벨 해석·설명문만.
9. 증빙: EVIDENCE_REQUIRED_ITEMS 전항목이 `cell_map`에 있어야 done 도달.

## 지표(수용 기준 — 값은 Constants 상수명)
- par 잔차 max ≤ TOL_PAR_FAIL (RF·RD 모두), Π DF_fwd 로그 잔차 ≤ TOL_FWD_SPOT_FAIL, knot 왕복 ≤ TOL_KNOT_ROUNDTRIP, 복리 왕복 ≤ TOL_ROUNDTRIP_COMP.
- 골든 재현: fixture A(라이브 KIS-NET) TOL_GOLDEN_ABS.A, B(엑셀 캐시, EXCEL_REF) .B, C(검토자 2024-12-31, REVIEWER_2024) .C_*, D(한공회 2023-05-03, KICPA_1130) .D.
- 두 갈래: 게이트 8곳 임계값 양쪽·NaN, 승인 3노드 approved/rejected/pending/결정선행, ack 일부/전부, 변조·상수 변경, 프로필 5종 — 시나리오 id 는 `graph_check.SCENARIOS`(= GRAPH_SPEC §4)이며 `tests/test_edges_two_branch.py`가 같은 표를 실제 노드로 돈다.
- `graph_check.py` exit 0: 정적 불변식(엣지 순서·게이트·승인 순서·람다 순수성·도달성), 시나리오가 68엣지 전부를 지나감, 노드 쓰기 추적(자기 접두사만), 상수 지문 프로세스 간 동일.

## 위험 대응(심각도 → 엣지)
FAIL → `fail` 노드(완료 불가), APPROVAL_REQUIRED → `approve_exception`, WARN → 기록. 표: GRAPH_SPEC §5.
확정된 결정(2026-09-07, 값은 Constants): 좌측 flat 외삽 = WARN(EXTRAP_LEFT_FLAT_SEVERITY); 헤드라인 = interp_linear_ytm(HEADLINE_RULE), 보고서 표기와 같은 3자리 비교(HEADLINE_ROUND_DIGITS); 기본 프로필 없음 — 실행 시 사용자 선택(PROFILE_SELECTION); 기준일 지연 3일(CURVE_DATE_MAX_LAG_DAYS); xlsx 필수(XLSX_REQUIRED, 검토자 Rf_dc/Rd_dc 서식 + par 검증 행, `docs/XLSX_TEMPLATE.md`), openpyxl 선언 의존성; 저장소 OneDrive 밖 + 비공개 원격; fixture·reference 덤프는 비공개 저장소에 커밋; 방법론 자료는 `ref/graph_engineering/`.
남은 열린 항목: fixture D 회사채 alt 표(alt_methods_corp_df) 미검증, MIN_KNOTS·FWD_JUMP_WARN_BP 값 근거 보강, 2단계 인터페이스 소비 측 검증.

## 산출물 목록
`graph/step1_graph.py`, `graph/graph_check.py`, `graph/export_spec.py`, `docs/GRAPH_SPEC.md`(생성), `docs/STATE_SCHEMA.md`, `docs/FORMULA_REFERENCE.md`, `docs/INTERPOLATION_METHODS.md`, `docs/CROSS_VERIFICATION_GUIDELINES.md`, `docs/BUILD_PROMPTS.md`, `docs/AUDITOR_QA.md`, `docs/XLSX_TEMPLATE.md`, 루트 `pyproject.toml`·`requirements.txt`·`README.md`, `tests/fixtures/*`, `reference/*`(검증된 참조 구현), `.claude/agents/*`, `.claude/commands/*`, `.claude/skills/bond-curve-conventions/SKILL.md`, 루트·step1·tests `CLAUDE.md`.
