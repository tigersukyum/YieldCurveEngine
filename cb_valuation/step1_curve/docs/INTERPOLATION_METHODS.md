# INTERPOLATION_METHODS — 보간법 카탈로그 (1단계 커브 노드용)

조사 경로: Hagan–West 2006/2008, West 2011, Le Floc'h 2013, Healy 2020, du Preez–Maré 2013, OpenGamma 2013, scipy `_cubic.py`·SLATEC `DPCHIM`·Moler `pchiptx.m`·QuantLib 원본, EIOPA/K-ICS 문서, KICPA 사례 1130, 한국자산평가·NICE P&I·KIS 공개 방법론. PCHIP 공식은 순수 Python 참조 구현(`reference/interp_ref.py`)을 scipy 1.18.1 `PchipInterpolator` 와 대조하고(값·기울기 대조 관측치의 수치는 저장소에 재현 스크립트가 없어 미확인 — 표준 라이브러리 환경에서 재현 가능한 검사는 `reference/test_interp_ref.py`) 독립 검증자 2명이 원본 코드와 축자 대조했다.

## 1. 채택 결정 요약

| method_id | 이름 | 보간 대상 | 코드 enum (`INTERP_METHOD` × `INTERP_SPACE_GRID`) | `INTERP_TABLE` include | 1단계 | 비고 |
|---|---|---|---|---|---|---|
| `linear_spot_periodic` | 연복리(이산복리) 현물 선형 (KICPA ①) | z(t) → 변환 | `linear` × `spot_annual` (annual_eff 기준 z 선형; z_m(m≠1) 공간은 enum 없음) | must | **must / DEFAULT 프로필 기본** | 감사 기준선(참조 엑셀 BM MF_INTERPOL = BOOT!M 연복리 spot 선형 재현). 재현된 한공회 6자리 표 `gov_spot_linear`(fixture `kicpa_case1130_20230503.json`)는 ① 소속; KICPA_1130 프로필도 `spot_annual` 명시. 마디값 ②와 동일, 중간값 미세 차이 |
| `linear_spot_continuous` | 연속복리 현물 선형 (KICPA ②) | r_c(t) | `linear` × `spot_continuous` | must | must (대안 공간) | HW 식 6–7; fixture `alt_methods_gov_df.continuous_spot_linear` 대조(§7) |
| `constant_forward_loglinear_df` | 선도 constant = 로그선형 DF (KICPA ④, HW raw) | g=r_c·t | `linear` × `log_df` | must | must | QuantLib/KAP 'Exponential' 표준, 선도 양수 보장(DF 감소 시); fixture `alt_methods_gov_df.constant_forward` 대조(§7) |
| `linear_ytm_then_bootstrap` | YTM 선형 후 폐형식 부트스트랩 (KICPA ③, 엑셀 BOOT 격자) | YTM | `linear` × `ytm` (모드 A 의 `INTERP_SPACE_PRE="ytm"` 이 BOOT!G/V 격자 재현) | must | must (감사/legacy 모드) | 기본값 비권장(§4 ③ 톱니) |
| `pchip_log_df` | **PCHIP on g=r_c·t=−ln DF** | g | `pchip` × `log_df` (= `PCHIP_RECOMMENDED_SPACE`; PCHIP_TREE 프로필이 명시 지정) | must | **must / PCHIP 기본** | 선도 양수·연속 보장 (DF 감소 시) |
| `pchip_spot_continuous` | PCHIP on r_c | r_c | `pchip` × `spot_continuous` | must(방법 단위) | recommended | 선도 양수 미보장·극값 마디 평탄화 경고 |
| `pchip_ytm_then_bootstrap` | YTM PCHIP 후 부트스트랩 | YTM | `pchip` × `ytm` (`INTERP_SPACE_PRE` 경로에 pchip 적용 여부 미확인) | must(방법 단위) | optional | legacy 비교용 |
| `natural_cubic_spline` | 자연 C2 스플라인 | g (r_c 비권장) | `natural_cubic` | compare_only | optional (비교 전용) | 전역·오버슈트·음의 선도 가능 |
| `bessel_hermite`, `kruger_hermite` | Bessel/포물선, Kruger(QuantLib Cubic 기본) | g | `bessel`, `kruger` | compare_only | optional (비교 전용) | 커널 공유, 비용 낮음 |
| `hyman_filter` | 단조 필터(후처리) | 임의 | enum 없음(`INTERP_TABLE` 키 아님) | — | optional | Bessel/스플라인 옵션 시 토글 |
| `monotone_convex_hagan_west` | HW 단조볼록 선도 보간 | f^d → g | `monotone_convex` | deferred_step2 | optional (2단계 이연) | 미 재무부·QuantLib ConvexMonotone; 참조 `reference/mc_test.py` |
| `smith_wilson` | Smith–Wilson (EIOPA/K-ICS) | DF | `smith_wilson` | compare_only | optional ('K-ICS 스타일' 참고) | 국내 유일 규제 방식(보험부채), CB 기본 금지 |
| `linear_df`, `loglinear_spot`, `linear_forward_continuous`, `akima_makima`, `tension_spline`, `nelson_siegel_svensson`, `fama_bliss_strip_bootstrap`, `fritsch_butland_hw_variant` | — | — | enum 없음 | — | **exclude** | 문헌 비권장 / 입력 미재현 / 명칭 충돌 / 입력자료 부적합 |

