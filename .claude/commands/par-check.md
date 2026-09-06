---
description: 부트스트랩 만기별 par 재가격 잔차를 계산해 Constants.TOL_PAR_FAIL 로 판정 (RF/RD/ALL)
argument-hint: [RF|RD|ALL] [state.json]
---
부트스트랩 만기별 par 재가격 잔차(Σ c·DF + DF_n − 목표가격)를 코드로 계산해 `Constants.TOL_PAR_FAIL`로 판정한다. `$1` = `RF` | `RD` | `ALL`(비우면 ALL), `$2` = state JSON 경로(선택; 비우면 최신 `state/` 스냅샷).

1. 스크립트가 있으면 실행: `python cb_valuation/step1_curve/scripts/par_check.py --curve $1` — `$2`가 있으면 `--state $2`를 덧붙인다. 없으면 "미구현 — BUILD_PROMPTS 4b·9단계에서 생성"이라고 보고하고 추정 결과를 쓰지 않는다. 임시 대안: `python cb_valuation/step1_curve/reference/recompute_boot.py`의 par 검증 섹션 출력을 인용(참조 엑셀 캐시 기준).
2. 출력 원문(만기별 잔차, PAR_FACE 환산 열, max|잔차|, 미사용 knot 잔차 INFO)을 붙인다.
3. max|잔차| > TOL_PAR_FAIL이면 FAIL(엣지 `파검증실패`), TOL_PAR_WARN < 잔차 ≤ TOL_PAR_FAIL이면 WARN(PAR_WARN). RF·RD 둘 다 실행됐는지 확인한다.
4. 허용오차 값은 쓰지 말고 상수명으로 인용한다.
