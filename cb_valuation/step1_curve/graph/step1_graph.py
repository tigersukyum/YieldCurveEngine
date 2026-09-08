# -*- coding: utf-8 -*-
"""
step1_graph.py — 1단계(이자율 커브) 그래프 선언: 상수 · state 스키마 · 노드 등록표 · EDGES 배열 · 라우터

그래프 엔지니어링 원칙(조태호):
  ① 흐름은 이 파일의 EDGES 배열 하나로만 정의된다. [현재 노드, 조건 이름, 조건 함수, 다음 노드]
  ② 라우터는 EDGES를 위에서부터 훑어 조건이 처음으로 참인 엣지를 따른다. 예외/실패 엣지는 항상
     기본(ALWAYS) 엣지보다 위에 둔다. 임계 게이트는 [비유한 → fail] [초과 → fail] [기본 → 다음] 3단.
  ③ 노드는 state의 자기 접두사 필드만 채우고 다음 노드를 정하지 않는다(graph_check가 쓰기 추적으로 검사).
  ④ 모든 판단은 Constants + 조건 람다(if)에만 있다. 프롬프트·문서는 설명일 뿐 강제가 아니다.
  ⑤ 사람승인 노드는 wait_for_human 에서 멈추고(스냅샷 저장) resume 시 같은 노드에서 EDGES를 재평가한다.
     승인 결정은 set_decision() 만 쓰며, 승인 요청(requested_at) 이전·정지 상태 밖에서는 기록할 수 없다.
  ⑥ AI는 interpret_labels 노드의 라벨 해석까지만. 숫자·판정·승인 필드에 접근하지 않는다.

이 파일의 노드 함수는 **스텁**이다(자기 접두사에 자리표시 값만 채움). 계산 엔진(curve/*)은 빌드 단계
(docs/BUILD_PROMPTS.md 4단계)에서 이식한다. 공식·출처: docs/FORMULA_REFERENCE.md, 보간법: docs/INTERPOLATION_METHODS.md
"""
from __future__ import annotations

import hashlib
import json
import math
import re
from datetime import datetime, timezone


# ----------------------------------------------------------------------------- 결정적 직렬화
def _canon(o):
    """json.dumps default: set/frozenset 은 정렬된 리스트로, 그 외는 repr — 프로세스 간 해시 동일성 보장."""
    if isinstance(o, (set, frozenset)):
        return sorted(repr(x) for x in o)
    return repr(o)


def canonical_json(obj) -> str:
    return json.dumps(obj, sort_keys=True, default=_canon, ensure_ascii=False, separators=(",", ":"))


