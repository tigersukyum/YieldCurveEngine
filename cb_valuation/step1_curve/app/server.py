# -*- coding: utf-8 -*-
"""
app/server.py — 로컬 HTTP 서버(표준 라이브러리). 브라우저에서 http://127.0.0.1:8765 를 열면 viewer.html 이 나온다.
API: GET /api/graph(EDGES·노드·프로필), GET /api/state, GET /api/fixture(연습 데이터), POST /api/run(입력 → 실행), POST /api/decision(승인/거절 → set_decision → 재개), POST /api/resume(스냅샷 파일 → 세션 복원).
서버는 흐름을 판단하지 않는다(EDGES). 승인 필드는 set_decision() 만 쓴다. 외부 네트워크 접근 없음(127.0.0.1 전용).
python -m cb_valuation.step1_curve.app.server [--port 8765] [--open]
"""
from __future__ import annotations
import argparse, json, os, sys, threading, webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from ..graph import step1_graph as G
from ..graph import snapshot as SNAP
from . import runner as R

HERE = os.path.dirname(os.path.abspath(__file__))
PKG = os.path.dirname(HERE)
SESSION = {"state": None, "C": None, "base_dir": os.getcwd(), "last_path": None, "error": None}
LOCK = threading.Lock()


def _state_json(s):
    return json.loads(G.canonical_json(s)) if s is not None else None


def graph_payload():
    j = G.export_edges_json()
    j["node_docs"] = {nid: (fn.__doc__ or "").strip() for nid, (_, _, fn) in G.NODES.items()}
    j["profiles"] = R.profiles_info()
    j["profile_selection"] = G.Constants.PROFILE_SELECTION
    return j


def fixture_payload():
    p = os.path.join(PKG, "tests", "fixtures", "kisnet_matrix_20251231.csv")
    with open(p, encoding="utf-8-sig") as fh:
        text = fh.read()
    return {"matrix_text": text, "valuation_date": "2025-12-31", "curve_date": "2025-12-31", "curve_set_id": "KBI_CB1", "source_agency": "KIS",
            "instrument": {"issuer": "참조 모형(KBI)", "cb_name": "제N회 무기명식 이권부 무보증 사모 전환사채", "maturity_date": "2029-06-21", "issuance_type": "사모", "rating": "BB+"}}


class H(BaseHTTPRequestHandler):
    def _send(self, code, obj, ctype="application/json"):
        body = obj if isinstance(obj, bytes) else json.dumps(obj, ensure_ascii=False, default=str).encode("utf-8")
        self.send_response(code); self.send_header("Content-Type", ctype + "; charset=utf-8"); self.send_header("Content-Length", str(len(body))); self.end_headers()
        self.wfile.write(body)

    def log_message(self, fmt, *args):  # 조용히
        pass

    def do_GET(self):
        if self.path in ("/", "/index.html"):
            with open(os.path.join(HERE, "viewer.html"), "rb") as fh:
                return self._send(200, fh.read(), "text/html")
        if self.path == "/api/graph":
            return self._send(200, graph_payload())
        if self.path == "/api/fixture":
            return self._send(200, fixture_payload())
        if self.path == "/api/state":
            with LOCK:
                s = SESSION["state"]
                return self._send(200, {"summary": R.summary(s) if s else None, "state": _state_json(s), "saved": SESSION["last_path"], "error": SESSION["error"]})
        return self._send(404, {"error": "not found"})

    def do_POST(self):
        n = int(self.headers.get("Content-Length") or 0)
        body = json.loads(self.rfile.read(n).decode("utf-8") or "{}")
        try:
            with LOCK:
                if self.path == "/api/run":
                    s, C = R.prepare_state(body, SESSION["base_dir"])
                    s, path = R.advance(s, C, SESSION["base_dir"])
                    SESSION.update(state=s, C=C, last_path=path, error=None)
                elif self.path == "/api/resume":  # 스냅샷 파일에서 세션 복원(CLI 와 같은 순서: load_state → with_profile)
                    sp = body.get("snapshot_path") or ""
                    path = sp if os.path.isabs(sp) else os.path.join(SESSION["base_dir"], sp)
                    s = SNAP.load_snapshot(path)
                    SESSION.update(state=s, C=G.Constants.with_profile(s.run.profile), last_path=path, error=None)
                elif self.path == "/api/decision":
                    s, C = SESSION["state"], SESSION["C"]
                    if s is None:
                        raise ValueError("실행 중인 세션이 없습니다")
                    s, path = R.decide_and_resume(s, C, SESSION["base_dir"], body.get("decision"), body.get("approver", ""), body.get("comment", ""), body.get("ack") or [])
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
    print(f"CB 커브 엔진 앱: {url}   (작업 폴더 {SESSION['base_dir']}; 종료 Ctrl+C)")
    if a.open:
        webbrowser.open(url)
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
