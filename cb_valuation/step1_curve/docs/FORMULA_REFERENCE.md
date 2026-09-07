# FORMULA_REFERENCE — 1단계(이자율 커브) 공식·관례·골든값 참조서

모든 에이전트·커맨드·노드 구현은 이 문서를 근거(source of truth)로 인용한다.
"출처 없는 공식은 쓰지 않는다" — 각 항목에 엑셀 셀 주소 또는 문헌 페이지를 붙였다.
임계값·허용오차의 **값**은 이 문서에 적지 않는다 — 상수명(`Constants.*`)만 인용하고 값은 GRAPH_SPEC §11 에서 본다. 심각도 표 §5·승인 정책 §6·두 갈래 시나리오 §4(A01~A04·E01~E50)·증빙 규격 §10 도 GRAPH_SPEC 이 원천이다.

## 0. 출처 약어

| 약어 | 출처 |
|---|---|
| **XL** | `ref/KBI메탈 전환사채/감사인 질의 및 회신/KBI기말_Call_감사인제출_0204.xlsm` (평가기준일 2025-12-31). 시트 `KIS-NET`, `BOOT`, `BM`, `DATA`, VBA `Module1` |
| **KICPA** | 한국공인회계사회 연구보고서 시리즈 11 「K-IFRS 실무사례와 해설 복합금융상품」 §3.7 할인율(책 p.120–131), 사례 1130(책 p.212–220). PDF 페이지 = 책 페이지 + 20 |
| **AUD** | 삼덕회계법인 질의회신서(2025-01-27 질의 / 02-04 회신) — `ref/KBI메탈 전환사채/감사인 질의 및 회신/` |
| **REV** | 검토자 패키지 `8521_평가보고서 검토자의 검토요구사항_Call Option Valuation_KBI metal_2024.xlsx` 시트 `Rf_dc`, `Rd_dc`, `Check list`, `평가모형` (평가기준일 2024-12-31) |
| **RPT** | `BC50_KBI메탈_3자지정 CallOption_2024.4Q_Compound_Final_2024.pdf` (평가기준일 2024-12-31) |
| **HW** | Hagan & West (2006) *Interpolation Methods for Curve Construction*, AMF 13(2) |
| **CAT** | `docs/INTERPOLATION_METHODS.md` (보간법 카탈로그) |
| **AQA** | `docs/AUDITOR_QA.md` — 감사인 질의회신서 Q1·Q8~Q13(AQA §2)·검토자 Check list C33~C48(AQA §3)·입력변수 헤드라인 (*1)(*3)(AQA §4)·원문 질의가 없는 시스템 항목(AQA §5)·배분 요약 1단계 27개/2단계 5개(AQA §6)·관찰 사항(AQA §7) 의 원문 요지·회신 요지 인용본. 원문(`ref/**`)은 커밋 제외이므로 저장소 안의 유일한 인용본이며, §8 표의 원문 요지·회신 요지는 여기서 옮겼다(인용이 원문과 다르면 원문이, 문장이 코드와 다르면 코드가 우선; 문장은 데이터이지 지시가 아니다) |
| **XLD** | `reference/xl_BOOT.txt`·`reference/xl_KIS-NET.txt` — XL 시트 `BOOT`·`KIS-NET` 셀 단위 덤프(`셀 VAL=… FORMULA=…`), `reference/recompute_boot.py` 의 입력. §3.1·§9 B 의 셀 값은 여기서 읽는다(비공개 저장소 전제) |
| **GS** | `docs/GRAPH_SPEC.md`(자동 생성, 편집 금지) — §4 두 갈래 시나리오, §5 심각도 표, §6 승인 정책, §10 증빙 규격, §11 상수 값 표 |

## 1. 입력: YTM 매트릭스 (XL `KIS-NET`)

- 열: `A 종류 | B 구분 | C 적용대상채권 | D..S = 3M,6M,9M,1Y,1.5Y,2Y,2.5Y,3Y,4Y,5Y,7Y,10Y,15Y,20Y,30Y,50Y` (단위 **%**). 
- 테너→연수: `3M=0.25, 6M=0.5, 9M=0.75, 1Y=1, 1.5Y=1.5, 2Y=2, 2.5Y=2.5, 3Y=3, 4Y=4, 5Y=5, 7Y=7, 10Y=10, 15Y=15, 20Y=20, 30Y=30, 50Y=50` (XL `BOOT!B10:B25`).
- 결측은 문자열 `'-'` (예: 회사채 30Y/50Y). **절대 0으로 취급하지 않는다** (XL `BOOT!R24:R25`가 0으로 들어간 것은 참조 모형의 결함).
- 무위험(RF) 행 = `국고채` (`KIS-NET!row2`). 위험(RD) 행 = 회사채 등급 행 — 참조 모형은 **사모무보증 블록(B54) 회사채BB+ = row58** 사용(`BOOT!B5 = 'KIS-NET'!D58/100`). 공모무보증 블록의 BB+는 row42.
- 출처 관례: 채권시가평가 기준수익률(금투협 채권정보센터, 민평 4사 평균) — KICPA §3.7.3.5(책 p.124). 국채 YTM은 6개월 이표 기준, 회사채 YTM은 3개월 이표 기준으로 고시.
- 발행방법 정합: 공모/사모 회사채 기준수익률이 따로 고시되므로 채권의 발행방법에 맞는 표를 적용 권장 — KICPA §3.7.3.1(책 p.123). AUD Q13 회신: "BB+ 기준 공모사채 사용(사모 미고시)" — 대체 사용 시 사유 기록·승인 필요.

## 2. 이표주기·이표율 변환

| 항목 | 값 | 출처 |
|---|---|---|
| RF 이표주기 m | **2** (반기) | KICPA §3.7.3.3(책 p.124); XL `BOOT!F = E*2` |
| RD 이표주기 m | **4** (분기) | KICPA §3.7.3.4(책 p.124); XL `BOOT!U = T*4` |
| 기간 이표율 c | **c = YTM / m** (명목) | XL `BOOT!G,V`(YTM/2, YTM/4); REV `Rf_dc!B19 'QUARTERLY PAYMENT RATE' = 0.0341/4`; REV Check list C35 '연간YTM/4' |
| 대안 | c = (1+YTM)^(1/m) − 1 | AUD Q10-2 ②(평가인 미답변) — `COUPON_CONV` enum 옵션으로만 |
| 검토자 관례 | RF/RD 모두 m=4 분기 | REV `Rf_dc`, `Rd_dc` — 주기는 파라미터로 두고 민감도 출력 |

## 3. 부트스트래핑

