# -*- coding: utf-8 -*-
"""
graph_check.py — EDGES 불변식 검사 + 두 갈래 시나리오 표(SCENARIOS) 드라이런 + 노드 쓰기 추적 + 상수 지문 결정성 + 내보내기

실행:  python cb_valuation/step1_curve/graph/graph_check.py          (프로젝트 루트에서)
종료코드 0 = 전부 통과, 1 = 위반 있음.  /graph-check 커맨드와 tests/test_graph_invariants.py 가 같은 함수를 쓴다.
SCENARIOS 표는 docs/GRAPH_SPEC.md §4 로 export_spec.py 가 내보낸다(문서는 이 표만 인용).
"""
from __future__ import annotations

import inspect
import json
import math
import os
import re
import subprocess
import sys

try:
    from . import step1_graph as G  # 패키지 import (테스트)
except ImportError:  # 스크립트 직접 실행
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    import step1_graph as G

C = G.Constants
HERE = os.path.dirname(os.path.abspath(__file__))
DOCS = os.path.join(os.path.dirname(HERE), "docs")


# ----------------------------------------------------------------------------- 정적 불변식
def static_checks():
    errs = []
    node_ids = set(G.NODES)
    by_from = {}
    for e in G.EDGES:
        by_from.setdefault(e[0], []).append(e)
    # (i) 등록·from 집합
    for f, n, _, t in G.EDGES:
        if f not in node_ids: errs.append(f"미등록 from 노드: {f}")
        if t not in node_ids: errs.append(f"미등록 to 노드: {t} (엣지 {f}/{n})")
    expected_from = node_ids - set(C.TERMINAL_NODES)
    if set(by_from) != expected_from:
        errs.append(f"from 노드 집합 불일치: 누락 {expected_from - set(by_from)}, 여분 {set(by_from) - expected_from}")
    # (ii) 각 from 의 마지막 엣지만 ALWAYS, 그 위에는 ALWAYS 없음
    for f, edges in by_from.items():
        if edges[-1][2] is not G.ALWAYS:
            errs.append(f"{f}: 마지막 엣지가 ALWAYS 가 아님 → '{edges[-1][1]}'")
        for e in edges[:-1]:
            if e[2] is G.ALWAYS:
                errs.append(f"{f}: 예외 엣지 위에 ALWAYS 엣지 '{e[1]}' 존재")
    # (iii) 승인 노드: HUMAN_EDGE_ORDER 완전 일치 ; wait_for_human 진입은 승인 노드에서만
    for f, n, _, t in G.EDGES:
        if t == "wait_for_human" and f not in C.HUMAN_NODES:
            errs.append(f"wait_for_human 진입이 승인 노드가 아님: {f}/{n}")
    for h in C.HUMAN_NODES:
        names = [n for _, n, _, _ in by_from.get(h, [])]
        if names != C.HUMAN_EDGE_ORDER[h]:
            errs.append(f"{h}: 엣지 순서 {names} ≠ HUMAN_EDGE_ORDER {C.HUMAN_EDGE_ORDER[h]}")
        tos = {n: t for _, n, _, t in by_from.get(h, [])}
        if tos.get("거절") != "fail" or tos.get("대기") != "wait_for_human":
            errs.append(f"{h}: 거절→fail / 대기→wait_for_human 아님")
    # (iv) 게이트: 첫 엣지가 '비유한'
    for g in G.GATE_NODES:
        names = [n for _, n, _, _ in by_from.get(g, [])]
        if not names or "비유한" not in names[0]:
            errs.append(f"{g}: 첫 엣지가 '비유한' 이 아님: {names[:1]}")
    # (v) done/export 전 노드, fail→done 없음
    if {f for f, _, _, t in G.EDGES if t == "done"} != {"export_evidence"}: errs.append("done 전 노드 ≠ export_evidence")
    if {(f, n) for f, n, _, t in G.EDGES if t == "export_evidence"} != {("approve_curve", "승인")}: errs.append("export_evidence 전 ≠ approve_curve/승인")
    # (vi) 조건 람다 순수성
    for f, n, cond, _ in G.EDGES:
        src = inspect.getsource(cond)
        for bad in (r"\bimport\b", r"\bopen\(", r"\bos\.", r"\bprint\(", r"\bexec\(", r"\beval\("):
            if re.search(bad, src): errs.append(f"{f}/{n}: 조건 람다에 금지 토큰 '{bad}'")
    # (vii) 접두사 ↔ state 스키마, EDGE_CODES 커버
    st = G.new_state()
    for nid, (_, prefixes, _) in G.NODES.items():
        for p in prefixes:
            if p not in st: errs.append(f"{nid}: 접두사 '{p}' 가 state 스키마에 없음")
    for f, n, _, t in G.EDGES:
        if t == "fail" and (f, n) not in G.EDGE_CODES: errs.append(f"EDGE_CODES 누락: {f}/{n}")
    # (viii) 도달 가능성
    reach, frontier = set(), ["load_matrix"]
    while frontier:
        cur = frontier.pop()
        if cur in reach: continue
        reach.add(cur); frontier += [t for f, _, _, t in G.EDGES if f == cur]
    if reach != node_ids: errs.append(f"도달 불가 노드: {node_ids - reach}")
    # (ix) Constants 에 set 등 비결정 직렬화 값이 없는지(정렬 처리되는 frozenset 은 허용) + 서브프로세스 지문 동일
    def walk(o):
        if isinstance(o, set): return True
        if isinstance(o, dict): return any(walk(v) for v in o.values())
        if isinstance(o, (list, tuple, frozenset)): return any(walk(v) for v in o)
        return False
    for k, v in C.items().items():
        if walk(v): errs.append(f"Constants.{k}: set 포함(frozenset/list 로 선언할 것)")
    fp = C.fingerprint()
    for seed in ("1", "2"):
        try:
            out = subprocess.run([sys.executable, "-c", "import sys; sys.path.insert(0, %r); import step1_graph as G; print(G.Constants.fingerprint())" % HERE],
                                 env={**os.environ, "PYTHONHASHSEED": seed}, capture_output=True, text=True, timeout=60)
            if out.stdout.strip() != fp:
                errs.append(f"fingerprint 비결정(PYTHONHASHSEED={seed}): {out.stdout.strip()[:12]} ≠ {fp[:12]} {out.stderr[-200:]}")
        except Exception as e:  # noqa: BLE001
            errs.append(f"서브프로세스 지문 검사 실패: {e}")
    return errs


