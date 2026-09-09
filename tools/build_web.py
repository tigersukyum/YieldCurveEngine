# -*- coding: utf-8 -*-
"""
tools/build_web.py — 정적 배포본(web/) 빌드: GitHub Pages 등 어디에 올려도 링크만 열면 브라우저 안에서 앱이 돈다(Pyodide = WebAssembly 파이썬).
산출물: web/index.html(viewer.html + 로더), web/cb_valuation.zip(엔진 패키지 — tests/fixtures·reference/xl_*.txt·docs 제외 → 금리표·고객 자료 없음), web/.nojekyll
로더가 하는 일: Pyodide(CDN) → micropip 으로 openpyxl(PyPI 순수 파이썬 휠) → cb_valuation.zip 을 MEMFS 에 풀고 browser_api.setup() → window.fetch 의 /api/* 를 B.call 로 바꿔치기.
사용: python tools/build_web.py [--out web] ; 점검만: python tools/build_web.py --check web ; 로컬 확인: python -m http.server 8790 --directory web → http://127.0.0.1:8790/
"""
from __future__ import annotations
import argparse, io, os, re, sys, time, zipfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PKG = os.path.join(ROOT, "cb_valuation")
VIEWER = os.path.join(PKG, "step1_curve", "app", "viewer.html")
PYODIDE_VERSION = "0.27.7"  # Python 3.12 — pyproject requires-python >=3.12 와 맞춘다
CDN = f"https://cdn.jsdelivr.net/pyodide/v{PYODIDE_VERSION}/full/"
EXCLUDE_DIRS = {"__pycache__", "tests", "docs"}
# reference/ 는 엔진이 쓰는 interp_ref.py 만 포함(나머지는 개발 도구·금리표 덤프·ref/ 경로를 가진 대조 스크립트); .md(PRD·CLAUDE.md 등 문서)·.pyc 제외. nodes/verify_*.py 는 엔진이라 포함.
EXCLUDE_PATH_RE = re.compile(r"(^|/)(reference/(?!interp_ref\.py$|__init__\.py$)[^/]+|[^/]*\.md|[^/]*\.pyc)$")
# 배포본 안에 있으면 안 되는 것: 금리표 파일·fixture·엑셀 덤프, 그리고 텍스트 안의 금리표 행(라벨 뒤 소수 셋째자리 숫자가 8개 이상 이어짐)
FORBIDDEN_NAME_RE = re.compile(r"(/tests/|/fixtures/|xl_|/ref/|\.(csv|xlsx|xlsm|json\.gz)$)")
RATE_ROW_RE = re.compile(r"(국고채|회사채|금융|특수|통안)[^\n]{0,40}?(\d+\.\d{3}\s*[,\t]\s*){8,}")

LOADER = """<script src="{cdn}pyodide.js"></script>
<script>
// 브라우저 실행 모드(정적 호스팅): 서버 없이 Pyodide 안에서 같은 파이썬 엔진을 돌린다. 화면 코드는 서버 모드와 같고 fetch("/api/…") 만 바꿔친다.
window.CB_BROWSER = true;
window.CB_BUILD = "{stamp}";
window.CB_BOOT = (async () => {{
  const ov = document.createElement("div"); ov.id = "cb-boot";
  ov.style.cssText = "position:fixed;inset:0;background:#000;color:#fff;font:700 15px Helvetica,Arial,'Malgun Gothic',sans-serif;display:flex;align-items:center;justify-content:center;z-index:9999;text-align:center;padding:24px;line-height:1.6";
  const step = t => {{ ov.innerHTML = "<div>이자율 커브 엔진<br><span style='font-weight:400;font-size:13px'>" + t + "</span></div>"; }};
  step("계산 엔진(Pyodide)을 불러오는 중… 처음 한 번은 10~30초 걸립니다."); document.body.appendChild(ov);
  const py = await loadPyodide({{ indexURL: "{cdn}" }});
  step("openpyxl 을 준비하는 중…");
  await py.loadPackage("micropip");
  await py.pyimport("micropip").install("openpyxl");
  step("앱 패키지를 불러오는 중…");
  const zip = await (await fetch("cb_valuation.zip?v={stamp}", {{ cache: "no-store" }})).arrayBuffer();
  py.unpackArchive(zip, "zip", {{ extractDir: "/app" }});
  py.runPython("import sys; sys.path.insert(0, '/app')\\nfrom cb_valuation.step1_curve.app import browser_api as B\\nB.setup('/work')");
  const call = py.runPython("B.call");
  const orig = window.fetch.bind(window);
  window.fetch = async (url, opts = {{}}) => {{
    const u = typeof url === "string" ? url : url.url;
    if (!u.startsWith("/api/")) return orig(url, opts);
    const res = JSON.parse(call(opts.method || "GET", u.split("?")[0], typeof opts.body === "string" ? opts.body : ""));
    if (res.b64) {{
      const bin = atob(res.b64); const arr = new Uint8Array(bin.length); for (let i = 0; i < bin.length; i++) arr[i] = bin.charCodeAt(i);
      return new Response(arr, {{ status: res.status, headers: {{ "Content-Type": res.content_type, "Content-Disposition": 'attachment; filename="' + res.filename + '"' }} }});
    }}
    return new Response(JSON.stringify(res.json), {{ status: res.status, headers: {{ "Content-Type": "application/json" }} }});
  }};
  ov.remove();
}})();
</script>
"""