### 3.1 모드 A — 보간 후 폐형식 부트스트랩 (XL 방식, KICPA 변형 ③)
이표 격자 t_k = k/m 위에 YTM(또는 c)을 보간한 뒤 순차 계산.

```
spot_1 = c_1                                        # XL BOOT!H10 = G10, W10 = V10
spot_n = ((1 + c_n) / (1 − c_n · Σ_{k<n} DF_k))^(1/n) − 1   # XL BOOT!H11 = ((1+G11)/(1-G11*SUM($I$10:I10)))^(1/F11)-1
DF_n   = 1 / (1 + spot_n)^n                         # XL BOOT!I11 = 1/(1+H11)^F11
동치:  DF_n = (1 − c_n · Σ_{k<n} DF_k) / (1 + c_n),  spot_n = DF_n^(−1/n) − 1
분모 1 − c_n·ΣDF ≤ DENOM_FLOOR  →  bootstrap.status = FAIL_DENOMINATOR → 엣지 `bootstrap:분모비양수` (fail)
```
- XL 격자: RF 0.5Y 간격 20기(`BOOT!E10:E29`), RD 0.25Y 간격 40기(`BOOT!T10:T49`), horizon 10Y(= CURVE_HORIZON_Y 기본). 15Y 이상 테너는 로드만 되고 미사용. RF 격자에 3M/9M 없음(3M은 `L10 = C10/2` 시드로만 사용, 9M 미사용).
- **L10→L11 점프(XLD `xl_BOOT.txt`)**: `BOOT!L10 = C10/2` 는 라이브 3M YTM(C10 = 0.02422)의 반기 기간이자율 시드(= RF_SEED_3M="excel_ytm_half")인데, `L11` 이후는 stale G 열에서 나온 H 열 기반이다(`L11` = 0.013975 = `H10` = `G10` 하드코딩, `L12` = (H10+H11)/2 = 0.0137611 중점 — RF_REGRID_RULE="excel_midpoint_per_period"). 따라서 L10→L11 사이에 점프가 있다: L11 − L10 = 0.013975 − 0.012110 = 0.001865 → **18.65bp**(basis per_period_m2); 연복리 M열(M = (1+L)^2−1)로는 M11 − M10 = 0.0281453 − 0.0243667 = 0.0037786 → **37.79bp**(basis annual_eff). 정상 모드(RF_SEED_3M="none", RF_REGRID_RULE="interp")에서는 재현하지 않으며 EXCEL_REF 프로필에서만 재현한다(fixture B `notes`: "L10 = C10/2 (live) while L11+ stale").
- XL `BOOT!G/V`는 **하드코딩된 stale 값**(현 KIS-NET 대비 RF 최대 0.515%p, RD 최대 1.523%p 차이). 라이브 도출 시 `G(t)=linear(knots{0.5..10}, YTM/2)`, `V(t)=linear(knots{0.25..10}, YTM/4)` — 기간이자율 공간 선형보간(재계산으로 0.000 오차 확인).
- 재계산 검증(`reference/recompute_boot.py`): H 2.2e-16, I 2.0e-15, W 0.0, X 7.8e-16; par 재가격 |P−1| ≤ 1.6e-15.

### 3.2 모드 B — 보간 내장 부트스트랩 (KICPA 사례 1130 §2.2 — 기본 아님, **권장 옵션**: KICPA_1130 프로필 BOOTSTRAP_MODE="bootstrap_with_interpolation")
- 기본(DEFAULT)은 모드 A(BOOTSTRAP_MODE="interpolate_then_bootstrap")이며, 모드 B 는 `Constants.with_profile("KICPA_1130")` 로 켜는 권장 옵션이다(GS §11 PROFILES).
- 공시 마디 T_k에서만 미지수(연속복리 현물 r_k 또는 ln DF_k). 만기 T_k 채권(이표 c=YTM_k, 주기 m, 만기에서 1/m년씩 역산한 이표일)의 방정식 Σ_j (c/m)·DF(s_j) + DF(T_k) = target_k 를 brent 로 푼다(수렴 ROOT_XTOL, 반복 ROOT_MAX_ITER, 브래킷 ROOT_BRACKET_STEP·ROOT_BRACKET_EXPANSIONS; 값 GS §11; 브래킷 실패·비수렴 → 엣지 `bootstrap:근찾기실패_비수렴`). 중간 이표일 s_j의 DF는 확정 마디 + 미지수 마디에 **선택 보간**(INTERP_METHOD·INTERP_SPACE_GRID — 트리 격자 매핑과 같은 함수, CONVENTION_REASONS["INTERP_METHOD"])을 적용해 얻는다.
- **PRICE_MODE**(목표가격 target_k; 모드 A·B 공통, `bootstrap.price_mode` 에 기록): `"par"` = 모든 테너 목표가격 1(액면; XL BOOT, REV `PV OF BOND 10000` = PAR_FACE) — DEFAULT. `"kicpa_conventional"` = 한공회 관행적 정식 가격(단위기간 복리 + 단수기간 단리 + 경과이자; KICPA §3.7.2, 책 p.121–122)을 액면 1 로 정규화한 목표가격 — fixture D `bond_prices_conventional_CU`(사례 §2.1: 국채 3M 10,080.6 / 9M 10,082.98 / 18M 9,999.10 / 24M 10,000.87; 회사채 전부 액면 이하 3M 9,999.252 … 120M 9,995.756). KICPA_1130 프로필이 모드 B 와 kicpa_conventional 을 함께 켠다.
- KICPA 원문: "3년과 4년 현물이자율을 선형 보간하여 3년 6개월 현물이자율을 만들고 … 시행착오법 또는 엑셀 해찾기" (책 p.215–216).
- 단기 스텁 규약(KICPA 표 재현으로 확인): 3M채 DF = 1/(1 + y·0.25) (단리, 국채 3M: 10,162.5/(1+0.0325·0.25)=10,080.6 → DF 0.99194 → zero 0.032898); 9M채는 3M에 c·0.25, 9M에 1 + c/2. **stub 은 이상화 격자(1/m 년 배수, 키 round(t, T_ROUND_DIGITS))에서 처리하며 실제 일수 stub 이 아니다** — 원전 표의 테너 시간이 실제 일수 기반(fixture D `notes`: "9M≈0.747y")이라 재현은 5~6자리 근사이고 허용오차는 TOL_GOLDEN_ABS.D 다(이상화 stub 으로 재계산한 9M 국채 **가격**은 저장소에 재계산 근거가 없어 적지 않는다 — **미확인**; fixtures/README 도 같은 취지. `reference/curve_demo.py` 의 9M 프로브는 가격이 아니라 zero 만 출력한다: stub c·0.25 로 0.033422 vs KICPA 0.033424, 정확 재현 stub 은 0.25004년 — CAT §9 열린 항목). 지역적 보간(선형 계열)은 1회 순회, PCHIP/스플라인(비국소)은 Gauss-Seidel 외부 반복(GS_TOL, GS_MAX_SWEEPS; 비수렴 → 엣지 `bootstrap:근찾기실패_비수렴`).
- KICPA 공표 국채 zero 14개·DF(10Y) 0.719607·DF(50Y) 0.18981은 **현물 선형보간 내장** 모드 B로 6자리 재현(9M만 0.02bp). constant-forward 내장 시 최대 0.05bp 차이 — 재현 목표는 fixture D `alt_methods_gov_df.constant_forward`(§9 D(c)).

