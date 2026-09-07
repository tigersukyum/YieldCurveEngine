# -*- coding: utf-8 -*-
"""
app/runner.py — CLI 와 서버가 함께 쓰는 실행기. 입력(폼/인수) → state(입력 접두사 채움) → run(nodes=NODES_IMPL) → 스냅샷/최종 파일 저장.
흐름 판단은 하지 않는다(EDGES 가 한다). 승인 결정은 set_decision() 으로만 기록한다.
"""
from __future__ import annotations
import os
from datetime import datetime, timezone
from ..graph import step1_graph as G
from ..graph import snapshot as SNAP
from ..nodes import NODES_IMPL, unsupported


def profiles_info():
    return [{"name": k, "description": v, "implemented": k in G.Constants.PROFILES_IMPLEMENTED} for k, v in G.Constants.PROFILE_DESCRIPTIONS.items()]


def _now():
    return datetime.now(timezone.utc).isoformat()


def _num(v):
    if v in (None, ""):
        return None
    return float(v)


def _int(v):
    if v in (None, ""):
        return None
    return int(v)


def prepare_state(form: dict, base_dir: str):
    """form 키(커브 전용 모드 = 앱 기본): profile(필수), matrix_text, step(월간/주간/일간 ∈ STEP_MODES), horizon_years(산출 기간, 년), rf_row_index, rd_row_index,
    valuation_date, curve_date, curve_set_id, operator, source_agency, downloaded_at, capture_path(행 캡처; 서버가 저장한 상대경로), chosen_at.
    선택(상품 모드; 2단계용): instrument{issuer, cb_name, maturity_date, issuance_type, rating, prior_rating_basis, prior_block_basis, event_dates,
    rating_capture_path, reported_rf_pct, reported_rd_pct, reported_source_doc}. 상품 정보가 없으면 헤드라인·등급 캡처는 요구되지 않는다."""
    profile = form.get("profile")
    if not profile:
        raise ValueError("프로필을 선택해야 합니다(PROFILE_SELECTION=required): " + ", ".join(G.Constants.PROFILES))
    if profile not in G.Constants.PROFILES:
        raise ValueError(f"알 수 없는 프로필 {profile}")
    if profile not in G.Constants.PROFILES_IMPLEMENTED:
        raise NotImplementedError(f"프로필 {profile} 은 초안에서 미구현(구현: {', '.join(G.Constants.PROFILES_IMPLEMENTED)})")
    C = G.Constants.with_profile(profile)
    bad = unsupported(C)  # 사전 게이트: 노드 안에서 NotImplementedError 가 나기 전에 상수 조합을 검사
    if bad:
        raise NotImplementedError("초안 미지원 상수 조합: " + "; ".join(bad))
    step = form.get("step") or None
    if step is not None and step not in C.STEP_MODES:
        raise ValueError(f"노드 간격은 {list(C.STEP_MODES)} 중 하나여야 합니다: {step!r}")
    s = G.new_state(C)
    s.run.base_dir = os.path.abspath(base_dir)
    s.run.run_id = f"run_{_now().replace(':', '').replace('-', '')[:15]}"
    s.run.curve_set_id = form.get("curve_set_id") or "CURVE1"
    s.input.raw_text = form.get("matrix_text") or ""
    p = s.provenance
    p.source_agency = form.get("source_agency") or None
    p.valuation_date = form.get("valuation_date") or None
    p.curve_date = form.get("curve_date") or p.valuation_date
    p.downloaded_at = form.get("downloaded_at") or _now()
    p.operator = form.get("operator") or None
    p.capture_path = form.get("capture_path") or None
    p.grid_settings.update(step=step, horizon_years=_num(form.get("horizon_years")) if step else None)
    p.row_choice.update(rf_row_index=_int(form.get("rf_row_index")), rd_row_index=_int(form.get("rd_row_index")))
    # 원본 사본(Q12): data/raw/<curve_date>/matrix_<curve_set_id>.csv
    if s.input.raw_text and p.curve_date:
        rd = os.path.join(base_dir, "data", "raw", p.curve_date); os.makedirs(rd, exist_ok=True)
        rp = os.path.join(rd, f"matrix_{s.run.curve_set_id}.csv")
        with open(rp, "w", encoding="utf-8", newline="\n") as fh:
            fh.write(s.input.raw_text)
        p.raw_copy_path = os.path.relpath(rp, base_dir).replace("\\", "/")
    inst = form.get("instrument") or {}
    i = p.instrument
    for k in ("issuer", "cb_name", "maturity_date", "issuance_type", "rating", "prior_rating_basis", "prior_block_basis"):
        i[k] = inst.get(k) or None
    i.event_dates = inst.get("event_dates") or []
    i.rating_evidence.capture_path = inst.get("rating_capture_path") or None
    rh = i.reported_headline
    rh.rf_pct = _num(inst.get("reported_rf_pct")); rh.rd_pct = _num(inst.get("reported_rd_pct")); rh.source_doc = inst.get("reported_source_doc") or None
    # 결정성: 같은 입력 두 번 → 같은 CALC_PREFIXES 해시가 되도록 시각은 입력값(downloaded_at)을 따른다(테스트가 고정값을 넣는다)
    p.method_choice.update(profile=profile, chosen_by=p.operator, chosen_at=form.get("chosen_at") or p.downloaded_at)
    return s, C


def advance(s, C, base_dir: str, start=None):
    """run → 정지면 스냅샷 저장, 종단이면 approved/failed 저장. 반환: (state, 저장 경로|None)."""
    s = G.run(s, C, start=start, nodes=NODES_IMPL)
    path = None
    if s.run.status == "paused":
        path = SNAP.save_snapshot(s, base_dir)
    elif s.run.status in ("done", "failed"):
        path = SNAP.save_terminal(s, base_dir)
    return s, path


def decide_and_resume(s, C, base_dir: str, decision: str, approver: str, comment: str = "", ack=()):
    node = s.run.paused_at_node
    if not node or s.run.status != "paused":
        raise ValueError("정지 상태가 아닙니다")
    kind = node.replace("approve_", "")
    G.set_decision(s, kind, decision, approver, comment, list(ack))
    return advance(s, C, base_dir, start=node)


def summary(s) -> dict:
    """화면·CLI 용 요약(값 복사; 판단 없음)."""
    return {"run_id": s.run.run_id, "status": s.run.status, "current_node": s.run.current_node, "paused_at_node": s.run.paused_at_node,
            "profile": s.run.profile, "resume_n": s.run.resume_n, "path": [list(p) for p in s.run.path], "snapshot_path": s.run.snapshot_path,
            "fail": {k: s.result[k] for k in ("fail_node", "fail_edge", "fail_code", "fail_reason", "fail_detail")} if s.run.status == "failed" else None}