코드 enum 출처(값은 GRAPH_SPEC §11): `Constants.INTERP_TABLE` = {method_id: (is_local, include)}, include 등급 ∈ {must, recommended, compare_only, deferred_step2}(방법 단위; 방법×공간 조합의 세부 등급은 '1단계' 열). `INTERP_SPACE_GRID` ∈ {`spot_annual`(①), `spot_continuous`(②), `log_df`(④), `ytm`(③)}, `INTERP_SPACE_PRE`(모드 A 이표 격자), `PCHIP_RECOMMENDED_SPACE`, `PROFILES`.

코드 구조: `INTERP_METHOD ∈ {linear, pchip | compare_only: natural_cubic, bessel, kruger, smith_wilson | deferred_step2: monotone_convex}` × `INTERP_SPACE_GRID ∈ {spot_annual(①), spot_continuous(②), log_df(④), ytm(③)}`. 기본 조합: DEFAULT 프로필 `linear×spot_annual`(감사 기준선, 참조 엑셀 BM 재현), PCHIP_TREE 프로필 `pchip×log_df`(트리 입력용). 프로필 5종(DEFAULT, EXCEL_REF, REVIEWER_2024, KICPA_1130, PCHIP_TREE) 중 `INTERP_METHOD`/`INTERP_SPACE_GRID` 를 오버라이드하는 것은 KICPA_1130(`spot_annual` 명시)·PCHIP_TREE 뿐이며, EXCEL_REF·REVIEWER_2024 는 보간 방법·공간을 바꾸지 않는다(외삽 상수 등만 변경). 비교 전용(compare_only) 방법은 부트스트랩 내부 사용 금지, '비교 전용' 라벨.

## 2. 공용 커널: 구간별 3차 Hermite (`cubic_hermite_kernel` — 앱 `curve/interp.py` 의 예정 이름, BUILD_PROMPTS 4a 이식 대상으로 **미구현**; 검증된 참조 구현은 `reference/interp_ref.py` 의 `_Hermite`·`pchip_slopes`)

