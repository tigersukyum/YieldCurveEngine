---
description: 보간 플러그인 수치 검사 — 참조 구현 테스트(PCHIP 확정 공식) → knot 왕복·MATLAB 예제·교차 방법 DF 차이표
argument-hint: [method] [space]
---
보간 플러그인 수치 검사. `$1`=method(linear|pchip|natural_cubic|…), `$2`=space(spot_annual|spot_continuous|log_df|ytm). 둘 다 비우면 전수(옵션 생략).

1. 참조 구현 테스트를 먼저 실행: `python cb_valuation/step1_curve/reference/test_interp_ref.py` (PCHIP은 scipy·SLATEC·MATLAB 예제와 대조 검증된 확정 공식 — `cb_valuation/step1_curve/docs/INTERPOLATION_METHODS.md §3`). TOTAL FAILURES가 0이 아니면 여기서 멈춘다.
2. 앱 스크립트가 있으면 실행: `python cb_valuation/step1_curve/scripts/interp_check.py` 에 `$1`이 있으면 `--method $1`, `$2`가 있으면 `--space $2`를 덧붙인다 — knot 왕복(TOL_KNOT_ROUNDTRIP), PCHIP 기울기 MATLAB 예제(INTERPOLATION_METHODS §7), 교차 방법·공간 DF 차이표(CROSS_METHOD_DF_WARN), Gauss-Seidel 수렴 로그, 외삽 플래그(EXTRAP_LEFT_FLAT/EXTRAP_RIGHT_USED). 없으면 "미구현 — BUILD_PROMPTS 4a단계" 보고.
3. `docs/INTERPOLATION_METHODS.md §7`의 방법별 검증 테스트 중 실행되지 않은 항목을 목록화한다.
4. 출력 원문을 붙인다. 숫자를 요약·반올림해 재서술하지 않는다.
