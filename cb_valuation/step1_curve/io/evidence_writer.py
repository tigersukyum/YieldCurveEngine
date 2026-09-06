# -*- coding: utf-8 -*-
"""
io/evidence_writer.py — 증빙 번들 작성기 (GRAPH_SPEC §10, docs/XLSX_TEMPLATE.md). state 값 복사만(배율·서식 제외) — 파생값은 노드가 state 에 기록한다.
evidence/<valuation_date>__<curve_set_id>/ 에 EVIDENCE_FILES 01~12 + README_conventions.md + checklist_map.json + evidence.xlsx(필수).
xlsx 의 Rf_dc/Rd_dc 는 XLSX_DC_BLOCKS/XLSX_DC_STYLE(검토자 2024 패키지 배치) 대로 행 지향으로 쓰고, 그 밖의 시트는 XLSX_COLUMNS 열 지향이다.
값은 state 의 double 그대로 쓰고 서식만 입힌다. 위치표(cell_map)는 실제 쓴 범위로 만든다.
"""
from __future__ import annotations
import csv, json, math, os
from ..graph import step1_graph as G

XLSX_NAME = "evidence.xlsx"


def _key(s):
    return f"{s.provenance.valuation_date or 'nodate'}__{s.run.curve_set_id or 'noset'}"


def _csv(path, header, rows):
    with open(path, "w", encoding="utf-8-sig", newline="") as fh:
        w = csv.writer(fh); w.writerow(header)
        for r in rows:
            w.writerow(["" if v is None else v for v in r])