마디 x_0<…<x_{n−1}, h_k=x_{k+1}−x_k, δ_k=(y_{k+1}−y_k)/h_k. 각 방법은 마디 기울기 d_k만 공급한다. 구간 [x_k,x_{k+1}], s=x−x_k (Moler pchiptx.m):
```
c_k = (3δ_k − 2d_k − d_{k+1}) / h_k
b_k = (d_k − 2δ_k + d_{k+1}) / h_k²
P(x)  = y_k + s·(d_k + s·(c_k + s·b_k))
P'(x) = d_k + s·(2c_k + 3b_k·s)
∫P    = y_k·s + d_k·s²/2 + c_k·s³/3 + b_k·s⁴/4
```
기저형(t=s/h): h00=2t³−3t²+1, h10=t³−2t²+t, h01=−2t³+3t², h11=t³−t². scipy PPoly: T=(d_k+d_{k+1}−2δ_k)/h, c3=T/h, c2=(δ_k−d_k)/h−T, c1=d_k, c0=y_k.
출력: y=g이면 DF=exp(−P), r_c=P/t, 순간선도 f=P', 이산선도 f(t1,t2)=(P(t2)−P(t1))/(t2−t1); y=r_c이면 f=P+t·P'. 커널 밖 외삽은 금지(끝 3차식 연장 금지) — §5 외삽 규칙 적용.

## 3. PCHIP 확정 공식 (scipy `PchipInterpolator` = SLATEC `PCHIM` = MATLAB `pchip` = Moler `pchiptx.m`)

```
n = 2:  d_0 = d_1 = δ_0
내부 k = 1..n−2:
  if sign(δ_{k−1}) ≠ sign(δ_k) or δ_{k−1} = 0 or δ_k = 0:  d_k = 0
  else:  w1 = 2h_k + h_{k−1},  w2 = h_k + 2h_{k−1}
         d_k = (w1 + w2) / (w1/δ_{k−1} + w2/δ_k)        # 가중조화평균 (가중치 교차 배정 주의)
끝점 edge(h0, h1, m0, m1):
  d = ((2h0 + h1)·m0 − h0·m1) / (h0 + h1)
  if sign(d) ≠ sign(m0):                    d = 0        # 0 규칙이 캡보다 우선
  elif sign(m0) ≠ sign(m1) and |d| > 3|m0|: d = 3·m0
  d_0 = edge(h_0, h_1, δ_0, δ_1);  d_{n−1} = edge(h_{n−2}, h_{n−3}, δ_{n−2}, δ_{n−3})
```
동치형: Brodlie/Fritsch–Butland d_k = δ_{k−1}δ_k/(a·δ_k + (1−a)·δ_{k−1}), a=(h_{k−1}+2h_k)/(3(h_{k−1}+h_k)); SLATEC d_k = Dmin/(W1·δ_{k−1}/Dmax + W2·δ_k/Dmax) (세 형태는 수치 동치 — 대조 허용오차: 테스트 상수(추가 예정, 열린 항목; `reference/test_interp_ref.py` 에 이 동치형 대조 검사는 아직 없음); 등간격이면 조화평균, Moler 예제 δ=(1,1/5)→d=1/3). 보장: 0 ≤ α_k=d_k/δ_k ≤ 3, 0 ≤ β_k=d_{k+1}/δ_k ≤ 3 (Fritsch–Carlson 단조영역 내부). 정확도: 기울기 O(h²), 매끄러운 단조 자료의 보간값 O(h³), 극값 근처 O(h²)(d=0 강제).

**명칭 정정(문서·보고서 반영)**: (1) Hagan–West 식(26)/QuantLib `FritschButland`의 3·Smin·Smax/(Smax+2Smin)은 **다른 공식**(Hyman 1983 귀속)이며 QuantLib판은 부호검사도 없다(S=(1,−1)→+3). 앱의 PCHIP은 Fritsch 본인의 SLATEC 코드 계열(가중조화평균)이다. (2) QuantLib `Harmonic`이 PCHIP에 해당하나 끝 시컨트가 정확히 0일 때 부호보정을 하지 않아(엄격 부등식) scipy와 다름 — 앱은 scipy 규칙. (3) MATLAB `interp1(...,'cubic')`은 R2020b 이후 cubic convolution이므로 PCHIP이 아님 — `pchip()`/`interp1(...,'pchip')` 사용. (4) Hagan–West의 b_1=b_n=0 끝조건은 r(t)용이며 g에 쓰면 양끝 선도가 0이 되므로 복사 금지.

