---
description: 두 갈래 확인 — graph_check.SCENARIOS(A01~A04·E01~E50)가 그래프(스텁)와 엔진(실제 노드) 양쪽에서 기대 엣지로 갈라지는지 확인
---
두 갈래 확인: 기준값 양쪽 입력으로 경로가 실제로 갈라지는지 코드로 확인한다. 시나리오 id·설명·기대 마지막 엣지·기대 status 의 유일한 원천은 `graph_check.SCENARIOS`(문서 사본: `cb_valuation/step1_curve/docs/GRAPH_SPEC.md §4`).

1. 그래프 수준(스텁): `python cb_valuation/step1_curve/graph/graph_check.py` — "two-branch scenarios" 부분과 미커버 엣지 목록(있으면)을 원문으로 붙인다.
2. 엔진 수준(빌드 후): `python -m unittest cb_valuation.step1_curve.tests.test_edges_two_branch -v` (없으면 "미구현 — BUILD_PROMPTS 8단계" 보고).
3. 각 시나리오의 기대 마지막 엣지 이름과 실제가 일치하는지 표(id | 기대 엣지/status | 실제 | 판정)로 정리한다. 오염 입력(E*)이 반드시 fail 또는 approve_exception/wait_for_human 에서 멈췄는지, 정상 입력(A*)이 done 에 갔는지 확인한다.
4. 의도대로 갈라지지 않으면 "완료"라고 쓰지 말고 의심 노드·엣지를 특정해 curve-fixer에 넘긴다.