## 4. 복리 변환 (코드 불변식)

```
기간이자율 s (주기 m)  →  연복리 z = (1+s)^m − 1          # XL BOOT!M = (1+L)^2-1, AB = (1+AA)^4-1
연복리 z              →  연속복리 r_c = ln(1+z)           # XL BOOT!N = LN(1+M), AC = LN(1+AB)
명목 r_m (주기 m)     →  연속복리 r_c = m·ln(1 + r_m/m)   # KICPA 사례 1124~1126: 2·ln(1+0.03/2), 4·ln(1+0.05/4)
DF(t) = exp(−r_c·t) = (1 + r_m/m)^(−m·t) = (1+z)^(−t)
역변환: r_m = m·(exp(r_c/m) − 1),  z = exp(r_c) − 1
```
- **금지(KICPA §3.7.4.4, 책 p.126)**: 분기복리 현물이자율을 exp(−r·t)에 직접 넣는 것. `n개월 할인율 = 1/(1+z_q/4)^(n/3) ≠ exp(−z_q·n/12)`. 10Y에서 DF 0.11%(3%)~0.45%(6%) 과소.
- 구현 규칙: 모든 금리 배열은 `RateVector(values, times, basis)` 이고 `basis ∈ Constants.BASIS = ("nominal_m2", "nominal_m4", "per_period_m2", "per_period_m4", "annual_eff", "continuous", "per_step_simple")` (한공회 §3.7.4.4). 라벨 의미: `nominal_m2`/`nominal_m4` = 고시 YTM(연 명목, 이표주기 m — `rows.ytm`); `per_period_m2`/`per_period_m4` = 기간이자율 s = YTM/m 과 기간 spot(BOOT!G/H, V/W — XLSX Rf_dc/Rd_dc 블록 3 열 `c[per_period_m2]`·`spot_pp[per_period_m2]`); `annual_eff` = 연복리 z(BOOT!M/AB, `D-SPOT[annual_eff]`); `continuous` = r_c(BOOT!N/AC, `C-SPOT[continuous]`·`C-FWD[continuous]`); `per_step_simple` = 트리 스텝 이산선도 F_i(`F_step[per_step_simple]`, REV Rf_dc!B26). **DF 는 annual_eff 또는 continuous 에서만 만든다 — per_period_m* → exp() 는 위 금지 항목(한공회 §3.7.4.4)이며 리뷰 실패다.** 할인·보간·선도 함수는 continuous 또는 DF 만 인수로 받는다. 왕복 검사 |to_nominal(to_continuous(r),m) − r| ≤ TOL_ROUNDTRIP_COMP(값 GS §11; 초과 → 엣지 `convert_compounding:왕복변환불일치`).
- 옵션 모형은 연속복리 현물·선도를 사용, DF = exp(−연속복리 현물 × 만기), 위험중립확률은 연속복리 선도 기준 — KICPA §3.7.4.1~4.3(책 p.125–126).

## 5. 선도이자율·할인계수 (XL `BM`, `DATA`)

```
D-SPOT(t) = MF_INTERPOL(cum_t, BOOT!K10:K49, BOOT!M10:M49)   # BM row6 (RF), row11 (RD: Z/AB)
C-SPOT_i  = LN(1 + D-SPOT_i)                                    # BM row7/12
C-FWD_i   = (C-SPOT_i·t_i − C-SPOT_{i−1}·t_{i−1}) / dt_i,  t_0 = 0   # BM row8: =IFERROR((C7*C4-B7*B4)/C3,0); DATA!H = (G*D − G_prev*D_prev)/E
DF_i      = 1 / EXP(C-FWD_i · dt_i)                            # BM row9
이산 선도: F_i = DF_{i−1}/DF_i − 1 (기간), 연환산 (1+F_i)^m − 1     # REV Rf_dc!B26:B27
검증: Π_i DF_fwd(i) = DF_spot(t_n)  (REV MODEL CHECK 0 / ±2.2e-16; AUD Q11 예시 1건 제출 요구)
```
- 노드 할인 규약(AUD Q8): ① 1/(1+fwd)^dt ② 1/(1+0.25·fwd)^(4dt) ③ exp(−fwd·dt). 평가인 E열=③(XL BM), F열=①; REV 체크리스트는 ① 수용. → 앱은 연속·이산 선도를 모두 출력하고 어느 것을 트리에 넣는지 선언.
- 위험중립확률(AUD Q9): p* = (exp(rf_fwd·dt) − d)/(u − d) (④, XL BM row21) 또는 ((1+rf_fwd)^dt − d)/(u − d) (①, REV).