def build_zip(out_zip: str) -> int:
    n = 0
    with zipfile.ZipFile(out_zip, "w", zipfile.ZIP_DEFLATED) as z:
        for root, dirs, files in os.walk(PKG):
            dirs[:] = sorted(d for d in dirs if d not in EXCLUDE_DIRS)
            for f in sorted(files):
                p = os.path.join(root, f); rel = os.path.relpath(p, ROOT).replace("\\", "/")
                if EXCLUDE_PATH_RE.search(rel) or f == "viewer.html":  # server.py 는 browser_api 가 graph_payload/handle_upload 를 재사용하므로 포함(표준 라이브러리만 import)
                    continue
                z.write(p, rel); n += 1
    return n


def build_index(stamp: str) -> str:
    html = open(VIEWER, encoding="utf-8").read()
    marker = "<script>\nconst VIEWER_VERSION"
    assert marker in html, "viewer.html 구조가 바뀜(로더 삽입 지점)"
    return html.replace(marker, LOADER.format(cdn=CDN, stamp=stamp) + marker, 1)


def check_bundle(out_dir: str) -> list[str]:
    """배포본 점검: 금지 파일명, 금리표 행 패턴(zip 안 텍스트·index.html), 허용되지 않은 reference/ 파일. 문제 목록을 돌려준다(비어 있으면 통과)."""
    problems = []
    zpath = os.path.join(out_dir, "cb_valuation.zip"); ipath = os.path.join(out_dir, "index.html")
    if not (os.path.exists(zpath) and os.path.exists(ipath)):
        return [f"배포본 없음: {zpath} / {ipath}"]
    with zipfile.ZipFile(zpath) as z:
        for name in z.namelist():
            if FORBIDDEN_NAME_RE.search("/" + name) or EXCLUDE_PATH_RE.search(name):
                problems.append(f"금지 파일: {name}")
            if name.endswith((".py", ".json", ".txt", ".html", ".xml", ".mmd")):
                text = z.read(name).decode("utf-8", "replace")
                if RATE_ROW_RE.search(text):
                    problems.append(f"금리표 행 패턴: {name}")
    html = open(ipath, encoding="utf-8").read()
    if RATE_ROW_RE.search(html):
        problems.append("금리표 행 패턴: index.html")
    return problems


def main(argv):
    ap = argparse.ArgumentParser(); ap.add_argument("--out", default=os.path.join(ROOT, "web")); ap.add_argument("--check", metavar="DIR", help="빌드하지 않고 DIR 의 배포본만 점검")
    a = ap.parse_args(argv[1:])
    if a.check:
        problems = check_bundle(a.check)
        print("\n".join(problems) if problems else f"배포본 점검 통과: {a.check} (금리표·fixture·고객 파일 없음)")
        return 1 if problems else 0
    os.makedirs(a.out, exist_ok=True)
    stamp = time.strftime("%Y%m%dT%H%M%SZ", time.gmtime())
    n = build_zip(os.path.join(a.out, "cb_valuation.zip"))
    with open(os.path.join(a.out, "index.html"), "w", encoding="utf-8", newline="\n") as fh:
        fh.write(build_index(stamp))
    open(os.path.join(a.out, ".nojekyll"), "w").close()
    # 포함 파일 점검: 금리표·고객 자료가 들어가면 안 된다
    with zipfile.ZipFile(os.path.join(a.out, "cb_valuation.zip")) as z:
        names = z.namelist()
    problems = check_bundle(a.out)
    assert not problems, f"배포본에 들어가면 안 되는 것: {problems}"
    print(f"web/ 빌드 완료: 패키지 파일 {n}개, stamp {stamp}, pyodide {PYODIDE_VERSION}; 확인 → python -m http.server 8790 --directory {a.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
