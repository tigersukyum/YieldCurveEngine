# -*- coding: utf-8 -*-
"""
export_spec.py — step1_graph.py(단일 진실 원천)와 graph_check.SCENARIOS 에서 docs/GRAPH_SPEC.md 를 생성한다.
노드 표·엣지 표(실행 순서·조건 소스·코드)·mermaid·두 갈래 시나리오·증빙 규격·상수 표는 코드에서 추출하고,
심각도·승인·AI 정책은 아래 POLICY 텍스트다(코드와 함께 유지).
실행: python cb_valuation/step1_curve/graph/export_spec.py
"""
from __future__ import annotations
import inspect, json, os, re, sys

try:
    from . import step1_graph as G
    from . import graph_check as GC
except ImportError:
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    import step1_graph as G
    import graph_check as GC
C = G.Constants
HERE = os.path.dirname(os.path.abspath(__file__))

POLICY = """
## 5. 심각도 표 (판정 위치 = 전용 엣지 또는 sanity_check 한 곳)

라우터 규칙: (1) 단일 노드로 판정되는 FAIL 은 그 노드의 전용 엣지가 처리하고(§2 표의 코드 열) sanity_check 는 재평가하지 않는다. (2) 다중 노드 교차 규칙(INTERP_MISMATCH)만 `sanity.fail` → `FAIL플래그존재`. (3) APPROVAL_REQUIRED 코드는 sanity_check 만 집계 → approve_exception 정지, 코드별 `--ack` 필수. (4) WARN 은 기록·증빙 인쇄만. (5) 같은 사건이 FAIL·APPROVAL 양쪽이면 FAIL 우선(엣지 순서). (6) 임계 게이트(GATE_NODES)는 [비유한→fail] [초과→fail] [기본→다음]. (7) 임계값은 `Constants` 에만 있고 문서는 상수명만 인용(§11).

| 심각도 | 코드 | 담당 | 비고 |
|---|---|---|---|
| FAIL | §2 표 '코드' 열 전부 | 각 노드 전용 엣지 | `result.fail_code` 에 기록 |
| FAIL | INTERP_MISMATCH (트리 매핑에 쓴 보간 방법/공간 ≠ interp.*) | sanity_check | 다중 노드 교차 규칙 |
| APPROVAL_REQUIRED | DATE_LAG (0<lag≤CURVE_DATE_MAX_LAG_DAYS), CAPTURE_MISSING (PROVENANCE_APPROVAL_FIELDS), NEG_FWD, RD_LT_RF (<RD_MIN_SPREAD), EXTRAP_COUPON_GRID, EXTRAP_LEFT_ORIGIN, EXTRAP_RIGHT_USED, EXTRAP_LEFT_FLAT(EXTRAP_LEFT_FLAT_SEVERITY 가 APPROVAL_REQUIRED 일 때), ROW_FALLBACK, NOTCH_APPLIED, RATING_CHANGED, BLOCK_CHANGED, KNOT_MISSING, HEADLINE_MISMATCH, EXCEL_REPLICATE_ON | sanity_check → approve_exception | DATE_LAG·CAPTURE_MISSING 은 `input_stage_flags()` 로 approve_input.flags_seen 에도 표시 |
| WARN | EXTRAP_LEFT_FLAT(기본), SAWTOOTH (>FWD_JUMP_WARN_BP), PAR_WARN (TOL_PAR_WARN<잔차≤TOL_PAR_FAIL), CROSS_METHOD_DF (>CROSS_METHOD_DF_WARN), FREQ_SENSITIVITY, ZERO_VALUE_CELL, LLM_PARSER_USED, UNPARSED_ROWS, TENOR_DROPPED, UNUSED_KNOT_RESIDUAL, NONMONO_YTM/NONMONO_SPOT(역전 커브 정상; 엔진 이식 후) | sanity_check(기록만) | |
| FAIL | XLSX_MISSING (XLSX_REQUIRED=True 인데 xlsx 미생성) | export_evidence 엣지 `xlsx누락` | 사용자 결정 2026-09-07: xlsx 필수, openpyxl 은 선언 의존성 |
| WARN | XLSX_SKIPPED (XLSX_REQUIRED=False 로 바꾼 경우에만) | export_evidence → `export.warnings` | sanity_check 이후 발생하므로 export 소속 |

## 6. 사람승인 정책 (엣지에 명시된 정지 3곳)

- **프로필 선택(PROFILE_SELECTION=required, 사용자 결정 2026-09-07)**: 보간법·프로필은 실행 시 사용자가 고른다(CLI `--profile` 필수, 화면 선택 목록 = `PROFILES` 키 + `PROFILE_DESCRIPTIONS`). 선택은 `provenance.method_choice{profile, interp_method, interp_space_grid, chosen_by, chosen_at}` 에 기록되고 PROVENANCE_REQUIRED_FIELDS 에 포함되어 미선택이면 `출처불완전`, 실행 상수의 PROFILE_NAME 과 다르면 `프로필불일치` 로 fail 한다. 조용한 기본값은 없다.
- **approve_input (필수, 계산 전)**: 원시 매트릭스 원문·헤더·provenance(평가사·curve_date·valuation_date·lag·파일 해시·다운로드 시각·담당자·행 캡처·등급 캡처·**method_choice**)·라벨 해석·상품/등급/발행형태를 보고 승인. `flags_seen` = `input_stage_flags()` 결과(DATE_LAG·CAPTURE_MISSING·ZERO_VALUE_CELL·LLM_PARSER_USED·UNPARSED_ROWS) — 판정 규칙은 sanity_check 와 같은 함수 한 곳.
- **approve_exception (조건부)**: `sanity.approval_required` 가 비어있지 않을 때만 도달. `--ack CODE` 로 코드마다 확인해야 하며 하나라도 빠지면 `미확인코드잔존` 이 wait_for_human 으로 되돌린다. ack 단위는 코드(커브 무관).
- **approve_curve (필수, 내보내기 전)**: 05/06/07 표·par 잔차·Q11 예시·헤드라인·관례 요약·전체 flag(APPROVAL+WARN, `flags_seen` 에 기록)를 보고 승인.
- 엣지 순서(`Constants.HUMAN_EDGE_ORDER`, graph_check 가 완전 일치 검사): `[거절→fail] [결정선행→fail] [상수변경감지→fail] [변조감지→fail] [(exception만) 미확인코드잔존→wait_for_human] [승인→다음] [대기(ALWAYS)→wait_for_human]`. decision 이 None 이든 예상 밖 값이든 라우터는 반드시 wait_for_human 으로 간다.
- 정지: 승인 노드 함수는 requested_at·snapshot_sha256(=hash_of(SNAPSHOT_SCOPE[node]))·flags_seen 을 처음 한 번만 쓴다(멱등). wait_for_human 이 `run.status='paused'`, `paused_at_node`, `paused_at` 을 쓰고 스냅샷(`state/<valuation_date>__<curve_set_id>/snapshot__<node>__<n>.json`)을 저장한 뒤 exit code 3.
- 결정: `set_decision()` 만 approval_<kind> 의 decision·approver·timestamp·comment·acknowledged_codes 를 쓰고 `history` 에 append 한다. 조건: 승인 요청 이후(requested_at 존재), `run.status=='paused'` 이고 `run.paused_at_node==approve_<kind>`, approver 비어있지 않음, ack ⊆ flags_seen 코드. 위반은 ValueError. 요청 시각보다 앞선 결정이 스냅샷에 들어 있으면 엣지 `결정선행` 이 fail 로 보낸다.
- 재개: `cli resume --snapshot <path> --decision approved|rejected --approver <이름> --comment "<문장>" [--ack CODE ...]` → `C = Constants.with_profile(state.run.profile)` 복원 → `set_decision()` → `run(state, C, start=run.paused_at_node)`. `start` 는 승인 노드이며 `paused_at_node` 와 같아야 하고(아니면 ValueError), 계산 노드는 재실행되지 않으며 CALC_PREFIXES 필드는 바이트 동일해야 한다(graph_check 재개 검사). 재개마다 `run.resume_n` 증가, `run.path` 항목에 시각·회차 기록.
- 변조 감지: `Constants.fingerprint()`(결정적 직렬화, 프로세스 무관) ≠ `run.constants_fingerprint` → `상수변경감지`; `hash_of(SNAPSHOT_SCOPE)` ≠ `snapshot_sha256` → `입력변조감지`/`계산상태변조감지`. SNAPSHOT_SCOPE 는 approve_exception 에 approval_input 을, approve_curve 에 approval_input·approval_exception 을 포함해 이전 승인 기록의 편집도 잡는다.
- 거절: 어느 승인이든 → fail. `result.fail_reason='<node>:거절'`, `result.fail_detail={node, edge, code, approver, comment, timestamp}`, 부분 번들 저장. 재시도는 새 run_id 로 처음부터.
- 기록: 승인자·ISO 시각·코멘트·flags_seen·acknowledged_codes·snapshot_sha256·history → state, 12_approvals.json, APPROVALS 시트, approved_state.json. 스냅샷·승인 state 는 커밋 제외(.gitignore)이되 삭제 금지. 승인은 CLI `resume` 로만 이루어진다(viewer.html 은 명령 문자열 생성만). AI 는 approval_* 접근이 없다.
- 드라이런(`/curve-validate`): 하네스가 approver='dry-run' 으로 입력 승인만 자동 기록하고 approve_exception/approve_curve 정지에서 보고 후 종료한다. approved_state.json 을 쓰지 않는다.

## 7. AI 의 역할 (해석까지)

허용: (a) `interpret_labels` 노드에서 LABEL_GRAMMAR 정규식 미매칭 행의 **라벨 문자열만** LLM 에 정규화 제안 요청(AI_ENABLED=True + API 키가 있을 때만; 페이로드에 숫자가 있으면 assert). 제안은 정규식 재검증을 통과해야 parser='llm' 으로 채택되고 LLM_PARSER_USED WARN 이 남는다. (b) 증빙·화면의 한국어 설명문(state 값을 문자열로 삽입, 숫자 생성 금지).
금지: YTM 값 읽기·요약, spot/DF/forward 계산, par 통과·심각도·헤드라인 판정, 커브 채택, 승인 필드 쓰기. 기본 경로는 정규식이며 API 키 없이 fixture A~E 전부 완주해야 한다. 고객 금리표·식별정보는 외부 LLM 으로 보내지 않는다.

## 8. 화면 (그래프·state 다음에 붙인다)

`app/viewer.html`(외부 라이브러리 없음)은 state JSON 과 `graph/edges_export.json` 만 읽는다. 왼쪽: 매트릭스·선택 행·BOOT/BM 열 순서의 결과표(basis 헤더)·par 잔차·Q11 예시·flag. 오른쪽: EDGES 그래프에서 현재 노드·지나온 엣지(run.path) 강조 + state JSON. 화면에 흐름 로직 없음(승인 버튼은 resume 명령 문자열 생성만). 지나온 경로(run.path: from, 조건, to, 시각, 재개 회차)가 그대로 감사조서다.

## 9. 2단계 인터페이스

`result.next_step_interface`(경로 참조): tree.spot_cont_on_grid.{RF,RD}, fwd.cont_on_grid.{RF,RD}, fwd.df_step.{RF,RD}, grid.tree.event_times, spot_lookup{method→interp.method, space→interp.space_grid, basis}, node_discount_conv→fwd.node_discount_conv, profile. 소비 측(트리/BDT/혼합이자율)은 basis 라벨과 할인 규약을 검사한다. 2단계 증빙 예약 항목: `Constants.STEP2_EVIDENCE_ITEMS`.
"""