# ----------------------------------------------------------------------------- 시나리오(두 갈래) — 문서는 이 표만 인용한다
def happy_state(Cc=C):
    s = G.new_state(Cc)
    s.input.update(header_ok=True, n_rows=62, rows=[{"row_index": 2}], file_sha256="sha256:fixtureA")
    s.provenance.update(source_agency="KIS", curve_date="2025-12-31", valuation_date="2025-12-31", raw_copy_path="data/raw/2025-12-31/x.csv",
                        downloaded_at="2025-12-31T09:00:00+09:00", operator="tester", capture_path="evidence/capture.png")
    s.provenance.instrument.update(maturity_date="2029-06-21", issuance_type="사모", rating="BB+")
    s.provenance.method_choice.update(profile=Cc.PROFILE_NAME, chosen_by="tester", chosen_at="2025-12-31T09:00:00+09:00")
    s.provenance.instrument.rating_evidence.capture_path = "evidence/rating.png"
    s.labels.rf_candidates = [{"row_index": 2}]
    s.rows.update(rf={"row_index": 2}, rd={"row_index": 58, "notch": 0}, usable_knot_count={"RF": 10, "RD": 12})
    s.grid.update(remaining_years=3.47, horizon_years=Cc.CURVE_HORIZON_Y)
    s.interp.update(all_finite=True, knot_roundtrip_max_err=0.0)
    s.bootstrap.update(status={"RF": "OK", "RD": "OK"}, df_valid={"RF": True, "RD": True})
    s.par_check.update(all_finite=True, max_abs_err=1.3e-15)
    s.conv.update(all_finite=True, roundtrip_max_err=2e-16)
    s.tree.update(df_finite=True, df_range_ok=True, df_monotone_ok=True, knot_roundtrip_max_err=0.0, extrap_left_flat_steps={"RF": [0, 1], "RD": [0]})
    s.fwd.update(all_finite=True)
    s.fwd_spot_check.update(all_finite=True, max_abs_err_log=2e-16)
    s.export.cell_map = {k: "evidence.xlsx!SHEET!A1" for k in Cc.EVIDENCE_REQUIRED_ITEMS}
    s.export.update(xlsx_written=True, xlsx_path="evidence.xlsx")
    return s


def path_names(s):
    return [p[1] for p in s.run.path]


def drive(s, decisions, Cc=C, hooks=None):
    """승인 지점마다 decisions[kind]=(decision, ack) 로 자동 재개. hooks[node] 는 재개 직전 state 변조(변조 감지 시나리오)."""
    s = G.run(s, Cc)
    applied = set()
    while s.run.status == "paused":
        node = s.run.paused_at_node; kind = node.replace("approve_", "")
        if kind not in decisions or node in applied:
            return s
        applied.add(node)
        dec, ack = decisions[kind]
        G.set_decision(s, kind, dec, "tester", "auto", ack)
        if hooks and node in hooks:
            hooks[node](s)
        s = G.run(s, Cc, start=node)
    return s