**권장 공간·프로필**: PCHIP 의 권장 보간 대상은 `PCHIP_RECOMMENDED_SPACE="log_df"`(g=r_c·t=−ln DF; DF 감소 자료에서 선도 양수·연속) 이며, `Constants.PROFILES["PCHIP_TREE"]` 가 `INTERP_METHOD="pchip"`·`INTERP_SPACE_GRID="log_df"` 를 명시 지정한다(두 갈래 시나리오 A04 가 PCHIP_TREE 완주와 `next_step_interface` 의 공간 log_df 를 검사, GRAPH_SPEC §4). 기본 프로필(DEFAULT)은 `linear`·`spot_annual` 이므로 PCHIP 은 `Constants.with_profile("PCHIP_TREE")`(또는 `items()` 전체 복사) 로만 켠다. 확정 공식은 위 블록 그대로이고 공간 선택은 커널 입력 y(g 또는 r_c)만 바꾼다(§2 출력 규칙).

KICPA 2023-05-03 국채 검증 수치: g 대상 14개 마디 기울기 모두 양수, 범위 0.030466(2.5Y)~0.034210(1Y), max(α,β)=1.054; 1/1200년 격자 선도 [2.970%, 3.643%]; DF(10Y)=0.7196095, DF(50Y)=0.1898107; (0,0) 마디 추가해도 범위 불변. r_c 대상: 기울기 0인 마디 {1.5, 3, 4, 5, 7, 10, 20}Y, 선도 [2.938%, 3.688%]. Hagan–West 반례 곡선(t=0.1,1,4,9,20,30; r=8.1,7,4.4,7,4,3%)에서 g 대상 PCHIP만 min f=+0.740%(자연 스플라인 on r −5.10%, PCHIP on r −1.07%, 자연 on g −1.07%).

## 4. 선형 계열 공식 (KICPA 4변형)

- **② 연속복리 현물 선형** (HW 식 6–7): r_c(t)=[(t−t_i)r_{i+1}+(t_{i+1}−t)r_i]/(t_{i+1}−t_i); DF=exp(−r_c·t); f(t)=[(2t−t_i)r_{i+1}+(t_{i+1}−2t)r_i]/(t_{i+1}−t_i) (구간 내 1차, 마디 점프; 좌극한 f(t_i−)=r_i+t_i(r_i−r_{i−1})/(t_i−t_{i−1}), KICPA 3Y 좌극한 2.965%).
- **① 이산복리 현물 선형**: z(t) 선형 → DF=(1+z/m)^(−mt)(연복리 (1+z)^(−t)); **반드시 r_c=m·ln(1+z/m)로 변환 후 exp 사용**(§3.7.4.4).
- **④ 선도 constant = 로그선형 DF** (HW 식 8–9): w=(t−t_i)/(t_{i+1}−t_i), DF(t)=DF_i^(1−w)·DF_{i+1}^w; f_i=(r_{i+1}t_{i+1}−r_it_i)/(t_{i+1}−t_i) 구간 상수; r_c(t)=[(t−t_i)t_{i+1}r_{i+1}+(t_{i+1}−t)t_ir_i]/((t_{i+1}−t_i)t). DF 감소이면 f>0 보장. (0,0) 마디 포함 시 [0,t_1]에서 f=r_1 — 엑셀 MF_INTERPOL의 '(0,0) 보간'이 옳게 적용될 대상은 현물이 아니라 g이다.
- **③ YTM 선형 후 부트스트랩**: y(t) 선형 → 격자 이표 c_k=y(t_k)/m → DF_k=(1−c_kΣ_{j<k}DF_j)/(1+c_k). 국채 반기 격자는 3M/9M 미준수(3M zero −1.1bp); 분기 스텁 격자로 바꾸면 홀/짝 분기 체인이 독립 부트스트랩되어 톱니 선도(Δf 부호변화 29회·20.8bp) → 1단계 출력용으로 쓰지 않는다.

### 알려진 한계 (PCHIP·log_df 계열 — 이 문서의 기존 서술을 모은 목록, 새 주장 없음)