### 5.1 VBA `MF_INTERPOL(pRSD, pPRDDATA, pINTDATA)` 의미 (XL Module1) 와 외삽 상수 EXTRAP_LEFT / EXTRAP_RIGHT
- 첫 knot x_1 이하: `y_1 · x / x_1` (**원점 (0,0) 앵커 선형**; t=0.0192에서 0.19% vs 평탄 2.44%). 상수 표기: EXTRAP_LEFT="origin_anchored" — **EXCEL_REF 프로필 전용**; 사용 스텝은 `tree.extrap_left_origin_steps` → EXTRAP_LEFT_ORIGIN(APPROVAL_REQUIRED, GS §5).
- knot 사이: 선형보간(INTERP_SPACE_GRID="spot_annual" = BOOT!M 연복리 spot 공간 = 한공회 변형 ①).
- 마지막 knot 초과: 어떤 값도 대입되지 않아 엑셀 VBA 는 **Empty(=0) 반환** — 10Y 초과 노드는 0% 할인(결함). 포팅된 `reference/recompute_boot.py::mf_interpol` 은 이 경우 **None 을 돌려준다**(Empty 를 0 으로 바꾸지 않음; `/compare-excel` 프로브도 None 기대). 상수 표기: EXTRAP_RIGHT="excel_zero" — **EXCEL_REF 프로필 전용**(EXCEL_REPLICATE=True, 경고 필수). 정상 모드에서 excel_zero 가 발동하면(`tree.excel_zero_used and not C.EXCEL_REPLICATE`) 엣지 **`map_tree_grid:엑셀제로외삽_정상모드`** → fail(코드 EXCEL_ZERO_OUTSIDE_REPLICATE; GS §4 시나리오 E29).
- 앱 기본 외삽(CAT §5): **EXTRAP_LEFT="flat"** — spot 공간이면 현물 평탄(=선도 r_1 상수, REV weeks 1~13 관례), log_df 공간(g=r_c·t)이면 (0,0) 마디를 포함한 정규 구간. 트리 첫 스텝(t<첫 knot)은 구조적으로 항상 해당하므로 심각도는 EXTRAP_LEFT_FLAT_SEVERITY(열린 결정; GS §5 코드 EXTRAP_LEFT_FLAT). **EXTRAP_RIGHT="flat_forward"** — 연속복리 선도 평탄(g 선형 연장): **g(t) = g_n + g'(t_n−)·(t − t_n)**, g'(t_n−) 는 마지막 마디의 **좌극한 기울기**(선형이면 마지막 구간 기울기, PCHIP 이면 끝 기울기 d_n). 대안 "flat_spot"(Hagan-West 현물 평탄, 선도 점프 발생). 우측 외삽 사용 스텝은 `tree.extrap_right_steps` → EXTRAP_RIGHT_USED(APPROVAL_REQUIRED). 항상 `assert horizon ≥ 만기` — CURVE_HORIZON_Y 초과는 엣지 `build_grid:만기초과`(fail).

### 5.2 트리 격자 (TREE_GRID · DAYCOUNT)
- RPT(TREE_GRID mode "report", DEFAULT): N=234, T=4.47397260 = 1,633/365 (DAYCOUNT="ACT/365", 2024-12-31→2029-06-21), dt≈0.01912(≈주간).
- XL 2025 기말 파일(TREE_GRID mode "excel", EXCEL_REF 프로필): `DATA!A4` **T=3.475** = 워크시트 함수 `=YEARFRAC(MAIN_주가!B7, MAIN_주가!B6, 0)`(basis 0 = US 30/360; VBA 프로시저가 아님 — XL 원본 DATA 시트에서 2026-09-07 확인: `MAIN_주가!B7`=평가기준일 2025-12-31, `MAIN_주가!B6`=만기일 2029-06-21; `Constants.DAYCOUNT` 주석), `DATA!B4` **N=181**(`Constants.TREE_GRID` 주석·`PROFILES["EXCEL_REF"]` 주석), `DATA!C4` **dT** `=A4/B4` = 0.0191989(캐시값; `BM!C3 = DATA!$C$4` — §5.1·§9 B 의 MF_INTERPOL 프로브 인수 0.019199 가 이 값). 산술 대조: 2025-12-31 → 2029-06-21 을 30/360 으로 세면 (2029−2025)·360 + (6−12)·30 + (21−30) = 1,251일 → 1,251/360 = 3.475 로 A4 와 같다.
- REV(TREE_GRID mode "weekly", REVIEWER_2024 프로필): dt=1/52, 233노드, 테너→주 매핑 13,26,39,52,78,104,130,156,208,260,364,520 (1Y=52주), 첫 테너 이전 평탄(EXTRAP_LEFT="flat"), TREE_FWD_RULE="piecewise_quarter_step".
- → 격자는 (N, T, DAYCOUNT ∈ {ACT/365, 30/360}, dt) 파라미터이며 `grid.tree.*`(N, T, dt_mode, dt, times, daycount, event_times)에 기록된다.

## 6. Par 검증 (핵심 게이트 — 노드 `verify_par`)

```
residual_n = c_n · Σ_{k=1..n} DF_k + DF_n − target_n     (부트스트랩 격자 만기 n 전부, RF·RD 각각;
                                                         target_n = 1 (PRICE_MODE="par") 또는 관행적 가격의 액면 1 정규화값 (PRICE_MODE="kicpa_conventional"))
[파잔차비유한 → fail(PAR_NONFINITE)] [max_n |residual_n| > TOL_PAR_FAIL → fail(PAR_RESIDUAL)] [기본 → convert_compounding]
TOL_PAR_WARN < max_n |residual_n| ≤ TOL_PAR_FAIL  →  sanity PAR_WARN (WARN)                       # 값: GS §11
```
- **검증 범위**: par 검증은 **부트스트랩 격자(1/m 년 배수) 만기에서만** 수행한다(`grid.boot_times`, `par_check.per_maturity`). 격자 밖 테너 — 모드 A 에서 `Constants.knot_tenors(curve)` 가 제외하는 마디(예: RF m=2 에서 3M·9M; RD m=4 는 공시 테너가 모두 격자 위) — 는 게이트 대상이 아니며 `par_check.unused_knot_max_abs_err` 에 **진단 잔차**로만 계산해 UNUSED_KNOT_RESIDUAL(WARN, sanity_check)로 보고한다. 모드 B 는 knot_tenors 가 CURVE_HORIZON_Y 이하의 모든 공시 테너이므로 전 마디(fixture D: 국채 16·회사채 12)가 게이트 대상이다.
- 관측(참조 재계산 — 판정값 아님): XL 1.55e-15(RF), 1.11e-15(RD); 라이브 1.33e-15; REV MODEL CHECK 10000 ± ~1e-11(≈1e-15 상대); 모드 A 오프그리드 마디(국채 3M/9M) 진단 잔차 2.7e-5/6.0e-5.
- KICPA 원리: "YTM으로 계산한 채권가격(1)과 STRIPs로 분해해 현물이자율로 계산한 가격(2)는 이론적으로 같아야 한다" §3.7.3.6(책 p.124).

## 7. 허용오차 상수 (값은 코드에만 — 상수명·용도·판정 위치)

값: GRAPH_SPEC §11. 이 표는 `Constants` 의 상수명과 용도, 그리고 그 상수를 읽는 판정 위치(엣지 이름 또는 sanity 코드)만 적는다.