# ----------------------------------------------------------------------------- Constants
class Constants:
    """모든 판단 기준값의 유일한 저장소. 값 옆 주석 = 출처(엑셀 셀 / 한공회 절 / 감사인·검토자 / 카탈로그). 문서에는 상수명만 인용한다."""
    STATE_SCHEMA_VERSION = "1.1.0"
    PROFILE_NAME = "DEFAULT"
    PROFILE_SELECTION = "required"  # 사용자 결정 2026-09-07: 보간법·프로필은 실행 시 사용자가 선택(조용한 기본값 없음) — CLI --profile 필수, provenance.method_choice 에 기록·approve_input 화면 표시, 미선택 → 출처불완전, 불일치 → 프로필불일치
    PROFILE_DESCRIPTIONS = {  # 앱 선택 화면·증빙 관례 선언문에 그대로 쓰는 설명(자유 텍스트 금지)
        "DEFAULT": "모드 A(이표격자 YTM 선형보간 후 폐형식 부트스트랩) + 트리 격자 연복리 현물 선형 — 엑셀 BOOT/BM·검토자 논리 재현(입력만 live 교정)",
        "PCHIP_TREE": "DEFAULT 와 같은 부트스트랩, 트리 격자 보간만 PCHIP(g=r_c·t, log_df) — 선도곡선 연속·음의 선도 방지(보간법 변경 공시 필요)",
        "KICPA_1130": "모드 B(공시 마디 미지수 근찾기 + 중간 이표일 보간) + 관행적 가격 — 한국공인회계사회 실무사례 1130 준용",
        "REVIEWER_2024": "RF·RD 분기 부트스트랩(c=YTM/4, par 10000), 격자 위 분기 선도 일정(분기 DF 사이 log-linear), 이산 할인 1/(1+F), 표시용 현물은 분기 연복리 현물의 선형보간 — 2024 내부 검토자 Rf_dc/Rd_dc 시트와 같은 원리(수식 시트 출력용)",
        "EXCEL_REF": "엑셀 결함 재현(stale 3M 시드·원점 앵커·Empty→0·ceil_tenor) — 재조정(compare-excel) 전용, 증빙 헤드라인 금지",
    }
    # --- 입력 레이아웃
    TENOR_LABELS = ["3M", "6M", "9M", "1Y", "1.5Y", "2Y", "2.5Y", "3Y", "4Y", "5Y", "7Y", "10Y", "15Y", "20Y", "30Y", "50Y"]  # KIS-NET!D1:S1, BOOT!B3:Q3
    TENOR_YEARS = {"3M": 0.25, "6M": 0.5, "9M": 0.75, "1Y": 1.0, "1.5Y": 1.5, "2Y": 2.0, "2.5Y": 2.5, "3Y": 3.0,
                   "4Y": 4.0, "5Y": 5.0, "7Y": 7.0, "10Y": 10.0, "15Y": 15.0, "20Y": 20.0, "30Y": 30.0, "50Y": 50.0}  # BOOT!B10:B25
    MISSING_TOKENS = frozenset({"-", "", "N/A", "n/a", "nan"})  # KIS-NET R58:S58 '-' ; BOOT!R24:R25=0 은 결함 → None (0 금지)
    PCT_TO_DEC = 0.01  # BOOT!B4 ='KIS-NET'!D2/100
    CURVE_IDS = ("RF", "RD")  # BOOT 행4/행5
    # --- 이표주기·이표율
    RF_FREQ = 2  # 한공회 §3.7.3.3(책 p.124) 국고채 반기 ; BOOT!F = E*2
    RD_FREQ = 4  # 한공회 §3.7.3.4(책 p.124) 회사채 분기 ; BOOT!U = T*4
    FREQ_SENSITIVITY_SET = {"RF": [2, 4], "RD": [4]}  # 검토자 Rf_dc(RF 분기 부트스트랩)
    COUPON_CONV = "nominal_div_m"  # c=YTM/m — 한공회 §3.7.3.5, 검토자 Check list!E35 '연간YTM/4' ; 대안 "effective_root" (감사인 Q10-2 ②)
    # --- 부트스트랩·가격·보간 (FORMULA_REFERENCE §3, INTERPOLATION_METHODS §1·§6)
    BOOTSTRAP_MODE = "interpolate_then_bootstrap"  # A(엑셀 BOOT·검토자 Rf_dc) | "bootstrap_with_interpolation" B(한공회 사례1130 §2.2)
    PRICE_MODE = "par"  # BOOT/검토자 PV OF BOND 10000 | "kicpa_conventional"(한공회 §3.7.2, 3M 국채 10,080.6)
    INTERP_METHOD = "linear"  # 검토자 C37 직선보간 ; "pchip" 필수 옵션 ; 비교 전용 natural_cubic/bessel/kruger/smith_wilson
    INTERP_SPACE_PRE = "ytm"  # 모드 A: knot→이표격자 per-period 선형 (BOOT!G/V 재현 오차 0)
    INTERP_METHOD_PRE = "linear"  # 모드 A 이표격자 보간법 — XL BOOT!G/V 선형; PCHIP_TREE 도 이표격자는 선형(PROFILE_DESCRIPTIONS "트리 격자 보간만 PCHIP")
    INTERP_SPACE_GRID = "spot_annual"  # BM MF_INTERPOL 이 BOOT!M(연복리 spot) 선형보간 = 한공회 변형① ; 대안 spot_continuous(②), log_df(④), ytm(③ 재현)
    PCHIP_RECOMMENDED_SPACE = "log_df"  # 카탈로그 §3: PCHIP 은 g=r_c·t 대상일 때 선도 양수·연속 보장 (PCHIP_TREE 프로필이 명시 지정)
    INTERP_TABLE = {  # method_id: (is_local, include) — INTERPOLATION_METHODS §1 (include: must|recommended|compare_only|deferred_step2)
        "linear": (True, "must"), "pchip": (False, "must"),
        "natural_cubic": (False, "compare_only"), "bessel": (False, "compare_only"), "kruger": (False, "compare_only"),
        "smith_wilson": (False, "compare_only"), "monotone_convex": (False, "deferred_step2"),
    }
    EXTRAP_LEFT = "flat"  # spot 공간: 현물 평탄(=선도 r_1 상수, 검토자 weeks1-13) ; log_df 공간: (0,0) 마디 포함 정규 구간 ; "origin_anchored" = VBA MF_INTERPOL Case1 (EXCEL_REF 전용)
    EXTRAP_RIGHT = "flat_forward"  # g(t)=g_n+g'(t_n−)(t−t_n) (카탈로그 §5) | "flat_spot"(Hagan-West) | "excel_zero"(VBA Empty→0, EXCEL_REF 전용; 정상 모드 발동 시 FAIL)
    EXTRAP_LEFT_FLAT_SEVERITY = "WARN"  # 트리 첫 스텝(t<첫 knot)은 구조적으로 항상 해당 → WARN ; "APPROVAL_REQUIRED" 로 되돌릴 수 있음(사용자 결정 2026-09-07: WARN 확정)
    CURVE_HORIZON_Y = 10.0  # BOOT!E29/T49 ; KICPA_1130 프로필 50
    RF_SEED_3M = "none"  # | "excel_ytm_half" (BOOT!L10 = C10/2, EXCEL_REF 전용)
    RF_REGRID_RULE = "interp"  # | "excel_midpoint_per_period" (BOOT!L11:L49 중점, EXCEL_REF 전용)
    MIN_KNOTS = 4  # PCHIP 끝점 3점식 요건 + 여유 (열린 결정)
    SENSITIVITY_COMBOS = [("linear", "spot_annual"), ("pchip", "log_df"), ("linear", "log_df"), ("pchip", "spot_annual"), ("linear", "spot_continuous")]  # 교차 민감도 대상(주 조합 제외) — CROSS_METHOD_DF_WARN 비교 모집단
    PROFILES_IMPLEMENTED = ("DEFAULT", "PCHIP_TREE", "REVIEWER_2024")  # 앱 구현 범위 — 러너 사전 게이트·화면 비활성화 (KICPA_1130 모드 B·EXCEL_REF 결함 재현은 미구현)
    BLOCK_OF_ISSUANCE = {"사모": "사모무보증", "공모": "공모무보증"}  # 발행형태 → KIS-NET 고시 블록(B39 공모무보증 / B54 사모무보증), 감사인 Q13
    RATING_ORDER = ["AAA", "AA+", "AA0", "AA-", "A+", "A0", "A-", "BBB+", "BBB0", "BBB-", "BB+", "BB0", "BB-", "B+", "B0", "B-"]  # KIS-NET 회사채 등급 서열(블록 분할 기준: 서열이 되돌아가면 새 블록); 부호 없는 등급은 "0" 으로 정규화
    NOTCH_DEFAULT = 0  # 한공회 §3.9.1 노칭 (≠0 → NOTCH_APPLIED 승인)
    DF_RANGE = (0.0, 1.0)  # DF 유효 범위(상한 1 = 명목금리 음수 불허 — 열린 결정) ; 부트스트랩 df_valid·트리 df_range_ok
    TOL_DF_MONOTONE = 1e-15  # 트리 DF 비증가 판정 여유(부동소수 반올림)
    BP_PER_UNIT = 1e4; WEEKS_PER_YEAR = 52  # 단위 환산(bp, 증빙 WEEKS 행)
    BLOCK_FALLBACK = {"사모무보증": "공모무보증", "공모무보증": "사모무보증"}  # 요청 블록 결측 시 대체 (감사인 Q13 회신 2025-02-04: 사모 미고시 → 공모 사용) ; 대체 사용 → ROW_FALLBACK 승인
    # --- 격자·일수
    DAYCOUNT = "ACT/365"  # 보고서 T=1633/365 ; "30/360" = 워크시트 함수 YEARFRAC(MAIN_주가!B7,MAIN_주가!B6,0) (XL DATA!A4=3.475, dT=DATA!C4=A4/B4, BM!C3=DATA!$C$4)
    STEP_MODES = {"monthly": 1.0 / 12.0, "weekly": 1.0 / 52.0, "daily": 1.0 / 365.0}  # 앱 노드 간격(월간/주간/일간) → dt(년, 달력 기준; 영업일 격자는 열린 결정) ; provenance.grid_settings.step
    STEP_LABELS = {"monthly": "월간", "weekly": "주간", "daily": "일간"}  # 화면 표시
    AGENCIES = ("KIS", "KAP", "NICE", "FN", "EG")  # 채권평가사 코드(KIS자산평가·한국자산평가·나이스피앤아이·에프앤자산평가·이지자산평가) — 화면 드롭다운
    TREE_GRID = {"mode": "report", "N": 234, "dt_weekly": 1.0 / 52.0}  # report: N 고정(보고서 234) | weekly: dt=1/52(검토자) | excel: N 고정 (XL DATA!B4=181)
    TREE_FWD_RULE = "continuous_from_spot"  # BM C-FWD ; | "piecewise_quarter_step" (검토자 Rf_dc 분기 이산선도→주간)
    NODE_DISCOUNT_CONV = "3_continuous_fwd"  # 감사인 Q8 ③ exp(−f·dt) = XL BM row9, 한공회 §3.7.4.1 ; ① "1_discrete_fwd"(검토자 Check list!E34), ② "2_quarterly_fwd"
    CONVENTION_REASONS = {  # 증빙 관례 선언문에 그대로 삽입되는 사유 문장(자유 텍스트 금지)
        "COUPON_CONV": "시가평가 기준수익률은 채권의 이표 빈도(국고채 6개월·회사채 3개월) 기준으로 고시되므로 기간 이표율은 명목 YTM/m 으로 한다(한공회 §3.7.3.5; 검토자 Check list E35 '연간YTM/4').",
        "NODE_DISCOUNT_CONV": "옵션 평가 모형은 연속복리 현물·선도이자율을 사용하고 할인계수는 exp(−f·dt)이다(한공회 §3.7.4.1~4.3; XL BM row9). 병기하는 ① 값은 XL BM F열 정의 (1+f_cont)^(−dt) 이며 ③ 과의 차이(≈f²dt/2)를 보인다; 일관 복리 하의 1/(1+F_step) 은 ③ 과 항등이라 병기하지 않는다(검토자 Check list E34 대조용).",
        "INTERP_METHOD": "마디 사이 보간은 부트스트랩 내부(모드 B 중간 이표일)와 트리 격자 매핑에 같은 방법·공간을 적용하고 공시한다(한공회 §3.7.3.6).",
        "EXTRAP": "첫 knot 이전은 현물 평탄(검토자 관례), 마지막 knot 이후는 연속복리 선도 평탄 외삽(g 선형 연장)이며 만기>horizon 은 실패 처리한다(카탈로그 §5).",
    }
    DENOM_FLOOR = 1e-12  # 1−c_n·ΣDF ≤ floor → FAIL (BOOT!H 분모)
    EPS_T = 1e-9  # 시간 비교 여유
    T_ROUND_DIGITS = 8  # 격자·이표일 공통 키 round(t, 8)
    ROOT_XTOL = 1e-14; ROOT_MAX_ITER = 200; ROOT_BRACKET_STEP = 0.05; ROOT_BRACKET_EXPANSIONS = 6  # 한공회 해찾기 대체(brent) ; KICPA 재현 실험 1e-12 → 채택 1e-14
    GS_TOL = 1e-14; GS_MAX_SWEEPS = 100  # 비국소 보간(pchip 등) 모드 B 전역 반복 ; 비수렴 → ROOTFIND_FAIL
    # --- 허용오차 (근거 관측치: XL par 1.5e-15, 검토자 MODEL CHECK ~1e-11, 재계산 2e-15)
    TOL_PAR_FAIL = 1e-10
    TOL_PAR_WARN = 1e-12
    TOL_FWD_SPOT_FAIL = 1e-12  # 로그 공간 |Σ ln df_step − ln DF_spot| (검토자 ±2.2e-16) ; 증빙에는 ΠDF−DF 절대차 병기
    TOL_KNOT_ROUNDTRIP = 1e-12  # BOOT!G knot 재현 0.0
    TOL_ROUNDTRIP_COMP = 1e-13  # BOOT!M/N 왕복 ≤2.2e-16
    TOL_EXCEL_RECON = 1e-12  # recompute_boot.py max|err| 2e-15
    TOL_GOLDEN_ABS = {"A": 1e-10, "B": 1e-12, "C_spot": 1e-9, "C_fwd_weekly": 5e-9, "C_pi": 1e-7, "D": 5e-6}  # 골든 원천은 fixture JSON double
    CROSS_METHOD_DF_WARN = 1e-3  # 교차 보간법 DF 상대차 (한공회 사례 §2.3 ≤0.07%)
    FWD_JUMP_WARN_BP = 100.0  # 인접 스텝 연속선도 점프 (검토자 수용 톱니 RF 35bp/RD 250bp — 열린 결정)
    RD_MIN_SPREAD = 0.0  # RD_spot − RF_spot < 0 → RD_LT_RF 승인
    CURVE_DATE_MAX_LAG_DAYS = 3  # 2024-12-31 휴장 vs 12-30 고시 (사용자 결정 2026-09-07: 3일) ; lag<0 또는 >3 → FAIL, 0<lag≤3 → DATE_LAG 승인
    HEADLINE_RULE = "interp_linear_ytm"  # 검토자 Check list!E44 직선보간 (사용자 결정 2026-09-07 확정) ; | "ceil_tenor" (EXCEL_REF: stale 5Y knot 2.765/11.854, T∈(4,5] 기준)
    HEADLINE_DEFS = ["interp_linear_ytm", "ceil_tenor", "nearest_tenor", "spot_annual_at_T", "spot_cont_at_T"]  # 진단표 전용
    HEADLINE_ROUND_DIGITS = 3  # 사용자 결정 2026-09-07: 보고서 표기(2.765/11.854)와 같은 % 소수 3자리 ROUND_HALF_UP 비교
    PAR_FACE = 10000  # 검토자 PV OF BOND 10000
    EXCEL_REPLICATE = False
    AI_ENABLED = False  # TTimes 6단계: API 키 없이 완결
    BASIS = ("nominal_m2", "nominal_m4", "per_period_m2", "per_period_m4", "annual_eff", "continuous", "per_step_simple")  # 한공회 §3.7.4.4
    LABEL_GRAMMAR = {"RF": r"^\s*국고채", "RD": r"회사채\s*(AAA|AA[+\-0]?|A[+\-0]?|BBB[+\-0]?|BB[+\-0]?|B[+\-0]?)\s*$",
                     "BLOCK": r"(공모|사모)\s*무보증"}  # KIS-NET!B2, B39, B54, C42, C58
    PROVENANCE_REQUIRED_FIELDS = ("source_agency", "curve_date", "valuation_date", "file_sha256", "raw_copy_path", "downloaded_at", "operator", "grid_settings.step", "grid_settings.horizon_years",
                                  "method_choice.profile", "method_choice.chosen_by")  # 감사인 Q12 + 격자 설정(노드 간격·산출 기간) + 프로필 선택(PROFILE_SELECTION) ; 누락 → FAIL. 상품(만기·등급)은 선택 입력
    PROVENANCE_APPROVAL_FIELDS = ()  # 사용자 결정 2026-09-08: 캡처 승인 절차 제거(앱이 캡처를 받지 않음 → CAPTURE_MISSING 발생 안 함). 감사인 Q12-2 캡처를 다시 요구하려면 ("capture_path",)
    PROVENANCE_APPROVAL_FIELDS_PRODUCT = ("instrument.rating_evidence.capture_path",)  # 감사인 Q13-1 등급 캡처 — 상품(등급) 정보가 입력된 경우에만 요구
    HUMAN_NODES = ("approve_input", "approve_exception", "approve_curve")
    TERMINAL_NODES = ("done", "fail", "wait_for_human")
    HUMAN_EDGE_ORDER = {  # graph_check 가 이름 시퀀스 완전 일치를 검사
        "approve_input": ["거절", "결정선행", "상수변경감지", "입력변조감지", "승인", "대기"],
        "approve_exception": ["거절", "결정선행", "상수변경감지", "계산상태변조감지", "미확인코드잔존", "승인", "대기"],
        "approve_curve": ["거절", "결정선행", "상수변경감지", "계산상태변조감지", "승인", "대기"],
    }
    CALC_PREFIXES = ("input", "provenance", "labels", "rows", "grid", "interp", "bootstrap", "par_check", "conv",
                     "tree", "fwd", "fwd_spot_check", "sensitivity", "headline", "sanity")
    SNAPSHOT_SCOPE = {"approve_input": ("input", "provenance", "labels"),  # 자기 approval_* 는 set_decision 이 스냅샷 뒤에 쓰므로 제외
                      "approve_exception": CALC_PREFIXES + ("approval_input",),
                      "approve_curve": CALC_PREFIXES + ("approval_input", "approval_exception")}
    EVIDENCE_REQUIRED_ITEMS = ["Q1", "Q8", "Q9_FWD_INPUT", "Q10_1", "Q10_2", "Q11", "Q12", "Q13", "C33", "C34", "C35", "C36", "C37",
                               "C38", "C39", "C40", "C41", "C43", "C44", "C48", "HEADLINE_RF", "HEADLINE_RD", "HEADLINE_RATING",
                               "HEADLINE_BLOCK", "KICPA_INTERP_DISCLOSURE", "RUN_PATH", "APPROVALS"]  # FORMULA_REFERENCE §8 (1단계 몫)
    STEP2_EVIDENCE_ITEMS = ["Q9", "C42", "C45", "C46", "C47"]  # 2단계(트리·일반사채 PV·풋) 산출물 — 1단계 checklist 에 포함하지 않음
    EVIDENCE_FILES = {"01": ("raw_matrix", "csv"), "02": ("rows_used", "csv"), "03": ("knots", "csv"), "04": ("bootstrap", "csv"),
                      "05": ("spot_table", "csv"), "06": ("tree_grid", "csv"), "07": ("par_residuals", "csv"), "08": ("fwd_spot_sample", "md"),
                      "09": ("flags", "csv"), "10": ("headline", "json"), "11": ("sensitivity", "csv"), "12": ("approvals", "json")}  # 번들 규격 (감사인 Q1 '파일/탭/셀')
    XLSX_REQUIRED = True  # 사용자 결정 2026-09-07: xlsx 는 필수 증빙 — 없으면 export 엣지 'xlsx누락' → fail ; openpyxl 은 pyproject 선언 의존성(배포 PC 는 pip install .)
    XLSX_TEMPLATE = "reviewer_2024_dc"  # REV 8521 검토요구사항 xlsx 의 Rf_dc/Rd_dc 시트 서식 재현 + par 검증 행 추가 (docs/XLSX_TEMPLATE.md)
    XLSX_FORMULA_SHEETS = True  # 사용자 결정 2026-09-08: Rf_dc/Rd_dc 는 검토자 시트 그대로 **살아있는 수식 + 원본 서식**(io/reviewer_sheet, docs/REVIEWER_SHEET_SPEC.md). 적용 조건은 reviewer_sheet.applicable(검토자 방식 상수 + 주간/월간 격자); 불가하면 값 시트(XLSX_DC_BLOCKS)
    XLSX_SHEETS = ("INPUT_RAW", "ROWS_USED", "PROVENANCE", "CONVENTIONS", "Rf_dc", "Rd_dc", "PAR_CHECK",
                   "FWD_SPOT_CHECK", "SENSITIVITY", "HEADLINE", "FLAGS", "APPROVALS", "RUN_PATH")  # 시트 순서 고정 ; Rf_dc/Rd_dc 는 행 지향(XLSX_DC_BLOCKS)
    XLSX_DC_STYLE = {"label_col": "B", "first_data_col": "C", "freeze_panes": "E1", "width_label": 18.7, "width_data": 12.7,
                     "title_cell": "B1", "date_cell": "D1", "title_bold": True, "block_title_bold": True}  # REV Rf_dc: B1 '무위험이자율', D1 =Summary!D1(평가기준일), 열 폭 B 18.7/데이터 12.7, 틀 고정 E1
    XLSX_DC_BLOCKS = [  # (블록 제목, [(행 라벨, 원천 state 접두사, 숫자 서식)]) — 열 = 마디(블록 1·3) 또는 격자 스텝(블록 2·4) ; 라벨·서식은 REV Rf_dc r3~r38 원문({…} 커브별 치환: rate=RISK FREE RATE|RISKY RATE, period=HALF-YEAR|QUARTER)
        ("{rate} - YTM", [("WEEKS", "rows", "#,##0_ "), ("TENOR", "rows", "@"), ("{rate} - YTM", "rows", "0.000%"), ("SPOT RATE", "bootstrap", "0.000%")]),
        ("Grid Forward {rate}(INTERPOLATED YTM AND SPOT RATE)", [("STEP", "grid", "#,##0_ "), ("t (years)", "grid", "0.0000_ "), ("{rate} - YTM", "tree", "0.000%"),
                                                                  ("SPOT RATE", "tree", "0.000%"), ("FORWARD RATE", "fwd", "0.000%")]),
        ("BOOTSTRAPPING({period})", [("{period}", "bootstrap", "#,##0_ "), ("WEEKS", "bootstrap", "#,##0_ "), ("YTM - YEARLY", "bootstrap", "0.000%"),
                                     ("{period} PAYMENT RATE", "bootstrap", "0.000%"), ("PV OF PRINCIPAL", "bootstrap", "#,##0.00_ "), ("PV OF BOND", "par_check", "#,##0.00_ "),
                                     ("PVF OF SPOT Rate", "bootstrap", "0.00000_ "), ("SUM OF PVF SPOT JUST PRIOR TO", "bootstrap", "#,##0.0000_ "),
                                     ("{period} SPOT Rate", "bootstrap", "0.000%"), ("SPOT Rate -Yearly", "bootstrap", "0.000%"), ("SPOT Rate -Continuous", "conv", "0.000%"),
                                     ("FORWARD Rate - {period}", "fwd", "0.000%"), ("FORWARD Rate - Yearly", "fwd", "0.000%"),
                                     ("MODEL CHECK (PAR REPRICE)", "par_check", "#,##0.00_ "), ("PAR RESIDUAL", "par_check", "0.00E+00")]),  # par 검증 행 2개 추가(사용자 요청)
        ("Grid Forward {rate}", [("STEP", "grid", "#,##0_ "), ("STEP SPOT RATE", "tree", "0.00000%"), ("FORMULA I", "fwd", "#,##0.0000_ "), ("FORMULA II -CUMM", "fwd", "#,##0.0000_ "),
                                 ("STEP FORWARD RATE", "fwd", "0.00000%"), ("PVF OF FORWARD RATE", "fwd", "0.00000_ "),
                                 ("MODEL CHECK (PROD DF_FWD - DF_SPOT)", "fwd_spot_check", "0.00000%"), ("MODEL CHECK (PV)", "fwd_spot_check", "#,##0.00_ ")]),  # REV 원문 철자 'FOMULA' 는 FORMULA 로
    ]
    XLSX_COLUMNS = {"PAR_CHECK": ["curve", "t", "n", "price", "target", "residual", "residual_x_face"],  # 검토자 MODEL CHECK
                    "FWD_SPOT_CHECK": ["curve", "step", "t", "prod_df_fwd", "df_spot", "diff_log", "diff_prod"],  # 감사인 Q11
                    "RUN_PATH": ["seq", "from", "condition", "to", "ts_utc", "resume_n"],
                    "APPROVALS": ["kind", "requested_at", "snapshot_sha256", "flags_seen", "decision", "approver", "timestamp", "comment", "acknowledged_codes"]}  # 열 지향 시트만 ; Rf_dc/Rd_dc 는 XLSX_DC_BLOCKS
    PROFILES = {  # 상수 오버라이드 dict 일 뿐 판단 로직 없음. fixture 매핑: A=DEFAULT, B=EXCEL_REF, C=REVIEWER_2024, D=KICPA_1130, PCHIP_TREE=A 입력 재사용
        "DEFAULT": {},
        "EXCEL_REF": {"EXCEL_REPLICATE": True, "RF_SEED_3M": "excel_ytm_half", "RF_REGRID_RULE": "excel_midpoint_per_period",
                      "EXTRAP_LEFT": "origin_anchored", "EXTRAP_RIGHT": "excel_zero", "HEADLINE_RULE": "ceil_tenor",
                      "TREE_GRID": {"mode": "excel", "N": 181, "dt_weekly": None}, "DAYCOUNT": "30/360"},  # XL DATA!A4=3.475(YearFrac basis 0), B4=181
        "REVIEWER_2024": {"RF_FREQ": 4, "RD_FREQ": 4, "TREE_GRID": {"mode": "weekly", "N": None, "dt_weekly": 1.0 / 52.0},
                          "INTERP_METHOD": "linear", "INTERP_SPACE_GRID": "log_df",  # 분기 DF 사이 log-linear(=변형 ④) ⇔ 분기 안 선도 일정(검토자 row13/35), (0,1) 마디로 Q1 도 일정
                          "TREE_FWD_RULE": "piecewise_quarter_step", "EXTRAP_LEFT": "flat", "NODE_DISCOUNT_CONV": "1_discrete_fwd"},
        "KICPA_1130": {"BOOTSTRAP_MODE": "bootstrap_with_interpolation", "PRICE_MODE": "kicpa_conventional",
                       "INTERP_SPACE_GRID": "spot_annual", "CURVE_HORIZON_Y": 50.0},
        "PCHIP_TREE": {"INTERP_METHOD": "pchip", "INTERP_SPACE_GRID": "log_df"},
    }

    @classmethod
    def items(cls) -> dict:
        return {k: getattr(cls, k) for k in dir(cls) if k.isupper()}

    @classmethod
    def fingerprint(cls) -> str:
        """대문자 상수 전체(상속 포함)의 결정적 sha256 — 프로세스·PYTHONHASHSEED 무관."""
        return hashlib.sha256(canonical_json(cls.items()).encode("utf-8")).hexdigest()

    @classmethod
    def with_profile(cls, name: str):
        ns = dict(cls.items()); ns.update(cls.PROFILES[name]); ns["PROFILE_NAME"] = name
        return type(f"Constants_{name}", (cls,), ns)

    @classmethod
    def knot_tenors(cls, curve: str) -> list:
        """마디 규칙: 모드 A → 이표 격자(1/m) 위에 놓이는 테너만(RF m=2: 3M/9M 제외) ; 모드 B → 모든 공시 테너. 항상 ≤ horizon."""
        m = cls.RF_FREQ if curve == "RF" else cls.RD_FREQ
        out = []
        for lab in cls.TENOR_LABELS:
            t = cls.TENOR_YEARS[lab]
            if t > cls.CURVE_HORIZON_Y + cls.EPS_T:
                continue
            if cls.BOOTSTRAP_MODE == "interpolate_then_bootstrap" and abs(t * m - round(t * m)) > cls.EPS_T:
                continue
            out.append(lab)
        return out


