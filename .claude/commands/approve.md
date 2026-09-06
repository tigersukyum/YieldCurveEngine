---
description: 멈춘 스냅샷에 승인/거절을 기록(set_decision)하고 같은 승인 노드에서 재개 — 승인자·코멘트·ack 는 사용자 확인 후
argument-hint: <snapshot.json> approved|rejected
---
멈춘 스냅샷에 승인/거절을 기록하고 같은 노드에서 재개한다. `$1` = 스냅샷 경로(`state/<valuation_date>__<curve_set_id>/snapshot__<node>__<n>.json`), `$2` = `approved` | `rejected`. 승인자·코멘트·확인 코드는 사용자에게 확인한 뒤 전달한다.

1. 스냅샷의 `run.paused_at_node`·`approval_<kind>.flags_seen`을 읽어 사용자에게 보여주고 승인자 이름, 코멘트, (approve_exception이면) `--ack CODE` 목록(코드 단위, flags_seen 의 코드만 가능)을 확정받는다. AI가 대신 승인하지 않는다.
2. 실행: `python -m cb_valuation.step1_curve.app.cli resume --snapshot $1 --decision $2 --approver "<이름>" --comment "<문장>" [--ack CODE ...]` (없으면 "미구현 — BUILD_PROMPTS 2·7단계" 보고). CLI 는 `load_state` → `Constants.with_profile(run.profile)` → `set_decision` → `run(start=paused_at_node)` 순서다.
3. 출력 원문과 재개 후 `run.path`(마지막 엣지 이름)·`run.status`·`run.resume_n`을 붙인다. `미확인코드잔존`으로 다시 멈추면 빠진 코드를 알려준다. 거절이면 `result.fail_reason`·`fail_detail`을 인용한다. `결정선행`·`상수변경감지`·`변조감지`로 fail 하면 스냅샷 외부 편집 여부를 사용자에게 묻는다.