| 상수 | 용도 | 판정 위치(엣지 이름 또는 sanity 코드) |
|---|---|---|
| `TOL_PAR_FAIL` | par 재가격 최대 절대잔차 상한(§6) | 엣지 `verify_par:파검증실패` → fail(PAR_RESIDUAL) |
| `TOL_PAR_WARN` | TOL_PAR_WARN < 잔차 ≤ TOL_PAR_FAIL 경고대(§6) | sanity `PAR_WARN`(WARN) |
| `TOL_FWD_SPOT_FAIL` | 로그 공간 \|Σ ln df_step − ln DF_spot\|(§5, 감사인 Q11; 증빙에는 ΠDF−DF 절대차 병기) | 엣지 `verify_fwd_spot:정합실패` → fail(FWD_SPOT_MISMATCH) |
| `TOL_KNOT_ROUNDTRIP` | 보간값이 knot 에서 원값 재현(`interp.knot_roundtrip_max_err`) | 엣지 `interpolate:knot왕복불일치` → fail(KNOT_ROUNDTRIP) |
| `TOL_ROUNDTRIP_COMP` | 복리 변환 왕복(§4, `conv.roundtrip_max_err`) | 엣지 `convert_compounding:왕복변환불일치` → fail(COMP_ROUNDTRIP) |
| `TOL_EXCEL_RECON` | XL BOOT/BM 캐시 대비 재조정(EXCEL_REF, `sensitivity.excel_recon`, `/compare-excel`, fixture B) | 엣지·sanity 코드 없음 — 테스트·커맨드 판정 전용 |
| `TOL_GOLDEN_ABS.{A,B,C_spot,C_fwd_weekly,C_pi,D}` | 골든 fixture(§9) 대조 허용오차(키 = fixture id / 항목) | 엣지·sanity 코드 없음 — unittest 전용 |
| `CROSS_METHOD_DF_WARN` | 교차 보간법 DF 상대차(`sensitivity.max_rel_df_diff`; KICPA 사례 §2.3 관측 ≤0.07% 는 근거이지 값이 아님) | sanity `CROSS_METHOD_DF`(WARN) |
| `FWD_JUMP_WARN_BP` | 인접 스텝 연속선도 점프(`fwd.max_jump_bp`, 테너 경계 톱니 — 열린 결정) | sanity `SAWTOOTH`(WARN) |
| `DENOM_FLOOR` | 모드 A 분모 1 − c_n·ΣDF ≤ floor(§3.1, `bootstrap.min_denominator`) | `bootstrap.status=FAIL_DENOMINATOR` → 엣지 `bootstrap:분모비양수` → fail(DENOM_NONPOS) |
| `ROOT_XTOL` | 모드 B brent 수렴(§3.2; ROOT_MAX_ITER·ROOT_BRACKET_STEP·ROOT_BRACKET_EXPANSIONS 동반) | `bootstrap.status=FAIL_BRACKET/FAIL_NO_CONVERGENCE` → 엣지 `bootstrap:근찾기실패_비수렴` → fail(ROOTFIND_FAIL) |
| `GS_TOL` | 모드 B 비국소 보간(pchip 등) Gauss-Seidel 전역 반복 수렴(§3.2; GS_MAX_SWEEPS 동반) | 위와 같은 엣지 `bootstrap:근찾기실패_비수렴` |
| `CURVE_DATE_MAX_LAG_DAYS` | curve_date → valuation_date 지연 일수(`provenance.date_lag_days`; 열린 결정) | lag<0 또는 lag>상수 → 엣지 `record_provenance:기준일역전_또는_지연초과` → fail(DATE_LAG_OUT_OF_RANGE); 0<lag≤상수 → `input_stage_flags()` DATE_LAG(APPROVAL_REQUIRED) |

심각도 표는 GRAPH_SPEC §5 (FAIL = 각 노드 전용 엣지 + 다중 노드 교차 규칙 INTERP_MISMATCH; APPROVAL_REQUIRED·WARN 집계는 sanity_check 한 곳; 좌측 flat 외삽은 EXTRAP_LEFT_FLAT_SEVERITY(열린 결정)). 역전 커브는 정상(NONMONO_* 는 WARN; KICPA 2023-05-03 국채 1.5Y 3.380 > 3Y 3.270, fixture D `notes`).

## 8. 감사인·검토자 검증 요구 (증빙 노드가 생산해야 할 것 — 행 키 = `Constants.EVIDENCE_REQUIRED_ITEMS`)

행 키는 `EVIDENCE_REQUIRED_ITEMS` 와 글자 단위로 같다. `export_evidence` 는 키마다 `export.cell_map[key]` 에 `<file>!<sheet|->!<range|json_path>` 위치가 있는지 검사하고, 하나라도 없으면 엣지 `export_evidence:증빙불완전` → fail(EVIDENCE_INCOMPLETE; GS §4 E46·E47, 규격 GS §10). 원문 요지·회신 요지는 AQA(`docs/AUDITOR_QA.md` §2 질의서·§3 Check list·§4 입력변수·§5 시스템 항목)에서 옮겼다 — 인용이 원문(`ref/**`)과 다르면 원문이, 문장이 코드와 다르면 코드가 우선한다. C 행의 회신은 Check list D열(C33~C48 전항목 'Yes') + E열 Comment/Ref. 요지다. 배분(1단계 27개·2단계 5개)은 AQA §6 = `EVIDENCE_REQUIRED_ITEMS`·`STEP2_EVIDENCE_ITEMS`.

