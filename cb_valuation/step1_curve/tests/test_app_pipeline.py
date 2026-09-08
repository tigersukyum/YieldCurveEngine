# -*- coding: utf-8 -*-
"""
엔진 수준 두 갈래·골든 테스트(초안): fixture A 를 실제 노드(NODES_IMPL)로 돌려 done 까지 가는지, 게이트 수치가 Constants 허용오차 안인지,
프로필 선택 필수(E48·E49 대응), 결정성(hash_of CALC_PREFIXES), PCHIP_TREE 경로, 노드 간격(월간/주간/일간) 격자, 상품 모드(만기·등급) 를 검사한다.
임시 폴더에 스냅샷·증빙을 쓴다. 러너: python -m unittest discover -s cb_valuation/step1_curve/tests -v   (프로젝트 루트)
"""
import os, shutil, tempfile, unittest
from cb_valuation.step1_curve.graph import step1_graph as G
from cb_valuation.step1_curve.app import runner as R

HERE = os.path.dirname(os.path.abspath(__file__))
FIXTURE_A = os.path.join(HERE, "fixtures", "kisnet_matrix_20251231.csv")


def form_a(profile, **over):
    """커브 전용 모드(앱 기본): 행 선택 + 노드 간격 + 산출 기간. 상품 정보 없음."""
    with open(FIXTURE_A, encoding="utf-8-sig") as fh:
        text = fh.read()
    f = {"profile": profile, "matrix_text": text, "valuation_date": "2025-12-31", "curve_date": "2025-12-31", "curve_set_id": "TEST",
         "operator": "tester", "source_agency": "KIS", "downloaded_at": "2025-12-31T09:00:00+09:00",
         "step": "weekly", "horizon_years": 10, "rf_row_index": 2, "rd_row_index": 58}
    f.update(over)
    return f


def drive_to_done(base, profile, **over):
    s, C = R.prepare_state(form_a(profile, **over), base)
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
        codes = [f["code"] for f in s.sanity.approval_required] + [f["code"] for f in s.approval_input.flags_seen]
        self.assertNotIn("CAPTURE_MISSING", codes)  # 사용자 결정 2026-09-08: PROVENANCE_APPROVAL_FIELDS=() → 캡처 승인 절차 없음
        self.assertEqual(s.result.next_step_interface["profile"], "DEFAULT")

    def test_gates_within_constants(self):
        s, C = self.s, self.C
        self.assertLessEqual(s.par_check.max_abs_err, C.TOL_PAR_FAIL)
        self.assertLessEqual(s.fwd_spot_check.max_abs_err_log, C.TOL_FWD_SPOT_FAIL)
        self.assertLessEqual(s.conv.roundtrip_max_err, C.TOL_ROUNDTRIP_COMP)
        self.assertLessEqual(s.interp.knot_roundtrip_max_err, C.TOL_KNOT_ROUNDTRIP)
        self.assertLessEqual(s.tree.knot_roundtrip_max_err, C.TOL_KNOT_ROUNDTRIP)
        self.assertTrue(s.tree.df_finite and s.tree.df_range_ok and s.tree.df_monotone_ok)
        self.assertEqual(s.fwd.negative_count["RF"], 0)

    def test_rows_grid_and_headline(self):
        s, C = self.s, self.C
        self.assertEqual((s.rows.rf["row_index"], s.rows.rf["selected_by"]), (2, "row_choice"))
        self.assertEqual((s.rows.rd["row_index"], s.rows.rd["block"], s.rows.rd["rating"]), (58, "사모무보증", "BB+"))
        self.assertEqual(s.grid.tree.dt_mode, "weekly")
        self.assertEqual(s.grid.tree.N, round(10 / C.STEP_MODES["weekly"]))
        self.assertEqual(s.grid.remaining_years, 10.0)
        self.assertIsNone(s.grid.maturity_years)
        self.assertEqual(s.headline.candidates, [])  # 상품 만기 없음 → 헤드라인 없음
        self.assertIsNone(s.headline.match_ok)

    def test_evidence_bundle(self):
        s = self.s
        self.assertTrue(s.export.checklist_all_present, [k for k, v in s.export.checklist.items() if not v])
        self.assertTrue(s.export.xlsx_written)
        self.assertTrue(os.path.exists(os.path.join(self.base, s.export.xlsx_path)))
        self.assertTrue(os.path.exists(os.path.join(self.base, s.result.approved_state_path)))
        self.assertTrue(os.path.exists(os.path.join(self.base, s.result.approved_state_path) + ".sha256"))

    def test_basis_labels(self):
        s, C = self.s, self.C
        for c in C.CURVE_IDS:
            for vec in (s.rows.ytm[c], s.bootstrap.spot_pp[c], s.conv.spot_annual[c], s.conv.spot_cont[c], s.tree.spot_cont_on_grid[c], s.fwd.cont_on_grid[c], s.fwd.disc_per_step[c]):
                self.assertIn(vec["basis"], C.BASIS)

    def test_export_xlsx(self):
        from cb_valuation.step1_curve.io.evidence_writer import export_xlsx, dc_blocks
        path = export_xlsx(self.s, self.C, self.base)
        self.assertTrue(os.path.exists(path))
        blocks = dc_blocks(self.s, self.C, "RF")
        self.assertEqual([b["index"] for b in blocks], [1, 2, 3, 4])
        row = next(x for x in blocks[3]["rows"] if x["label"] == "FORMULA II -CUMM")
        self.assertEqual(row["values"][0], 1.0)  # 검토자 r34: 첫 열 = 1