def _json(path, obj):
    with open(path, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(json.dumps(json.loads(G.canonical_json(obj)), ensure_ascii=False, indent=1))


def _col(n: int) -> str:
    out = ""
    while n:
        n, r = divmod(n - 1, 26); out = chr(65 + r) + out
    return out


def dc_values(s, C, c: str) -> dict:
    """XLSX_DC_BLOCKS 의 행 라벨(치환 전 원문) → 값 리스트. **state 값 복사만** 한다(PAR_FACE 배율·WEEKS 환산은 표시 배율).
    블록 1·3 = 마디/부트스트랩 격자, 블록 2·4 = 트리 격자 스텝. 정의는 docs/XLSX_TEMPLATE.md §4."""
    knots = s.grid.knots[c]
    ann = dict(zip(s.conv.spot_annual[c]["times"], s.conv.spot_annual[c]["values"]))
    cont = dict(zip(s.conv.spot_cont[c]["times"], s.conv.spot_cont[c]["values"]))
    bt = s.grid.boot_times[c]
    pts = s.bootstrap.points[c]
    par = s.par_check.per_maturity[c]
    times = s.grid.tree.times
    N = len(times) - 1
    fsr = s.fwd_spot_check.rows.get(c, []) if isinstance(s.fwd_spot_check.rows, dict) else []
    W = C.WEEKS_PER_YEAR
    return {
        # 블록 1 (마디)
        "WEEKS": [round(k["t"] * W) for k in knots], "TENOR": [k["tenor"] for k in knots],
        "{rate} - YTM": [k["ytm"] for k in knots], "SPOT RATE": [ann.get(round(k["t"], C.T_ROUND_DIGITS)) for k in knots],
        # 블록 2 (트리 격자)
        "STEP": list(range(1, N + 1)), "t (years)": times[1:], "{rate} - YTM#grid": s.tree.ytm_on_grid[c]["values"][1:],
        "SPOT RATE#grid": s.tree.spot_annual_on_grid[c]["values"][1:], "FORWARD RATE": s.fwd.disc_per_step[c]["values"],
        # 블록 3 (부트스트랩 격자)
        "{period}": [p["n"] for p in pts], "WEEKS#boot": [round(t * W) for t in bt], "YTM - YEARLY": s.interp.ytm_on_coupon_grid[c]["values"],
        "{period} PAYMENT RATE": [p["c"] for p in pts], "PV OF PRINCIPAL": [C.PAR_FACE * p["df"] for p in pts],
        "PV OF BOND": [C.PAR_FACE * r["target"] for r in par], "PVF OF SPOT Rate": [p["df"] for p in pts],
        "SUM OF PVF SPOT JUST PRIOR TO": [p["sum_df_prior"] for p in pts], "{period} SPOT Rate": [p["spot_pp"] for p in pts],
        "SPOT Rate -Yearly": [ann.get(t) for t in bt], "SPOT Rate -Continuous": [cont.get(t) for t in bt],
        "FORWARD Rate - {period}": s.fwd.boot_fwd_pp[c]["values"], "FORWARD Rate - Yearly": s.fwd.boot_fwd_annual[c]["values"],
        "MODEL CHECK (PAR REPRICE)": [C.PAR_FACE * r["price"] for r in par], "PAR RESIDUAL": [r["residual"] for r in par],
        # 블록 4 (트리 격자; 검토자 r32~r38 의미)
        "STEP SPOT RATE": s.fwd.spot_per_step[c]["values"], "FORMULA I": s.fwd.growth_step[c], "FORMULA II -CUMM": s.fwd.growth_cum_prev[c],
        "STEP FORWARD RATE": s.fwd.disc_per_step[c]["values"], "PVF OF FORWARD RATE": s.fwd.df_step[c],
        "MODEL CHECK (PROD DF_FWD - DF_SPOT)": [r["diff_prod"] for r in fsr] if fsr else [None] * N,
        "MODEL CHECK (PV)": [C.PAR_FACE * d for d in s.fwd.df_backward[c]],
    }


def _write_dc_sheet(ws, s, C, c: str) -> dict:
    from openpyxl.styles import Font
    st = C.XLSX_DC_STYLE
    m = C.RF_FREQ if c == "RF" else C.RD_FREQ
    rate = "RISK FREE RATE" if c == "RF" else "RISKY RATE"
    period = {1: "YEAR", 2: "HALF-YEAR", 4: "QUARTER", 12: "MONTH"}.get(m, f"1/{m}Y")
    vals = dc_values(s, C, c)
    ws[st["title_cell"]] = "무위험이자율" if c == "RF" else "위험이자율"; ws[st["title_cell"]].font = Font(bold=True)
    ws[st["date_cell"]] = s.provenance.valuation_date
    ws.column_dimensions[st["label_col"]].width = st["width_label"]
    ws.freeze_panes = st["freeze_panes"]
    r = 3
    ranges = {}
    first_col = ord(st["first_data_col"]) - 64
    max_col = first_col
    for bi, (title, rows) in enumerate(C.XLSX_DC_BLOCKS, start=1):
        ws.cell(r, 2, title.format(rate=rate, period=period)).font = Font(bold=st["block_title_bold"])
        r0 = r; r += 1
        if bi == 1:
            ws.cell(r, 2, s.provenance.curve_date)  # REV Rf_dc!B5 = 고시일
        for label, _src, fmt in rows:
            key = label
            if bi == 2 and label in ("{rate} - YTM", "SPOT RATE"): key = label + "#grid"
            if bi == 3 and label == "WEEKS": key = "WEEKS#boot"
            data = vals.get(key, [])
            ws.cell(r, 2, label.format(rate=rate, period=period))
            for j, v in enumerate(data):
                cell = ws.cell(r, first_col + j, v)
                cell.number_format = fmt
            max_col = max(max_col, first_col + max(len(data), 1) - 1)
            ranges[f"{c}:{label}"] = f"{st['first_data_col']}{r}:{_col(first_col + max(len(data), 1) - 1)}{r}"
            r += 1
        ranges[f"{c}:block{bi}"] = f"B{r0}:{_col(max_col)}{r - 1}"
        r += 1
    for j in range(first_col, max_col + 1):
        ws.column_dimensions[_col(j)].width = st["width_data"]
    return ranges


def _write_table(ws, header, rows):
    from openpyxl.styles import Font
    for j, h in enumerate(header, start=1):
        ws.cell(1, j, h).font = Font(bold=True)
    for i, row in enumerate(rows, start=2):
        for j, v in enumerate(row, start=1):
            ws.cell(i, j, v if not (isinstance(v, float) and not math.isfinite(v)) else str(v))
    return f"A1:{_col(max(len(header), 1))}{len(rows) + 1}"


def write_bundle(s, C, base_dir: str) -> dict:
    key = _key(s)
    d = os.path.join(base_dir, "evidence", key); os.makedirs(d, exist_ok=True)
    files, warnings, cell_map = [], [], {}
    def add(name): files.append({"path": name, "abs": os.path.join(d, name)})
    ef = {k: f"{k}_{n}.{e}" for k, (n, e) in C.EVIDENCE_FILES.items()}
    # 01 raw matrix
    _csv(os.path.join(d, ef["01"]), ["row_index", "kind", "group", "label"] + C.TENOR_LABELS,
         [[r["row_index"], r["kind_raw"], r["group_raw"], r["label_raw"]] + [r["ytm_pct"][t] for t in C.TENOR_LABELS] for r in s.input.rows]); add(ef["01"])
    # 02 rows used
    rows_used = []
    for c in C.CURVE_IDS:
        r = s.rows[c.lower()]
        if r: rows_used.append([c, r["row_index"], r["label_raw"], r.get("block"), r.get("block_requested"), r.get("rating"), r.get("notch"), f"nominal_m{C.RF_FREQ if c == 'RF' else C.RD_FREQ}"] + [r["ytm_pct"][t] for t in C.TENOR_LABELS])
    _csv(os.path.join(d, ef["02"]), ["curve", "row_index", "label", "block", "block_requested", "rating", "notch", "basis"] + C.TENOR_LABELS, rows_used); add(ef["02"])
    # 03 knots
    _csv(os.path.join(d, ef["03"]), ["curve", "tenor", "t", "ytm[nominal]"], [[c, k["tenor"], k["t"], k["ytm"]] for c in C.CURVE_IDS for k in s.grid.knots[c]]); add(ef["03"])
    # 04 bootstrap
    boot_rows = []
    for c in C.CURVE_IDS:
        m = C.RF_FREQ if c == "RF" else C.RD_FREQ
        for p in s.bootstrap.points[c]:
            boot_rows.append([c, p["n"], p["t"], p["c"], p["price_target"], p["spot_pp"], p["df"], p["denominator"], f"per_period_m{m}"])
    _csv(os.path.join(d, ef["04"]), ["curve", "n", "t", "c[per_period]", "price_target", "spot_pp[per_period]", "DF", "denominator", "basis"], boot_rows); add(ef["04"])
    # 05 spot table
    spot_rows = []
    for c in C.CURVE_IDS:
        for t, spp, z, r, df in zip(s.grid.boot_times[c], s.bootstrap.spot_pp[c]["values"], s.conv.spot_annual[c]["values"], s.conv.spot_cont[c]["values"], s.bootstrap.df[c]):
            spot_rows.append([c, t, spp, z, r, df])
    _csv(os.path.join(d, ef["05"]), ["curve", "t", "spot_pp[per_period]", "spot_annual[annual_eff]", "spot_cont[continuous]", "DF"], spot_rows); add(ef["05"])
    # 06 tree grid
    tg = []
    times = s.grid.tree.times
    for c in C.CURVE_IDS:
        za, zc, dfs = s.tree.spot_annual_on_grid[c]["values"], s.tree.spot_cont_on_grid[c]["values"], s.tree.df_spot_on_grid[c]
        f, F, Fa, ds, da, dc = (s.fwd.cont_on_grid[c]["values"], s.fwd.disc_per_step[c]["values"], s.fwd.disc_annual_eff[c]["values"], s.fwd.df_step[c], s.fwd.df_step_alt[c], s.fwd.df_cum[c])
        flags = {i: "left_flat" for i in s.tree.extrap_left_flat_steps[c]}; flags.update({i: "right" for i in s.tree.extrap_right_steps[c]})
        for i in range(1, len(times)):
            tg.append([c, i, times[i], s.grid.tree.dt[i - 1], za[i], zc[i], dfs[i], f[i - 1], F[i - 1], Fa[i - 1], ds[i - 1], da[i - 1], dc[i - 1], flags.get(i, "")])
    _csv(os.path.join(d, ef["06"]), ["curve", "step", "t", "dt", "D-SPOT[annual_eff]", "C-SPOT[continuous]", "DF", "C-FWD[continuous]", "F_step[per_step_simple]", "F_annual[annual_eff]", "DF_step", "DF_step_alt", "DF_cum", "extrap_flag"], tg); add(ef["06"])
    # 07 par residuals
    _csv(os.path.join(d, ef["07"]), C.XLSX_COLUMNS["PAR_CHECK"], [[r["curve"], r["t"], r["n"], r["price"], r["target"], r["residual"], r["residual_x_face"]] for c in C.CURVE_IDS for r in s.par_check.per_maturity[c]]); add(ef["07"])
    # 08 fwd-spot sample (md)
    smp = s.fwd_spot_check.sample or {}
    with open(os.path.join(d, ef["08"]), "w", encoding="utf-8", newline="\n") as fh:
        fh.write("# 감사인 Q11 — Π DF_fwd = DF_spot 예시 1건\n\n")
        fh.write(f"- 커브 {smp.get('curve')} / step {smp.get('step')} / t = {smp.get('t')}\n- Π df_step = {smp.get('prod_df_fwd')!r}\n- DF_spot(t) = {smp.get('df_spot')!r}\n")
        fh.write(f"- 차이(곱) = {smp.get('diff_prod')!r}, 차이(로그) = {smp.get('diff_log')!r}\n- 전 격자점 최대: 로그 {s.fwd_spot_check.max_abs_err_log!r}, 곱 {s.fwd_spot_check.max_abs_err_prod!r} (게이트 TOL_FWD_SPOT_FAIL)\n")
    add(ef["08"])
    # 09 flags
    flag_rows = [[f["severity"], f["code"], f.get("curve"), json.dumps(f.get("value"), ensure_ascii=False, default=str), f.get("threshold"), f.get("detail")]
                 for lst in (s.sanity.fail, s.sanity.approval_required, s.sanity.warn) for f in lst]
    _csv(os.path.join(d, ef["09"]), ["severity", "code", "curve", "value", "threshold", "detail"], flag_rows); add(ef["09"])
    # 10 headline
    _json(os.path.join(d, ef["10"]), dict(s.headline)); add(ef["10"])
    # 11 sensitivity
    _csv(os.path.join(d, ef["11"]), ["method", "space", "curve", "max_rel_df_diff", "note"], [[r["method"], r["space"], r["curve"], r["max_rel_df_diff"], r.get("note")] for r in s.sensitivity.table]); add(ef["11"])
    # 12 approvals
    _json(os.path.join(d, ef["12"]), {k: dict(s[f"approval_{k}"]) for k in ("input", "exception", "curve")}); add(ef["12"])
    # README_conventions.md
    stmt = "\n".join(f"- **{k}** = `{getattr(C, k)}` — {v}" for k, v in C.CONVENTION_REASONS.items() if hasattr(C, k)) + \
           f"\n- **EXTRAP** = EXTRAP_LEFT `{C.EXTRAP_LEFT}` / EXTRAP_RIGHT `{C.EXTRAP_RIGHT}` — {C.CONVENTION_REASONS['EXTRAP']}"
    mc = s.provenance.method_choice
    with open(os.path.join(d, "README_conventions.md"), "w", encoding="utf-8", newline="\n") as fh:
        fh.write(f"# 관례 선언문 — {key} (프로필 {s.run.profile})\n\n## 프로필(사용자 선택, PROFILE_SELECTION={C.PROFILE_SELECTION})\n- {mc.profile}: {C.PROFILE_DESCRIPTIONS.get(mc.profile, '')}\n- 선택자 {mc.chosen_by}, 시각 {mc.chosen_at}; 보간 {mc.interp_method} / 공간 {mc.interp_space_grid}\n\n")
        fh.write("## 관례(CONVENTION_REASONS)\n" + stmt + "\n\n")
        fh.write(f"## INTERP_METHOD\n- 방법 `{C.INTERP_METHOD}` / 트리 격자 공간 `{C.INTERP_SPACE_GRID}` / 이표격자 공간 `{C.INTERP_SPACE_PRE}`(선형) — 한공회 §3.7.3.6 공시 항목(KICPA_INTERP_DISCLOSURE)\n\n")
        fh.write(f"## NODE_DISCOUNT_CONV\n- `{C.NODE_DISCOUNT_CONV}` — {C.CONVENTION_REASONS['NODE_DISCOUNT_CONV']}\n\n## COUPON_CONV\n- `{C.COUPON_CONV}` — {C.CONVENTION_REASONS['COUPON_CONV']}\n\n")
        fh.write(f"## 상수 지문\n- constants_fingerprint `{s.run.constants_fingerprint}`\n\n## 상수 전부\n")
        for k, v in sorted(C.items().items()):
            fh.write(f"- {k} = `{json.dumps(v, ensure_ascii=False, default=str)[:300]}`\n")
    add("README_conventions.md")
    # xlsx (필수)
    xlsx_written, xlsx_path, ranges = False, None, {}
    try:
        from openpyxl import Workbook
        wb = Workbook(); wb.remove(wb.active)
        ws = {name: wb.create_sheet(name) for name in C.XLSX_SHEETS}
        rng = {}
        rng["INPUT_RAW"] = _write_table(ws["INPUT_RAW"], ["row_index", "kind", "group", "label"] + C.TENOR_LABELS, [[r["row_index"], r["kind_raw"], r["group_raw"], r["label_raw"]] + [r["ytm_pct"][t] for t in C.TENOR_LABELS] for r in s.input.rows])
        rng["ROWS_USED"] = _write_table(ws["ROWS_USED"], ["curve", "row_index", "label", "block", "block_requested", "rating", "notch", "basis"] + C.TENOR_LABELS, rows_used)
        prov = [(k, json.dumps(v, ensure_ascii=False, default=str) if isinstance(v, (dict, list)) else v) for k, v in json.loads(G.canonical_json(s.provenance)).items()]
        rng["PROVENANCE"] = _write_table(ws["PROVENANCE"], ["field", "value"], prov)
        rng["CONVENTIONS"] = _write_table(ws["CONVENTIONS"], ["constant", "value"], [(k, json.dumps(v, ensure_ascii=False, default=str)) for k, v in sorted(C.items().items())])
        for c, name in (("RF", "Rf_dc"), ("RD", "Rd_dc")):
            ranges.update(_write_dc_sheet(ws[name], s, C, c))
        rng["PAR_CHECK"] = _write_table(ws["PAR_CHECK"], C.XLSX_COLUMNS["PAR_CHECK"], [[r["curve"], r["t"], r["n"], r["price"], r["target"], r["residual"], r["residual_x_face"]] for c in C.CURVE_IDS for r in s.par_check.per_maturity[c]])
        fs_rows = [[c, r["step"], r["t"], r["prod_df_fwd"], r["df_spot"], r["diff_log"], r["diff_prod"]] for c in C.CURVE_IDS for r in (s.fwd_spot_check.rows.get(c, []) if isinstance(s.fwd_spot_check.rows, dict) else [])]
        rng["FWD_SPOT_CHECK"] = _write_table(ws["FWD_SPOT_CHECK"], C.XLSX_COLUMNS["FWD_SPOT_CHECK"], fs_rows)
        rng["SENSITIVITY"] = _write_table(ws["SENSITIVITY"], ["method", "space", "curve", "max_rel_df_diff", "note"], [[r["method"], r["space"], r["curve"], r["max_rel_df_diff"], r.get("note")] for r in s.sensitivity.table] + [["freq_alt", "", c, json.dumps(v, ensure_ascii=False), ""] for c, v in dict(s.sensitivity.freq_alt).items()])
        hl = json.loads(G.canonical_json(s.headline))
        rng["HEADLINE"] = _write_table(ws["HEADLINE"], ["field", "value"], [(k, json.dumps(v, ensure_ascii=False) if isinstance(v, (dict, list)) else v) for k, v in hl.items()])
        rng["FLAGS"] = _write_table(ws["FLAGS"], ["severity", "code", "curve", "value", "threshold", "detail"], flag_rows)
        ap_rows = [[k, a.requested_at, a.snapshot_sha256, json.dumps([f["code"] for f in a.flags_seen], ensure_ascii=False), a.decision, a.approver, a.timestamp, a.comment, json.dumps(a.acknowledged_codes, ensure_ascii=False)]
                   for k, a in (("input", s.approval_input), ("exception", s.approval_exception), ("curve", s.approval_curve))]
        rng["APPROVALS"] = _write_table(ws["APPROVALS"], C.XLSX_COLUMNS["APPROVALS"], ap_rows)
        rng["RUN_PATH"] = _write_table(ws["RUN_PATH"], C.XLSX_COLUMNS["RUN_PATH"], [[i + 1] + list(p) for i, p in enumerate(s.run.path)])
        xlsx_path = os.path.join(d, XLSX_NAME); wb.save(xlsx_path); xlsx_written = True; add(XLSX_NAME)
    except ImportError:
        warnings.append("XLSX_SKIPPED: openpyxl 없음")
        rng = {}
    X = XLSX_NAME
    n06 = len(tg) + 1
    cell_map = {
        "Q1": f"{X}!Rf_dc!{ranges.get('RF:block3', 'B1')}", "Q8": "README_conventions.md!-!NODE_DISCOUNT_CONV",
        "Q9_FWD_INPUT": f"{ef['06']}!-!A1:N{n06}", "Q10_1": f"{ef['05']}!-!A1:F{len(spot_rows) + 1}", "Q10_2": "README_conventions.md!-!COUPON_CONV",
        "Q11": f"{ef['08']}!-!sample", "Q12": f"{X}!PROVENANCE!{rng.get('PROVENANCE', 'A1')}", "Q13": f"{ef['02']}!-!A1:X{len(rows_used) + 1}",
        "C33": f"{X}!Rf_dc!{ranges.get('RF:block4', 'B1')}", "C34": f"{ef['06']}!-!DF_step", "C35": f"{X}!Rf_dc!{ranges.get('RF:block3', 'B1')}",
        "C36": f"{X}!PAR_CHECK!{rng.get('PAR_CHECK', 'A1')}", "C37": "README_conventions.md!-!INTERP_METHOD", "C38": f"{X}!Rd_dc!{ranges.get('RD:block3', 'B1')}",
        "C39": f"{X}!Rd_dc!{ranges.get('RD:block1', 'B1')}", "C40": f"{X}!Rd_dc!{ranges.get('RD:block2', 'B1')}", "C41": f"{ef['06']}!-!A1:N{n06}",
        "C43": f"{ef['05']}!-!A1:F{len(spot_rows) + 1}", "C44": f"{ef['10']}!-!rf_ytm_remaining", "C48": f"{ef['05']}!-!spot_annual[annual_eff]",
        "HEADLINE_RF": f"{ef['10']}!-!rf_ytm_remaining", "HEADLINE_RD": f"{ef['10']}!-!rd_ytm_remaining", "HEADLINE_RATING": f"{ef['10']}!-!rating_applied",
        "HEADLINE_BLOCK": f"{ef['10']}!-!block_applied", "KICPA_INTERP_DISCLOSURE": "README_conventions.md!-!INTERP_METHOD",
        "RUN_PATH": f"{X}!RUN_PATH!{rng.get('RUN_PATH', 'A1')}", "APPROVALS": f"{ef['12']}!-!$",
    }
    _json(os.path.join(d, "checklist_map.json"), cell_map); add("checklist_map.json")
    return {"dir": os.path.relpath(d, base_dir).replace("\\", "/"), "files": files, "cell_map": cell_map, "conventions_statement": stmt,
            "xlsx_written": xlsx_written, "xlsx_path": (os.path.relpath(xlsx_path, base_dir).replace("\\", "/") if xlsx_path else None), "warnings": warnings}
