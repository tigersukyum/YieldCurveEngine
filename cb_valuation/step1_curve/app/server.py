# -*- coding: utf-8 -*-
"""
app/server.py — 로컬 HTTP 서버(표준 라이브러리 + openpyxl). 브라우저에서 http://127.0.0.1:8765 를 열면 viewer.html 이 나온다.
API: GET /api/graph(EDGES·노드·프로필·노드 간격·평가사·담당자), GET /api/state, GET /api/blocks(검토자 형식 4블록),
     GET /api/export(현재 state 를 xlsx 로 내려받기), POST /api/parse(붙여넣기 표 미리보기), POST /api/upload(매트릭스 파일·캡처 파일),
     POST /api/run(입력 → 실행), POST /api/decision(승인/거절 → set_decision → 재개), POST /api/resume(스냅샷 파일 → 세션 복원).
서버는 흐름을 판단하지 않는다(EDGES). 승인 필드는 set_decision() 만 쓴다. 외부 네트워크 접근 없음(127.0.0.1 전용).
python -m cb_valuation.step1_curve.app.server [--port 8765] [--open]
"""
from __future__ import annotations
import argparse, base64, getpass, json, os, re, sys, threading, webbrowser
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from ..graph import step1_graph as G
from ..graph import snapshot as SNAP
from ..io.matrix_parser import read_matrix_bytes, preview
from ..io.evidence_writer import dc_blocks, export_xlsx
from . import runner as R

HERE = os.path.dirname(os.path.abspath(__file__))
PKG = os.path.dirname(HERE)
SESSION = {"state": None, "C": None, "base_dir": os.getcwd(), "last_path": None, "error": None}
LOCK = threading.Lock()
C0 = G.Constants


def _state_json(s):
    return json.loads(G.canonical_json(s)) if s is not None else None


def _operators(base_dir: str) -> list:
    """담당자 드롭다운 목록: config/operators.json (없으면 OS 로그인 이름으로 생성)."""
    p = os.path.join(base_dir, "config", "operators.json")
    if not os.path.exists(p):
        os.makedirs(os.path.dirname(p), exist_ok=True)
        with open(p, "w", encoding="utf-8", newline="\n") as fh:
            json.dump({"operators": [getpass.getuser()]}, fh, ensure_ascii=False, indent=1)
    with open(p, encoding="utf-8") as fh:
        return list(json.load(fh).get("operators") or [getpass.getuser()])


def graph_payload():
    j = G.export_edges_json()
    j["node_docs"] = {nid: (fn.__doc__ or "").strip() for nid, (_, _, fn) in G.NODES.items()}
    j["profiles"] = R.profiles_info()
    j["profile_selection"] = C0.PROFILE_SELECTION
    j["step_modes"] = [{"key": k, "label": C0.STEP_LABELS.get(k, k), "dt": v} for k, v in C0.STEP_MODES.items()]
    j["agencies"] = list(C0.AGENCIES)
    j["operators"] = _operators(SESSION["base_dir"])
    j["horizon_default"] = C0.CURVE_HORIZON_Y
    j["tenor_labels"] = list(C0.TENOR_LABELS)
    return j


def _safe_name(name: str) -> str:
    return re.sub(r"[^\w.\-가-힣]", "_", os.path.basename(name or "file"))


def handle_upload(body: dict) -> dict:
    kind, name = body.get("kind"), body.get("name") or "file"
    data = base64.b64decode(body.get("content_b64") or "")
    if kind == "matrix":
        text = read_matrix_bytes(name, data)
        return {"name": name, "matrix_text": text, "preview": preview(text, C0)}
    if kind == "capture":
        d = os.path.join(SESSION["base_dir"], "data", "raw", "uploads"); os.makedirs(d, exist_ok=True)
        stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        path = os.path.join(d, f"{stamp}_{_safe_name(name)}")
        with open(path, "wb") as fh:
            fh.write(data)
        return {"name": name, "capture_path": os.path.relpath(path, SESSION["base_dir"]).replace("\\", "/"), "bytes": len(data)}
    raise ValueError(f"알 수 없는 업로드 종류 {kind!r}")