def cond_src(fn):
    if fn is G.ALWAYS:
        return "ALWAYS"
    src = inspect.getsource(fn)
    if "lambda s, C:" in src:
        body = src.split("lambda s, C:", 1)[1].rsplit(",", 2)[0]
    else:
        body = src.strip()
    return re.sub(r"\s{2,}", " ", body.strip().rstrip(","))


def constants_table():
    """step1_graph.py 소스에서 '이름 = 값  # 출처' 를 뽑아 표로."""
    rows = []
    src = open(os.path.join(HERE, "step1_graph.py"), encoding="utf-8").read().split("\n")
    for line in src:
        m = re.match(r"^    ([A-Z][A-Z0-9_]+) = (.+?)(?:\s+# (.*))?$", line)
        if m:
            name, val, note = m.group(1), m.group(2).strip(), (m.group(3) or "").strip()
            for part in re.split(r";\s+", val):  # 한 줄에 여러 상수
                mm = re.match(r"^([A-Z][A-Z0-9_]+) = (.+)$", part)
                if mm and mm.group(1) != name:
                    rows.append((mm.group(1), mm.group(2), note))
                elif part.startswith(name) is False and not mm:
                    pass
            rows.append((name, re.split(r";\s+", val)[0], note))
    seen, out = set(), []
    for n, v, note in rows:
        if n in seen: continue
        seen.add(n); out.append((n, v.replace("|", "\\|")[:90], note.replace("|", "\\|")))
    return out