APPROVE_ALL = {"input": ("approved", []), "curve": ("approved", [])}
CAP = type("Constants_CAP", (C,), {**C.items(), "EXTRAP_LEFT_FLAT_SEVERITY": "APPROVAL_REQUIRED", "PROFILE_NAME": "DEFAULT"})


def _lag(s, curve_date):
    s.provenance.curve_date = curve_date
    return s

def _preset(kind):
    """정지 후 승인 필드를 외부에서(set_decision 우회) 요청 시각보다 앞선 시각으로 써넣는 변조."""
    def f(s):
        a = s[f"approval_{kind}"]
        a.decision, a.timestamp, a.approver = "approved", "2000-01-01T00:00:00+00:00", "attacker"
    return f

# (id, 설명, 프로필상수, setup(state)->state, decisions, hooks, 기대 마지막 엣지, 기대 status)
SCENARIOS = [
    ("A01", "정상 입력 → 승인 2곳 → done (EXTRAP_LEFT_FLAT=WARN 기본)", C, lambda s: s, APPROVE_ALL, None, "내보내기완료", "done"),
    ("A02", "정상 입력, EXTRAP_LEFT_FLAT_SEVERITY=APPROVAL → approve_exception 경유 후 done", CAP, lambda s: s,
     {"input": ("approved", []), "exception": ("approved", ["EXTRAP_LEFT_FLAT"]), "curve": ("approved", [])}, None, "내보내기완료", "done"),
    ("A03", "결정 없이 approve_input 정지", C, lambda s: s, {}, None, "대기", "paused"),
    ("A04", "PCHIP_TREE 프로필 정상 완주(next_step_interface.space=log_df)", C.with_profile("PCHIP_TREE"), lambda s: s, APPROVE_ALL, None, "내보내기완료", "done"),
    ("E01", "헤더 불일치", C, lambda s: (s.input.update(header_ok=False), s)[1], {}, None, "헤더불일치", "failed"),
    ("E02", "파싱 오류", C, lambda s: (s.input.parse_errors.append("row 7: not numeric"), s)[1], {}, None, "파싱오류", "failed"),
    ("E03", "행 0개", C, lambda s: (s.input.update(n_rows=0), s)[1], {}, None, "행없음", "failed"),
    ("E04", "출처 불완전(만기일 없음)", C, lambda s: (s.provenance.instrument.update(maturity_date=None), s)[1], {}, None, "출처불완전", "failed"),
    ("E05", "curve_date 지연 5일", C, lambda s: _lag(s, "2025-12-26"), {}, None, "기준일역전_또는_지연초과", "failed"),
    ("E06", "curve_date 가 평가기준일보다 미래(lag −1)", C, lambda s: _lag(s, "2026-01-01"), {}, None, "기준일역전_또는_지연초과", "failed"),
    ("E07", "curve_date 지연 1일 → DATE_LAG 승인 후 done", C, lambda s: _lag(s, "2025-12-30"),
     {"input": ("approved", []), "exception": ("approved", ["DATE_LAG"]), "curve": ("approved", [])}, None, "내보내기완료", "done"),
    ("E08", "RF 후보 라벨 없음", C, lambda s: (s.labels.update(rf_candidates=[]), s)[1], {}, None, "RF후보없음", "failed"),
    ("E09", "입력 승인 거절", C, lambda s: s, {"input": ("rejected", [])}, None, "거절", "failed"),
    ("E10", "입력 승인 결정선행(외부 편집)", C, lambda s: s, {}, {"approve_input": _preset("input")}, "결정선행", "failed"),
    ("E11", "입력 승인 후 상수 변경", C, lambda s: s, {"input": ("approved", [])}, {"approve_input": lambda s: s.run.update(constants_fingerprint="stale")}, "상수변경감지", "failed"),
    ("E12", "입력 승인 후 입력 변조", C, lambda s: s, {"input": ("approved", [])}, {"approve_input": lambda s: s.input.update(n_rows=61)}, "입력변조감지", "failed"),
    ("E13", "RF 행 없음", C, lambda s: (s.rows.update(rf=None), s)[1], {"input": ("approved", [])}, None, "RF행없음", "failed"),
    ("E14", "RD 행 없음·대체 불가", C, lambda s: (s.rows.update(rd=None), s)[1], {"input": ("approved", [])}, None, "RD행없음_대체불가", "failed"),
    ("E15", "knot 부족", C, lambda s: (s.rows.usable_knot_count.update(RD=3), s)[1], {"input": ("approved", [])}, None, "knot부족", "failed"),
    ("E16", "잔여만기 미산출(None)", C, lambda s: (s.grid.update(remaining_years=None), s)[1], {"input": ("approved", [])}, None, "잔여만기비유한", "failed"),
    ("E17", "만기 12Y > horizon", C, lambda s: (s.grid.update(remaining_years=12.0), s)[1], {"input": ("approved", [])}, None, "만기초과", "failed"),
    ("E18", "보간 비유한", C, lambda s: (s.interp.update(all_finite=False), s)[1], {"input": ("approved", [])}, None, "보간비유한", "failed"),
    ("E19", "knot 왕복 불일치", C, lambda s: (s.interp.update(knot_roundtrip_max_err=2 * C.TOL_KNOT_ROUNDTRIP), s)[1], {"input": ("approved", [])}, None, "knot왕복불일치", "failed"),
    ("E20", "부트스트랩 DF 무효", C, lambda s: (s.bootstrap.df_valid.update(RF=False), s)[1], {"input": ("approved", [])}, None, "DF무효_비유한", "failed"),
    ("E21", "부트스트랩 분모 ≤ 0", C, lambda s: (s.bootstrap.status.update(RD="FAIL_DENOMINATOR"), s)[1], {"input": ("approved", [])}, None, "분모비양수", "failed"),
    ("E22", "근찾기 비수렴", C, lambda s: (s.bootstrap.status.update(RD="FAIL_NO_CONVERGENCE"), s)[1], {"input": ("approved", [])}, None, "근찾기실패_비수렴", "failed"),
    ("E23", "par 잔차 NaN", C, lambda s: (s.par_check.update(all_finite=False, max_abs_err=float("nan")), s)[1], {"input": ("approved", [])}, None, "파잔차비유한", "failed"),
    ("E24", "par 잔차 2×TOL", C, lambda s: (s.par_check.update(max_abs_err=2 * C.TOL_PAR_FAIL), s)[1], {"input": ("approved", [])}, None, "파검증실패", "failed"),
    ("E25", "par 잔차 0.5×TOL 통과", C, lambda s: (s.par_check.update(max_abs_err=0.5 * C.TOL_PAR_FAIL), s)[1], APPROVE_ALL, None, "내보내기완료", "done"),
    ("E26", "복리 변환 비유한", C, lambda s: (s.conv.update(all_finite=False), s)[1], {"input": ("approved", [])}, None, "변환비유한", "failed"),
    ("E27", "복리 왕복 불일치", C, lambda s: (s.conv.update(roundtrip_max_err=2 * C.TOL_ROUNDTRIP_COMP), s)[1], {"input": ("approved", [])}, None, "왕복변환불일치", "failed"),
    ("E28", "트리 DF 비유한", C, lambda s: (s.tree.update(df_finite=False), s)[1], {"input": ("approved", [])}, None, "트리DF비유한", "failed"),
    ("E29", "excel_zero 외삽이 정상 모드에서 발동", C, lambda s: (s.tree.update(excel_zero_used=True), s)[1], {"input": ("approved", [])}, None, "엑셀제로외삽_정상모드", "failed"),
    ("E30", "트리 DF 단조 위반", C, lambda s: (s.tree.update(df_monotone_ok=False), s)[1], {"input": ("approved", [])}, None, "DF범위_또는_단조위반", "failed"),
    ("E31", "선도 비유한", C, lambda s: (s.fwd.update(all_finite=False), s)[1], {"input": ("approved", [])}, None, "선도비유한", "failed"),
    ("E32", "선도-현물 잔차 NaN", C, lambda s: (s.fwd_spot_check.update(all_finite=False), s)[1], {"input": ("approved", [])}, None, "정합잔차비유한", "failed"),
    ("E33", "선도-현물 잔차 2×TOL", C, lambda s: (s.fwd_spot_check.update(max_abs_err_log=2 * C.TOL_FWD_SPOT_FAIL), s)[1], {"input": ("approved", [])}, None, "정합실패", "failed"),
    ("E34", "보고서 헤드라인 있는데 비교 안 됨", C, lambda s: (s.provenance.instrument.reported_headline.update(rf_pct=2.77), s)[1], {"input": ("approved", [])}, None, "헤드라인미비교", "failed"),
    ("E35", "보간 방법 불일치(트리가 다른 방법 사용) → sanity FAIL", C, lambda s: (setattr(G.node_map_tree_grid, "_tamper", True), s)[1], {"input": ("approved", [])},
     {"__after_map__": None}, "FAIL플래그존재", "failed"),
    ("E36", "음의 선도 → approve_exception, 일부 ack → 재정지", C, lambda s: (s.fwd.negative_count.update(RD=3), _lag(s, "2025-12-30"))[1],
     {"input": ("approved", []), "exception": ("approved", ["NEG_FWD"])}, None, "미확인코드잔존", "paused"),
    ("E37", "예외 승인 거절", C, lambda s: _lag(s, "2025-12-30"), {"input": ("approved", []), "exception": ("rejected", [])}, None, "거절", "failed"),
    ("E38", "예외 승인 결정선행", C, lambda s: _lag(s, "2025-12-30"), {"input": ("approved", [])}, {"approve_exception": _preset("exception")}, "결정선행", "failed"),
    ("E39", "예외 승인 후 상수 변경", C, lambda s: _lag(s, "2025-12-30"), {"input": ("approved", []), "exception": ("approved", ["DATE_LAG"])},
     {"approve_exception": lambda s: s.run.update(constants_fingerprint="stale")}, "상수변경감지", "failed"),
    ("E40", "예외 승인 후 계산 상태 변조", C, lambda s: _lag(s, "2025-12-30"), {"input": ("approved", []), "exception": ("approved", ["DATE_LAG"])},
     {"approve_exception": lambda s: s.par_check.update(max_abs_err=5e-11)}, "계산상태변조감지", "failed"),
    ("E41", "최종 승인 거절", C, lambda s: s, {"input": ("approved", []), "curve": ("rejected", [])}, None, "거절", "failed"),
    ("E42", "최종 승인 결정선행", C, lambda s: s, {"input": ("approved", [])}, {"approve_curve": _preset("curve")}, "결정선행", "failed"),
    ("E43", "최종 승인 후 상수 변경", C, lambda s: s, APPROVE_ALL, {"approve_curve": lambda s: s.run.update(constants_fingerprint="stale")}, "상수변경감지", "failed"),
    ("E44", "최종 승인 후 이전 승인 기록 변조", C, lambda s: s, APPROVE_ALL, {"approve_curve": lambda s: s.approval_input.update(approver="someone")}, "계산상태변조감지", "failed"),
    ("E45", "증빙 쓰기 오류", C, lambda s: (s.export.errors.append("PermissionError"), s)[1], APPROVE_ALL, None, "쓰기오류", "failed"),
    ("E46", "증빙 필수 항목 누락(Q11)", C, lambda s: (s.export.cell_map.pop("Q11"), s)[1], APPROVE_ALL, None, "증빙불완전", "failed"),
    ("E47", "증빙 위치 문자열 형식 오류", C, lambda s: (s.export.cell_map.update(Q1="placeholder"), s)[1], APPROVE_ALL, None, "증빙불완전", "failed"),
    ("E48", "프로필 미선택(method_choice.profile=None) → 출처불완전", C, lambda s: (s.provenance.method_choice.update(profile=None), s)[1], {}, None, "출처불완전", "failed"),
    ("E49", "선택한 프로필 ≠ 실행 상수 프로필", C, lambda s: (s.provenance.method_choice.update(profile="PCHIP_TREE"), s)[1], {}, None, "프로필불일치", "failed"),
    ("E50", "xlsx 미생성(XLSX_REQUIRED)", C, lambda s: (s.export.update(xlsx_written=False), s)[1], APPROVE_ALL, None, "xlsx누락", "failed"),
    ("E51", "트리 격자 보간체 knot 왕복 2×TOL", C, lambda s: (s.tree.update(knot_roundtrip_max_err=2 * C.TOL_KNOT_ROUNDTRIP), s)[1], {"input": ("approved", [])}, None, "격자knot왕복불일치", "failed"),
]


