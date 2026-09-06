---
description: 매트릭스 파일을 승인 없이 sanity_check 까지 드라이런(입력 승인은 approver 'dry-run' 자동) — 심각도 표·헤드라인·민감도 출력
argument-hint: --matrix <path> --valuation-date <YYYY-MM-DD> --profile DEFAULT|PCHIP_TREE|KICPA_1130|REVIEWER_2024|EXCEL_KBI
---
매트릭스 파일 하나를 드라이런하고 심각도 표·헤드라인·민감도를 출력한다(검토 준비용). `$ARGUMENTS` = `--matrix <path> --valuation-date <YYYY-MM-DD> --profile NAME`. **`--profile` 은 필수**(PROFILE_SELECTION=required — 빠지면 스크립트가 PROFILE_DESCRIPTIONS 목록을 보여주고 종료; AI 가 대신 고르지 않는다).

드라이런 정의(GRAPH_SPEC §6): 하네스가 approve_input 정지에서 `set_decision(approver='dry-run')`으로 입력 승인만 자동 기록하고 계산을 끝까지 돌린 뒤, approve_exception/approve_curve 정지에서는 재개하지 않고 보고 후 종료한다. `state/` 스냅샷과 `approved_state.json`을 쓰지 않는다(영속화 없음).

1. 실행: `python cb_valuation/step1_curve/scripts/curve_validate.py $ARGUMENTS --dry-run` (없으면 "미구현 — BUILD_PROMPTS 7단계" 보고).
2. 출력: FAIL/APPROVAL_REQUIRED/WARN 코드 표(코드·커브·값·임계 상수명), 헤드라인(RF/RD 잔여만기 YTM, HEADLINE_RULE 정의명, 보고서 값 비교), 교차 방법 DF 차이, 지나간 엣지 이름 목록(run.path).
3. 승인 노드 도달 시 "승인 필요 코드: …"(approve_exception) 또는 "최종 승인 대기"(approve_curve)로 보고하고 종료한다. 실제 승인은 `/approve`(실행 모드 스냅샷에서만).