- **C1 까지만**: Hermite 커널(§2)은 마디에서 값·1계 도함수만 연속이다(§7 C1 검사). g 대상이면 순간선도 f=g' 는 연속이지만 f'=g'' 은 마디에서 불연속 — 선도곡선이 마디에서 꺾인다(2차 매끄러움 없음).
- **선도 양수 보장의 조건**: g=−ln DF 가 단조증가(DF 감소)인 자료에서만 PCHIP 의 형태보존이 f>0 을 보장한다(§1 `pchip_log_df`). r_c 대상 PCHIP(`pchip_spot_continuous`)은 선도 양수를 보장하지 않는다(§1).
- **극값 마디 평탄화**: 시컨트 부호가 바뀌거나 0 인 마디에서 d_k=0 을 강제하므로(§3 확정 공식) 그 부근 정확도는 O(h²)로 떨어지고 곡선이 평탄해진다(§3). r_c 대상에서는 KICPA 국채 마디 {1.5, 3, 4, 5, 7, 10, 20}Y 가 기울기 0 이 된다(§3).
- **비국소성(부트스트랩 관점)**: `INTERP_TABLE["pchip"]` 의 is_local=False. d_k 가 δ_k(다음 마디 값)에 의존하므로 모드 B 에서는 외부 반복(GS_TOL·GS_MAX_SWEEPS)이 필요하고 비수렴은 ROOTFIND_FAIL 이다(§6 B). 선형 계열은 1회 순회로 끝난다.
- **끝점**: 커널 밖 3차식 연장은 금지(§2·§5); Hagan–West 의 b_1=b_n=0 끝조건을 g 에 복사하면 양끝 선도가 0 이 된다(§3 명칭 정정 (4)). 끝점 기울기는 3점식이므로 MIN_KNOTS 요건이 붙는다(GRAPH_SPEC §11 비고).
- **log_df 공간의 선형(④ constant forward)**: 구간 상수 선도이므로 마디에서 선도가 점프한다(§4 ④; §6 '마디 좌·우 선도 점프 보고'). ② 연속복리 현물 선형도 마디 점프(§4 ②). PCHIP×log_df 는 점프 대신 위 C1 꺾임이 남는다.
- **국내 관행 부재**: PCHIP 은 국내 공개 방법론 문서에 없으므로(§8) 보고서에 §8 문구로 방법·공간·외삽을 공시해야 한다.

## 5. 외삽 정책 (코드 고정: `Constants.EXTRAP_LEFT` / `Constants.EXTRAP_RIGHT`; 값·대안 목록은 GRAPH_SPEC §11)

| 구간 | 기본 (`EXTRAP_LEFT="flat"`, `EXTRAP_RIGHT="flat_forward"`) | 대안(옵션 / 프로필 전용) | 금지 | 심각도 코드 (GRAPH_SPEC §5) |
|---|---|---|---|---|
| t < 첫 knot (`Constants.knot_tenors(curve)` 의 첫 테너; 모드 A RF 는 3M/9M 이 이표 격자 밖이라 제외) | spot 공간(`spot_annual`·`spot_continuous`): 현물 평탄 = 선도 r_1 상수(검토자 관례) ; log_df 공간: (0,0) 마디를 포함한 정규 구간([0,t_1] 에서 f=r_1, §4 ④) | `origin_anchored`: 현물 (0,0) 직선(VBA MF_INTERPOL Case1, EXCEL_REF 전용) | 정상 모드의 현물 (0,0) 직선 | EXTRAP_LEFT_FLAT(`tree.extrap_left_flat_steps`) → `EXTRAP_LEFT_FLAT_SEVERITY`(열린 결정; 시나리오 A01/A02 가 양쪽 설정을 검사) ; EXTRAP_LEFT_ORIGIN(`tree.extrap_left_origin_steps`) → APPROVAL_REQUIRED(approve_exception) |
| t > 마지막 knot | `flat_forward`: 연속복리 선도 평탄 = g 선형 연장 g(t)=g_n+g'(t_n−)(t−t_n), 기울기는 마지막 마디의 좌극한(선형·④: 마지막 구간 기울기 ; PCHIP: §3 끝점 규칙의 d_{n−1}) → g, g' 연속·DF 감소 | `flat_spot`(Hagan–West 관행, 현물 평탄 → 선도 점프) ; `excel_zero`(VBA Empty→0, EXCEL_REF 전용) | 끝 3차식 연장(scipy/MATLAB 기본) ; 정상 모드의 `excel_zero` | EXTRAP_RIGHT_USED(`tree.extrap_right_steps`) → APPROVAL_REQUIRED(approve_exception) ; 정상 모드 `excel_zero` 발동 → FAIL EXCEL_ZERO_OUTSIDE_REPLICATE(map_tree_grid 엣지 `엑셀제로외삽_정상모드`, 시나리오 E29) |
| 항상 | 잔여만기 ≤ `CURVE_HORIZON_Y`(build_grid 엣지 `만기초과` → FAIL MATURITY_GT_HORIZON, 시나리오 E17) ; 모드 A 이표 격자 보간에 외삽이 쓰이면(`interp.coupon_grid_extrap_used`) EXTRAP_COUPON_GRID → APPROVAL_REQUIRED | | | |

