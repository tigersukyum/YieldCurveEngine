---
description: 트리 격자 전 점에서 Π DF_fwd = DF_spot (감사인 Q11) 을 로그 공간 잔차로 검증
argument-hint: <state.json>
---
선도-현물 정합(감사인 Q11): 트리 격자 모든 점에서 Π_{k≤i} DF_fwd(k) = DF_spot(t_i) 를 로그 공간(`|Σ −f_k·dt_k − ln DF_spot|`)과 곱 절대차로 계산하고 예시 1건(마지막 격자점)을 출력한다. `$1` = state JSON 경로.

1. 실행: `python cb_valuation/step1_curve/scripts/fwd_spot_check.py --state $1` (없으면 "미구현 — BUILD_PROMPTS 4c단계" 보고).
2. 출력 원문을 붙이고 max 로그 잔차를 `Constants.TOL_FWD_SPOT_FAIL`과 비교해 판정한다(엣지 `정합실패`/`정합잔차비유한`).
3. Q11 제출용 예시(커브, step, t, Π DF_fwd, DF_spot, 차이)를 검토자 형식(`docs/AUDITOR_QA.md` Q11, fixture C 의 week 520 예시)으로 인용한다.
