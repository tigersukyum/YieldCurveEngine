# -*- coding: utf-8 -*-
"""
엔진 수준 두 갈래·골든 테스트(초안): fixture A 를 실제 노드(NODES_IMPL)로 돌려 done 까지 가는지, 게이트 수치가 Constants 허용오차 안인지,
프로필 선택 필수(E48·E49 대응), 결정성(hash_of CALC_PREFIXES), PCHIP_TREE 경로를 검사한다. 임시 폴더에 스냅샷·증빙을 쓴다.
러너: python -m unittest discover -s cb_valuation/step1_curve/tests -v   (프로젝트 루트)
"""
import os, shutil, tempfile, unittest
from cb_valuation.step1_curve.graph import step1_graph as G
from cb_valuation.step1_curve.app import runner as R

HERE = os.path.dirname(os.path.abspath(__file__))
FIXTURE_A = os.path.join(HERE, "fixtures", "kisnet_matrix_20251231.csv")


def form_a(profile, **over):
    with open(FIXTURE_A, encoding="utf-8-sig") as fh:
        text = fh.read()
    f = {"profile": profile, "matrix_text": text, "valuation_date": "2025-12-31", "curve_date": "2025-12-31", "curve_set_id": "TEST",
         "operator": "tester", "source_agency": "KIS", "downloaded_at": "2025-12-31T09:00:00+09:00",
         "instrument": {"maturity_date": "2029-06-21", "issuance_type": "사모", "rating": "BB+", "issuer": "참조 모형(KBI)"}}
    f.update(over)
    return f


def drive_to_done(base, profile):
    s, C = R.prepare_state(form_a(profile), base)
    s, _ = R.advance(s, C, base)
    while s.run.status == "paused":
        kind = s.run.paused_at_node.replace("approve_", "")
        ack = [f["code"] for f in s[f"approval_{kind}"].flags_seen] if kind == "exception" else []
        s, _ = R.decide_and_resume(s, C, base, "approved", "tester", "auto", ack)
    return s, C


class TestPipelineFixtureA(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.base = tempfile.mkdtemp(prefix="cb_test_")
        cls.s, cls.C = drive_to_done(cls.base, "DEFAULT")

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.base, ignore_errors=True)

    def test_done_path(self):
        s = self.s
        self.assertEqual(s.run.status, "done")
        names = [p[1] for p in s.run.path]
        self.assertEqual(names[-1], "내보내기완료")
        self.assertIn("승인필요플래그존재", names)  # fixture A: 캡처 없음 → CAPTURE_MISSING
        self.assertEqual(s.result.next_step_interface["profile"], "DEFAULT")

    def test_gates_within_constants(self):
        s, C = self.s, self.C
        self.assertLessEqual(s.par_check.max_abs_err, C.TOL_PAR_FAIL)
        self.assertLessEqual(s.fwd_spot_check.max_abs_err_log, C.TOL_FWD_SPOT_FAIL)
        self.assertLessEqual(s.conv.roundtrip_max_err, C.TOL_ROUNDTRIP_COMP)
        self.assertLessEqual(s.interp.knot_roundtrip_max_err, C.TOL_KNOT_ROUNDTRIP)
        self.assertTrue(s.tree.df_finite and s.tree.df_range_ok and s.tree.df_monotone_ok)
        self.assertEqual(s.fwd.negative_count["RF"], 0)

    def test_rows_and_headline(self):
        s = self.s
        self.assertEqual(s.rows.rf["row_index"], 2)   # KIS-NET row2 국고채
        self.assertEqual(s.rows.rd["row_index"], 58)  # 사모무보증 BB+ row58
        self.assertEqual(s.rows.rd["block"], "사모무보증")
        self.assertFalse(s.rows.rd_fallback_used)
        self.assertEqual(s.headline.rule, self.C.HEADLINE_RULE)
        self.assertIsNone(s.headline.match_ok)  # 보고서 값 미입력
        defs = [c["def"] for c in s.headline.candidates]
        self.assertEqual(defs, list(self.C.HEADLINE_DEFS))

    def test_evidence_bundle(self):
        s = self.s
        self.assertTrue(s.export.checklist_all_present, [k for k, v in s.export.checklist.items() if not v])
        self.assertTrue(s.export.xlsx_written)
        self.assertTrue(os.path.exists(os.path.join(self.base, s.export.xlsx_path)))
        self.assertTrue(os.path.exists(os.path.join(self.base, s.result.approved_state_path)))

    def test_basis_labels(self):
        s, C = self.s, self.C
        for c in C.CURVE_IDS:
            for vec in (s.rows.ytm[c], s.bootstrap.spot_pp[c], s.conv.spot_annual[c], s.conv.spot_cont[c], s.tree.spot_cont_on_grid[c], s.fwd.cont_on_grid[c], s.fwd.disc_per_step[c]):
                self.assertIn(vec["basis"], C.BASIS)


class TestProfileSelection(unittest.TestCase):
    def test_missing_profile_raises(self):
        base = tempfile.mkdtemp(prefix="cb_test_")
        try:
            with self.assertRaises(ValueError):
                R.prepare_state(form_a(""), base)
            with self.assertRaises(NotImplementedError):
                R.prepare_state(form_a("KICPA_1130"), base)
        finally:
            shutil.rmtree(base, ignore_errors=True)

    def test_profile_mismatch_edge(self):
        """E49: 선택 프로필 ≠ 실행 상수 → 프로필불일치 → fail (엔진 수준)."""
        base = tempfile.mkdtemp(prefix="cb_test_")
        try:
            s, C = R.prepare_state(form_a("DEFAULT"), base)
            s.provenance.method_choice.profile = "PCHIP_TREE"
            s, _ = R.advance(s, C, base)
            self.assertEqual(s.run.status, "failed")
            self.assertEqual(s.result.fail_code, "PROFILE_MISMATCH")
        finally:
            shutil.rmtree(base, ignore_errors=True)


class TestDeterminismAndPchip(unittest.TestCase):
    def test_same_input_same_calc_hash(self):
        b1, b2 = tempfile.mkdtemp(prefix="cb_t1_"), tempfile.mkdtemp(prefix="cb_t2_")
        try:
            s1, C = drive_to_done(b1, "DEFAULT"); s2, _ = drive_to_done(b2, "DEFAULT")
            self.assertEqual(G.hash_of(s1, C.CALC_PREFIXES), G.hash_of(s2, C.CALC_PREFIXES))
            self.assertEqual(s1.result.next_step_interface, s2.result.next_step_interface)
        finally:
            shutil.rmtree(b1, ignore_errors=True); shutil.rmtree(b2, ignore_errors=True)

    def test_pchip_tree_done(self):
        base = tempfile.mkdtemp(prefix="cb_test_")
        try:
            s, C = drive_to_done(base, "PCHIP_TREE")
            self.assertEqual(s.run.status, "done")
            self.assertEqual((s.tree.interp_method_used, s.tree.interp_space_used), ("pchip", "log_df"))
            self.assertEqual(s.result.next_step_interface["spot_lookup"]["basis"], "continuous")
            self.assertEqual(s.tree.extrap_left_flat_steps["RF"], [])  # log_df 는 (0,0) 마디 포함 → 좌측 외삽 없음
            self.assertLessEqual(s.par_check.max_abs_err, C.TOL_PAR_FAIL)
        finally:
            shutil.rmtree(base, ignore_errors=True)


if __name__ == "__main__":
    unittest.main()