# ----------------------------------------------------------------------------- State
class NS(dict):
    """dict + 속성 접근. state.input.header_ok 처럼 쓴다."""
    def __getattr__(self, k):
        try:
            return self[k]
        except KeyError as e:
            raise AttributeError(k) from e
    def __setattr__(self, k, v):
        self[k] = v


def _approval() -> NS:
    return NS(requested_at=None, snapshot_sha256=None, flags_seen=[], decision=None, approver=None, timestamp=None,
              comment=None, acknowledged_codes=[], history=[])


def new_state(C=Constants) -> NS:
    """STATE_SCHEMA.md 와 1:1. 노드가 채우기 전의 빈 state."""
    curve = lambda v: {c: (list(v) if isinstance(v, list) else v) for c in C.CURVE_IDS}
    return NS(
        run=NS(run_id=None, profile=C.PROFILE_NAME, curve_set_id=None, base_dir=None, constants_snapshot=None, constants_fingerprint=C.fingerprint(),
               current_node=None, path=[], status="running", paused_at_node=None, snapshot_path=None, paused_at=None, resume_n=0),
        input=NS(raw_text=None, file_sha256=None, n_rows=0, header_labels=[], header_ok=False, rows=[], parse_errors=[], zero_value_cells=[]),
        provenance=NS(source_agency=None, agencies=[], averaging=False,
                      method_choice=NS(profile=None, interp_method=None, interp_space_grid=None, chosen_by=None, chosen_at=None),
                      grid_settings=NS(step=None, horizon_years=None), row_choice=NS(rf_row_index=None, rd_row_index=None),
                      curve_date=None, valuation_date=None, date_lag_days=None,
                      raw_copy_path=None, downloaded_at=None, operator=None, capture_path=None, complete=False,
                      instrument=NS(issuer=None, cb_name=None, maturity_date=None, issuance_type=None, rating=None,
                                    prior_rating_basis=None, prior_block_basis=None, event_dates=[],
                                    rating_evidence=NS(source_agency=None, lookup_date=None, capture_path=None, rating_valid_from=None, sha256=None),
                                    reported_headline=NS(rf_pct=None, rd_pct=None, source_doc=None, page=None,
                                                         basis_rf=f"nominal_m{C.RF_FREQ}", basis_rd=f"nominal_m{C.RD_FREQ}"))),
        labels=NS(parsed=[], rf_candidates=[], rd_candidates=[], unparsed_rows=[]),
        approval_input=_approval(),
        rows=NS(rf=None, rd=None, rd_fallback_used=False, rd_fallback_reason=None, rating_consistency_ok=None, block_consistency_ok=None,
                ytm=curve(None), knot_tenors=curve([]), missing_knots=curve([]), usable_knot_count=curve(0)),
        grid=NS(knots=curve([]), boot_times=curve([]), horizon_years=None, remaining_years=None, maturity_years=None, unused_tenors=curve([]),
                tree=NS(N=None, T=None, dt_mode=None, dt=[], times=[], daycount=None, event_times=[])),
        interp=NS(method=None, method_pre=None, space_pre=None, space_grid=None, extrap_left=None, extrap_right=None, is_local=None,
                  par_coupon_on_grid=None, ytm_on_coupon_grid=curve(None), knot_roundtrip_max_err=None, all_finite=False, extrapolated_points=curve([]), coupon_grid_extrap_used=False),
        bootstrap=NS(mode=None, price_mode=None, status=curve(None), points=curve([]), spot_pp=curve(None), df=curve([]),
                     min_denominator=curve(None), df_valid=curve(False), solver_log=curve([]), errors=[]),
        par_check=NS(per_maturity=curve([]), max_abs_err=None, all_finite=False, unused_knot_max_abs_err=None),
        conv=NS(spot_annual=curve(None), spot_cont=curve(None), roundtrip_max_err=None, all_finite=False),
        tree=NS(spot_annual_on_grid=curve(None), spot_cont_on_grid=curve(None), df_spot_on_grid=curve([]), df_finite=False, df_range_ok=False,
                df_monotone_ok=False, extrap_left_flat_steps=curve([]), extrap_left_origin_steps=curve([]), extrap_right_steps=curve([]),
                excel_zero_used=False, interp_method_used=None, interp_space_used=None, knot_roundtrip_max_err=None, ytm_on_grid=curve(None),
                spot_annual_interp_on_grid=curve(None)),
        fwd=NS(cont_on_grid=curve(None), disc_per_step=curve(None), disc_annual_eff=curve(None), df_step=curve([]), df_step_alt=curve([]), df_cum=curve([]),
               spot_per_step=curve(None), growth_step=curve([]), growth_cum_prev=curve([]), df_backward=curve([]), boot_fwd_pp=curve(None), boot_fwd_annual=curve(None),
               negative_count=curve(0), max_jump_bp=curve(0.0), all_finite=False, rule=None, node_discount_conv=None, node_discount_reason=None, tenor_table=curve([])),
        fwd_spot_check=NS(max_abs_err_log=None, max_abs_err_prod=None, all_finite=False, sample=None, rows=curve([])),
        sensitivity=NS(table=[], max_rel_df_diff=None, freq_alt=NS(), excel_recon=None),
        headline=NS(rule=None, rf_ytm_remaining=None, rd_ytm_remaining=None, rf_spot_remaining_annual=None, rd_spot_remaining_annual=None,
                    candidates=[], reported_rf=None, reported_rd=None, match_ok=None, rating_applied=None, block_applied=None),
        sanity=NS(fail=[], approval_required=[], warn=[]),
        approval_exception=_approval(),
        approval_curve=_approval(),
        export=NS(dir=None, files=[], errors=[], warnings=[], cell_map={}, checklist={}, checklist_detail={}, checklist_all_present=False, conventions_statement=None,
                  xlsx_written=False, xlsx_path=None),
        result=NS(status=None, fail_node=None, fail_edge=None, fail_code=None, fail_reason=None, fail_detail=None,
                  approved_state_path=None, approved_state_sha256=None, next_step_interface=None),
    )