class H(BaseHTTPRequestHandler):
    def _send(self, code, obj, ctype="application/json", headers=None):
        body = obj if isinstance(obj, bytes) else json.dumps(obj, ensure_ascii=False, default=str).encode("utf-8")
        self.send_response(code); self.send_header("Content-Type", ctype + ("; charset=utf-8" if ctype.startswith(("text", "application/json")) else ""))
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")  # 옛 화면 캐시 방지
        for k, v in (headers or {}).items():
            self.send_header(k, v)
        self.end_headers(); self.wfile.write(body)

    def log_message(self, fmt, *args):  # 조용히
        pass

    def do_GET(self):
        try:
            if self.path in ("/", "/index.html"):
                with open(os.path.join(HERE, "viewer.html"), "rb") as fh:
                    return self._send(200, fh.read(), "text/html")
            if self.path == "/api/graph":
                return self._send(200, graph_payload())
            if self.path == "/api/state":
                with LOCK:
                    s = SESSION["state"]
                    return self._send(200, {"summary": R.summary(s) if s else None, "state": _state_json(s), "saved": SESSION["last_path"], "error": SESSION["error"]})
            if self.path == "/api/blocks":
                with LOCK:
                    s, Cc = SESSION["state"], SESSION["C"]
                    if s is None or not s.tree.df_finite:
                        return self._send(400, {"error": "계산 결과가 아직 없습니다(입력 승인 후 계산이 끝나야 합니다)"})
                    return self._send(200, {c: dc_blocks(s, Cc, c) for c in Cc.CURVE_IDS})
            if self.path.startswith("/api/export"):
                with LOCK:
                    s, Cc = SESSION["state"], SESSION["C"]
                    if s is None or not s.tree.df_finite:
                        return self._send(400, {"error": "계산 결과가 아직 없습니다(입력 승인 후 계산이 끝나야 합니다)"})
                    path = export_xlsx(s, Cc, SESSION["base_dir"])
                with open(path, "rb") as fh:
                    data = fh.read()
                return self._send(200, data, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                                  {"Content-Disposition": f'attachment; filename="{os.path.basename(path)}"'})
            return self._send(404, {"error": "not found"})
        except Exception as e:  # noqa: BLE001
            return self._send(400, {"error": f"{type(e).__name__}: {e}"})

    def do_POST(self):
        n = int(self.headers.get("Content-Length") or 0)
        body = json.loads(self.rfile.read(n).decode("utf-8") or "{}")
        try:
            if self.path == "/api/parse":
                text = body.get("matrix_text") or ""
                return self._send(200, {"matrix_text": text, "preview": preview(text, C0)})
            if self.path == "/api/upload":
                return self._send(200, handle_upload(body))
            with LOCK:
                if self.path == "/api/run":
                    s, Cc = R.prepare_state(body, SESSION["base_dir"])
                    s, path = R.advance(s, Cc, SESSION["base_dir"])
                    SESSION.update(state=s, C=Cc, last_path=path, error=None)
                elif self.path == "/api/resume":  # 스냅샷 파일에서 세션 복원(CLI 와 같은 순서: load_state → with_profile)
                    sp = body.get("snapshot_path") or ""
                    path = sp if os.path.isabs(sp) else os.path.join(SESSION["base_dir"], sp)
                    s = SNAP.load_snapshot(path)
                    SESSION.update(state=s, C=G.Constants.with_profile(s.run.profile), last_path=path, error=None)
                elif self.path == "/api/decision":
                    s, Cc = SESSION["state"], SESSION["C"]
                    if s is None:
                        raise ValueError("실행 중인 세션이 없습니다")
                    s, path = R.decide_and_resume(s, Cc, SESSION["base_dir"], body.get("decision"), body.get("approver", ""), body.get("comment", ""), body.get("ack") or [])
                    SESSION.update(state=s, last_path=path, error=None)
                else:
                    return self._send(404, {"error": "not found"})
                s = SESSION["state"]
                return self._send(200, {"summary": R.summary(s), "state": _state_json(s), "saved": SESSION["last_path"], "error": None})
        except Exception as e:  # noqa: BLE001 — 사용자에게 원문 그대로
            SESSION["error"] = f"{type(e).__name__}: {e}"
            s = SESSION["state"]
            return self._send(400, {"summary": R.summary(s) if s else None, "state": _state_json(s), "saved": SESSION["last_path"], "error": SESSION["error"]})


def main(argv=None):
    ap = argparse.ArgumentParser(); ap.add_argument("--port", type=int, default=8765); ap.add_argument("--open", action="store_true"); ap.add_argument("--base-dir", default=os.getcwd())
    a = ap.parse_args(argv)
    SESSION["base_dir"] = os.path.abspath(a.base_dir)
    srv = ThreadingHTTPServer(("127.0.0.1", a.port), H)
    url = f"http://127.0.0.1:{a.port}/"
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:  # noqa: BLE001
        pass
    print(f"이자율 커브 엔진 앱: {url}   (작업 폴더 {SESSION['base_dir']}; 화면 {os.path.join(HERE, 'viewer.html')}; 종료 Ctrl+C)")
    print("브라우저에서 위 주소를 여세요. viewer.html 파일을 직접 열면 동작하지 않습니다.")
    if a.open:
        webbrowser.open(url)
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
