# REVIEWER_SHEET_SPEC — 검토자 `Rf_dc` / `Rd_dc` 시트의 수식·서식 재현 명세 (사용자 결정 2026-09-08)

원천: 내부 검토자 패키지 `8521_평가보고서 검토자의 검토요구사항_Call Option Valuation_KBI metal_2024.xlsx` 의 `Rf_dc`(B1:TC39)·`Rd_dc`(A1:TD53) 시트(`ref/` 커밋 제외).
두 시트는 **값복사 상태**(남은 수식: Rf D1 `=Summary!D1`, B5 `=Summary!C19`, TC32 `=1/(1+TB32)^TB31`, TC36 `=PRODUCT(C36:TB36)`, TC38 `=#REF!`; Rd D1, B5 뿐)라
값복사된 셀(전 열 520주·40분기·12테너)에서 원래 수식을 역산했다. 구현 `io/reviewer_sheet.py`(수식 생성·파이썬 모형·서식), 자원 `io/reviewer_dc_layout.json`·`io/reviewer_theme1.xml`
(원본에서 `reference/extract_reviewer_layout.py` 로 뽑은 **서식·라벨만** — 금리 값 없음), Excel 대조 `reference/verify_reviewer_sheet.py`, 테스트 `tests/test_reviewer_sheet.py`.

## 1. 원리 (두 시트 공통)
1. 테너 YTM(행 6, 입력) → 주 단위 **선형보간**(행 11; 첫 테너 13주 앞은 평탄, 마지막 테너 뒤는 평탄).
2. 분기(13주) 격자에서 **par 채권 부트스트래핑**: 만기 13q 주의 YTM(행 18 = HLOOKUP(행 10:11)), 분기 이표율 c = YTM/4, 액면 10000,
   `DF_q = (P − c·P·S_q)/(P + c·P)`, `S_q = Σ_{k<q} DF_k`(체인 덧셈). 검증(MODEL CHECK) `c·P·S_q + (c·P + P)·DF_q = 10000` — **이것이 par 검증**이다.
3. 분기 현물 `s_q = (1/DF_q)^(1/q) − 1`, 연현물 `(1+s_q)^4 − 1`, 분기 선도 `DF_{q−1}/DF_q − 1`, 연선도 `(1+f_q)^4 − 1`. **1분기 열(C)은 연현물·연선도가 YTM 자체**(원본 C25 `=C18`, C27 `=C25`; 명목 앵커).
4. 주간 격자: 분기말 주(13q)의 **주간복리 현물** `r_{13q} = (1/DF_q)^(1/(13q)) − 1`(앵커) → 분기 안 **일정한 주간 선도**
   `F_w = ((1+r_{13q})^{13q} / (1+r_{13(q−1)})^{13(q−1)})^{1/13} − 1`(q = ROUNDUP(w/13,0); q=1 은 분모 1) → FOMULA I `1+F_w` → FOMULA II 누적곱 `Π_{j<w}(1+F_j)`(첫 열 1)
   → 비분기말 주간 현물 `r_w = (FOMULA II_w · FOMULA I_w)^{1/w} − 1` → 연현물(행 12) `(1+r_w)^52 − 1` → 테너 현물(행 7) `INDEX(행 12, 테너 주)`.
   PVF OF FORWARD RATE `1/(1+F_w)`(이산 할인, NODE_DISCOUNT_CONV=1_discrete_fwd), MODEL CHECK 1 `PVF·(1+F) − 1 = 0`, MODEL CHECK 2 = 액면의 **역방향 PV** `10000·Π_{j≥w} PVF_j`(오른쪽에서 왼쪽으로 곱), C열 = 검증 TRUE.
5. `Rd_dc` 에는 같은 YTM 을 **주간 격자에서 직접 부트스트랩**하는 대조 블록(행 39~52; c = YTM/52, 액면 C40)이 있다: `DF_w` 폐형식, 주간 현물, MODEL CHECK(= 10000),
   FOMULA I `(1+s_w)^w / Π_{j<w}`, 주간 선도, PVF, 검증 2행.
   이 원리는 엔진 프로필 `REVIEWER_2024`(RF·RD 분기 부트스트랩, INTERP linear × log_df ⇔ 분기 안 선도 일정, 1/(1+F) 할인)와 같다 — GRAPH_SPEC/FORMULA_REFERENCE 의 상수로 선언.