def load_state(obj):
    """스냅샷 JSON(dict) → NS 재귀 변환. run.path 항목은 리스트로 남는다(해시는 JSON 기준이라 동일). CLI resume 가 쓴다."""
    if isinstance(obj, dict):
        return NS({k: load_state(v) for k, v in obj.items()})
    if isinstance(obj, list):
        return [load_state(v) for v in obj]
    return obj


def hash_of(state: NS, prefixes) -> str:
    """승인 시점 변조 감지 해시. 스냅샷 저장/재적재와 같은 정규 JSON 을 기준으로 한다."""
    payload = json.loads(canonical_json({p: state[p] for p in prefixes}))
    return hashlib.sha256(canonical_json(payload).encode("utf-8")).hexdigest()


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


_fin = lambda x: isinstance(x, (int, float)) and not isinstance(x, bool) and math.isfinite(x)
_fin_all = lambda xs: all(_fin(x) for x in xs)


def _get_path(obj, dotted: str):
    for k in dotted.split("."):
        obj = obj.get(k) if isinstance(obj, dict) else None
        if obj is None:
            return None
    return obj


def input_stage_flags(s: NS, C=Constants) -> list:
    """입력 단계 사실 → 코드 매핑(순수 함수). approve_input.flags_seen 과 sanity_check 가 같은 함수를 쓴다(판정 규칙 한 곳)."""
    out = []
    lag = s.provenance.date_lag_days
    if _fin(lag) and 0 < lag <= C.CURVE_DATE_MAX_LAG_DAYS:
        out.append({"severity": "APPROVAL_REQUIRED", "code": "DATE_LAG", "curve": None, "value": lag, "threshold": C.CURVE_DATE_MAX_LAG_DAYS})
    fields = list(C.PROVENANCE_APPROVAL_FIELDS) + (list(C.PROVENANCE_APPROVAL_FIELDS_PRODUCT) if s.provenance.instrument.rating else [])
    for f in fields:
        if _get_path(s.provenance, f) in (None, ""):
            out.append({"severity": "APPROVAL_REQUIRED", "code": "CAPTURE_MISSING", "curve": None, "value": f, "threshold": None})
    if s.input.zero_value_cells:
        out.append({"severity": "WARN", "code": "ZERO_VALUE_CELL", "curve": None, "value": list(s.input.zero_value_cells), "threshold": None})
    if any(p.get("parser") == "llm" for p in s.labels.parsed):
        out.append({"severity": "WARN", "code": "LLM_PARSER_USED", "curve": None, "value": None, "threshold": None})
    if s.labels.unparsed_rows:
        out.append({"severity": "WARN", "code": "UNPARSED_ROWS", "curve": None, "value": list(s.labels.unparsed_rows), "threshold": None})
    return out


