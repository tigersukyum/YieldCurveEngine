# -*- coding: utf-8 -*-
"""
app/cli.py — 명령행. run: 매트릭스 파일 + 평가기준일 + --profile(필수) → 정지(exit 3, 스냅샷 경로 출력) / done(0) / failed(1)
resume: 스냅샷 → load_state → Constants.with_profile(run.profile) → set_decision → run(start=paused_at_node).
python -m cb_valuation.step1_curve.app.cli run --matrix <csv> --valuation-date 2025-12-31 --profile DEFAULT --maturity-date 2029-06-21 --rating BB+ --issuance 사모
python -m cb_valuation.step1_curve.app.cli resume --snapshot state/<key>/snapshot__approve_input__1.json --decision approved --approver 홍길동 --comment "..." [--ack CODE ...]
"""
from __future__ import annotations
import argparse, getpass, json, os, sys
from ..graph import step1_graph as G
from ..graph import snapshot as SNAP
from . import runner as R


def _print_state(s, path):
    sm = R.summary(s)
    print(json.dumps(sm, ensure_ascii=False, indent=1, default=str))
    if path:
        print("saved:", path)


def cmd_run(a):
    if not a.profile:
        print("프로필을 선택하세요(--profile, 필수):")
        for p in R.profiles_info():
            print(f"  {p['name']:<14} {'[구현]' if p['implemented'] else '[초안 미구현]'} {p['description']}")
        return 2
    with open(a.matrix, encoding="utf-8-sig") as fh:
        text = fh.read()
    form = {"profile": a.profile, "matrix_text": text, "valuation_date": a.valuation_date, "curve_date": a.curve_date, "curve_set_id": a.curve_set_id,
            "operator": a.operator or getpass.getuser(), "source_agency": a.source_agency, "capture_path": a.capture_path, "downloaded_at": a.downloaded_at,
            "instrument": {"issuer": a.issuer, "cb_name": a.cb_name, "maturity_date": a.maturity_date, "issuance_type": a.issuance, "rating": a.rating,
                           "prior_rating_basis": a.prior_rating, "prior_block_basis": a.prior_block, "rating_capture_path": a.rating_capture_path,
                           "reported_rf_pct": a.reported_rf, "reported_rd_pct": a.reported_rd}}
    s, C = R.prepare_state(form, a.base_dir)
    s, path = R.advance(s, C, a.base_dir)
    _print_state(s, path)
    return {"paused": SNAP.PAUSE_EXIT_CODE, "done": 0, "failed": 1}.get(s.run.status, 1)


def cmd_resume(a):
    s = SNAP.load_snapshot(a.snapshot)
    C = G.Constants.with_profile(s.run.profile)
    s, path = R.decide_and_resume(s, C, a.base_dir, a.decision, a.approver, a.comment or "", a.ack or [])
    _print_state(s, path)
    return {"paused": SNAP.PAUSE_EXIT_CODE, "done": 0, "failed": 1}.get(s.run.status, 1)


def main(argv=None):
    ap = argparse.ArgumentParser(prog="cb_valuation.step1_curve.app.cli")
    ap.add_argument("--base-dir", default=os.getcwd())
    sub = ap.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("run")
    r.add_argument("--matrix", required=True); r.add_argument("--valuation-date", required=True); r.add_argument("--profile")
    r.add_argument("--curve-date"); r.add_argument("--curve-set-id", default="CB1"); r.add_argument("--operator"); r.add_argument("--source-agency", default="KIS")
    r.add_argument("--capture-path"); r.add_argument("--rating-capture-path")
    r.add_argument("--downloaded-at", help="다운로드 시각(ISO). 재실행 결정성 검사용으로 고정값을 줄 수 있다; 비우면 현재 시각")
    r.add_argument("--maturity-date", required=True); r.add_argument("--rating", required=True); r.add_argument("--issuance", required=True, choices=["사모", "공모"])
    r.add_argument("--issuer"); r.add_argument("--cb-name"); r.add_argument("--prior-rating"); r.add_argument("--prior-block")
    r.add_argument("--reported-rf", type=float); r.add_argument("--reported-rd", type=float)
    r.set_defaults(fn=cmd_run)
    m = sub.add_parser("resume")
    m.add_argument("--snapshot", required=True); m.add_argument("--decision", required=True, choices=["approved", "rejected"])
    m.add_argument("--approver", required=True); m.add_argument("--comment", default=""); m.add_argument("--ack", nargs="*")
    m.set_defaults(fn=cmd_resume)
    a = ap.parse_args(argv)
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:  # noqa: BLE001
        pass
    return a.fn(a)


if __name__ == "__main__":
    sys.exit(main())
