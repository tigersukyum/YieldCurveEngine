---
description: 참조 엑셀(KBI BOOT 캐시) 셀 단위 재현(stale) 또는 라이브 도출 대비 차이표(live)
argument-hint: stale|live
---
참조 엑셀(KBI메탈 `BOOT` 시트 캐시값) 대조. `$1` = `stale`(BOOT!G/V 하드코딩 이표율 주입 → H/I/W/X/L/M/N/AA/AB/AC 셀 단위 재현, 기대 ≤ `Constants.TOL_EXCEL_RECON`) | `live`(현재 KIS-NET 행에서 라이브 도출 → stale 대비 차이표·공시 문구).

1. 실행: `python cb_valuation/step1_curve/scripts/compare_excel.py --vintage $1` (없으면 임시로 `python cb_valuation/step1_curve/reference/recompute_boot.py`를 실행하고 해당 섹션을 인용; 입력은 `reference/xl_BOOT.txt`·`xl_KIS-NET.txt`, fixture `tests/fixtures/boot_cached_20251231.json`).
2. 열별 max|diff| 표와 MF_INTERPOL 프로브(FORMULA_REFERENCE §5.1 의 x 값: 첫 스텝 → 원점 앵커 값, 마지막 knot 초과 → None) 결과를 원문으로 붙인다.
3. stale/live 차이(수치는 FORMULA_REFERENCE §3.1)를 '참조 모델 내부 불일치' 공시 문구로 정리한다. 재현은 EXCEL_KBI 프로필에서만 유효하고 정상 모드에서는 `엑셀제로외삽_정상모드` 엣지가 FAIL 임을 명시한다.