# ----------------------------------------------------------------------------- Node stubs (자기 접두사만 채움)
# 각 함수의 docstring = 빌드 단계에서 구현할 알고리즘 요약(출처: FORMULA_REFERENCE.md)
def node_load_matrix(s, C):
    """input.*: 원문 보존, sha256, 헤더 셀 단위 비교(TENOR_LABELS), rows 항목 {row_index, label_raw, block, ytm_pct{tenor→float|None}} (% 원문 유지; ×PCT_TO_DEC 는 select_rows), '-'→None(0 금지), zero_value_cells=[(row_index, tenor_label)] (ZERO_VALUE_CELL 후보), parse_errors."""
    if not s.input.rows:
        s.input.header_ok = False

def node_record_provenance(s, C):
    """provenance.*: data/raw 사본, date_lag_days=(valuation−curve).days, 행 캡처(Q12), 등급 캡처(Q13), instrument, method_choice(사용자가 고른 프로필·chosen_by; interp_method/space 는 C 에서 복사), PROVENANCE_REQUIRED_FIELDS 완전성."""
    p = s.provenance
    if p.method_choice.profile and p.method_choice.interp_method is None:
        p.method_choice.interp_method, p.method_choice.interp_space_grid = C.INTERP_METHOD, C.INTERP_SPACE_GRID
    if p.curve_date and p.valuation_date and p.date_lag_days is None:
        p.date_lag_days = (datetime.fromisoformat(p.valuation_date) - datetime.fromisoformat(p.curve_date)).days
    if not p.agencies and p.source_agency:
        p.agencies = [p.source_agency]
    fields = {"file_sha256": s.input.file_sha256}
    p.complete = all((fields[f] if f in fields else _get_path(p, f)) not in (None, "") for f in C.PROVENANCE_REQUIRED_FIELDS)

def node_interpret_labels(s, C):
    """labels.*: LABEL_GRAMMAR 정규식(기본); parsed 항목 {row_index, kind, rating, block, parser}, rf/rd_candidates 는 parsed 부분집합, unparsed_rows=[row_index]. AI_ENABLED 시 미매칭 행 라벨 문자열만 LLM 에 제안 요청 → 재검증 통과 시 parser='llm'. 숫자 필드 쓰기 금지."""
    pass

def _human(kind):
    def fn(s, C):
        a = s[f"approval_{kind}"]
        if a.requested_at is None:  # 멱등: 재개 시 재기록하지 않음
            a.requested_at = _now()
            a.snapshot_sha256 = hash_of(s, C.SNAPSHOT_SCOPE[f"approve_{kind}"])
            if kind == "input":
                a.flags_seen = input_stage_flags(s, C)
            elif kind == "exception":
                a.flags_seen = list(s.sanity.approval_required)
            else:
                a.flags_seen = list(s.sanity.approval_required) + list(s.sanity.warn)
    fn.__doc__ = f"approval_{kind}.requested_at·snapshot_sha256·flags_seen 만 처음 한 번 기록(멱등). 결정 필드는 set_decision() 전용."
    return fn

node_approve_input = _human("input")
node_approve_exception = _human("exception")
node_approve_curve = _human("curve")

def node_select_rows(s, C):
    """rows.*: RF/RD 행 = provenance.row_choice(사용자 드롭다운 선택; 앱 기본) 또는 상품 정보(등급+BLOCK_OF_ISSUANCE, BLOCK_FALLBACK 대체 시 사실 기록), 전기 등급·블록 일관성, ytm_pct×PCT_TO_DEC → ytm RateVector(basis nominal_m{RF_FREQ}/nominal_m{RD_FREQ} ∈ BASIS), knot_tenors=C.knot_tenors(curve), missing_knots."""
    for c in C.CURVE_IDS:
        if not s.rows.knot_tenors[c]:
            s.rows.knot_tenors[c] = C.knot_tenors(c)

def node_build_grid(s, C):
    """grid.*: knots(≤horizon), boot_times(1/m 격자), 산출 격자 = provenance.grid_settings(step∈STEP_MODES, horizon_years=T → N=T/dt; 앱 기본) 또는 상품 만기(TREE_GRID·DAYCOUNT), remaining_years=T, maturity_years(만기일 있을 때만), tree(N,T,dt,event_times)."""
    if s.grid.horizon_years is None:
        s.grid.horizon_years = C.CURVE_HORIZON_Y

def node_interpolate(s, C):
    """interp.*: method(트리 격자용 INTERP_METHOD)·method_pre(이표격자용 INTERP_METHOD_PRE) 기록, 모드 A 면 이표격자 YTM(ytm_on_coupon_grid) → c_n(COUPON_CONV, par_coupon_on_grid), knot 왕복 검사, 외삽 사용 기록."""
    s.interp.method, s.interp.space_pre, s.interp.space_grid = C.INTERP_METHOD, C.INTERP_SPACE_PRE, C.INTERP_SPACE_GRID
    s.interp.extrap_left, s.interp.extrap_right = C.EXTRAP_LEFT, C.EXTRAP_RIGHT
    s.interp.is_local = C.INTERP_TABLE[C.INTERP_METHOD][0]

def node_bootstrap(s, C):
    """bootstrap.*: 모드 A DF_n=(1−c_nΣDF)/(1+c_n) (BOOT!H/I 동치) / 모드 B knot brent + 중간 이표일 보간(+Gauss-Seidel), df_valid, solver_log."""
    s.bootstrap.mode, s.bootstrap.price_mode = C.BOOTSTRAP_MODE, C.PRICE_MODE

def node_verify_par(s, C):
    """par_check.*: 모든 만기 Σ c·DF + DF_n − 목표가격 (RF/RD), max_abs_err, 미사용 knot 잔차 INFO."""
    pass

def node_convert_compounding(s, C):
    """conv.*: annual=expm1(m·log1p(s)), cont=m·log1p(s) ; 왕복 검사 ; basis annual_eff/continuous (§3.7.4.4 구조적 차단)."""
    pass

def node_map_tree_grid(s, C):
    """tree.*: 동일 보간 함수(interp.method/space_grid)로 spot→트리 격자, DF=exp(−r_c t), 유한·범위(DF_RANGE)·단조(TOL_DF_MONOTONE), 격자 보간체의 마디 왕복 오차(knot_roundtrip_max_err), 외삽 스텝 사실 기록(판정 없음), 실제 사용한 method/space(보간체 객체에서) 기록, ytm_on_grid·spot_annual_interp_on_grid(표시용: INTERP_METHOD_PRE YTM 보간, 연복리 현물 선형보간 = 검토자 row11/row12)."""
    s.tree.interp_method_used, s.tree.interp_space_used = s.interp.method, s.interp.space_grid

def node_compute_forward(s, C):
    """fwd.*: f_i=(lnDF_{i−1}−lnDF_i)/dt_i (BM C-FWD), df_step = exp(−f dt)[③] 또는 1/(1+F)[① NODE_DISCOUNT_CONV=1_discrete_fwd], df_step_alt = 다른 쪽(③ 모드에서는 XL BM F열 (1+f)^(−dt)), F_i=expm1(f dt), 연환산, spot_per_step, growth_step=1+F, growth_cum_prev=Π_{j<k}(1+F_j), df_backward=Π_{j≥k}df_step_j, 부트스트랩 격자 선도(boot_fwd_pp/annual), negative_count, max_jump_bp(BP_PER_UNIT), 테너간 선도표(Q10-1)."""
    s.fwd.rule = C.TREE_FWD_RULE
    s.fwd.node_discount_conv = C.NODE_DISCOUNT_CONV
    s.fwd.node_discount_reason = C.CONVENTION_REASONS["NODE_DISCOUNT_CONV"]

def node_verify_fwd_spot(s, C):
    """fwd_spot_check.*: |Σ_{k≤i}(−f_k dt_k) − ln DF_spot(t_i)| 로그 공간 게이트 + ΠDF−DF 절대차 + Q11 예시."""
    pass

def node_run_sensitivity(s, C):
    """sensitivity.*: (method×space) + FREQ_SENSITIVITY_SET 변형을 순수 함수로 재실행, DF 상대차표(주 커브 불변) ; EXCEL_REF 면 excel_recon."""
    pass

def node_compute_headline(s, C):
    """headline.*: HEADLINE_RULE 잔여만기(grid.maturity_years) YTM(RF/RD), 후보 진단표, reported_*=instrument.reported_headline 복사, ROUND_HALF_UP·HEADLINE_ROUND_DIGITS 자리 비교 → match_ok(True/False; reported 없으면 None). 만기일 없는 커브 전용 실행에서는 후보 없음·None."""
    s.headline.rule = C.HEADLINE_RULE
    rh = s.provenance.instrument.reported_headline
    s.headline.reported_rf, s.headline.reported_rd = rh.rf_pct, rh.rd_pct
    if rh.rf_pct is None and rh.rd_pct is None:
        s.headline.match_ok = None

