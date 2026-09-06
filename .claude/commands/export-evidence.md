---
description: 승인된 state 로 증빙 번들을 재생성하고 EVIDENCE_REQUIRED_ITEMS 체크리스트(파일!시트!범위)를 검증
argument-hint: <valuation_date> [curve_set_id]
---
승인된 state로 증빙 번들을 재생성하고 `Constants.EVIDENCE_REQUIRED_ITEMS` 체크리스트를 검증한다. `$1` = 평가기준일(YYYY-MM-DD), `$2` = curve_set_id(선택; 비우면 해당 기준일의 유일한 세트, 둘 이상이면 사용자에게 묻는다).

1. 실행: `python cb_valuation/step1_curve/scripts/export_evidence.py --valuation-date $1` — `$2`가 있으면 `--curve-set-id $2`를 덧붙인다. 이어서 `python cb_valuation/step1_curve/scripts/evidence_check.py evidence/<key>` (없으면 "미구현 — BUILD_PROMPTS 9단계" 보고).
2. 출력: 생성 파일 목록(EVIDENCE_FILES 01~12, README_conventions.md, xlsx 또는 `export.warnings` 의 XLSX_SKIPPED, checklist_map.json, 12_approvals.json)과 체크리스트 표(항목 | 존재 | 파일!시트!범위). 위치 문자열 형식은 `<file>!<sheet|->!<range|json_path>`(GRAPH_SPEC §10).
3. 누락·형식 오류 항목이 있으면 export는 FAIL(`증빙불완전`)이며 done에 도달할 수 없음을 명시한다. 이후 `@agent-audit-evidence-reviewer`에 번들 경로를 넘긴다.
