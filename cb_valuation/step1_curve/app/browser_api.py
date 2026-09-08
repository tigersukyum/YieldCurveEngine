# -*- coding: utf-8 -*-
"""
app/browser_api.py — 브라우저(Pyodide) 브리지. server.py 의 /api/* 와 **같은 경로·같은 JSON** 을 함수 호출로 제공한다.
GitHub Pages 같은 정적 호스팅에서 링크만 열면 브라우저 안의 파이썬(Pyodide, WebAssembly)이 이 패키지를 실행한다 — 서버·네트워크 전송 없음,
매트릭스·산출물은 전부 브라우저 메모리 파일시스템(/work)에만 있다(탭을 닫으면 사라짐; xlsx·증빙 zip 은 내려받기 버튼으로 저장).
흐름 판단은 여기에도 없다(runner → run(EDGES)). tools/build_web.py 가 web/index.html 의 로더에서 `B.call` 을 fetch 대신 부른다.
"""
from __future__ import annotations
import base64, json, os
from . import server as SV
from . import runner as R
from ..graph import step1_graph as G
from ..graph import snapshot as SNAP
from ..io.matrix_parser import preview
from ..io.evidence_writer import dc_blocks, export_xlsx, evidence_zip_bytes

XLSX_CT = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"


def setup(base_dir: str = "/work") -> str:
    """작업 폴더(MEMFS)를 만들고 세션의 base_dir 로 삼는다. 담당자 목록 파일은 빈 목록으로 두어 화면이 이름을 직접 받게 한다."""
    os.makedirs(os.path.join(base_dir, "config"), exist_ok=True)
    p = os.path.join(base_dir, "config", "operators.json")
    if not os.path.exists(p):
        with open(p, "w", encoding="utf-8") as fh:
            json.dump({"operators": []}, fh)
    SV.SESSION["base_dir"] = base_dir
    os.chdir(base_dir)
    return base_dir


def _ok(obj, status=200):
    return json.dumps({"status": status, "json": obj}, ensure_ascii=False, default=str)


def _err(status, msg, extra=None):
    j = {"error": msg}
    if extra:
        j.update(extra)
    return json.dumps({"status": status, "json": j}, ensure_ascii=False, default=str)


def _file(data: bytes, content_type: str, filename: str):
    return json.dumps({"status": 200, "b64": base64.b64encode(data).decode("ascii"), "content_type": content_type, "filename": filename})


def _state_payload():
    s = SV.SESSION["state"]
    return {"summary": R.summary(s) if s else None, "state": SV._state_json(s), "saved": SV.SESSION["last_path"], "error": SV.SESSION["error"]}


def call(method: str, path: str, body_json: str = "") -> str:
    """JS → (method, path, body JSON 문자열) → JSON 문자열 {status, json} 또는 {status, b64, content_type, filename}."""
    S = SV.SESSION
    try:
        body = json.loads(body_json) if body_json else {}
        if path == "/api/graph":
            return _ok(SV.graph_payload())
        if path == "/api/version":
            return _ok({"app_version": SV.APP_VERSION, "pid": 0, "base_dir": S["base_dir"], "runtime": "browser"})
        if path == "/api/state":
            return _ok(_state_payload())
        if path == "/api/blocks":
            s, Cc = S["state"], S["C"]
            if s is None or not s.tree.df_finite:
                return _err(400, "계산 결과가 아직 없습니다(입력 확인 후 계산이 끝나야 합니다)")
            return _ok({c: dc_blocks(s, Cc, c) for c in Cc.CURVE_IDS})
        if path.startswith("/api/export"):
            s, Cc = S["state"], S["C"]
            if s is None or not s.tree.df_finite:
                return _err(400, "계산 결과가 아직 없습니다(입력 확인 후 계산이 끝나야 합니다)")
            p = export_xlsx(s, Cc, S["base_dir"])
            with open(p, "rb") as fh:
                return _file(fh.read(), XLSX_CT, os.path.basename(p))
        if path.startswith("/api/evidence_zip"):
            s = S["state"]
            if s is None or not s.export.dir:
                return _err(400, "증빙 번들이 아직 없습니다(최종 확인 후 생성)")
            return _file(evidence_zip_bytes(s, S["base_dir"]), "application/zip", os.path.basename(s.export.dir.rstrip("/")) + "_evidence.zip")
        if path == "/api/parse":
            text = body.get("matrix_text") or ""
            return _ok({"matrix_text": text, "preview": preview(text, SV.C0)})
        if path == "/api/upload":
            return _ok(SV.handle_upload(body))
        if path == "/api/run":
            s, Cc = R.prepare_state(body, S["base_dir"])
            s, p = R.advance(s, Cc, S["base_dir"])
            S.update(state=s, C=Cc, last_path=p, error=None)
            return _ok(_state_payload())
        if path == "/api/resume":
            sp = body.get("snapshot_path") or ""
            p = sp if os.path.isabs(sp) else os.path.join(S["base_dir"], sp)
            s = SNAP.load_snapshot(p)
            S.update(state=s, C=G.Constants.with_profile(s.run.profile), last_path=p, error=None)
            return _ok(_state_payload())
        if path == "/api/decision":
            s, Cc = S["state"], S["C"]
            if s is None:
                raise ValueError("실행 중인 세션이 없습니다")
            s, p = R.decide_and_resume(s, Cc, S["base_dir"], body.get("decision"), body.get("approver", ""), body.get("comment", ""), body.get("ack") or [])
            S.update(state=s, last_path=p, error=None)
            return _ok(_state_payload())
        if path == "/api/shutdown":
            return _ok({"ok": True, "pid": 0})
        return _err(404, "not found")
    except Exception as e:  # noqa: BLE001 — 사용자에게 원문 그대로
        S["error"] = f"{type(e).__name__}: {e}"
        return _err(400, S["error"], {"summary": R.summary(S["state"]) if S["state"] else None, "state": SV._state_json(S["state"]), "saved": S["last_path"]})