def node_sanity_check(s, C):
    """sanity.*: 심각도 코드 집계의 유일 지점. 전용 엣지가 처리한 FAIL 은 재평가하지 않는다. sanity.fail = 다중 노드 교차 규칙(INTERP_MISMATCH)."""
    fl, ap, wn = [], [], []
    def add(lst, sev, code, curve=None, value=None, threshold=None, detail=None):
        lst.append({"severity": sev, "code": code, "curve": curve, "value": value, "threshold": threshold, "detail": detail})
    if s.tree.interp_method_used is not None and (s.tree.interp_method_used != s.interp.method or s.tree.interp_space_used != s.interp.space_grid):
        add(fl, "FAIL", "INTERP_MISMATCH", detail=f"tree {s.tree.interp_method_used}/{s.tree.interp_space_used} ≠ interp {s.interp.method}/{s.interp.space_grid}")
    for f in input_stage_flags(s, C):
        (ap if f["severity"] == "APPROVAL_REQUIRED" else wn).append(f)
    for c in C.CURVE_IDS:
        if s.fwd.negative_count[c] > 0: add(ap, "APPROVAL_REQUIRED", "NEG_FWD", c, s.fwd.negative_count[c], 0)
        if s.tree.extrap_left_origin_steps[c]: add(ap, "APPROVAL_REQUIRED", "EXTRAP_LEFT_ORIGIN", c)
        if s.tree.extrap_right_steps[c]: add(ap, "APPROVAL_REQUIRED", "EXTRAP_RIGHT_USED", c)
        if s.tree.extrap_left_flat_steps[c]:
            sev = C.EXTRAP_LEFT_FLAT_SEVERITY
            add(ap if sev == "APPROVAL_REQUIRED" else wn, sev, "EXTRAP_LEFT_FLAT", c)
        if s.fwd.max_jump_bp[c] > C.FWD_JUMP_WARN_BP: add(wn, "WARN", "SAWTOOTH", c, s.fwd.max_jump_bp[c], C.FWD_JUMP_WARN_BP)
        if s.rows.missing_knots[c]: add(ap, "APPROVAL_REQUIRED", "KNOT_MISSING", c, s.rows.missing_knots[c])
    rf, rd = s.tree.spot_annual_on_grid["RF"], s.tree.spot_annual_on_grid["RD"]
    if isinstance(rf, dict) and isinstance(rd, dict) and rf.get("values") and rd.get("values"):
        diffs = [b - a for a, b in zip(rf["values"], rd["values"]) if _fin(a) and _fin(b)]
        if diffs and min(diffs) < C.RD_MIN_SPREAD: add(ap, "APPROVAL_REQUIRED", "RD_LT_RF", None, min(diffs), C.RD_MIN_SPREAD)
    if s.interp.coupon_grid_extrap_used: add(ap, "APPROVAL_REQUIRED", "EXTRAP_COUPON_GRID")
    if s.rows.rd_fallback_used: add(ap, "APPROVAL_REQUIRED", "ROW_FALLBACK", detail=s.rows.rd_fallback_reason)
    if s.rows.rd and s.rows.rd.get("notch", C.NOTCH_DEFAULT) != C.NOTCH_DEFAULT:
        add(ap, "APPROVAL_REQUIRED", "NOTCH_APPLIED", value=s.rows.rd.get("notch"), threshold=C.NOTCH_DEFAULT)
    if s.rows.rating_consistency_ok is False: add(ap, "APPROVAL_REQUIRED", "RATING_CHANGED")
    if s.rows.block_consistency_ok is False: add(ap, "APPROVAL_REQUIRED", "BLOCK_CHANGED")
    if s.headline.match_ok is False: add(ap, "APPROVAL_REQUIRED", "HEADLINE_MISMATCH")
    if C.EXCEL_REPLICATE: add(ap, "APPROVAL_REQUIRED", "EXCEL_REPLICATE_ON")
    if _fin(s.sensitivity.max_rel_df_diff) and s.sensitivity.max_rel_df_diff > C.CROSS_METHOD_DF_WARN:
        add(wn, "WARN", "CROSS_METHOD_DF", value=s.sensitivity.max_rel_df_diff, threshold=C.CROSS_METHOD_DF_WARN)
    if _fin(s.par_check.max_abs_err) and C.TOL_PAR_WARN < s.par_check.max_abs_err <= C.TOL_PAR_FAIL:
        add(wn, "WARN", "PAR_WARN", value=s.par_check.max_abs_err, threshold=C.TOL_PAR_WARN)
    if _fin(s.par_check.unused_knot_max_abs_err) and s.par_check.unused_knot_max_abs_err > 0:
        add(wn, "WARN", "UNUSED_KNOT_RESIDUAL", value=s.par_check.unused_knot_max_abs_err)
    for c in C.CURVE_IDS:
        if s.grid.unused_tenors[c]: add(wn, "WARN", "TENOR_DROPPED", c, s.grid.unused_tenors[c])
    fa = s.sensitivity.freq_alt
    if isinstance(fa, dict) and fa: add(wn, "WARN", "FREQ_SENSITIVITY", value=dict(fa))
    # NONMONO_YTM/NONMONO_SPOT: 역전 커브는 정상 — 이식 시 rows.ytm/conv.spot_annual 로 WARN 만 기록
    s.sanity.fail, s.sanity.approval_required, s.sanity.warn = fl, ap, wn

_LOC_RE = re.compile(r"^[^!\s]+![^!]*!.+$")  # '<file>!<sheet|->!<range|json_path>'

def node_export_evidence(s, C):
    """export.*: EVIDENCE_FILES 01~12 + README_conventions.md(CONVENTION_REASONS·PROFILE_DESCRIPTIONS·상수 전부) + xlsx(XLSX_TEMPLATE: XLSX_SHEETS, Rf_dc/Rd_dc 는 XLSX_DC_BLOCKS·XLSX_DC_STYLE, 나머지 XLSX_COLUMNS; xlsx_written/xlsx_path) + checklist(EVIDENCE_REQUIRED_ITEMS 전항목 위치 유효성). XLSX_REQUIRED 인데 미생성 → 엣지 xlsx누락(FAIL); XLSX_REQUIRED=False 일 때만 export.warnings XLSX_SKIPPED."""
    known = {f.get("path") for f in s.export.files if isinstance(f, dict)}
    det = {}
    for k in C.EVIDENCE_REQUIRED_ITEMS:
        loc = s.export.cell_map.get(k)
        ok = isinstance(loc, str) and bool(_LOC_RE.match(loc)) and (not known or loc.split("!")[0] in known)
        det[k] = {"location": loc, "exists": ok}
    s.export.checklist_detail = det
    s.export.checklist = {k: v["exists"] for k, v in det.items()}
    s.export.checklist_all_present = all(s.export.checklist.values())

def node_done(s, C):
    """result.*: approved_state.json 저장(키 valuation_date__curve_set_id), next_step_interface(경로 참조·basis 선언·할인 규약)."""
    s.result.status = "done"; s.run.status = "done"
    basis = "continuous" if s.interp.space_grid in ("log_df", "spot_continuous") else "annual_eff"
    s.result.next_step_interface = {"rf_spot_cont": "tree.spot_cont_on_grid.RF", "rd_spot_cont": "tree.spot_cont_on_grid.RD",
                                    "rf_fwd_cont": "fwd.cont_on_grid.RF", "rd_fwd_cont": "fwd.cont_on_grid.RD",
                                    "rf_df_step": "fwd.df_step.RF", "rd_df_step": "fwd.df_step.RD", "event_times": "grid.tree.event_times",
                                    "spot_lookup": {"method": "interp.method", "space": "interp.space_grid", "basis": basis},
                                    "node_discount_conv": "fwd.node_discount_conv", "profile": s.run.profile}

def node_fail(s, C):
    """result.*: 실패 노드·엣지·코드(EDGE_CODES)·사유·승인자/코멘트(승인 노드 거절 시) 기록, failed_state.json + 부분 번들. done 으로 가는 엣지 없음."""
    s.result.status = "failed"; s.run.status = "failed"
    if s.run.path:
        frm, edge = s.run.path[-1][0], s.run.path[-1][1]
        s.result.fail_node, s.result.fail_edge = frm, edge
        s.result.fail_code = EDGE_CODES.get((frm, edge))
        s.result.fail_reason = f"{frm}:{edge}"
        det = {"node": frm, "edge": edge, "code": s.result.fail_code}
        if frm in C.HUMAN_NODES:
            a = s[f"approval_{frm.replace('approve_', '')}"]
            det.update(approver=a.approver, comment=a.comment, timestamp=a.timestamp)
        s.result.fail_detail = det

def node_wait_for_human(s, C):
    """run.paused_*: 멈춘 자리 기록 + 스냅샷 저장(state/<key>/snapshot__<node>__<n>.json) + exit 3. 재개는 cli resume → set_decision → run(start=paused_at_node)."""
    s.run.status = "paused"
    s.run.paused_at_node = s.run.path[-1][0] if s.run.path else None
    s.run.paused_at = _now()


# ----------------------------------------------------------------------------- Node registry: id → (한국어 이름, 쓰는 접두사, 함수)
NODES = {
    "load_matrix":         ("매트릭스 적재",        ("input",),               node_load_matrix),
    "record_provenance":   ("출처 기록",            ("provenance",),          node_record_provenance),
    "interpret_labels":    ("행 라벨 해석(AI 허용)", ("labels",),              node_interpret_labels),
    "approve_input":       ("입력 승인(필수)",      ("approval_input",),      node_approve_input),
    "select_rows":         ("행 선택",              ("rows",),                node_select_rows),
    "build_grid":          ("격자 생성",            ("grid",),                node_build_grid),
    "interpolate":         ("보간",                 ("interp",),              node_interpolate),
    "bootstrap":           ("부트스트랩(RF·RD)",    ("bootstrap",),           node_bootstrap),
    "verify_par":          ("파 검증(핵심 게이트)", ("par_check",),           node_verify_par),
    "convert_compounding": ("복리 변환",            ("conv",),                node_convert_compounding),
    "map_tree_grid":       ("트리 격자 매핑",       ("tree",),                node_map_tree_grid),
    "compute_forward":     ("선도금리 산출",        ("fwd",),                 node_compute_forward),
    "verify_fwd_spot":     ("선도-현물 정합(Q11)",  ("fwd_spot_check",),      node_verify_fwd_spot),
    "run_sensitivity":     ("민감도 분석",          ("sensitivity",),         node_run_sensitivity),
    "compute_headline":    ("헤드라인 산출",        ("headline",),            node_compute_headline),
    "sanity_check":        ("건전성 점검·집계",     ("sanity",),              node_sanity_check),
    "approve_exception":   ("예외 승인(조건부)",    ("approval_exception",),  node_approve_exception),
    "approve_curve":       ("최종 커브 승인(필수)", ("approval_curve",),      node_approve_curve),
    "export_evidence":     ("증빙 내보내기",        ("export",),              node_export_evidence),
    "done":                ("완료",                 ("result", "run"),        node_done),
    "fail":                ("실패",                 ("result", "run"),        node_fail),
    "wait_for_human":      ("사람 대기(정지)",      ("run",),                 node_wait_for_human),
}