증빙의 관례 선언문은 `CONVENTION_REASONS["EXTRAP"]` 문장을 그대로 쓴다(자유 텍스트 금지). 외삽 스텝의 사실 기록은 map_tree_grid(`tree.extrap_*_steps`)가 하고, 심각도 판정·집계는 sanity_check 한 곳이다(GRAPH_SPEC §5).

## 6. 부트스트랩과 보간의 결합 (`BOOTSTRAP_MODE`)

- **A `interpolate_then_bootstrap`** (DEFAULT 프로필 기본, `BOOTSTRAP_MODE`): 공시 YTM을 이표 격자에 보간(`INTERP_SPACE_PRE="ytm"`, 선형) 후 폐형식. 루트파인딩 없음, 격자상 마디 par 재가격 잔차는 TOL_PAR_WARN 이하(관측치는 `Constants` 허용오차 주석과 `reference/curve_demo.py` 의 on-grid max|P−1| 출력). 액면곡선에 가정을 부과(무차익 정합 없음), 격자 m 의존. 용도: 엑셀·검토자 재현.
- **B `bootstrap_with_interpolation`** (KICPA_1130 프로필; 카탈로그 권장): 공시 마디만 미지수, 중간 이표일은 선택 보간으로 표현, Brent(ROOT_XTOL·ROOT_MAX_ITER, 브래킷 ROOT_BRACKET_STEP·ROOT_BRACKET_EXPANSIONS). 선형 계열은 1회 순회; PCHIP·스플라인(is_local=False)은 Gauss–Seidel 외부 반복(GS_TOL·GS_MAX_SWEEPS; 비수렴 → ROOTFIND_FAIL). 출력이 '마디 곡선'이므로 세밀 격자와 부트스트랩 가정이 일관. KICPA 표(`gov_spot_linear`, 변형 ① `spot_annual`) = 현물 선형 내장 B 로 6자리 재현(TOL_GOLDEN_ABS.D; 9M −0.02bp 는 §9).
- **C `hybrid`**: 부트스트랩은 현물 선형(B), 세밀 격자만 PCHIP. 보고서에 '부트스트래핑은 현물 선형보간, 출력 곡선은 PCHIP' 명기 필수. (코드 enum 미확인 — `BOOTSTRAP_MODE` 주석은 A·B 만 열거.)
- 모든 모드 공통 자체검사: 마디 재현 |r(t_i)−r_i| ≤ TOL_KNOT_ROUNDTRIP(interpolate 엣지 `knot왕복불일치` → FAIL KNOT_ROUNDTRIP); 구간별 ∫f=(g(t_i)−g(t_{i−1}))/(t_i−t_{i−1}) 등식(허용오차: 테스트 상수(추가 예정, 열린 항목)); min f<0 → NEG_FWD(APPROVAL_REQUIRED, approve_exception; `fwd.negative_count`, 시나리오 E36); 마디 좌·우 선도 점프 보고(인접 스텝 점프 > FWD_JUMP_WARN_BP 는 SAWTOOTH WARN); 격자 이산선도는 f(t_a,t_b)=(g(t_b)−g(t_a))/(t_b−t_a)로 통일.

