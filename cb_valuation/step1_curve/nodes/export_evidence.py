# -*- coding: utf-8 -*-
"""export.*: io/evidence_writer 가 번들(CSV/JSON/MD + xlsx)을 쓰고 위치표(cell_map)를 돌려준다. 체크리스트 검사는 step1_graph 의 규칙 함수를 그대로 쓴다.
번들 루트 = state.run.base_dir(러너가 기록; 없으면 현재 폴더) 아래 evidence/<key>/. 환경변수는 읽지 않는다."""
import os
from ..graph import step1_graph as G
from ..io.evidence_writer import write_bundle


def node_export_evidence(s, C):
    base = s.run.base_dir or os.getcwd()
    try:
        r = write_bundle(s, C, base)
        s.export.update(dir=r["dir"], files=r["files"], cell_map=r["cell_map"], conventions_statement=r["conventions_statement"],
                        xlsx_written=r["xlsx_written"], xlsx_path=r["xlsx_path"], warnings=r["warnings"])
    except Exception as e:  # 쓰기 실패는 사실로 기록 → 엣지 '쓰기오류'
        s.export.errors.append(f"{type(e).__name__}: {e}")
    G.node_export_evidence(s, C)