def _run_scenario(sc):
    sid, desc, Cc, setup, decisions, hooks, exp_edge, exp_status = sc
    s = setup(happy_state(Cc))
    if sid == "E35":  # 트리 매핑이 다른 보간 방법을 썼다고 기록(다중 노드 교차 FAIL)
        orig = G.NODES["map_tree_grid"][2]
        def tampered(s_, C_):
            orig(s_, C_); s_.tree.interp_method_used = "natural_cubic"
        G.NODES["map_tree_grid"] = (G.NODES["map_tree_grid"][0], G.NODES["map_tree_grid"][1], tampered)
        try:
            s = drive(s, decisions, Cc)
        finally:
            G.NODES["map_tree_grid"] = (G.NODES["map_tree_grid"][0], G.NODES["map_tree_grid"][1], orig)
        return s
    if hooks and any(k in hooks for k in ("approve_input", "approve_exception", "approve_curve")):
        # 결정선행: set_decision 없이 외부 편집만 한 뒤 같은 노드에서 재개
        s = G.run(s, Cc)
        while s.run.status == "paused":
            node = s.run.paused_at_node; kind = node.replace("approve_", "")
            hook = hooks.get(node)
            if kind in decisions:
                G.set_decision(s, kind, *decisions[kind][:1], "tester", "auto", decisions[kind][1])
            elif hook is None:
                return s
            if hook: hook(s)
            s = G.run(s, Cc, start=node)
            if hook: return s
        return s
    return drive(s, decisions, Cc)