# ----------------------------------------------------------------------------- EDGES: 유일한 흐름 정의 (위→아래 첫 일치)
ALWAYS = lambda s, C: True  # 기본 엣지 전용 센티널 — 각 노드의 마지막 엣지에만 쓴다

def _pre(kind):  # 결정선행: 요청(requested_at) 이전 시각의 결정이 스냅샷에 들어 있음(외부 편집)
    return lambda s, C: s[f"approval_{kind}"].decision is not None and s[f"approval_{kind}"].timestamp is not None and \
        (s[f"approval_{kind}"].requested_at is None or s[f"approval_{kind}"].timestamp < s[f"approval_{kind}"].requested_at)

EDGES = [
    # load_matrix
    ("load_matrix", "헤더불일치", lambda s, C: not s.input.header_ok, "fail"),
    ("load_matrix", "파싱오류", lambda s, C: len(s.input.parse_errors) > 0, "fail"),
    ("load_matrix", "행없음", lambda s, C: s.input.n_rows == 0, "fail"),
    ("load_matrix", "적재완료", ALWAYS, "record_provenance"),
    # record_provenance
    ("record_provenance", "출처불완전", lambda s, C: not s.provenance.complete, "fail"),
    ("record_provenance", "프로필불일치", lambda s, C: s.provenance.method_choice.profile != C.PROFILE_NAME, "fail"),
    ("record_provenance", "기준일역전_또는_지연초과", lambda s, C: not _fin(s.provenance.date_lag_days) or s.provenance.date_lag_days < 0 or s.provenance.date_lag_days > C.CURVE_DATE_MAX_LAG_DAYS, "fail"),
    ("record_provenance", "출처기록완료", ALWAYS, "interpret_labels"),
    # interpret_labels
    ("interpret_labels", "RF후보없음", lambda s, C: len(s.labels.rf_candidates) == 0, "fail"),
    ("interpret_labels", "라벨해석완료", ALWAYS, "approve_input"),
    # approve_input  [거절 → 결정선행 → 상수변경 → 변조 → 승인 → 대기(ALWAYS)]
    ("approve_input", "거절", lambda s, C: s.approval_input.decision == "rejected", "fail"),
    ("approve_input", "결정선행", _pre("input"), "fail"),
    ("approve_input", "상수변경감지", lambda s, C: s.approval_input.decision is not None and C.fingerprint() != s.run.constants_fingerprint, "fail"),
    ("approve_input", "입력변조감지", lambda s, C: s.approval_input.decision is not None and hash_of(s, C.SNAPSHOT_SCOPE["approve_input"]) != s.approval_input.snapshot_sha256, "fail"),
    ("approve_input", "승인", lambda s, C: s.approval_input.decision == "approved", "select_rows"),
    ("approve_input", "대기", ALWAYS, "wait_for_human"),
    # select_rows
    ("select_rows", "RF행없음", lambda s, C: s.rows.rf is None, "fail"),
    ("select_rows", "RD행없음_대체불가", lambda s, C: s.rows.rd is None, "fail"),
    ("select_rows", "knot부족", lambda s, C: min(s.rows.usable_knot_count[c] for c in C.CURVE_IDS) < C.MIN_KNOTS, "fail"),
    ("select_rows", "행선택완료", ALWAYS, "build_grid"),
    # build_grid  (게이트: 비유한 → 초과 → 기본)
    ("build_grid", "잔여만기비유한", lambda s, C: not (_fin(s.grid.remaining_years) and _fin(s.grid.horizon_years)), "fail"),
    ("build_grid", "만기초과", lambda s, C: s.grid.remaining_years > s.grid.horizon_years + C.EPS_T, "fail"),
    ("build_grid", "격자완료", ALWAYS, "interpolate"),
    # interpolate
    ("interpolate", "보간비유한", lambda s, C: not (s.interp.all_finite and _fin(s.interp.knot_roundtrip_max_err)), "fail"),
    ("interpolate", "knot왕복불일치", lambda s, C: s.interp.knot_roundtrip_max_err > C.TOL_KNOT_ROUNDTRIP, "fail"),
    ("interpolate", "보간완료", ALWAYS, "bootstrap"),
    # bootstrap
    ("bootstrap", "DF무효_비유한", lambda s, C: any(s.bootstrap.status[c] == "FAIL_DF_INVALID" or not s.bootstrap.df_valid[c] for c in C.CURVE_IDS), "fail"),
    ("bootstrap", "분모비양수", lambda s, C: any(s.bootstrap.status[c] == "FAIL_DENOMINATOR" for c in C.CURVE_IDS), "fail"),
    ("bootstrap", "근찾기실패_비수렴", lambda s, C: any(s.bootstrap.status[c] in ("FAIL_BRACKET", "FAIL_NO_CONVERGENCE") for c in C.CURVE_IDS), "fail"),
    ("bootstrap", "부트스트랩완료", ALWAYS, "verify_par"),
    # verify_par
    ("verify_par", "파잔차비유한", lambda s, C: not (s.par_check.all_finite and _fin(s.par_check.max_abs_err)), "fail"),
    ("verify_par", "파검증실패", lambda s, C: s.par_check.max_abs_err > C.TOL_PAR_FAIL, "fail"),
    ("verify_par", "파검증통과", ALWAYS, "convert_compounding"),
    # convert_compounding
    ("convert_compounding", "변환비유한", lambda s, C: not (s.conv.all_finite and _fin(s.conv.roundtrip_max_err)), "fail"),
    ("convert_compounding", "왕복변환불일치", lambda s, C: s.conv.roundtrip_max_err > C.TOL_ROUNDTRIP_COMP, "fail"),
    ("convert_compounding", "변환완료", ALWAYS, "map_tree_grid"),
    # map_tree_grid
    ("map_tree_grid", "트리DF비유한", lambda s, C: not (s.tree.df_finite and _fin(s.tree.knot_roundtrip_max_err)), "fail"),
    ("map_tree_grid", "격자knot왕복불일치", lambda s, C: s.tree.knot_roundtrip_max_err > C.TOL_KNOT_ROUNDTRIP, "fail"),
    ("map_tree_grid", "엑셀제로외삽_정상모드", lambda s, C: s.tree.excel_zero_used and not C.EXCEL_REPLICATE, "fail"),
    ("map_tree_grid", "DF범위_또는_단조위반", lambda s, C: not (s.tree.df_range_ok and s.tree.df_monotone_ok), "fail"),
    ("map_tree_grid", "격자매핑완료", ALWAYS, "compute_forward"),
    # compute_forward
    ("compute_forward", "선도비유한", lambda s, C: not s.fwd.all_finite, "fail"),
    ("compute_forward", "선도완료", ALWAYS, "verify_fwd_spot"),
    # verify_fwd_spot
    ("verify_fwd_spot", "정합잔차비유한", lambda s, C: not (s.fwd_spot_check.all_finite and _fin(s.fwd_spot_check.max_abs_err_log)), "fail"),
    ("verify_fwd_spot", "정합실패", lambda s, C: s.fwd_spot_check.max_abs_err_log > C.TOL_FWD_SPOT_FAIL, "fail"),
    ("verify_fwd_spot", "정합통과", ALWAYS, "run_sensitivity"),
    # run_sensitivity / compute_headline
    ("run_sensitivity", "민감도완료", ALWAYS, "compute_headline"),
    ("compute_headline", "헤드라인미비교", lambda s, C: (s.headline.reported_rf is not None or s.headline.reported_rd is not None) and s.headline.match_ok is None, "fail"),
    ("compute_headline", "헤드라인완료", ALWAYS, "sanity_check"),
    # sanity_check
    ("sanity_check", "FAIL플래그존재", lambda s, C: len(s.sanity.fail) > 0, "fail"),
    ("sanity_check", "승인필요플래그존재", lambda s, C: len(s.sanity.approval_required) > 0, "approve_exception"),
    ("sanity_check", "플래그없음", ALWAYS, "approve_curve"),
    # approve_exception  [거절 → 결정선행 → 상수변경 → 변조 → 미확인코드 → 승인 → 대기]
    ("approve_exception", "거절", lambda s, C: s.approval_exception.decision == "rejected", "fail"),
    ("approve_exception", "결정선행", _pre("exception"), "fail"),
    ("approve_exception", "상수변경감지", lambda s, C: s.approval_exception.decision is not None and C.fingerprint() != s.run.constants_fingerprint, "fail"),
    ("approve_exception", "계산상태변조감지", lambda s, C: s.approval_exception.decision is not None and hash_of(s, C.SNAPSHOT_SCOPE["approve_exception"]) != s.approval_exception.snapshot_sha256, "fail"),
    ("approve_exception", "미확인코드잔존", lambda s, C: s.approval_exception.decision == "approved" and bool({f["code"] for f in s.sanity.approval_required} - set(s.approval_exception.acknowledged_codes)), "wait_for_human"),
    ("approve_exception", "승인", lambda s, C: s.approval_exception.decision == "approved", "approve_curve"),
    ("approve_exception", "대기", ALWAYS, "wait_for_human"),
    # approve_curve
    ("approve_curve", "거절", lambda s, C: s.approval_curve.decision == "rejected", "fail"),
    ("approve_curve", "결정선행", _pre("curve"), "fail"),
    ("approve_curve", "상수변경감지", lambda s, C: s.approval_curve.decision is not None and C.fingerprint() != s.run.constants_fingerprint, "fail"),
    ("approve_curve", "계산상태변조감지", lambda s, C: s.approval_curve.decision is not None and hash_of(s, C.SNAPSHOT_SCOPE["approve_curve"]) != s.approval_curve.snapshot_sha256, "fail"),
    ("approve_curve", "승인", lambda s, C: s.approval_curve.decision == "approved", "export_evidence"),
    ("approve_curve", "대기", ALWAYS, "wait_for_human"),
    # export_evidence
    ("export_evidence", "쓰기오류", lambda s, C: len(s.export.errors) > 0, "fail"),
    ("export_evidence", "xlsx누락", lambda s, C: C.XLSX_REQUIRED and not s.export.xlsx_written, "fail"),
    ("export_evidence", "증빙불완전", lambda s, C: not s.export.checklist_all_present, "fail"),
    ("export_evidence", "내보내기완료", ALWAYS, "done"),
]