| 키 | 요구 | 출처 |
|---|---|---|
| `Q1` | 할인율·현가계수 삭제 금지, 데이터 위치(파일/탭/셀) 명시 제출 → `checklist_map.json` | AUD 질의서 D10, B6:B7 |
| `Q8` | 노드 할인 규약 선택(①②③)과 사유 — NODE_DISCOUNT_CONV + CONVENTION_REASONS["NODE_DISCOUNT_CONV"], ① 1/(1+F) 값(`fwd.df_step_alt`) 병기 | AUD row17 |
| `Q9_FWD_INPUT` | **1단계 몫**: 트리 입력용 스텝 선도(`fwd.cont_on_grid`, `fwd.disc_per_step`)·DF(`fwd.df_step`) 표 + basis 라벨(Rf_dc/Rd_dc 블록 2·4 시트, §4 BASIS). 트리 자체 검증(위험중립확률 ①~④, 노드별 데이터)은 `Q9` — 아래 2단계 소표 | AUD row18 |
| `Q10_1` | 평가기준일별·커브별 YTM→Spot→Forward 표(테너 기준, `fwd.tenor_table`) | AUD row19 |
| `Q10_2` | 연YTM→분기 변환 방식(YTM/4 vs (1+YTM)^0.25−1)과 사유 — COUPON_CONV + CONVENTION_REASONS["COUPON_CONV"] | AUD row19; REV C35 |
| `Q11` | Π DF_fwd = DF_spot 검증 샘플 1건 + 잔차표(08_fwd_spot_sample.md, FWD_SPOT_CHECK 시트; §5) | AUD row20; REV Rf_dc!37 = fixture C `sheets/Rf_dc` row37 'MODEL CHECK'(TRUE) — 대조 값은 row32 'WEEKLY SPOT RATE' TC = 0.7225497001388543 vs row36 'PVF OF FORWARD RATE' TC = 0.7225497001388529 (AQA §2 Q11 과 동일 인용) |
| `Q12` | YTM 커브 데이터 형식·출처(PROVENANCE_REQUIRED_FIELDS 8개: 평가사·curve_date·valuation_date·파일 해시·원본 사본·다운로드 시각·담당자·instrument.maturity_date), 평균 적용 시 캡처(PROVENANCE_APPROVAL_FIELDS → 누락 시 CAPTURE_MISSING 승인). RPT 각주 "평가기관 5사 평균"(엑셀은 KIS 단일)은 `provenance.agencies`·`averaging` 로 여기 귀속 | AUD row21 (평가인: KIS-NET 직접 다운로드, 캡처 없음); RPT p.16 |
| `Q13` | 신용등급 캡처(`instrument.rating_evidence`), 공모/사모 구분·사유(BLOCK_FALLBACK 사용 → ROW_FALLBACK 승인), 전기 일관성(RATING_CHANGED·BLOCK_CHANGED) | AUD row22; REV C38, C41 |
| `C33` | 이항모형 할인율 기준은 적정한가? — 회신 Yes: 평가기준일 국고채 유통수익률과 해당 신용등급 금리를 측정주기(weekly)에 따른 이자율 기간구조로 고려해 매시점별 단기선도이자율 적용. 증빙: 06_tree_grid.csv / Rf_dc·Rd_dc 블록 2·4(`step, date, t, dt, C-FWD[continuous], F_step[per_step_simple]`) + CONVENTIONS(TREE_GRID·TREE_FWD_RULE) | REV Check list C33/E33; AQA §3 |
| `C34` | 이항모형 구간별 할인율 추출방법은 적절한가? — 회신 Yes: "1/(1+fwd)^dt 로 할인"(= Q8 ①). 증빙: Rf_dc·Rd_dc 블록 2·4 `F_step[per_step_simple]`·`DF_step`(NODE_DISCOUNT_CONV 선언, 코드 주석 "검토자 Check list!E34") + 이산 1/(1+F) 병기 = state `fwd.df_step_alt`(XLSX_COLUMNS 에 열 없음 — AQA §7 관찰 5, 열린 결정) + CONVENTION_REASONS["NODE_DISCOUNT_CONV"] | REV Check list C34/E34; AQA §3 |
| `C35` | 관측 YTM 에서 Zero Coupon rate(Spot rate) Bootstrapping 방법은 적절한가? — 회신 Yes: "연간YTM/4". 증빙: 04_bootstrap.csv / Rf_dc·Rd_dc 블록 3(`n, t, c[per_period_m*], price_target, spot_pp[per_period_m*], DF, denominator`) + CONVENTIONS(COUPON_CONV·RF_FREQ·RD_FREQ·BOOTSTRAP_MODE·PRICE_MODE; 코드 주석 "검토자 Check list!E35 '연간YTM/4'") + RF 분기 변형 FREQ_SENSITIVITY_SET → 11_sensitivity.csv. Q10_2 와 같은 증빙 위치 | REV Check list C35/E35; AQA §3 |
| `C36` | 신용도 및 기간구조를 고려한 Spot rate & Forward rate 가 유의적 차이가 없는가? — 회신 Yes: "Rd_dc 시트". 증빙: 07_par_residuals.csv / PAR_CHECK(`curve, t, n, price, target, residual, residual_x_face`) + 11_sensitivity.csv / SENSITIVITY(교차 보간법·주기 DF 상대차); 독립 재계산 대조 = fixture C(REVIEWER_2024) 골든 테스트(TOL_GOLDEN_ABS 의 C_* 키) | REV Check list C36/E36 (Rd_dc); AQA §3 |
| `C37` | 만기가 동일하지 않은 경우 보간법을 적용하여 잔존만기에 해당하는 수익률을 적용하였는가? — 회신 Yes: 잔존만기에 정확히 일치하는 Tenor 가 없어 관측가능한 Tenor 수익률 간 직선보간법 적용. 증빙: README_conventions.md / CONVENTIONS(INTERP_METHOD("linear", 주석 "검토자 C37 직선보간")·INTERP_SPACE_PRE·INTERP_SPACE_GRID·EXTRAP_LEFT·EXTRAP_RIGHT + CONVENTION_REASONS["INTERP_METHOD"]) + 03_knots.csv + 10_headline.json `rule`; KICPA_INTERP_DISCLOSURE 와 연결. 헤드라인 값 자체는 HEADLINE_* 행(분리) | REV Check list C37/E37; AQA §3 |
| `C38` | 회사의 신용등급 및 옵션 잔존만기에 해당하는 회사채 이자율을 사용하였는가 — 회신 Yes: 발행사의 신용도·유동성·부가옵션·담보/보증·금리변동 등 채권 특성을 고려해 Yield Curve 결정, Kisline 등에서 조회되는 각 평가기준일 신용등급 인용. 증빙: 02_rows_used.csv / ROWS_USED(RD 행 등급·블록) + PROVENANCE(instrument.rating·rating_evidence) + 10_headline.json / HEADLINE(`rating_applied`·`rd_ytm_remaining`); Q13 계열(신용등급·공모/사모·전기 일관성) | REV Check list C38/E38; AQA §3 |
| `C39` | 위험할인율은 독립적으로 조회 및 산출한 위험이자율 커브와 유의적 차이가 없는가? — 회신 Yes: "Rd_dc 시트". 증빙: 05_spot_table.csv(RD) / Rd_dc 블록 3·2·4 + PAR_CHECK(curve=RD); 독립 대조 = fixture C Rd 골든(REVIEWER_2024, TOL_GOLDEN_ABS.C_spot) | REV Check list C39/E39 (Rd_dc); AQA §3 |
| `C40` | 무위험할인율은 독립적으로 조회한 국고채수익률과 일치하는가? — 회신 Yes: "Rf_dc 시트". 증빙: 01_raw_matrix.csv / INPUT_RAW(국고채 행 원문) + 02_rows_used.csv / ROWS_USED(RF) + PROVENANCE(file_sha256·raw_copy_path) | REV Check list C40/E40 (Rf_dc); AQA §3 |
| `C41` | (분류 '일반사채(Straight bond) 가치의 검토') 전환사채 발행회사의 신용등급이 독립적으로 조회한 신용등급과 일치하는가? — 회신 Yes: "KIS". 증빙: PROVENANCE(instrument.rating·rating_evidence.{source_agency, lookup_date, capture_path, sha256}·prior_rating_basis) + 09_flags.csv / FLAGS(RATING_CHANGED) + HEADLINE `rating_applied`; Q13 계열 | REV Check list C41/E41; AQA §3 |
| `C43` | 일반사채 현금흐름 할인 시 사용된 할인율이 감사인이 독립적으로 재계산한 할인율과 일치하는가? — 회신 Yes: "Bond Value". 1단계 몫: 잔여만기 spot 조회 — 05_spot_table.csv / Rd_dc 블록 2·4(`t, D-SPOT[annual_eff], C-SPOT[continuous], DF`) + 10_headline.json(`rd_spot_remaining_annual`) + 임의 시점 spot(t) 조회 규약 `result.next_step_interface.spot_lookup`(method·space·basis). 일반사채 PV 자체는 2단계(C45) | REV Check list C43/E43; AQA §3 |
| `C44` | 잔여만기 YTM 헤드라인의 **정의**(HEADLINE_RULE="interp_linear_ytm" 직선보간, 주석 "검토자 Check list!E44")와 계산 근거 문서화 — 값 자체는 `HEADLINE_RF`/`HEADLINE_RD` 행(분리) | REV Check list E44; AUD 입력변수 (*1) |
| `C48` | 조기상환금액의 현재가치 산정 시 사용된 할인율은 조기상환 최적시점에 해당하는 잔존만기 할인율(Spot rate)이 사용되었는가? — 회신 Yes(E48 Comment 없음). 1단계 몫: 05_spot_table.csv / Rd_dc 블록 2·4 의 spot·DF at `grid.tree.event_times`(풋 행사일) + `result.next_step_interface.spot_lookup`·`event_times`(C43 과 같은 조회 규약) | REV Check list C48; AQA §3 |
| `HEADLINE_RF` | 잔여만기 RF YTM 헤드라인 **값**(`headline.rf_ytm_remaining`) + 정의명(`headline.rule`) + 보고서 값 대조(`headline.match_ok`; 불일치 → HEADLINE_MISMATCH 승인, 비교 불가 → 엣지 `compute_headline:헤드라인미비교`). 참조: RPT p.16 "2.77%"(정의 미공시); 감사인 입력변수 (*1) 2.765% 는 ceil_tenor(stale 5Y knot, T∈(4,5]) 정의 — §9 B | RPT p.16; AUD (*1); 10_headline.json |
| `HEADLINE_RD` | 잔여만기 RD YTM 헤드라인 값(`headline.rd_ytm_remaining`; 규칙 위와 같음. 입력변수 (*1) 11.854% 는 ceil_tenor) | AUD (*1); 10_headline.json |
| `HEADLINE_RATING` | 적용 신용등급(`headline.rating_applied`; RPT: BB+, Nice bizline) + 등급 캡처(Q13) + 노칭(NOTCH_DEFAULT≠0 → NOTCH_APPLIED 승인) | RPT p.16; AUD row22 |
| `HEADLINE_BLOCK` | 적용 블록(`headline.block_applied`; 참조 모형 사모무보증 row58 = XL BOOT!B5, AUD Q13 회신은 "사모 미고시 → 공모 사용") | XL BOOT!B5; AUD Q13 회신 |
| `KICPA_INTERP_DISCLOSURE` | 보간 방법 1개·PRE/GRID 공간·부트스트랩 내부와 트리 격자 매핑 동일 적용·연속복리 변환 규칙(m=2/4)·외삽 규칙·프로필·상수 fingerprint 공시(README_conventions.md, CONVENTIONS 시트; CONVENTION_REASONS 4항) | KICPA §3.7.3.6; CONVENTION_REASONS |
| `RUN_PATH` | 지나온 엣지(`run.path`: from, 조건, to, 시각, 재개 회차) 시트 = 감사조서 | GS §8·§10 |
| `APPROVALS` | 승인 기록(12_approvals.json, APPROVALS 시트: kind·requested_at·snapshot_sha256·flags_seen·decision·approver·timestamp·comment·acknowledged_codes) | GS §6·§10 |