## 7. 방법별 검증 테스트 (qa-test-engineer 체크리스트)

- 커널: 마디 통과, (b,c)형=기저형=PPoly형 일치, C1 연속, 적분 항등식, n=2 직선 (허용오차: 테스트 상수(추가 예정, 열린 항목)).
- PCHIP: scipy fixture 회귀(허용오차: 테스트 상수(추가 예정, 열린 항목); 참조 구현 대조 관측치는 문서 머리말); Moler δ=(1,1/5)→1/3; MATLAB 예제 x=−3..3, y=[−1−1−1 0 1 1 1]→기울기 [0,0,0,1,0,0,0], p(−0.5)=−0.625; 끝점 규칙(캡 2.7→0.3, 부호 불일치 −2.3→0, 끝 시컨트 0: y=[1,1,2,3]→d=[0,0,1,1]); α,β∈[0,3]; 단조 자료 오버슈트 없음(4,001점 스캔); KICPA 국채 수치(§3); HW 반례 min f=+0.740%; 외삽 시 g,g' 연속·DF 감소(§5 `flat_forward`).
- 선형 ①(`linear`×`spot_annual`, DEFAULT·KICPA_1130): fixture `gov_spot_linear`(df·zero_annual·zero_continuous, 6자리) 재현, 허용오차 TOL_GOLDEN_ABS.D; 9M −0.02bp 잔차는 §9 열린 항목(`reference/curve_demo.py` C 표가 ①~④ 모두에서 같은 잔차를 보인다).
- 선형 ②(`linear`×`spot_continuous`): fixture `alt_methods_gov_df.continuous_spot_linear`(48~600M DF) 대조(TOL_GOLDEN_ABS.D); 3Y 좌극한 2.9653%, 1/1200 격자 선도 [2.965%,3.632%] 는 기존 기재값으로 fixture·reference 스크립트 출력에 없음 → 미확인.
- ④(`linear`×`log_df`): DF 기하보간 항등식(허용오차: 테스트 상수(추가 예정, 열린 항목)), 구간 내 선도 상수, 재현 목표 = fixture `kicpa_case1130_20230503.json` 의 `alt_methods_gov_df.constant_forward` DF 240M 0.512348 / 360M 0.367699 / 600M 0.189762(전 키 36~600M; 책 p.218–219 표; 허용오차 TOL_GOLDEN_ABS.D), 선도 범위 [3.011%,3.543%](`reference/curve_demo.py` D 표 재현).
- ③(`linear`×`ytm`): KICPA 2.3.3 표 4Y 0.0330506 / 10Y 0.0334524 / 20Y 0.0340029 / 50Y 0.0337937 정확 재현(fixture `alt_methods_gov_df.ytm_linear_then_bootstrap` DF 병기 — 48/120/600M 은 TOL_GOLDEN_ABS.D 이내로 환산 일치, 240M 은 fixture 값 자릿수가 짧아 미확인); 격자 마디 par 잔차 ≤ TOL_PAR_WARN(verify_par 게이트는 TOL_PAR_FAIL); 오프그리드 마디 잔차는 `par_check.unused_knot_max_abs_err` → UNUSED_KNOT_RESIDUAL WARN.
- 비교 방법: 자연 스플라인 오버슈트 시연(MATLAB 계단 ±1.0801), KICPA 국채 r_c 대상 30Y 3.436% 불룩 경고, HW 반례 음의 선도 경고 트리거.
- 복리: 왕복 ≤ TOL_ROUNDTRIP_COMP(convert_compounding 엣지 `왕복변환불일치` → FAIL COMP_ROUNDTRIP); exp(−ln(1+z)·t) → DF(10Y) 0.7196095, DF(50Y) 0.1898107(fixture `gov_spot_linear.df` 120M/600M 과 TOL_GOLDEN_ABS.D 이내); r_4를 continuous 로 오라벨한 음성 대조가 10Y DF 상대오차 > CROSS_METHOD_DF_WARN 로 검출.

