# -*- coding: utf-8 -*-
"""tools/e2e_web.py — 개발 검증 도구(Edge + 인터넷 필요): 정적 배포본(web/) E2E: headless Edge 를 원격 디버깅으로 띄우고 CDP(Runtime.evaluate, awaitPromise)로 Pyodide 부팅 → 매트릭스 업로드 → 실행 → 확인 2회 → 결과·엑셀·증빙 zip 까지 브라우저 안에서 확인.
표준 라이브러리만(웹소켓 클라이언트 최소 구현). 인터넷(CDN·PyPI) 필요."""
import base64, json, os, re, shutil, socket, struct, subprocess, sys, tempfile, time, urllib.request
os.chdir(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))  # 저장소 루트(web/ 는 tools/build_web.py 로 먼저 빌드)
PORT, DBG = 8792, 9333


class WS:
    def __init__(self, url):
        m = re.match(r"ws://([^:/]+):(\d+)(/.*)", url); host, port, path = m.group(1), int(m.group(2)), m.group(3)
        self.s = socket.create_connection((host, port)); self.s.settimeout(300)
        key = base64.b64encode(os.urandom(16)).decode()
        self.s.sendall(f"GET {path} HTTP/1.1\r\nHost: {host}:{port}\r\nUpgrade: websocket\r\nConnection: Upgrade\r\nSec-WebSocket-Key: {key}\r\nSec-WebSocket-Version: 13\r\n\r\n".encode())
        buf = b""
        while b"\r\n\r\n" not in buf:
            buf += self.s.recv(4096)
        assert b" 101 " in buf.split(b"\r\n")[0], buf[:200]
        self.n = 0

    def _recv(self, k):
        out = b""
        while len(out) < k:
            c = self.s.recv(k - len(out))
            if not c: raise ConnectionError("closed")
            out += c
        return out

    def send(self, obj):
        data = json.dumps(obj).encode(); mask = os.urandom(4); n = len(data)
        hdr = bytes([0x81]) + (bytes([0x80 | n]) if n < 126 else bytes([0x80 | 126]) + struct.pack(">H", n) if n < 65536 else bytes([0x80 | 127]) + struct.pack(">Q", n))
        self.s.sendall(hdr + mask + bytes(b ^ mask[i % 4] for i, b in enumerate(data)))

    def recv(self):
        while True:
            b0, b1 = self._recv(2); fin, op = b0 & 0x80, b0 & 0x0F; n = b1 & 0x7F
            if n == 126: n = struct.unpack(">H", self._recv(2))[0]
            elif n == 127: n = struct.unpack(">Q", self._recv(8))[0]
            payload = self._recv(n)
            if op == 0x8: raise ConnectionError("ws close")
            if op == 0x9: continue
            if op in (0x1, 0x0):
                if not hasattr(self, "_frag"): self._frag = b""
                self._frag += payload
                if fin:
                    msg = self._frag; self._frag = b""; return json.loads(msg.decode())

    def call(self, method, **params):
        self.n += 1; self.send({"id": self.n, "method": method, "params": params})
        while True:
            m = self.recv()
            if m.get("id") == self.n:
                return m


def ev(ws, expr, await_promise=True, timeout_note=""):
    r = ws.call("Runtime.evaluate", expression=expr, awaitPromise=await_promise, returnByValue=True)
    res = r.get("result", {})
    if "exceptionDetails" in res:
        raise RuntimeError(f"JS 오류{timeout_note}: {json.dumps(res['exceptionDetails'].get('exception', {}).get('description') or res['exceptionDetails'], ensure_ascii=False)[-1800:]}")
    return res.get("result", {}).get("value")