def dynamic_checks():
    errs, traversed = [], set()
    for sc in SCENARIOS:
        sid, desc, Cc, *_ , exp_edge, exp_status = sc
        try:
            s = _run_scenario(sc)
        except Exception as e:  # noqa: BLE001
            errs.append(f"[{sid}] 예외 발생: {type(e).__name__}: {e}")
            continue
        names = path_names(s)
        traversed.update((p[0], p[1]) for p in s.run.path)
        if not names or names[-1] != exp_edge or s.run.status != exp_status:
            errs.append(f"[{sid} {desc}] 기대 '{exp_edge}'/{exp_status}, 실제 '{names[-1] if names else None}'/{s.run.status}: {names}")
        if sid == "A01" and "승인필요플래그존재" in names: errs.append("[A01] EXTRAP_LEFT_FLAT=WARN 인데 approve_exception 경유")
        if sid == "A02" and "승인필요플래그존재" not in names: errs.append("[A02] approve_exception 미경유")
        if sid == "A04" and s.result.next_step_interface and s.result.next_step_interface["profile"] != "PCHIP_TREE":
            errs.append("[A04] next_step_interface.profile ≠ PCHIP_TREE")
        if sid == "A04" and s.interp.space_grid != "log_df": errs.append("[A04] PCHIP_TREE 공간이 log_df 가 아님")
        if sid == "E10" and s.result.fail_code != "DECISION_BEFORE_REQUEST": errs.append("[E10] fail_code 미기록")
        if sid == "E41" and (s.result.fail_detail or {}).get("approver") != "tester": errs.append("[E41] fail_detail 에 승인자 없음")
    # 커버리지: 모든 엣지가 최소 1회
    uncovered = [(f, n) for f, n, _, _ in G.EDGES if (f, n) not in traversed]
    if uncovered: errs.append(f"시나리오가 지나가지 않은 엣지 {len(uncovered)}개: {uncovered}")
    # 추가 검사: 요청 전 set_decision 금지, 정지 밖 set_decision 금지, ack 검증, 재개 후 계산 필드 불변, 저장→재적재 해시 동일, 프로필 불일치
    s = happy_state()
    try:
        G.set_decision(s, "input", "approved", "tester"); errs.append("요청 전 set_decision 이 허용됨")
    except ValueError:
        pass
    s = G.run(happy_state(), C)
    try:
        G.set_decision(s, "curve", "approved", "tester"); errs.append("정지 중이 아닌 노드에 set_decision 허용됨")
    except ValueError:
        pass
    try:
        G.set_decision(s, "input", "approved", "tester", acknowledged_codes=["TYPO"]); errs.append("flags_seen 밖 ack 허용됨")
    except ValueError:
        pass
    before = G.hash_of(s, C.CALC_PREFIXES)
    G.set_decision(s, "input", "approved", "tester"); s = G.run(s, C, start="approve_input")
    if s.run.status != "paused": errs.append("[재개] approve_curve 에서 멈추지 않음")
    if G.hash_of(s, C.CALC_PREFIXES) == before: errs.append("[재개] 계산 노드가 실행되지 않음(해시 불변) — 입력 승인 후 계산 필드가 채워져야 함")
    before = G.hash_of(s, C.CALC_PREFIXES)
    G.set_decision(s, "curve", "approved", "tester"); s = G.run(s, C, start="approve_curve")
    if G.hash_of(s, C.CALC_PREFIXES) != before: errs.append("[재개] 최종 승인 재개 후 계산 필드 변경")
    reloaded = G.load_state(json.loads(G.canonical_json(s)))
    if G.hash_of(reloaded, C.CALC_PREFIXES) != before: errs.append("[스냅샷] 저장→재적재 후 해시 불일치")
    if reloaded.result.next_step_interface != s.result.next_step_interface: errs.append("[스냅샷] 재적재 후 next_step_interface 불일치")
    try:
        G.run(happy_state(), C.with_profile("PCHIP_TREE")); errs.append("프로필 불일치 state 로 run 허용됨")
    except ValueError:
        pass
    try:
        s2 = G.run(happy_state(), C); G.run(s2, C, start="select_rows"); errs.append("계산 노드에서 재개 허용됨")
    except ValueError:
        pass
    if len(s.approval_input.history) != 1 or s.approval_input.history[0]["approver"] != "tester": errs.append("승인 history 미기록")
    return errs