**2단계 예약 — `Constants.STEP2_EVIDENCE_ITEMS`(트리·일반사채 PV·풋 산출물; 1단계 checklist 에 포함하지 않으며 있으면 오히려 비정상)**

| 키 | 요구 | 출처 |
|---|---|---|
| `Q9` | 위험중립확률 형태(①~④: ④ p* = (exp(rf_fwd·dt) − d)/(u − d) = XL BM row21, ① ((1+rf_fwd)^dt − d)/(u − d) = REV)와 노드별 데이터 — 1단계는 입력만 `Q9_FWD_INPUT` 으로 제공 | AUD row18 |
| `C42` | 이자지급주기와 계산방식 가정이 계약서와 일치하는가? — 회신 Yes: "무이자 조건". 2단계: 일반사채 현금흐름 | REV Check list C42/E42; AQA §3 |
| `C45` | 일반사채 평가 시 사용된 수식이 적정하며, 독립적으로 재계산한 일반사채 현재가치와 일치하는가? — 회신 Yes: 유의적 차이 범위 내(별첨 Bond value). 2단계: 일반사채 PV(1단계는 C43 의 spot 조회 규약만 제공) | REV Check list C45/E45; AQA §3 |
| `C46` | (분류 '상환권(Put Option) 검토') 풋옵션 평가모형은 일반적으로 인정되는 모형인가? — 회신 Yes: 각 이항모형 Node 에서 Max[보유가치, 풋가치] 로 산출. 2단계: 트리 | REV Check list C46/E46; AQA §3 |
| `C47` | 조기상환 최적시점의 예측 근거는 적정한가? — 회신 Yes: 위험할인율과 조기상환청구이자율이 유의적으로 차이 나므로 조기상환가능기간 중 가장 이른 시점 행사 가정. 2단계: 풋 행사 시점(1단계는 `grid.tree.event_times` 만 제공) | REV Check list C47/E47; AQA §3 |

## 9. 골든값 (표시용 인용 — 원천은 `tests/fixtures/golden/<id>.json`)

이 절의 숫자는 **표시용 인용**이다. 테스트가 대조하는 원천은 `tests/fixtures/golden/<fixture_id>.json` 의 **double** 값이며(빌드 **1단계** BUILD_PROMPTS §1 '연습용 데이터' 에서 생성 — fixtures/README 와 동일; 4단계(4b·4c)의 `tests/test_fixtures_golden.py` 는 이 JSON 을 소비만 한다. 각 항목에 `source`·`tolerance`(TOL_GOLDEN_ABS 키) 기록), 문서와 JSON 이 다르면 JSON 이 우선한다. 허용오차 값은 GS §11 `TOL_GOLDEN_ABS`. fixture ↔ 프로필: A=DEFAULT, B=EXCEL_REF, C=REVIEWER_2024, D=KICPA_1130, PCHIP_TREE 는 A 입력 재사용(`Constants.PROFILES` 주석, fixtures/README).