## 2. 행별 수식 (열 C = 주 1 / 분기 1 / 테너 1; 아래는 C·D열 예시, 오른쪽 열은 상대참조로 같은 꼴. `Lw`=마지막 주 열(TB), `Lt`=마지막 테너 열(N), `Lq`=마지막 분기 열(AP))
### Rf_dc
| 행 | B열 라벨(원문) | 수식/값 | 근거(원본 값과의 비트 대조, 전 열) |
|---|---|---|---|
| 1 | 무위험이자율 | D1 = 실행 표식(평가기준일·세트·평가사; 원본 `=Summary!D1` 회사명 → 앱은 회사명 없음) | — |
| 4 | WEEKS | C4:N4 = 테너 주수(입력; 연수×52) | 12/12 |
| 5 | (B5 = 고시일, `mm-dd-yy`; 원본 `=Summary!C19`) | C5:N5 = `3 MTH … 10 YEAR` | — |
| 6 | RISK FREE RATE - YTM | 입력(소수) | — |
| 7 | SPOT RATE | `=INDEX($C$12:$Lw$12,C$4)` | 12/12 |
| 9 | Weekly Forward Risk free Rate(LINEAR INTERPOLATED …) | 테너 주 열에 마커 `3mth … 10year` | — |
| 10 | (주 번호) | `1`, `=C10+1` | 520/520 |
| 11 | RISK FREE RATE - YTM | `=IF(C$10<=$C$4,$C$6,IF(C$10>=$Lt$4,$Lt$6,INDEX($C$6:$Lt$6,M)+(INDEX($C$6:$Lt$6,M+1)-INDEX($C$6:$Lt$6,M))*(C$10-INDEX($C$4:$Lt$4,M))/(INDEX($C$4:$Lt$4,M+1)-INDEX($C$4:$Lt$4,M))))`, `M=MATCH(C$10,$C$4:$Lt$4,1)` | 520/520 (연산 순서 `a+(b−a)·(w−w0)/(w1−w0)`) |
| 12 | SPOT RATE | `=(1+C32)^52-1` | 520/520 (정수지수 = Excel 이진 거듭제곱) |
| 13 | FORWARD RATE | q=1: `=((1+$O$32)^13)^(1/13)-1`; q≥2: `=((1+$<13q>$32)^{13q}/(1+$<13(q−1)>$32)^{13(q−1)})^(1/13)-1` (예 P13 `=((1+$AB$32)^26/(1+$O$32)^13)^(1/13)-1`) | 520/520 (`(1+f_q)^(1/13)−1` 형은 442/520 불일치 → 앵커 형 확정) |
| 16 | QUARTER | `1`, `=C16+1` | 40/40 |
| 17 | WEEKS | `=C16*13` | 40/40 |
| 18 | YTM - YEARLY | `=HLOOKUP(C17,$C$10:$Lw$11,2,FALSE)` | 40/40 |
| 19 | QUARTERLY PAYMENT RATE | `=C18/4` | 40/40 |
| 20 | PV OF PRINCIPAL | `=C$21/(1+C19)^C16` (정보용; 하위 행이 참조 안 함) | 31/40, AM열 31ulp 원본 이상치(미확인) |
| 21 | PV OF BOND | `10000`(상수) | 40/40 정수 |
| 22 | PVF OF SPOT Rate | `=(C21-C19*C21*C23)/(C21+C19*C21)` | 원본은 값(해찾기 잔차 ≤3.8e-15, 최대 34ulp) — 폐형식으로 재현, Excel 재계산 차이 3.55e-15 |
| 23 | SUM OF PVF SPOT JUST PRIOR TO | `0`, `=C23+C22` | 40/40 (체인; `SUM($C22:B22)` 는 오답) |
| 24 | QUARTERLY SPOT Rate | `=(1/C22)^(1/C16)-1` | 40/40 |
| 25 | SPOT Rate -Yearly | C `=C18`(명목 앵커), D~ `=(1+D24)^4-1` | 40/40 |
| 26 | FORWARD Rate - Quarterly | C `=C24`, D~ `=C22/D22-1` | 40/40 |
| 27 | FORWARD Rate - Yearly | C `=C25`, D~ `=(1+D26)^4-1` | 40/40 |
| 28 | MODEL CHECK (par) | `=C19*C21*C23+(C19*C21+C21)*C22` | 40/40 (원본 잔차 ≤3.8e-11 은 해찾기 흔적; 수식판은 ≤1.8e-12) |
| 30 | Weekly Forward Risk free rate | 분기말 열 마커 `0.25YR, 0.5YR, 0.75YR, 1year, 1.25year … 10year` | — |
| 31 | (주 번호) | `1`, `=C31+1` | 520/520 |
| 32 | WEEKLY SPOT RATE␠ | 분기말(13q): `=(1/<DF_q 셀>)^(1/O31)-1` (O32 `=(1/C22)^(1/O31)-1`); 그 외: `=(C34*C33)^(1/C31)-1`; TC32 `=1/(1+TB32)^TB31`(원본 수식) | 520/520 |
| 33 | FOMULA I | `=1+C13` | 520/520 |
| 34 | FOMULA II -CUMM | `1`, `=C34*C33` | 520/520 |
| 35 | WEEKLY FORWARD RATE | `=C13` | 520/520 |
| 36 | PVF OF FORWARD RATE | `=1/C33`; TC36 `=PRODUCT(C36:TB36)`(원본 수식) | 520/520 |
| 37 | MODEL CHECK | C `=ROUND(SUMPRODUCT(ABS(D37:TB37)),9)=0`(TRUE); D~ `=D36*D33-1` | 원본 D~TB 는 0·±2.2e-16 — 정의 확정 불가(후보 모두 잡음 수준), 원리(PVF×(1+F)=1)로 복원 |
| 38 | MODEL CHECK | C `=ROUND(D38*C36-TC36*$C$21,6)=0`(TRUE); D~TB `=E38*D36`(역방향 곱); TC38 `=$C$21`(원본 `#REF!` — 삭제된 출발값을 액면으로 복원) | 원본 TB38 = 10000.000000000002×TB36 (출발값 미확인) — 차이 ≤7.5e-10 |

