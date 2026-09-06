---
name: bond-curve-conventions
description: 이자율 커브 코드(cb_valuation/step1_curve/curve/*, nodes/*, io/*, graph/step1_graph.py Constants·EDGES)를 편집하거나 새 보간 플러그인·노드·엣지를 추가할 때 자동으로 적용하는 관례 — basis 라벨, 주기 상수, 출처 주석, fsum/log1p/expm1, 노드 자기 필드 규칙, 편집 후 /graph-check·/par-check 실행. 트리거: 부트스트래핑, 보간(PCHIP/선형), 복리 변환, 선도이자율, DF, par 검증, 커브 노드/엣지 수정.
---

이 스킬이 적용되면 아래 규칙을 즉시 따른다. 설명하지 말고 적용한다. 한국어로 응답하고 식별자·공식은 영문.

1. **금리 배열**은 `RateVector(values, times, basis)`로만 만든다. `basis ∈ Constants.BASIS`. DF는 `annual_eff` 또는 `continuous`에서만 계산한다(`per_period`/`nominal` → `exp()` 금지, 한공회 §3.7.4.4). 변환은 `r_c = m·ln(1 + r_m/m)`, `annual = (1+s)^m − 1 = expm1(m·log1p(s))`.
2. **상수**: 주기·이표 변환·보간·외삽·허용오차·격자 값은 `graph/step1_graph.py`의 `Constants`에서 import한다. 코드·테스트·문서에 숫자 리터럴로 임계값을 적지 않는다. 새 수치 상수는 출처 주석(엑셀 셀 / 한공회 절 / fixture) 없이 추가 금지.
3. **수치**: `math.fsum`, `log1p`, `expm1`; `(1+s)^m − 1` 직접 계산 금지; 격자·이표일 키는 `round(t, Constants.T_ROUND_DIGITS)`; 결측 `'-'`는 `None`(0 금지).
4. **공식 변경** 시 `docs/FORMULA_REFERENCE.md`의 같은 항목을, **state 필드 추가** 시 `docs/STATE_SCHEMA.md`와 `new_state()`를 같은 커밋에서 갱신한다.
5. **보간 플러그인 추가**: `Constants.INTERP_TABLE`에 `(is_local, include)` 등록 + knot 왕복 테스트 + (PCHIP 계열이면) MATLAB 예제 `x=−3..3, y=[−1,−1,−1,0,1,1,1] → d=[0,0,0,1,0,0,0]` 테스트. 추가 방법은 `docs/INTERPOLATION_METHODS.md` 카탈로그에서 must/recommended/optional 판정을 인용한다. 같은 보간 함수 객체를 부트스트랩 내부(모드 B)와 트리 격자 매핑에 쓴다.
6. **노드 편집**: NODES 등록표의 자기 접두사 밖 필드 쓰기 금지, 다음 노드 반환 금지, 심각도 판정은 `sanity_check`와 EDGES 람다에만.
7. **엣지 추가**: 예외 엣지를 기본(True) 엣지 위에, 임계 게이트에는 `비유한` 엣지를 첫 번째로, 승인 노드는 `[거절][상수변경][변조][(미확인코드)][승인][대기]` 순서.
8. **편집 후** `python cb_valuation/step1_curve/graph/graph_check.py`와 관련 테스트(`python -m unittest …`, `/par-check`)를 실행하고 출력 원문을 첨부한다. "완료" 문장만으로 끝내지 않는다.
9. 참조 구현 `reference/interp_ref.py`(scipy 대조 검증)의 PCHIP 기울기 규칙은 바꾸지 않는다. 바꿔야 한다면 근거(원본 소스 URL)와 재검증 결과를 먼저 제시한다.