# ----------------------------------------------------------------------------- 노드 쓰기 추적(자기 접두사만) — 스텁(NODES)과 실제 구현(nodes.NODES_IMPL) 둘 다
class _Tracking(G.NS):
    """중첩 dict 까지 감싸서 최상위 접두사 이름으로 쓰기를 기록한다. _who 는 현재 실행 중인 노드 id 를 담는 공유 dict."""
    def __init__(self, prefix, log, who, data):
        super().__init__({k: _track(prefix, log, who, v) for k, v in data.items()})
        object.__setattr__(self, "_prefix", prefix); object.__setattr__(self, "_log", log); object.__setattr__(self, "_who", who)
    def _mark(self):
        if self._who.get("node") is not None:
            self._log.setdefault(self._who["node"], set()).add(self._prefix)
    def __setattr__(self, k, v):
        self._mark(); dict.__setitem__(self, k, v)
    def __setitem__(self, k, v):
        self._mark(); dict.__setitem__(self, k, v)
    def update(self, *a, **kw):
        self._mark(); dict.update(self, *a, **kw)


def _track(prefix, log, who, v):
    if isinstance(v, dict):
        return _Tracking(prefix, log, who, v)
    if isinstance(v, list):
        return [_track(prefix, log, who, x) for x in v]
    return v