### Rd_dc (행 배치가 다름)
| 행 | B열 라벨(원문) | 수식/값 | 근거 |
|---|---|---|---|
| 1~13 | 위험이자율 / Risk Rate - YTM / … / RISKY RATE - YTM / SPOT RATE / FORWARD RATE | Rf 와 동일(행 12 `=(1+C30)^52-1`, 행 13 앵커 `$…$30`) | 행 12·13 520/520 |
| 15 | BOOTSTRAPPING(Quarterly) | — | |
| 16~18 | QUARTER / WEEKS / YTM - YEARLY | Rf 와 동일 | 40/40 |
| 19 | PV OF BOND | `=PV(C18/4,C16,-C18/4*$C$40,-$C$40)` (원본 AF·AP 열 10000.000000000002 = PV 함수 잔존값) | 33~38/40 |
| 20 | PVF OF SPOT Rate | `=(C19-C18/4*C19*C21)/(C19+C18/4*C19)` (이표율 인라인 `C18/4`) | 원본 값(해찾기 잔차 ≤1.55e-15) |
| 21 | SUM OF PVF SPOT JUST PRIOR TO | `0`, `=C21+C20` | 40/40 |
| 22 | QUARTERLY SPOT RATE␠ | `=(1/C20)^(1/C16)-1` | 40/40 |
| 23 | SPOT RATE -YEARLY | C `=C18`, D~ `=(1+D22)^4-1` | 40/40 |
| 24 | FORWARD Rate - Quarterly | C `=C22`, D~ `=C20/D20-1` | 40/40 |
| 25 | FORWARD Rate - Yearly | C `=C23`, D~ `=(1+D24)^4-1` | 40/40 |
| 26 | MODEL CHECK (par) | `=C18/4*$C$40*C21+(C18/4*$C$40+$C$40)*C20` (액면 = C40 리터럴 10000 — 행 19 참조형은 AF 열 1ulp 불일치) | 40/40 |
| 28 | Weekly Forward Risk rate | 분기말 마커 | — |
| 29 | (주 번호) | `1`, `=C29+1` | |
| 30 | WEEKLY SPOT RATE␠ | 분기말 `=(1/<DF_q>)^(1/O29)-1`, 그 외 `=(C32*C31)^(1/C29)-1` | 520/520 |
| 31 / 32 / 33 | FOMULA I / FOMULA II -CUMM / WEEKLY FORWARD RATE | `=1+C13` / `1`,`=C32*C31` / `=C13` | 520/520 |
| 34 | (라벨 없음) | `=(1+C33)^52-1` — 주간 선도의 연환산(분기 안 일정; 원본 값이 정확히 이 식) | 520/520 |
| 35 | MODEL CHECK | C `=ROUND(SUMPRODUCT(ABS(D35:TB35)),9)=0`; D~ `=D37*D31-1` | 원본 0·±2.2e-16 (정의 불가 → 원리 복원) |
| 36 | MODEL CHECK | C `=ROUND(D36*C37-PRODUCT(C37:TB37)*$C$40,6)=0`; D~TA `=E36*D37`; TB `=$C$40*TB37`(원본 TB36 = 10000×TB37 정확) | ≤2.0e-11 |
| 37 | PVF OF FORWARD RATE | `=1/C31` | 520/520 |
| 39 | BOOTSTRAPPING(Weekly) | — | |
| 40 | (C40) | `10000`(액면 상수) | |
| 41 | (주 번호) | `1`, `=C41+1` | |
| 42 | WEEKLY PAYMENT RATE | `=C11/52` | 520/520 |
| 43 | PVF OF SPOT RATE | `=($C$40-C42*$C$40*C44)/($C$40+C42*$C$40)` | 원본 값(잔차 ≤2.6e-14) |
| 44 | SUM OF PVF SPOT JUST PRIOR TO | `0`, `=C44+C43` | 체인 |
| 45 | WEEKLY SPOT RATE␠ | `=(1/C43)^(1/C41)-1` | 517/520 |
| 46 | MODEL CHECK (par, 주간) | `=C42*$C$40*C44+(C42*$C$40+$C$40)*C43` | 520/520 (시트 값 기준) |
| 47 | FOMULA I | `=(1+C45)^C41/C48` (주간 현물 → 성장계수 ÷ 누적) | 513/520 |
| 48 | FOMULA II -CUMM | `1`, `=C48*C47` | 516/520 |
| 49 | WEEKLY FORWARD RATE | `=C47-1` | 520/520 |
| 50 | PVF OF FORWARD RATE | `=1/C47`; TC50 `=PRODUCT(C50:TB50)` (원본 TC50 값 0.15487 은 오래된 값 — 어떤 현재 값과도 맞지 않음, 미확인) | 513/520 |
| 51 | MODEL CHECK | C `=ROUND(SUMPRODUCT(ABS(D51:TB51)),9)=0`; D~ `=D50*D47-1` | 원본 0·±2.2e-16 |
| 52 | MODEL CHECK | C `=ROUND(SUMPRODUCT(ABS(D52:TB52)),6)=0`; D~ `=D46-$C$40`(par 잔차) | 원본 |v|≤2.5e-10, 정의 미확인 → par 잔차로 복원 |

