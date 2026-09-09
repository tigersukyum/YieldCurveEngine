# tests/fixtures — 두 갈래 확인용 연습 데이터 (기준선 양쪽)

| 파일 | 출처 | 프로필 | 용도 |
|---|---|---|---|
| `kisnet_matrix_20251231.csv/.json` | KBI xlsm `KIS-NET` 시트 원문(62행, %, '-' 보존) | DEFAULT | fixture **A** 정상 경로(라이브 도출), 행 선택·라벨 문법·결측 처리 |
| `boot_cached_20251231.json` | KBI xlsm `BOOT` 캐시값(G/V stale 이표율, H/I/W/X/L/M/N/AA/AB/AC) | EXCEL_REF | fixture **B** 엑셀 재조정(≤TOL_EXCEL_RECON), MF_INTERPOL 프로브, 헤드라인 ceil_tenor 2.765/11.854 |
| `reviewer_curves_20241231.json` | 검토자 패키지 `Rf_dc`/`Rd_dc`/`Bond Value`/`Summary`/`Result` 시트 셀 전량 | REVIEWER_2024 | fixture **C** 분기 부트스트랩(RF/RD m=4), 주간 선도(piecewise_quarter_step), Π DF 0.7225497 |
| `kisnet_matrix_20241231.xlsx` | 사용자 제공 2024-12-31 KIS-NET 매트릭스 원본(xlsx, 60행, 값만; 2026-09-09) | — | `reference/crosscheck_ref.py E`: KBI xlsm BOOT 잔존 마디의 출처(국고채 row2·공모 회사채BB+ row42 와 정확히 일치), DATA!F 재현, 2024 검토자 Rf_dc/Rd_dc 행 6 과의 불일치 확인. 비공개 저장소에서만 커밋 |
| `kicpa_case1130_20230503.json` | 한공회 사례 1130 표(책 p.212–220) | KICPA_1130 | fixture **D** 모드 B + 관행적 가격, 4개 보간 변형 표, 역전 커브(WARN만) |
| `kisnet_matrix_20251231.csv/.json` (fixture A 입력 재사용) | fixture A 와 동일 | PCHIP_TREE | 시나리오 **A04** 정상 완주 — INTERP_METHOD=pchip · INTERP_SPACE_GRID=log_df(PCHIP_RECOMMENDED_SPACE) 로 A 를 재실행, `next_step_interface.space=log_df`·basis continuous 확인(GRAPH_SPEC §4 A04). 전용 골든값 없음(FORMULA_REFERENCE §9 는 A~D 만) — knot 왕복·par·Π DF 게이트와 `reference/test_interp_ref.py`(PCHIP 참조 구현) 로 검증 |
| `golden/<fixture_id>.json` (A·B·C·D; 빌드 1단계 = BUILD_PROMPTS §1 에서 생성) | FORMULA_REFERENCE §9 · `reference/recompute_boot.py` · `reference/curve_demo.py` 출력 | fixture 별(A=DEFAULT, B=EXCEL_REF, C=REVIEWER_2024, D=KICPA_1130) | 골든값의 유일한 원천(§9 는 표시용 인용). 각 항목에 `source`·`tolerance`(Constants.TOL_GOLDEN_ABS 키: A, B, C_spot, C_fwd_weekly, C_pi, D) 필수; 출처(셀/페이지/재계산 스크립트) 없는 골든 변경 금지 |
| `E_corrupted/<scenario_id>.json` (빌드 1단계 = BUILD_PROMPTS §1 에서 생성) | 규칙 생성(FORMULA_REFERENCE §9 E 항목) | DEFAULT(시나리오별 프로필은 GRAPH_SPEC §4 표) | E01~E50 실패·승인·경계 경로 — id 는 GRAPH_SPEC §4 = `graph_check.SCENARIOS`(A01~A04·E01~E50)만 인용, 파일마다 `expected_last_edge`(엣지 이름)·기대 `status` 기재. 정상 경로 A01~A04 는 fixture A 입력을 쓴다(A02 = EXTRAP_LEFT_FLAT_SEVERITY(열린 결정) 의 다른 값, A04 = PCHIP_TREE) |