# 임계 게이트(첫 엣지가 '…비유한' 이어야 함)
GATE_NODES = ("build_grid", "interpolate", "bootstrap", "verify_par", "convert_compounding", "map_tree_grid", "compute_forward", "verify_fwd_spot")

# FAIL 엣지 → 심각도 코드 (GRAPH_SPEC §2 코드 열·§5 FAIL 행은 이 표에서 생성)
EDGE_CODES = {
    ("load_matrix", "헤더불일치"): "HEADER_MISMATCH", ("load_matrix", "파싱오류"): "PARSE_ERROR", ("load_matrix", "행없음"): "MATRIX_EMPTY",
    ("record_provenance", "출처불완전"): "PROVENANCE_INCOMPLETE", ("record_provenance", "프로필불일치"): "PROFILE_MISMATCH", ("record_provenance", "기준일역전_또는_지연초과"): "DATE_LAG_OUT_OF_RANGE",
    ("interpret_labels", "RF후보없음"): "NO_RF_CANDIDATE",
    ("approve_input", "거절"): "APPROVAL_REJECTED", ("approve_input", "결정선행"): "DECISION_BEFORE_REQUEST", ("approve_input", "상수변경감지"): "CONSTANTS_CHANGED", ("approve_input", "입력변조감지"): "INPUT_TAMPERED",
    ("select_rows", "RF행없음"): "ROW_MISSING_RF", ("select_rows", "RD행없음_대체불가"): "ROW_MISSING_RD", ("select_rows", "knot부족"): "TOO_FEW_KNOTS",
    ("build_grid", "잔여만기비유한"): "MATURITY_NONFINITE", ("build_grid", "만기초과"): "MATURITY_GT_HORIZON",
    ("interpolate", "보간비유한"): "INTERP_NONFINITE", ("interpolate", "knot왕복불일치"): "KNOT_ROUNDTRIP",
    ("bootstrap", "DF무효_비유한"): "BOOT_DF_INVALID", ("bootstrap", "분모비양수"): "DENOM_NONPOS", ("bootstrap", "근찾기실패_비수렴"): "ROOTFIND_FAIL",
    ("verify_par", "파잔차비유한"): "PAR_NONFINITE", ("verify_par", "파검증실패"): "PAR_RESIDUAL",
    ("convert_compounding", "변환비유한"): "COMP_NONFINITE", ("convert_compounding", "왕복변환불일치"): "COMP_ROUNDTRIP",
    ("map_tree_grid", "트리DF비유한"): "TREE_DF_NONFINITE", ("map_tree_grid", "격자knot왕복불일치"): "TREE_KNOT_ROUNDTRIP", ("map_tree_grid", "엑셀제로외삽_정상모드"): "EXCEL_ZERO_OUTSIDE_REPLICATE", ("map_tree_grid", "DF범위_또는_단조위반"): "DF_RANGE_OR_MONOTONE",
    ("compute_forward", "선도비유한"): "FWD_NONFINITE",
    ("verify_fwd_spot", "정합잔차비유한"): "FWD_SPOT_NONFINITE", ("verify_fwd_spot", "정합실패"): "FWD_SPOT_MISMATCH",
    ("compute_headline", "헤드라인미비교"): "HEADLINE_NOT_COMPARED",
    ("sanity_check", "FAIL플래그존재"): "SANITY_FAIL",
    ("approve_exception", "거절"): "APPROVAL_REJECTED", ("approve_exception", "결정선행"): "DECISION_BEFORE_REQUEST", ("approve_exception", "상수변경감지"): "CONSTANTS_CHANGED", ("approve_exception", "계산상태변조감지"): "STATE_TAMPERED",
    ("approve_curve", "거절"): "APPROVAL_REJECTED", ("approve_curve", "결정선행"): "DECISION_BEFORE_REQUEST", ("approve_curve", "상수변경감지"): "CONSTANTS_CHANGED", ("approve_curve", "계산상태변조감지"): "STATE_TAMPERED",
    ("export_evidence", "쓰기오류"): "EXPORT_ERROR", ("export_evidence", "xlsx누락"): "XLSX_MISSING", ("export_evidence", "증빙불완전"): "EVIDENCE_INCOMPLETE",
}


# ----------------------------------------------------------------------------- Router
def run(state: NS, C=Constants, start: str | None = None, max_steps: int = 200, nodes=None) -> NS:
    """위→아래 첫 일치 엣지. 노드는 채우기만, 라우팅은 여기서만. wait_for_human/done/fail 에서 반환.
    start 는 재개 전용: 승인 노드이며 run.paused_at_node 와 같아야 한다. 재개는 C = Constants.with_profile(state.run.profile) 로 호출한다.
    nodes 는 노드 함수 등록표(기본 NODES = 스텁; 앱은 nodes 패키지의 구현표를 넘긴다). EDGES 는 바뀌지 않는다."""
    NODES_ = nodes or NODES
    if set(NODES_) != set(NODES):
        raise ValueError("노드 등록표의 id 집합이 NODES 와 다름")
    for nid in NODES:  # 접두사 튜플 동일 + 승인·종단·sanity_check 는 반드시 이 파일의 함수(set_decision 우회·집계 교체 차단)
        if tuple(NODES_[nid][1]) != tuple(NODES[nid][1]):
            raise ValueError(f"노드 {nid} 의 접두사가 NODES 와 다름")
        if nid in C.HUMAN_NODES + C.TERMINAL_NODES + ("sanity_check",) and NODES_[nid][2] is not NODES[nid][2]:
            raise ValueError(f"노드 {nid} 함수는 교체할 수 없음(step1_graph 전용)")
    if start is None:
        if C.fingerprint() != state.run.constants_fingerprint:
            raise ValueError("state 가 다른 Constants(프로필)로 생성됨 — new_state(C) 와 run(state, C) 의 C 가 같아야 함")
        current = "load_matrix"
    else:
        if start not in C.HUMAN_NODES or start != state.run.paused_at_node:
            raise ValueError(f"재개는 승인 노드(run.paused_at_node={state.run.paused_at_node})에서만 가능: {start}")
        state.run.resume_n += 1
        current = start
    state.run.status = "running"
    for _ in range(max_steps):
        if current not in NODES_:
            raise ValueError(f"미등록 노드: {current}")
        state.run.current_node = current
        NODES_[current][2](state, C)
        if current in C.TERMINAL_NODES:
            return state
        for frm, name, cond, to in EDGES:
            if frm == current and cond(state, C):
                state.run.path.append((frm, name, to, _now(), state.run.resume_n))
                current = to
                break
        else:
            raise RuntimeError(f"no matching edge from {current} (EDGES 불변식 위반)")
    raise RuntimeError("max_steps exceeded")


def set_decision(state: NS, kind: str, decision: str, approver: str, comment: str = "", acknowledged_codes=()):
    """approval_<kind> 의 결정 필드만 쓴다(append-only history 포함). 정지 중인 바로 그 승인 노드에만 기록할 수 있다."""
    if kind not in ("input", "exception", "curve") or decision not in ("approved", "rejected"):
        raise ValueError("kind ∈ {input, exception, curve}, decision ∈ {approved, rejected}")
    if not (isinstance(approver, str) and approver.strip()):
        raise ValueError("approver 는 비어 있을 수 없음")
    a = state[f"approval_{kind}"]
    if a.requested_at is None or a.snapshot_sha256 is None:
        raise ValueError(f"approve_{kind}: 승인 요청 전에는 결정을 기록할 수 없음")
    if state.run.status != "paused" or state.run.paused_at_node != f"approve_{kind}":
        raise ValueError(f"approve_{kind}: 정지 중인 노드(run.paused_at_node={state.run.paused_at_node})에만 결정 가능")
    seen = {f["code"] for f in a.flags_seen}
    unknown = set(acknowledged_codes) - seen
    if unknown:
        raise ValueError(f"acknowledged_codes 가 flags_seen 밖: {sorted(unknown)}")
    a.decision, a.approver, a.timestamp, a.comment = decision, approver, _now(), comment
    a.acknowledged_codes = list(acknowledged_codes)
    a.history.append({"decision": decision, "approver": approver, "timestamp": a.timestamp, "comment": comment,
                      "acknowledged_codes": list(acknowledged_codes), "snapshot_sha256": a.snapshot_sha256, "resume_n": state.run.resume_n + 1})
    return state


def to_mermaid(highlight_path=None) -> str:
    """EDGES → mermaid flowchart (viewer.html / 문서 공용)."""
    hp = {(p[0], p[1], p[2]) for p in (highlight_path or [])}
    out = ["flowchart TD"]
    for nid, (ko, _, _) in NODES.items():
        shape = ("([%s])" if nid in Constants.HUMAN_NODES else "[[%s]]" if nid in Constants.TERMINAL_NODES else "[%s]") % f"{nid}<br/>{ko}"
        out.append(f"  {nid}{shape}")
    for f, n, _, t in EDGES:
        arrow = "==>" if (f, n, t) in hp else "-->"
        out.append(f"  {f} {arrow}|{n}| {t}")
    return "\n".join(out)


def export_edges_json() -> dict:
    return {"schema_version": Constants.STATE_SCHEMA_VERSION, "constants_fingerprint": Constants.fingerprint(),
            "nodes": [{"id": k, "name_ko": v[0], "writes": list(v[1])} for k, v in NODES.items()],
            "edges": [{"from": f, "condition": n, "to": t, "order": i, "code": EDGE_CODES.get((f, n))} for i, (f, n, _, t) in enumerate(EDGES)],
            "human_nodes": list(Constants.HUMAN_NODES), "terminal_nodes": list(Constants.TERMINAL_NODES), "gate_nodes": list(GATE_NODES)}
