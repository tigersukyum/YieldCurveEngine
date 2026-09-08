# -*- coding: utf-8 -*-
"""브라우저(Pyodide) 브리지 app/browser_api — 서버와 같은 /api/* 경로를 함수로: 업로드 → 실행 → 확인 → 결과·엑셀·증빙 zip. (실제 Pyodide 실행은 tools/e2e_web.py, Edge+인터넷 필요)"""
import base64, json, os, shutil, tempfile, unittest

from cb_valuation.step1_curve.app import browser_api as B

HERE = os.path.dirname(os.path.abspath(__file__))
FIXTURE_A = os.path.join(HERE, "fixtures", "kisnet_matrix_20251231.csv")


class TestBrowserApi(unittest.TestCase):
    def test_full_flow(self):
        base = tempfile.mkdtemp(prefix="cb_web_"); cwd = os.getcwd()
        try:
            B.setup(base)
            g = json.loads(B.call("GET", "/api/graph"))
            self.assertEqual(g["status"], 200); self.assertEqual([p["label"] for p in g["json"]["profiles"] if p["visible"]], ["선형 보간", "PCHIP"])
            with open(FIXTURE_A, "rb") as fh:
                raw = fh.read()
            up = json.loads(B.call("POST", "/api/upload", json.dumps({"kind": "matrix", "name": "m.csv", "content_b64": base64.b64encode(raw).decode()})))
            self.assertEqual(up["status"], 200); pv = up["json"]["preview"]; self.assertTrue(pv["header_ok"])
            form = {"profile": "LINEAR", "matrix_text": up["json"]["matrix_text"], "step": "weekly", "horizon_years": "10", "rf_row_index": str(pv["rf_candidates"][0]),
                    "rd_row_index": str(pv["rd_candidates"][0]), "valuation_date": "2025-12-31", "curve_date": "2025-12-31", "curve_set_id": "WEB", "operator": "web", "source_agency": "KIS"}
            run = json.loads(B.call("POST", "/api/run", json.dumps(form))); self.assertEqual(run["status"], 200); self.assertEqual(run["json"]["state"]["run"]["status"], "paused")
            for _ in range(4):
                st = json.loads(B.call("GET", "/api/state"))["json"]["state"]
                if st["run"]["status"] != "paused":
                    break
                kind = st["run"]["paused_at_node"].replace("approve_", "")
                codes = sorted({f["code"] for f in st["approval_" + kind]["flags_seen"]})
                d = json.loads(B.call("POST", "/api/decision", json.dumps({"decision": "approved", "approver": "web", "comment": "", "ack": codes})))
                self.assertEqual(d["status"], 200, d["json"].get("error"))
            self.assertEqual(json.loads(B.call("GET", "/api/state"))["json"]["state"]["run"]["status"], "done")
            bl = json.loads(B.call("GET", "/api/blocks")); self.assertEqual(bl["status"], 200); self.assertEqual(bl["json"]["RF"][0]["orient"], "rows")
            ex = json.loads(B.call("GET", "/api/export")); self.assertEqual(ex["status"], 200); self.assertTrue(ex["filename"].endswith(".xlsx")); self.assertGreater(len(base64.b64decode(ex["b64"])), 100000)
            ez = json.loads(B.call("GET", "/api/evidence_zip")); self.assertEqual(ez["status"], 200); self.assertTrue(ez["filename"].endswith("_evidence.zip"))
            self.assertEqual(json.loads(B.call("GET", "/api/nothing"))["status"], 404)
            bad = json.loads(B.call("POST", "/api/run", json.dumps({"profile": "", "matrix_text": ""}))); self.assertEqual(bad["status"], 400); self.assertIn("error", bad["json"])
        finally:
            os.chdir(cwd); shutil.rmtree(base, ignore_errors=True)


if __name__ == "__main__":
    unittest.main()