주의
- 골든값의 원천은 `golden/<fixture_id>.json`(A·B·C·D)이며 `docs/FORMULA_REFERENCE.md §9` 는 표시용 인용이다(tests/CLAUDE.md). 각 golden.json 항목에 `source`·`tolerance`(Constants.TOL_GOLDEN_ABS 키)를 적는다.
- fixture A의 RF 0.25Y 값 0.0243666521은 엑셀의 3M 시드(YTM_3M/2 → (1+s)^2−1) 규약 산물이다. DEFAULT 프로필(flat 좌측 외삽)에서는 0.25Y 격자값이 0.5Y spot과 같으므로, 0.25Y 골든은 `RF_SEED_3M=excel_ytm_half`일 때만 검증한다. 반기 격자점(1Y·3Y·5Y·10Y) 골든은 프로필과 무관.
- fixture C의 헤드라인(2.765%/11.854%)은 검토자 매트릭스에서 나오지 않는다(stale BOOT 5Y knot). C의 헤드라인은 interp_linear_ytm 재계산 회귀값으로만 기록한다.
- fixture C(`reviewer_curves_20241231.json`)의 행 6 YTM 은 검토자 패키지가 표방한 평가기준일(2024-12-31)의 KIS-NET 고시값이 **아니다**(2026-09-09 `kisnet_matrix_20241231.xlsx` 와 대조: 어느 행과도 불일치, 스프레드 구조는 공모 BB+; 2024-06-21 고시분 가설). '20241231' 은 패키지의 평가기준일 표기이며, C 는 '검토자 시트 입력 → 검토자 시트 출력' 의 계산 대조용이다(`docs/CROSS_CHECK_REF_2026-09-08.md` §E5).
- fixture D 의 시간축은 **이상화 격자**다 — `gov_spot_linear.months`·`corp_spot_linear.months` 의 정수 개월(t = months/12)로, 이표주기 1/m 년 배수 마디 위에 놓이며 국채(m=2) 3M·9M 은 단기 stub 규약(FORMULA_REFERENCE §3.2)을 따른다. 실제 일수(ACT) stub 이 아니다. 한공회 원표는 실제 일수 기반(fixture `notes`: 9M≈0.747y)이므로 골든 재현은 5~6자리 근사에 그친다 — 허용오차는 Constants.TOL_GOLDEN_ABS 의 `D` 키(값은 GRAPH_SPEC §11). 이상화 stub 으로 재계산한 9M 국채 가격은 저장소에 재계산 근거가 없어 적지 않는다(미확인).
- fixture D 의 골든 DF 중 관행적 가격 `bond_prices_conventional_CU` 가 액면(PAR_FACE)과 다른 마디 — 국채 3M·9M·18M·24M·36M 등, 회사채는 12M·120M 을 포함한 전 마디 — 는 PRICE_MODE=kicpa_conventional(KICPA_1130 프로필)에서만 검증한다(PRICE_MODE=par 에서의 일치 여부는 검증 대상이 아님).
- `alt_methods_gov_df` 재배정(fixture `notes` 2026-09-06 검토와 동일): ③ `ytm_linear_then_bootstrap` = 책 p.220 표, ④ `constant_forward` = 책 p.218–219 표, ② `continuous_spot_linear` 는 240/360/600 연장 포함(① spot_annual 선형은 `gov_spot_linear`/`corp_spot_linear`; 번호는 Constants.INTERP_SPACE_GRID 주석). `alt_methods_corp_df` 는 재검증하지 않음(열린 항목·미검증).
- `reviewer_curves_20241231.json`의 `Bond`/`Summary`/`Result` 시트는 2단계(일반사채 PV·콜옵션 결과) 대조용으로 보관.
- 데이터 분류: 이 폴더의 fixture CSV/JSON 과 `reference/xl_*.txt` 는 참조 모형(KBI 엑셀·검토자 패키지·한공회 사례 표)의 금리표를 담고 있다. 비공개 저장소 전제로만 커밋한다(열린 결정 — 루트 `.gitignore` 주석: 공개/공유 시 `tests/fixtures/*.csv`·`reference/xl_*.txt` 두 줄의 주석 해제). 금리표·식별정보를 외부 LLM/서비스에 보내지 않는다(루트 CLAUDE.md).