prof = tempfile.mkdtemp(prefix="edge_prof_")
srv = subprocess.Popen([sys.executable, "-m", "http.server", str(PORT), "--bind", "127.0.0.1", "--directory", "web"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
edge = shutil.which("msedge") or r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"
br = subprocess.Popen([edge, "--headless=new", "--disable-gpu", f"--remote-debugging-port={DBG}", f"--user-data-dir={prof}", "--no-first-run", "--window-size=1600,1000", f"http://127.0.0.1:{PORT}/index.html"],
                      stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
try:
    time.sleep(1.5)
    tgt = None
    for _ in range(60):
        try:
            for t in json.load(urllib.request.urlopen(f"http://127.0.0.1:{DBG}/json", timeout=2)):
                if t.get("type") == "page" and "index.html" in t.get("url", ""): tgt = t
            if tgt: break
        except Exception:
            pass
        time.sleep(0.5)
    assert tgt, "페이지 타깃 없음"
    ws = WS(tgt["webSocketDebuggerUrl"]); ws.call("Runtime.enable")
    t0 = time.time()
    for _ in range(240):  # pyodide.js(CDN) 가 내려와 로더 스크립트가 실행되면 window.CB_BOOT 가 생긴다 — 최대 2분 대기
        if ev(ws, "typeof window.CB_BOOT") == "object":
            break
        time.sleep(0.5)
    else:
        raise RuntimeError("window.CB_BOOT 가 생기지 않음 — pyodide.js(CDN) 로딩 실패 또는 로더 미삽입")
    print("boot:", ev(ws, "window.CB_BOOT.then(() => 'ok')"), f"{time.time() - t0:.1f}s")
    print("version/options:", ev(ws, "JSON.stringify({v: VIEWER_VERSION, opts: [...document.querySelectorAll('#f-profile option')].map(o => o.textContent), err: document.getElementById('init-error').textContent, boot: !!document.getElementById('cb-boot')})"))
    # 업로드: 사용자가 평가사 파일을 올리는 것과 같은 경로(파일 → base64 → /api/upload → 파서). E2E_MATRIX 에 xlsx/xlsm/csv 경로를 주면 그 파일로, 없으면 fixture A csv 로.
    mpath = os.environ.get("E2E_MATRIX") or "cb_valuation/step1_curve/tests/fixtures/kisnet_matrix_20251231.csv"
    mb64 = base64.b64encode(open(mpath, "rb").read()).decode(); mname = os.path.basename(mpath)
    t0 = time.time()
    print("upload:", mname, ev(ws, "(async () => { const bin = atob(" + json.dumps(mb64) + "); const arr = new Uint8Array(bin.length); for (let i = 0; i < bin.length; i++) arr[i] = bin.charCodeAt(i); await onMatrixFile(new File([arr], " + json.dumps(mname) + ")); return document.getElementById('matrix-info').textContent.slice(0, 80) + ' | rf=' + document.getElementById('f-rf').value + ' rd=' + document.getElementById('f-rd').value; })()"), f"{time.time() - t0:.1f}s")
    ev(ws, "(() => { const $ = id => document.getElementById(id); $('f-profile').value = 'PCHIP'; $('f-valuation_date').value = '2025-12-31'; $('f-curve_date').value = '2025-12-31'; $('f-curve_set_id').value = 'WEB'; $('f-operator').value = '테스터'; return 'set'; })()", await_promise=False)
    t0 = time.time()
    print("run:", ev(ws, "runApp().then(() => STATE.run.status + ' @ ' + STATE.run.paused_at_node + ' err=' + document.getElementById('run-error').textContent)"), f"{time.time() - t0:.1f}s")
    for i in range(4):
        st = ev(ws, "STATE.run.status", await_promise=False)
        if st != "paused": break
        t0 = time.time()
        print("decide:", ev(ws, "(async () => { document.querySelectorAll('.ack').forEach(x => x.checked = true); await decide('approved'); return STATE.run.status + ' @ ' + (STATE.run.paused_at_node || STATE.run.current_node) + ' err=' + (document.getElementById('a-error')?.textContent || ''); })()"), f"{time.time() - t0:.1f}s")
    print("result:", ev(ws, "JSON.stringify({status: STATE.run.status, par: STATE.par_check.max_abs_err, blocks: BLOCKS ? Object.keys(BLOCKS) : null, rf_rows: BLOCKS ? BLOCKS.RF[0].rows.length : null, evidence: STATE.export && STATE.export.dir, xlsx: STATE.export && STATE.export.xlsx_written, tables: document.querySelectorAll('#result-body table').length, here: document.querySelector('.tabs button.here')?.textContent})"))
    t0 = time.time()
    print("export:", ev(ws, "fetch('/api/export').then(async r => { const b = await r.blob(); return r.status + ' ' + b.size + ' bytes ' + (r.headers.get('Content-Disposition') || ''); })"), f"{time.time() - t0:.1f}s")
    print("evidence zip:", ev(ws, "fetch('/api/evidence_zip').then(async r => { const b = await r.blob(); return r.status + ' ' + b.size + ' bytes ' + (r.headers.get('Content-Disposition') || ''); })"))
    print("footer:", ev(ws, "document.getElementById('foot-note').textContent", await_promise=False)[:60])
finally:
    br.kill(); srv.kill(); time.sleep(0.5); shutil.rmtree(prof, ignore_errors=True)