정수 지수(`^4`, `^52`, `^13q`)는 Excel 이 right-to-left 이진 거듭제곱으로 계산한다((x²)² 등) — 파이썬 모형 `_xpow` 가 같은 순서를 쓴다(libm pow 로는 496/520 셀 ≤1e-14 어긋남).
행 13 은 **정적 순환 참조가 없도록** 분기말 앵커 셀만 절대참조한다(범위 INDEX 로 행 32 전체를 참조하면 Excel 이 순환으로 판정) — `tests/test_reviewer_sheet.py::test_no_circular_reference`.

## 3. 서식 (원본 그대로; `io/reviewer_dc_layout.json`)
- 테마 **'보라 II'**(theme1.xml 을 통합문서에 그대로 넣음 → 테마색+tint 가 원본과 동일), 탭 색 theme4/−0.5, 눈금선 없음, 틀 고정 E1, 열 폭 A 1.5 / B 18.66 / 나머지 12.66, 행 높이 14.9(1행 22.5·Rd 18.75, Rd 14행 12.0), 행 개요 수준 1(Rf 15~38, Rd 14~53), thickTop/thickBot 행 플래그.
- 글꼴: 라벨 Calibri 8(굵게 = 검증 행), 데이터 **Calisto MT 8**, 섹션 제목 Calibri 11 굵게 `FF002060`, 1행 맑은 고딕 11 흰색 굵게 + 보라 채우기(theme4/−0.5) + 아래 thick 테두리.
- 채우기: B열 라벨 theme3/0.8(연보라), 입력·강조 theme6/0.8·0.6(연남색; 행 11 테너 주 열, 행 18 테너 분기 열 굵게), 선도 행 theme2/−0.1, Rd 행 33 분기 첫 주 theme9/0.8, 검증 TRUE 셀 gray0625 패턴; 테두리 thin theme3/0.6(5행은 0.4).
- 숫자 서식: `0.000%`(YTM·현물·선도), `0.00000%`(주간 현물·선도), `0.00000_ `(DF·PVF), `#,##0.00_ `(PV·MODEL CHECK), `#,##0.0000_ `(FOMULA), `#,##0_ `(주·분기), `mm-dd-yy`(B5).
- 열 수가 원본과 다를 때(다른 산출 기간·월간 격자)는 열의 성격(첫 열·분기 첫 스텝·분기말·테너·마지막·여분 TC/TD)이 같은 원본 열의 서식을 쓴다(`_orig_col`). 라벨의 WEEK/QUARTER 는 스텝·이표기간 단어로 치환(주간×분기면 원문 그대로, 'FOMULA' 철자·끝 공백 포함).
- 재현하지 않는 것: Rd 의 도형(TC43~TC49 화살표), phoneticPr, 우연한 서식 잔재(Rf HB9 빨간 글꼴, P30/AC30 `0.00000%`, Rd 53행 빨간 글꼴 9열).

