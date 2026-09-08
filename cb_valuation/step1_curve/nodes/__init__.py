# -*- coding: utf-8 -*-
"""
nodes/ — 노드 구현(자기 접두사만 채움). 흐름(EDGES)·상수·라우터는 graph/step1_graph.py 에만 있다.
NODES_IMPL 은 step1_graph.NODES 와 같은 id·한국어 이름·접두사를 쓰고 함수만 구현으로 바꾼 등록표다(run(nodes=NODES_IMPL)).
승인 노드·sanity_check·done·fail·wait_for_human 은 step1_graph 의 함수를 그대로 쓴다(run() 이 항등을 검사한다).
unsupported(C) 는 이 초안이 지원하지 않는 상수 조합을 실행 전에 알려준다(러너 사전 게이트; 노드 안의 NotImplementedError 는 도달 불가 방어).
"""
from ..graph import step1_graph as G
from ..curve.interp import INTERPOLATORS
from . import (load_matrix, interpret_labels, select_rows, build_grid, interpolate, bootstrap, verify_par,
               convert_compounding, map_tree_grid, compute_forward, verify_fwd_spot, run_sensitivity, compute_headline, export_evidence)

_IMPL = {
    "load_matrix": load_matrix.node_load_matrix,
    "interpret_labels": interpret_labels.node_interpret_labels,
    "select_rows": select_rows.node_select_rows,
    "build_grid": build_grid.node_build_grid,
    "interpolate": interpolate.node_interpolate,
    "bootstrap": bootstrap.node_bootstrap,
    "verify_par": verify_par.node_verify_par,
    "convert_compounding": convert_compounding.node_convert_compounding,
    "map_tree_grid": map_tree_grid.node_map_tree_grid,
    "compute_forward": compute_forward.node_compute_forward,
    "verify_fwd_spot": verify_fwd_spot.node_verify_fwd_spot,
    "run_sensitivity": run_sensitivity.node_run_sensitivity,
    "compute_headline": compute_headline.node_compute_headline,
    "export_evidence": export_evidence.node_export_evidence,
}

NODES_IMPL = {nid: (ko, prefixes, _IMPL.get(nid, fn)) for nid, (ko, prefixes, fn) in G.NODES.items()}

SUPPORTED = {
    "BOOTSTRAP_MODE": ("interpolate_then_bootstrap",), "PRICE_MODE": ("par",), "INTERP_SPACE_PRE": ("ytm",),
    "INTERP_SPACE_GRID": ("spot_annual", "spot_continuous", "log_df"), "EXTRAP_LEFT": ("flat",), "EXTRAP_RIGHT": ("flat_forward", "flat_spot"),
    "TREE_FWD_RULE": ("continuous_from_spot", "piecewise_quarter_step"), "NODE_DISCOUNT_CONV": ("3_continuous_fwd", "1_discrete_fwd"), "DAYCOUNT": ("ACT/365", "30/360"),
    "RF_SEED_3M": ("none",), "RF_REGRID_RULE": ("interp",), "COUPON_CONV": ("nominal_div_m", "effective_root"),
    "AI_ENABLED": (False,), "EXCEL_REPLICATE": (False,),
}


def unsupported(C) -> list:
    out = [f"{k}={getattr(C, k)!r} (지원: {v})" for k, v in SUPPORTED.items() if getattr(C, k) not in v]
    for k in ("INTERP_METHOD", "INTERP_METHOD_PRE"):
        if getattr(C, k) not in INTERPOLATORS:
            out.append(f"{k}={getattr(C, k)!r} (지원: {sorted(INTERPOLATORS)})")
    if C.TREE_GRID.get("mode") not in ("report", "weekly", "excel"):
        out.append(f"TREE_GRID.mode={C.TREE_GRID.get('mode')!r}")
    return out
