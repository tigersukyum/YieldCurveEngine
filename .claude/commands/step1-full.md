---
description: 1단계 통합 게이트(fail-fast) — graph_check → 참조 구현 테스트 → unittest → 골든/엑셀/보간 → 드라이런·증빙 검사 → 요약표
argument-hint: [--matrix <path> --valuation-date <YYYY-MM-DD>] --profile NAME
---
1단계 통합 게이트. 단계마다 검증하고 첫 ERROR에서 중단한다(fail-fast). `$ARGUMENTS` = `[--matrix <path> --valuation-date <YYYY-MM-DD>] --profile NAME`(매트릭스를 비우면 fixture A; **`--profile` 은 필수** — 없으면 5단계를 "프로필 미지정" ERROR 로 처리).

순서(각 단계 출력 원문을 붙이고 WARN/ERROR로 분류; 슬래시 커맨드가 아니라 스크립트를 직접 실행한다):
1. `python cb_valuation/step1_curve/graph/graph_check.py` — exit≠0이면 ERROR 중단. `GRAPH_SPEC.md 구버전`이면 `python cb_valuation/step1_curve/graph/export_spec.py` 후 재실행.
2. `python cb_valuation/step1_curve/reference/test_interp_ref.py` — TOTAL FAILURES≠0이면 ERROR.
3. `python -m unittest discover -s cb_valuation/step1_curve/tests -v` (테스트가 아직 없으면 "미구현" WARN).
4. `python cb_valuation/step1_curve/scripts/compare_excel.py --vintage stale`, 같은 스크립트 `--vintage live`, `python cb_valuation/step1_curve/scripts/interp_check.py` — 스크립트 없으면 WARN(임시 대안 `reference/recompute_boot.py`).
5. `python cb_valuation/step1_curve/scripts/curve_validate.py $ARGUMENTS --dry-run`(드라이런 정의는 `/curve-validate`), 이어서 `python cb_valuation/step1_curve/scripts/evidence_check.py <최근 번들>` — 스크립트 없으면 WARN.
6. 요약: 단계 | 명령 | 종료코드 | 판정 | 핵심 수치. 통합 스크립트 `scripts/step1_full.py`가 생기면 그것을 실행한다.

ERROR가 하나라도 있으면 "통과"라고 쓰지 않는다. 마지막에 다음 행동(검토자 에이전트 병렬 호출 → 백업/커밋 → curve-fixer)을 제안한다.
