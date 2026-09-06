---
description: EDGES 불변식·두 갈래 시나리오(전 엣지 커버)·노드 쓰기 추적·상수 지문 결정성을 graph_check.py 로 검사하고 출력 원문을 보고
---
EDGES 불변식과 두 갈래 드라이런을 코드로 검사한다. 판단은 스크립트가 하고, 너는 출력 원문을 그대로 붙인 뒤 해석만 한다.

1. 실행: `python cb_valuation/step1_curve/graph/graph_check.py`
2. 종료코드와 출력 전문을 보고에 붙인다(요약 금지). 네 부분(static invariants / two-branch scenarios / node write ownership / GRAPH_SPEC.md 신선도)의 판정을 각각 옮긴다. 위반이 있으면 각 줄을 `cb_valuation/step1_curve/docs/GRAPH_SPEC.md`의 절 번호(§2 엣지 순서, §4 시나리오 id, §6 승인 순서)와 함께 표로 정리하고 curve-fixer에 넘길 위반 번호를 매긴다.
3. 출력에 `GRAPH_SPEC.md 구버전` 이 있으면 `python cb_valuation/step1_curve/graph/export_spec.py`를 실행해 동기화하고 다시 1을 실행한다. 생성물 `graph/edges_export.json`·`graph/graph.mmd`는 커밋 대상이 아니다.
4. exit 0이 아니면 "완료"라고 쓰지 않는다.