## 4. 적용 조건과 폴백 (`Constants.XLSX_FORMULA_SHEETS`, `reviewer_sheet.applicable`)
수식 시트는 엔진이 같은 원리로 계산했을 때만 쓴다: `TREE_FWD_RULE=piecewise_quarter_step`, `NODE_DISCOUNT_CONV=1_discrete_fwd`, `INTERP_METHOD_PRE=linear`, `(INTERP_METHOD, INTERP_SPACE_GRID)=(linear, log_df)`(= 프로필 REVIEWER_2024)
이고 격자가 **주간 또는 월간**이며 이표기간(1/RF_FREQ·1/RD_FREQ)과 테너가 스텝의 정수배일 때. 아니면(DEFAULT·PCHIP_TREE, 일간 격자) 값 시트(XLSX_DC_BLOCKS, `docs/XLSX_TEMPLATE.md`)로 쓰고 B2 에 사유를 남긴다.
화면(`/api/blocks`)도 같은 판단으로 검토자 배치(행 = 항목, 열 = 스텝, `orient: rows`)의 파이썬 모형 값을 보여준다 — 엑셀을 열면 같은 숫자가 수식으로 다시 계산된다.

## 5. 검증 결과 (2026-09-08, `reference/verify_reviewer_sheet.py`, Excel 16.0 COM 재계산, 원본 입력 2024-12-31)
| 구분 | 원본 값복사 vs 수식 재계산 | 파이썬 모형 vs Excel |
|---|---|---|
| 금리 행(YTM·현물·선도·FOMULA·PVF) | Rf ≤1.3e-14, Rd ≤3.2e-14(대부분 520/520 비트 일치) | ≤1.2e-14 |
| 분기 DF(행 22/20) | 3.6e-15 / 1.6e-15 (원본 해찾기 잔차) | 0 / 1.7e-16 |
| 10000 배율(행 28/26/46, 역방향 PV 38/36, 52) | ≤3.6e-11 / 1.6e-11 / 2.6e-10 / 7.5e-10 / 2.0e-11 / 2.5e-10 | ≤1.8e-12 |
| 검증 TRUE 셀(Rf C37·C38, Rd C35·C36·C51·C52) | 모두 TRUE | 모두 TRUE |
| 예외 | Rf 행 20 AM 열(원본 이상치 2.8e-11), Rd TC50(원본 오래된 값 0.1549 vs PRODUCT 0.2555) | — |