- **A. 라이브 KIS-NET 2025-12-31**(`kisnet_matrix_20251231.json`, 라이브 G/V 도출, TOL_GOLDEN_ABS.A): RF 10Y D-SPOT(Y) 0.0343360261 / C-SPOT 0.0337597002 / PV 0.7134827621; RF 1Y 0.0256725775, 3Y 0.0297999369, 5Y 0.0327933527. RD(row58) 10Y 0.1585729885 / 0.1471890655 / 0.2294911861; 0.25Y 0.0728706763, 1Y 0.0945230632, 3Y 0.1318590889, 5Y 0.1443296933. par 1.33e-15. **RF 0.25Y 0.0243666521 은 엑셀 3M 시드 규약(YTM_3M/2 → (1+s)^2−1, §3.1 L10) 산물이므로 RF_SEED_3M="excel_ytm_half" 일 때만 검증한다** — DEFAULT(RF_SEED_3M="none", EXTRAP_LEFT="flat")에서는 0.25Y 격자값이 0.5Y spot 과 같다(fixtures/README). 반기 격자점(1Y·3Y·5Y·10Y) 골든은 프로필 무관.
- **B. XL BOOT 캐시**(`boot_cached_20251231.json`, stale G/V 주입, TOL_GOLDEN_ABS.B / TOL_EXCEL_RECON): H/I/W/X/L/M/N/AA/AB/AC 전열 max|err| ≤ 2.0e-15(`recompute_boot.py` SUMMARY 원문: H 2.22e-16 · I 2.00e-15 · W 0 · X 7.77e-16 · L 0 · M 0 · N 0 · AA 0 · AB 2.22e-16 · AC 0; TOL_EXCEL_RECON 코드 주석 "max|err| 2e-15" 및 §3.1 과 일치); RF 10Y D-SPOT(Y) 0.0289009955(C-SPOT 0.0284912380), RD 0.1384841678(0.1296977002); MF_INTERPOL(0.019199)=0.0018713(마지막 knot 초과 프로브는 None, §5.1). **헤드라인**: 2.765%/11.854% 는 HEADLINE_RULE="ceil_tenor" 가 stale 5Y knot 를 집은 값이며 잔여만기 T∈(4,5] 일 때만 나온다(Constants HEADLINE_RULE 주석). fixture B 자체 기준일(2025-12-31 → 2029-06-21, XL DATA!A4 T=3.475, §5.2)의 잔여만기로는 ceil_tenor=4Y 이므로 KIS-NET 4Y 열 값이 된다: RF(row2 국고채) **3.155%**, RD(row58 사모무보증 BB+) **12.858%**(`kisnet_matrix_20251231.json` rows[excel_row=2/58].ytm_pct[4Y]; 참고 공모무보증 BB+ row42 4Y 11.837%).
- **C. 검토자 2024-12-31**(`reviewer_curves_20241231.json`, 12테너 분기 m=4 양 커브, TOL_GOLDEN_ABS.C_spot / C_fwd_weekly / C_pi): Rf spot(연효과) 3.4539%, 3.3612%, 3.3634%, 3.3354%, 3.3168%, 3.2781%, 3.2520%, 3.2118%, 3.2503%, 3.2318%, 3.3104%, 3.3031%; Rd 7.4622% … 14.3643%; Q1 분기 spot 0.008525, Q2 0.008299066; weekly fwd 0.00065320(1~13주)/0.00061871(14~26주); Π PVF(520주)=0.7225497. **헤드라인**: 검토자 매트릭스에서 2.765/11.854 는 나오지 않는다(stale BOOT 5Y knot; fixtures/README). C 의 헤드라인은 HEADLINE_RULE="interp_linear_ytm" 으로 검토자 매트릭스에서 재계산한 **회귀값(재계산, 감사 자료 아님)** 으로만 골든 JSON 에 기록한다 — 이 문서에는 값을 적지 않는다(현재 미기재).
- **D. KICPA 2023-05-03**(`kicpa_case1130_20230503.json`, KICPA_1130 프로필 = 모드 B + PRICE_MODE="kicpa_conventional" + CURVE_HORIZON_Y 50, TOL_GOLDEN_ABS.D). 두 집합으로 나눈다.
  - (a) **par 모드 zero 집합**: `gov_spot_linear`/`corp_spot_linear` 의 `zero_annual`·`zero_continuous`(및 `df`). 표시: 국채 zero(연) 3M 0.032898 / 9M 0.033424 / 36M 0.032936 / 120M 0.033452 / 600M 0.033793; 국채 DF 3M 0.99194 / 9M 0.975733 / 36M 0.907279 / 120M 0.719607 / 600M 0.18981; 회사채 DF 12M 0.96217 / 120M 0.592541. 모드 B(현물 선형 내장)로 6자리 재현(9M −0.02bp).
  - (b) **관행적 가격 DF 집합**(`bond_prices_conventional_CU` 로 재현되는 DF): 국채 9M 10,082.98 / 18M 9,999.10 / 24M 10,000.87 / 36M 9,999.169, 회사채 12M 9,998.912 / 120M 9,995.756 — **PRICE_MODE="kicpa_conventional" 에서만 검증**하며 par 모드 골든에 넣지 않는다. stub 은 이상화 격자(§3.2)이고 원전 표의 테너 시간은 실제 일수 기반(fixture `notes`)이라 재현은 5~6자리 근사(TOL_GOLDEN_ABS.D).
  - (c) 한공회 ④ constant_forward 재현 목표: fixture `alt_methods_gov_df.constant_forward` — 240M 0.512348 / 360M 0.367699 / 600M 0.189762(fixture `notes`: 책 p.218–219 표). ③ ytm_linear_then_bootstrap = 책 p.220 표(`alt_methods_gov_df.ytm_linear_then_bootstrap`), ② continuous_spot_linear 는 240/360/600 연장 포함. `alt_methods_corp_df` 는 재검증되지 않음(열린 항목).
- **E. 오염 케이스**(생성 규칙; 두 갈래 시나리오 id 는 GS §4 의 E01~E50 만 인용): 테너 결측(KNOT_MISSING 승인 / E15 knot부족), RD<RF 행(RD_LT_RF 승인), spot +1bp 교란(par 실패 유도, E24), 분모≤0(E21), 만기>horizon(E17), 역전-정상 커브(통과해야 함), 헤더 오타(E01), '-'가 0으로 들어간 행(ZERO_VALUE_CELL WARN).