def _tracked_state(state, log, who):
    return G.NS({k: _Tracking(k, log, who, v) for k, v in json.loads(G.canonical_json(state)).items()})


def _wrap_registry(registry, who):
    out = {}
    for nid, (ko, pre, fn) in registry.items():
        def mk(nid, fn):
            def w(s, C):
                who["node"] = nid
                try:
                    fn(s, C)
                finally:
                    who["node"] = None
            return w
        out[nid] = (ko, pre, fn if nid in C.HUMAN_NODES + C.TERMINAL_NODES + ("sanity_check",) else mk(nid, fn))
    return out


def ownership_checks():
    errs = []
    # (a) 스텁: 채워진 state 위에서 노드 하나씩 실행
    base = drive(happy_state(), APPROVE_ALL)
    for nid, (_, prefixes, fn) in G.NODES.items():
        log, who = {}, {"node": nid}
        s = _tracked_state(base, log, who)
        try:
            fn(s, C)
        except Exception as e:  # noqa: BLE001
            errs.append(f"[{nid}] 스텁 실행 예외: {e}"); continue
        bad = log.get(nid, set()) - set(prefixes)
        if bad: errs.append(f"[스텁 {nid}] 자기 접두사 {prefixes} 밖 쓰기: {sorted(bad)}")
    # (b) 실제 구현: fixture A 로 정상 경로를 끝까지 돌리며 노드별 쓰기 접두사 기록(승인·종단·sanity 는 step1_graph 함수라 제외)
    try:
        try:
            from ..nodes import NODES_IMPL
            from ..app import runner as RUN
            from ..graph import step1_graph as G2  # NODES_IMPL 과 같은 모듈 객체(스크립트 실행 시 이중 임포트 방지)
        except ImportError:
            root = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))  # …/cb_valuation/step1_curve/graph → 저장소 루트
            sys.path.insert(0, root)
            from cb_valuation.step1_curve.nodes import NODES_IMPL
            from cb_valuation.step1_curve.app import runner as RUN
            from cb_valuation.step1_curve.graph import step1_graph as G2
    except Exception as e:  # noqa: BLE001
        return errs + [f"[구현] nodes/runner 임포트 실패: {e}"]
    import tempfile, shutil
    fixture = os.path.join(os.path.dirname(HERE), "tests", "fixtures", "kisnet_matrix_20251231.csv")
    if not os.path.exists(fixture):
        return errs + ["[구현] fixture A 없음 — 실제 노드 쓰기 추적 생략"]
    tmp = tempfile.mkdtemp(prefix="gc_own_")
    try:
        with open(fixture, encoding="utf-8-sig") as fh:
            text = fh.read()
        form = {"profile": "DEFAULT", "matrix_text": text, "valuation_date": "2025-12-31", "curve_date": "2025-12-31", "curve_set_id": "GC", "operator": "graph_check",
                "source_agency": "KIS", "downloaded_at": "2025-12-31T09:00:00+09:00", "instrument": {"maturity_date": "2029-06-21", "issuance_type": "사모", "rating": "BB+"}}
        s0, Cc = RUN.prepare_state(form, tmp)
        log, who = {}, {"node": None}
        s = _tracked_state(s0, log, who)
        reg = _wrap_registry(NODES_IMPL, who)
        s = G2.run(s, Cc, nodes=reg)
        while s.run.status == "paused":
            kind = s.run.paused_at_node.replace("approve_", "")
            ack = [f["code"] for f in s[f"approval_{kind}"].flags_seen] if kind == "exception" else []
            G2.set_decision(s, kind, "approved", "graph_check", "auto", ack)
            s = G2.run(s, Cc, start=s.run.paused_at_node, nodes=reg)
        if s.run.status != "done": errs.append(f"[구현] fixture A 정상 경로가 done 에 도달하지 않음: {s.run.status} {path_names(s)[-3:]}")
        for nid, (_, prefixes, _) in NODES_IMPL.items():
            bad = log.get(nid, set()) - set(prefixes)
            if bad: errs.append(f"[구현 {nid}] 자기 접두사 {prefixes} 밖 쓰기: {sorted(bad)}")
        # 노드 소스에 프로세스 전역 입력(환경변수) 금지
        ndir = os.path.join(os.path.dirname(HERE), "nodes")
        for f in sorted(os.listdir(ndir)):
            if f.endswith(".py") and "os.environ" in open(os.path.join(ndir, f), encoding="utf-8").read():
                errs.append(f"[구현] nodes/{f}: os.environ 사용(노드 입력은 state·Constants 뿐)")
    except Exception as e:  # noqa: BLE001
        errs.append(f"[구현] 실행 예외: {type(e).__name__}: {e}")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    return errs