def main():
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:  # noqa: BLE001
        pass
    L = ["# GRAPH_SPEC — 1단계 이자율 커브 그래프 (자동 생성: graph/export_spec.py ← graph/step1_graph.py + graph_check.SCENARIOS)", "",
         f"노드 {len(G.NODES)}개 · 엣지 {len(G.EDGES)}개 · 승인 노드 {len(C.HUMAN_NODES)}개 · 종단 {len(C.TERMINAL_NODES)}개 · 게이트 {len(G.GATE_NODES)}개 · 시나리오 {len(GC.SCENARIOS)}개 · 상수 fingerprint `{C.fingerprint()[:12]}…` · spec `{GC.spec_digest()[:12]}…`(스키마 {C.STATE_SCHEMA_VERSION}; graph_check 가 spec 다이제스트로 이 문서의 신선도를 검사)",
         "", "흐름의 유일한 정의는 `graph/step1_graph.py` 의 `EDGES` 배열이다. 이 문서는 그 배열을 사람이 읽기 좋게 펼친 것이며, 불일치가 있으면 코드가 우선한다(`python cb_valuation/step1_curve/graph/export_spec.py` 로 재생성). `python cb_valuation/step1_curve/graph/graph_check.py` 가 불변식·두 갈래 시나리오·노드 쓰기 추적·상수 지문 결정성을 검사한다.",
         "", "## 1. 노드 (id · 한국어 이름 · 쓰는 접두사 · 알고리즘 요약)", "", "| # | id | 이름 | 쓰는 state 접두사 | 알고리즘 요약(출처: FORMULA_REFERENCE.md) |", "|---|---|---|---|---|"]
    for i, (nid, (ko, prefixes, fn)) in enumerate(G.NODES.items()):
        doc = (fn.__doc__ or "").strip().replace("|", "\\|").replace("\n", " ")
        L.append(f"| {i} | `{nid}` | {ko} | `{', '.join(prefixes)}` | {doc} |")
    L += ["", "## 2. EDGES (실행 순서 — 라우터는 위→아래 첫 일치; 코드 열 = result.fail_code)", "", "| # | 현재 노드 | 조건 이름 | 조건 함수 (s=state, C=Constants) | 다음 노드 | 코드 |", "|---|---|---|---|---|---|"]
    for i, (f, n, cond, t) in enumerate(G.EDGES):
        L.append(f"| {i} | `{f}` | {n} | `{cond_src(cond).replace('|', '\\|')}` | `{t}` | {G.EDGE_CODES.get((f, n), '')} |")
    L += ["", "## 3. 다이어그램 (mermaid; 승인 노드=스타디움, 종단=이중 사각형)", "", "```mermaid", G.to_mermaid(), "```", "",
          "## 4. 두 갈래 시나리오 (graph_check.SCENARIOS — 문서·프롬프트·fixture E 는 이 표의 id 만 인용)", "",
          "| id | 설명 | 프로필 | 기대 마지막 엣지 | 기대 status |", "|---|---|---|---|---|"]
    for sid, desc, Cc, *_ , edge, status in GC.SCENARIOS:
        L.append(f"| {sid} | {desc.replace('|', '\\|')} | {getattr(Cc, 'PROFILE_NAME', 'DEFAULT')}{'(EXTRAP_LEFT_FLAT=APPROVAL)' if Cc is GC.CAP else ''} | {edge} | {status} |")
    L += [POLICY.rstrip(), "", "## 10. 증빙 번들 규격 (Constants.EVIDENCE_FILES / XLSX_SHEETS / XLSX_COLUMNS / EVIDENCE_REQUIRED_ITEMS)", "",
          "| 번호 | 파일 | 형식 |", "|---|---|---|"]
    for k, (name, ext) in C.EVIDENCE_FILES.items():
        L.append(f"| {k} | {k}_{name}.{ext} | {ext} |")
    L += ["", f"xlsx: XLSX_REQUIRED={C.XLSX_REQUIRED}(미생성 → 엣지 `xlsx누락`), 템플릿 `{C.XLSX_TEMPLATE}`(docs/XLSX_TEMPLATE.md), 시트 순서: " + ", ".join(C.XLSX_SHEETS),
          "", "| 열 지향 시트 | 열(basis 라벨 포함) |", "|---|---|"]
    for sh, cols in C.XLSX_COLUMNS.items():
        L.append(f"| {sh} | {', '.join(cols)} |")
    L += ["", "Rf_dc / Rd_dc (행 지향, XLSX_DC_BLOCKS; 서식 XLSX_DC_STYLE = " + json.dumps(C.XLSX_DC_STYLE, ensure_ascii=False) + ")", "",
          "| 블록 | 행 라벨 | 원천 접두사 | 숫자 서식 |", "|---|---|---|---|"]
    for title, rows in C.XLSX_DC_BLOCKS:
        for label, src, fmt in rows:
            L.append(f"| {title} | {label} | {src} | `{fmt}` |")
    L += ["", "프로필 선택 목록(PROFILE_DESCRIPTIONS; PROFILE_SELECTION=" + C.PROFILE_SELECTION + ")", "", "| 프로필 | 설명 |", "|---|---|"]
    for k, v in C.PROFILE_DESCRIPTIONS.items():
        L.append(f"| {k} | {v} |")
    L += ["", "필수 증빙 항목(전항목이 `export.cell_map` 에 `<file>!<sheet|->!<range|json_path>` 로 있어야 done 도달): " + ", ".join(C.EVIDENCE_REQUIRED_ITEMS),
          "", "2단계 예약(1단계 checklist 제외): " + ", ".join(C.STEP2_EVIDENCE_ITEMS), "",
          "## 11. 상수 표 (Constants — 값·출처는 코드 주석에서 추출; 문서 인용은 상수명으로)", "", "| 상수 | 값 | 출처/비고 |", "|---|---|---|"]
    for n, v, note in constants_table():
        L.append(f"| `{n}` | `{v}` | {note} |")
    out = os.path.join(os.path.dirname(HERE), "docs", "GRAPH_SPEC.md")
    with open(out, "w", encoding="utf-8") as fh:
        fh.write("\n".join(L) + "\n")
    print("written", out, f"({len(L)} lines)")


if __name__ == "__main__":
    main()
