# -*- coding: utf-8 -*-
"""
snapshot.py — 정지 스냅샷·승인 완료·실패 state 의 파일 저장/로드 (STATE_SCHEMA §3.5, GRAPH_SPEC §6).
경로 규칙: state/<valuation_date>__<curve_set_id>/snapshot__<node>__<n>.json  (n = 그 노드의 정지 회차, 1부터)
파일 쓰기는 여기와 app/cli.py·app/server.py 만 한다(노드는 파일을 만들지 않는다). 스냅샷은 삭제 금지(감사 증빙).
"""
from __future__ import annotations
import hashlib, json, os
from . import step1_graph as G

PAUSE_EXIT_CODE = 3


def state_key(state) -> str:
    return f"{state.provenance.valuation_date or 'nodate'}__{state.run.curve_set_id or 'noset'}"


def state_dir(state, base_dir: str) -> str:
    return os.path.join(base_dir, "state", state_key(state))


def dump_state(state) -> str:
    """정규 JSON(들여쓰기) — hash_of 와 같은 canonical 규칙으로 값을 직렬화하되 사람이 읽게 들여쓴다."""
    return json.dumps(json.loads(G.canonical_json(state)), ensure_ascii=False, indent=1, sort_keys=True)


def save_snapshot(state, base_dir: str) -> str:
    d = state_dir(state, base_dir); os.makedirs(d, exist_ok=True)
    node = state.run.paused_at_node or "unknown"
    n = 1 + sum(1 for f in os.listdir(d) if f.startswith(f"snapshot__{node}__") and f.endswith(".json"))
    path = os.path.join(d, f"snapshot__{node}__{n}.json")
    state.run.snapshot_path = os.path.relpath(path, base_dir).replace("\\", "/")
    with open(path, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(dump_state(state))
    return path


def save_terminal(state, base_dir: str) -> str:
    """done → approved_state.json + 사이드카 approved_state.json.sha256, failed → failed_state.json.
    해시 원상 = 파일 바이트 그대로(파일 안의 result.approved_state_sha256 는 null). 메모리 state 에는 해시를 기록한다(STATE_SCHEMA §3.5)."""
    d = state_dir(state, base_dir); os.makedirs(d, exist_ok=True)
    name = "approved_state.json" if state.run.status == "done" else "failed_state.json"
    path = os.path.join(d, name)
    if state.run.status == "done":
        state.result.approved_state_path = os.path.relpath(path, base_dir).replace("\\", "/")
        state.result.approved_state_sha256 = None
        payload = dump_state(state)
        sha = hashlib.sha256(payload.encode("utf-8")).hexdigest()
        with open(path, "w", encoding="utf-8", newline="\n") as fh:
            fh.write(payload)
        with open(path + ".sha256", "w", encoding="utf-8", newline="\n") as fh:
            fh.write(f"{sha}  {name}\n")
        state.result.approved_state_sha256 = sha
        return path
    with open(path, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(dump_state(state))
    return path


def load_snapshot(path: str):
    with open(path, encoding="utf-8") as fh:
        return G.load_state(json.load(fh))