## 7. 앱의 보간법 선택(LINEAR / PCHIP)과 이표기간 (사용자 결정 2026-09-08)
- 앱 '보간법' 드롭다운은 프로필 **LINEAR("선형 보간")·PCHIP** 두 개만 보여준다(`Constants.PROFILES_UI`). 둘 다 이 문서의 검토자 방식 수식 시트를 만들고, **국고채(RF)는 반기(RF_FREQ=2, 26주 이표기간), 회사채(RD)는 분기(RD_FREQ=4, 13주)** 로 부트스트랩한다.
  RF 시트는 이표기간이 26주라 라벨이 `HALF-YEAR`, `HALF-YEARLY PAYMENT RATE`, `FORWARD Rate - Half-Yearly` 로 바뀌고(`_adapt`), 행 17 `=C16*26`, 행 19 `=C18/2`, 연환산 `^2`, 주간 선도 앵커는 26주 간격(`$AB$32`, `$BB$32`, …), 이표 격자 열은 20개(C~V), 테너 블록은 이표 격자 위 마디만(3M·9M 제외 — `Constants.knot_tenors`). Rd 시트는 원본과 같은 분기 구조.
- 선택이 바꾸는 것은 **마디 YTM 보간(행 11)** 하나다(엔진 `INTERP_METHOD_PRE`). 이표기간 안 선도 일정(분기 DF 사이 log-linear)·이산 할인·검증 행은 두 선택 모두 같다.
- **PCHIP 일 때 추가되는 행**(원본 배치 밖; xlsx 에도 수식으로 들어감):
  - 행 8 `PCHIP SLOPE (dY/dSTEP)`: 마디별 기울기 d_k. 내부 마디 `=IF(OR(SIGN(δL)<>SIGN(δR),δL=0,δR=0),0,1/(((2hR+hL)/δL+(hR+2hL)/δR)/((2hR+hL)+(hR+2hL))))`,
    끝 마디 `=IF(SIGN(d)<>SIGN(δ0),0,IF(AND(SIGN(δ0)<>SIGN(δ1),ABS(d)>3*ABS(δ0)),3*δ0,d))`, `d=((2h0+h1)δ0−h0δ1)/(h0+h1)` — `reference/interp_ref.pchip_slopes`(scipy PchipInterpolator 와 동일)와 같은 식·연산 순서(x 는 스텝 단위).
  - 보조행 2개(Rf 40·41, Rd 54·55): `PCHIP SEGMENT` `=IFERROR(MATCH(w,$C$4:$L$4,1),1)`, `PCHIP s` `=(w−x_i)/(x_{i+1}−x_i)`(마지막 구간 뒤는 0).
  - 행 11 `=IF(w<=x_1,y_1,IF(w>=x_n,y_n,(2s³−3s²+1)·y_i+(s³−2s²+s)·h·d_i+(−2s³+3s²)·y_{i+1}+(s³−s²)·h·d_{i+1}))` — `interp_ref._Hermite._eval` 과 같은 항 순서.
  - 검증(`reference/verify_formula_sheet.py PCHIP`, Excel 재계산 vs 파이썬 모형): 행 8 ≤3.3e-19, 행 11 ≤2.8e-17, 나머지 행 ≤1.3e-14(10000 배율 행 1.8e-12). LINEAR 도 같은 도구로 확인.
- 엔진과의 관계: 엔진은 연 단위 t 로, 시트는 스텝 단위로 PCHIP 을 평가한다(PCHIP 은 x 의 선형 변환에 불변) — 이표 격자 YTM(행 18)·DF 는 1e-12 안에서 일치(`tests/test_reviewer_sheet.py::TestInterpolationChoice`).

## 6. 엔진(state)과의 관계
수식 시트는 state 값을 복사하지 않고 **입력(테너·YTM·고시일)만** 받아 Excel 이 다시 계산한다. 엔진의 REVIEWER_2024 결과와는 정의가 같아 분기 DF 는 2.2e-16, 격자 주간 선도는 ≤4e-10 안에서 일치한다(`tests/test_reviewer_sheet.py`; 선도의 차이는 엔진 격자 시각이 `T_ROUND_DIGITS` 로 반올림되어(1/52 → 0.01923077, 상대 4e-8) 생기는 것이고 시트는 정확한 1/13 지수를 쓴다).
표시 정의가 다른 곳(원본 C열 명목 앵커, 행 12/32 의 주간복리 체인)은 시트 쪽 정의를 따르며 state 에는 쓰지 않는다. par 검증은 시트의 MODEL CHECK 행(수식)과 엔진의 PAR_CHECK 시트(값) 두 곳에 남는다.