class TestStepModes(unittest.TestCase):
    def test_monthly_and_daily(self):
        for step, years in (("monthly", 10), ("daily", 3)):
            base = tempfile.mkdtemp(prefix="cb_test_")
            try:
                s, C = drive_to_done(base, "DEFAULT", step=step, horizon_years=years)
                self.assertEqual(s.run.status, "done", s.result.fail_reason)
                self.assertEqual(s.grid.tree.N, round(years / C.STEP_MODES[step]))
                self.assertAlmostEqual(s.grid.tree.times[-1], years, places=C.T_ROUND_DIGITS)
                self.assertLessEqual(s.par_check.max_abs_err, C.TOL_PAR_FAIL)
            finally:
                shutil.rmtree(base, ignore_errors=True)

    def test_horizon_over_constant_fails(self):
        base = tempfile.mkdtemp(prefix="cb_test_")
        try:
            s, C = R.prepare_state(form_a("DEFAULT", horizon_years=12), base)
            s, _ = R.advance(s, C, base)
            s, _ = R.decide_and_resume(s, C, base, "approved", "tester")
            self.assertEqual((s.run.status, s.result.fail_code), ("failed", "MATURITY_GT_HORIZON"))
        finally:
            shutil.rmtree(base, ignore_errors=True)


class TestProductMode(unittest.TestCase):
    def test_product_fields_select_row_and_headline(self):
        base = tempfile.mkdtemp(prefix="cb_test_")
        try:
            s, C = drive_to_done(base, "DEFAULT", rf_row_index=None, rd_row_index=None,
                                 instrument={"maturity_date": "2029-06-21", "issuance_type": "사모", "rating": "BB+", "reported_rf_pct": 3.048, "reported_rd_pct": 12.549})
            self.assertEqual(s.run.status, "done", s.result.fail_reason)
            self.assertEqual((s.rows.rd["row_index"], s.rows.rd["selected_by"]), (58, "product"))
            self.assertIsNotNone(s.grid.maturity_years)
            self.assertEqual(s.headline.rule, C.HEADLINE_RULE)
            self.assertTrue(s.headline.match_ok)  # 3자리 반올림 비교
            self.assertEqual([c["def"] for c in s.headline.candidates], list(C.HEADLINE_DEFS))
        finally:
            shutil.rmtree(base, ignore_errors=True)


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

    def test_missing_step_is_provenance_incomplete(self):
        """E04: 노드 간격 미선택 → 출처불완전."""
        base = tempfile.mkdtemp(prefix="cb_test_")
        try:
            s, C = R.prepare_state(form_a("DEFAULT", step=None), base)
            s, _ = R.advance(s, C, base)
            self.assertEqual((s.run.status, s.result.fail_code), ("failed", "PROVENANCE_INCOMPLETE"))
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