def spec_digest() -> str:
    """GRAPH_SPEC.md 가 의존하는 모든 것(상수 지문·노드 표·엣지 표·코드 표·시나리오 표)의 해시. export_spec 이 헤더에 쓰고 여기서 대조한다."""
    import hashlib
    payload = {
        "fingerprint": C.fingerprint(),
        "nodes": [(nid, ko, list(pre), (fn.__doc__ or "").strip()) for nid, (ko, pre, fn) in G.NODES.items()],
        "edges": [(f, n, "ALWAYS" if cond is G.ALWAYS else inspect.getsource(cond).strip(), t) for f, n, cond, t in G.EDGES],
        "codes": sorted((f"{f}/{n}", c) for (f, n), c in G.EDGE_CODES.items()),
        "scenarios": [(sid, desc, getattr(Cc, "PROFILE_NAME", ""), edge, status) for sid, desc, Cc, *_, edge, status in SCENARIOS],
    }
    return hashlib.sha256(G.canonical_json(payload).encode("utf-8")).hexdigest()


def spec_freshness():
    """docs/GRAPH_SPEC.md 헤더의 spec 다이제스트가 현재 코드와 같은지(다르면 export_spec.py 재실행 안내)."""
    p = os.path.join(DOCS, "GRAPH_SPEC.md")
    if not os.path.exists(p): return "GRAPH_SPEC.md 없음 — export_spec.py 실행"
    m = re.search(r"spec `([0-9a-f]{12})", open(p, encoding="utf-8").read())
    return None if (m and m.group(1) == spec_digest()[:12]) else "GRAPH_SPEC.md 구버전 — export_spec.py 재실행 필요"


def main():
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:  # noqa: BLE001
        pass
    se, de, oe = static_checks(), dynamic_checks(), ownership_checks()
    with open(os.path.join(HERE, "edges_export.json"), "w", encoding="utf-8") as f:
        json.dump(G.export_edges_json(), f, ensure_ascii=False, indent=1)
    with open(os.path.join(HERE, "graph.mmd"), "w", encoding="utf-8") as f:
        f.write(G.to_mermaid())
    print(f"NODES {len(G.NODES)} | EDGES {len(G.EDGES)} | HUMAN {len(C.HUMAN_NODES)} | TERMINAL {len(C.TERMINAL_NODES)} | SCENARIOS {len(SCENARIOS)} | fingerprint {C.fingerprint()[:12]}")
    for title, errs in (("static invariants", se), ("two-branch scenarios", de), ("node write ownership", oe)):
        print(f"{title}: {'OK' if not errs else 'FAIL'}"); [print("  -", e) for e in errs]
    fresh = spec_freshness()
    print("GRAPH_SPEC.md:", fresh or "up to date")
    print("exported: edges_export.json, graph.mmd")
    return 0 if not (se or de or oe) else 1


if __name__ == "__main__":
    sys.exit(main())