## 8. 국내 실무 요약 (보고서 인용용)

- 입력: 금투협 채권정보센터 채권시가평가기준수익률(민평 4사 산술평균, KIS·KAP·NICE P&I·FnPricing). 협회는 현물곡선·보간 규칙을 공표하지 않는다.
- KICPA 사례 1130·2025 실무서(V.5 사례 5-11~5-13): 부트스트랩 후 보간 — ① 연복리 현물 선형(最古·기본), ② 연속복리 현물 선형, ③ YTM 선형 후 부트스트랩(엑셀 그리드), ④ 선도 constant. 3.7.4.4 오류 경고.
- 평가사: KAP 국고채 Fama–Bliss Strip & Bootstrapping, IRS는 par 선형(3개월 격자)+DF 'Exponential Interpolation'; NICE P&I 'Bootstrapping, Interpolation, Smith-Wilson, Nelson-Siegel' 열거(민평 산출 방식 비공개); KIS '1차 선형보간·3차 스플라인'은 씨티은행 요약 스니펫뿐(미검증).
- 감독: 보험업감독업무시행세칙 K-ICS 5-3·IFRS17 9-3 — 민평평균 국고채 YTM을 현금흐름기반 Smith–Wilson(α=0.1)으로 현물 전환, LOT 20Y(30Y 확대 예정)→60Y 수렴, LTFR 4.80%(2023)/4.55%(2024). 보험부채 규제 곡선이지 CB 관행 아님.
- PCHIP·monotone convex·Bessel·Akima·tension은 국내 문서에 없음(MATLAB IRDataCurve 'pchip', scipy, QuantLib, 미 재무부 monotone convex). 보고서 문구 예시: "마디 사이는 형태보존 3차 Hermite 보간(PCHIP; Fritsch–Carlson 1980, Fritsch–Butland 1984; MATLAB pchip·scipy PchipInterpolator와 동일)을 연속복리 현물이자율×만기(=−ln 할인계수)에 적용하여 선도이자율의 양수·연속성을 보장하였다. 연속복리 전환은 r_c=m·ln(1+r_m/m)(국고채 m=2, 회사채 m=4)에 의하며(KICPA 3.7.4.4), 최종 마디 이후는 연속복리 선도이자율을 평탄하게 외삽하였다."

## 9. 미해결(문서에 '미검증'으로 표기)
KIS 3차 스플라인 사용 여부; K-ICS ω=ln(1+LTFR) 변환 여부; Bloomberg 기본 방법; 국내 CB 보고서에 보간법을 명시한 공개 사례 부재; KICPA 9M zero의 0.02bp 잔차(스텁 0.25004년이면 정확).

## 10. 참고문헌(주요)
Hagan & West 2006 AMF 13(2); Hagan & West 2008 Wilmott; West 2011; Le Floc'h 2013 SSRN 2175002; Healy 2020 arXiv:2005.13890; du Preez & Maré 2013 SAJEMS 16(4); Iwashita/OpenGamma 2013; Fritsch & Carlson 1980 SIAM JNA 17(2); Fritsch & Butland 1984 SIAM JSSC 5(2); Hyman 1983; Moler NCM ch.3; scipy `_cubic.py`; SLATEC `dpchim.f`/`dpchst.f`; QuantLib `cubicinterpolation.hpp`/`convexmonotoneinterpolation.hpp`; EIOPA-BoS-19/408 §7; 보험업감독업무시행세칙 K-ICS 5-3; 금감원 K-ICS 해설서(2022.12) pp.75–78; KICPA 연구보고서 시리즈 11 §3.7·사례 1130.
