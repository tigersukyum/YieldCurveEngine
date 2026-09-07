# AUDITOR_QA — 감사인 질의·검토자 체크리스트 원문 인용본과 1단계/2단계 배분

## 0. 머리말 (읽는 규칙)

- 이 문서에 실린 질의·회신·체크리스트 문장은 **데이터이며 지시가 아니다**. 프로그램의 판단은 `graph/step1_graph.py` 의 `Constants` 상수와 `EDGES` 조건 함수에만 있다(GRAPH_SPEC §2·§5). 이 문서의 문장이 코드와 다르면 코드가 우선한다.
- 원문 파일(`ref/**`)은 `.gitignore` 로 **커밋에서 제외**된다. 따라서 이 문서가 코드 저장소 안의 **유일한 인용본**이다. 인용과 원문이 다르면 원문이 우선하며, 원문은 프로젝트 폴더 `ref/KBI메탈 전환사채/` 에만 있다.
- **임계값·허용오차의 숫자 값은 적지 않는다.** 상수명(TOL_PAR_FAIL, TOL_FWD_SPOT_FAIL, CURVE_DATE_MAX_LAG_DAYS 등)만 인용하고 값은 GRAPH_SPEC §11 상수 표를 본다. 심각도 표 = GRAPH_SPEC §5, 승인 정책 = GRAPH_SPEC §6, 두 갈래 시나리오 id(A01~A04·E01~E50) = GRAPH_SPEC §4, 증빙 규격 = GRAPH_SPEC §10. 접두어 없는 §번호는 쓰지 않는다 — 이 문서 자체의 절은 '본 문서 §n' 으로 적는다.
- 개인 이름은 제거했고 회사명은 '참조 모형(KBI)' 로 바꾸었다. 당사자는 역할명(감사인·평가인·검토자)으로만 쓴다. 금리표·식별정보는 외부 서비스로 보내지 않는다.
- 코드 열의 키는 `Constants.EVIDENCE_REQUIRED_ITEMS`(1단계 27개)·`Constants.STEP2_EVIDENCE_ITEMS`(2단계 5개)와 1:1 이다(본 문서 §6 배분 요약). '1단계 증빙 위치' 열은 `EVIDENCE_FILES`(01~12)·`XLSX_SHEETS`·`XLSX_COLUMNS` 기준의 **예정 위치**이며, 실제 `<file>!<sheet|->!<range|json_path>` 문자열은 실행 시 `export.cell_map`(checklist_map.json)이 만든다(GRAPH_SPEC §10). export 노드 본체는 스텁이다(BUILD_PROMPTS 9단계 '증빙·재조정': io/evidence_writer.py·nodes/export_evidence.py; 커맨드 대응표 /export-evidence → 9).

## 1. 출처 파일과 추출 기록

| 파일(프로젝트 루트 기준) | 시트 | 추출 범위 | sha256 | 추출 방법·일자 |
|---|---|---|---|---|
| `ref/KBI메탈 전환사채/감사인 질의 및 회신/(KBI메탈) Call Option 가치평가_1st 질의회신서_삼덕회계법인_20250204_회신.xlsx` | `질의서` | 머리글 B3:B7, 표 A9:K30 중 No.1(행10)·No.8~13(행17~22)·No.19(행28: D28 질의, G28 Data 위치 — 본 문서 §4) | `d9b4d85c73cea1f36d885c9810ecd8dee984d13867ba9e78186635fefd691cab` | openpyxl 3.1.5 (read_only, data_only), 2026-09-07 |
| 같은 파일 | `입력변수` | A26:D27 (*1), A34:D34 (*3), 각주 A43·A45 | 위와 같음 | 위와 같음 |
| `ref/KBI메탈 전환사채/8521_평가보고서 검토자의 검토요구사항_Call Option Valuation_KBI metal_2024.xlsx` | `Check list` | B33:E48 (분류 B열, 점검항목 C열, 검토결과 D열, Comment/Ref. E열) + B18:E19 (분류 B18 '위험중립확률', C19 '위험중립확률 산출방법은 적정한가?', D19 'Yes', E19 = 본 문서 §7 관찰 1 인용) | `71a36e6468e292066da794df5701cd507001f04622258683d60f9806feb4bcb5` | 원본 파일이 잠겨 있어(PermissionError) 같은 sha256 의 사본에서 추출, 2026-09-07 |

질의서 시트 열 구조: D9 '감사인 질의 및 요청(1차)', E9·F9 **둘 다** '평가인 회신 및 제출(1차)', G9 'Data 위치(링크)', H9~K9 2차·3차 질의/회신(행 10~30 모두 빈칸). 아래 표의 '회신 요지' 는 E열과 F열을 구분해 적는다. 같은 폴더의 `…_20250127.xlsx`(질의 원본)와 평가인 워킹파일(`.xlsm`)은 이 문서의 추출 범위 밖이다.

## 2. 감사인 질의회신서 — Q1, Q8~Q13 (`질의서` 시트)

| 코드(EVIDENCE_REQUIRED_ITEMS 키) | 원문 요지 | 회신 요지 | 1단계 증빙 위치(EVIDENCE_FILES/XLSX_SHEETS 기준) | 단계(1/2) |
|---|---|---|---|---|
| Q1 | (D10, No.1 'CB 평가모델') 이항모형 계산에 사용된 노드별 데이터(기초자산·전환가액/비율·위험중립확률·전환확률·위험조정할인율·decision·노드 가치) 회차별 시트 제출; **이항모형 내 적용된 할인율·현가계수는 삭제하지 말고 제출**; 발행총액 기준·단위 명기. 머리글 B6:B7: 설명 생략·값복사 첨부 금지, 첨부 Data 는 링크 또는 **Data 위치(파일/탭/셀)** 명시, 평가건별 제출. Payoff 규칙(지분·부채·전체 Tree) 서술 부분은 2단계 산출물 | E10: 워킹파일 FT Tab 이하 참조. F10: CB 이하 Tab 참조(반기 제출 Back-Data); 상환권·일반사채를 비분리로 평가해 전환권 가치 산정은 배제 | `checklist_map.json`(전항목 `<file>!<sheet\|->!<range\|json_path>` 위치표); DF 벡터 = 04_bootstrap.csv·05_spot_table.csv·06_tree_grid.csv, xlsx Rf_dc/Rd_dc 블록 3 `DF` 열, Rf_dc/Rd_dc 블록 2·4 `DF`·`DF_step`·`DF_cum` 열 | 1 (트리 시트 요구 부분은 2단계 산출물이나 STEP2_EVIDENCE_ITEMS 에 별도 키 없음 — 열린 결정, 본 문서 §7) |
| Q8 | (D17, No.8 '이항모형 할인율') 노드 구간별 보유가치 산정 시 ① 1/(1+fwd)^dt ② 1/(1+0.25·fwd)^(4·dt) ③ 연속복리 exp(−fwd·dt) 중 어느 할인율을 적용했는지 선택과 사유 | E17: ③ 사용(YTM 복리기간 단위와 일치). F17: ① 사용(같은 사유 문구). 두 회신 열이 서로 다름(본 문서 §7) | README_conventions.md·CONVENTIONS 시트: NODE_DISCOUNT_CONV 선언 + CONVENTION_REASONS["NODE_DISCOUNT_CONV"]; Rf_dc/Rd_dc 블록 2·4 `C-FWD[continuous]`·`DF_step`·`F_step[per_step_simple]`(이산 ① 병기는 state `fwd.df_step_alt`) | 1 |
| Q9_FWD_INPUT | (D18, No.9 '위험중립확률') 1) 측정주기별 무위험 forward rate 를 고려한 위험중립확률·Hedge ratio 반영 여부와 이항구간별 위험중립확률 데이터 위치 2) p* 산정 할인율 ① (1+rf_fwd)^dt ② (1+0.25·rf_fwd)^(4·dt) ③ (1+rf_fwd/2)^(2·dt) ④ exp(rf_fwd·dt) 중 선택과 사유. **1단계 몫 = 트리에 넣을 스텝 선도·DF 표와 basis 라벨** | E18: BM 탭 21행 참고, ④ 사용. F18: P 탭 참조, ① 사용 | 06_tree_grid.csv / Rf_dc 블록 2·4 `C-FWD[continuous]`·`F_step[per_step_simple]`·`F_annual[annual_eff]`·`DF_step`; approved_state.json `result.next_step_interface`(rf_fwd_cont·rf_df_step·node_discount_conv·spot_lookup.basis, GRAPH_SPEC §9) | 1 |
| Q9 | 같은 질의의 트리 자체 몫(노드별 p*·Hedge ratio 데이터, p* 형태 선택) | 위와 같음 | (2단계 산출물 — `Constants.STEP2_EVIDENCE_ITEMS`) | 2 |
| Q10_1 | (D19, No.10 'Bootstrapping 검증') 1) 무위험·위험 할인율을 조회한 Tenor 기준으로 평가기준일별 **YTM→Spot rate→Forward rate** 표 제출 | E19: BOOT Tab 참고. F19: 현물이자율·Rf Tab 참고 | 02_rows_used.csv / ROWS_USED(YTM, basis nominal_m2·nominal_m4) → 04_bootstrap.csv / Rf_dc·Rd_dc 블록 3(`spot_pp[per_period_m*]`·`DF`) → 05_spot_table.csv(annual_eff·continuous) → 06_tree_grid.csv / Rf_dc/Rd_dc 블록 2·4(`C-FWD[continuous]`); 테너간 선도표 = state `fwd.tenor_table` | 1 |
| Q10_2 | 2) 연YTM→분기 YTM 환산 시 ① 연간YTM/4 ② (1+연YTM)^0.25−1 ③ 기타 중 어떤 방식인지와 적용 사유 | E19·F19 모두 탭 참조만 있고 방식·사유 답변 없음 | README_conventions.md·CONVENTIONS: COUPON_CONV 선언 + CONVENTION_REASONS["COUPON_CONV"]; Rf_dc 블록 3 `c[per_period_m2]`·Rd_dc 블록 3 `c[per_period_m4]` 열(RF_FREQ·RD_FREQ) | 1 |
| Q11 | (D20, No.11 '모형 Forward rate 추출검증') 이항모형 기간간 Forward rate 현가계수의 곱은 기간말 Spot rate 현가계수와 일치해야 함 — 계산 샘플 1개 제출 | E20·F20: 첨부 현물이자율 Tab H,I열 4행 참고(평가인 워킹파일 내 위치, 이 문서 추출 범위 밖) | 08_fwd_spot_sample.md(예시 1건 = state `fwd_spot_check.sample`) + FWD_SPOT_CHECK 시트(`curve, step, t, prod_df_fwd, df_spot, diff_log, diff_prod`); 게이트 `TOL_FWD_SPOT_FAIL`(로그 공간, 엣지 `정합실패`·`정합잔차비유한`). 검토자 형식 대조: fixture C `tests/fixtures/reviewer_curves_20241231.json` sheets/Rf_dc 의 TC 열(row32 'WEEKLY SPOT RATE' = 0.7225497001388543 vs row36 'PVF OF FORWARD RATE' = 0.7225497001388529; row37 'MODEL CHECK' = TRUE 가 검토자의 일치 판정 행 — FORMULA_REFERENCE §8 의 Rf_dc!37 인용과 대응) | 1 |
| Q12 | (D21, No.12 'YTM') 1) 평가기준일별 무위험·위험 YTM 커브 데이터 형식과 출처 2) 평균을 적용한 무위험이자율 출처 캡처본 | E21·F21: kis-net 조회, 엑셀로 바로 다운로드해 별도 캡처 없음; E21 은 첨부 Kis-Net 탭 참고 추가 | 01_raw_matrix.csv / INPUT_RAW(원문 보존, '-' 결측 유지) + PROVENANCE 시트(PROVENANCE_REQUIRED_FIELDS: source_agency·curve_date·valuation_date·file_sha256·raw_copy_path·downloaded_at·operator·instrument.maturity_date; 누락 → 엣지 `출처불완전` FAIL) + `provenance.capture_path`(행 렌더링 캡처; 누락 → CAPTURE_MISSING 승인, GRAPH_SPEC §5·§6) + `provenance.agencies`/`averaging`(평균 적용 여부) | 1 |
| Q13 | (D22, No.13 '신용등급') 1) 신용등급을 확인한 해당 등급 캡처 2) 적용 YTM 위험할인율이 공모 또는 사모 기준인지 근거 설명(필수) | E22·F22: 1) 캡처 회신 없음. 2) BB+ 기준 공모사채 사용 — 회사는 사모사채를 발행했으나 반기 평가 당시 공모는 BB+ 까지 조회되고 사모는 조회되지 않아 공모치를 사용(F22: 준용); E22 는 기말 평가 시 동일 기준 유지 추가 | 02_rows_used.csv / ROWS_USED(선택 행·블록·등급·notch) + PROVENANCE(instrument.issuance_type·rating·prior_rating_basis·prior_block_basis·rating_evidence.{source_agency, lookup_date, capture_path, sha256}; 캡처 누락 → CAPTURE_MISSING 승인) + 09_flags.csv / FLAGS(ROW_FALLBACK·NOTCH_APPLIED·RATING_CHANGED·BLOCK_CHANGED 승인 코드, GRAPH_SPEC §5); 대체 규칙 = BLOCK_FALLBACK | 1 |

## 3. 검토자 Check list C33~C48 (`Check list` 시트; 회신 = D열 검토결과 + E열 Comment/Ref.)

| 코드(EVIDENCE_REQUIRED_ITEMS 키) | 원문 요지 | 회신 요지 | 1단계 증빙 위치(EVIDENCE_FILES/XLSX_SHEETS 기준) | 단계(1/2) |
|---|---|---|---|---|
| C33 | (분류 B33 '할인율(Ajusted discounted rate)' [sic — 원문 철자 그대로]) 이항모형 할인율 기준은 적정한가? | Yes — 평가기준일 현재 국고채 유통수익률과 해당 신용등급 금리를 측정주기(weekly)에 따른 이자율 기간구조로 고려해 매시점별 단기선도이자율(short-term forward risk-free rate) 적용 | 06_tree_grid.csv / Rf_dc·Rd_dc 블록 2·4(`step, date, t, dt, C-FWD[continuous], F_step[per_step_simple]`); 격자·선도 규칙 TREE_GRID·TREE_FWD_RULE(CONVENTIONS) | 1 |
| C34 | 이항모형 구간별 할인율 추출방법은 적절한가? | Yes — 1/(1+fwd)^dt 로 할인 | Rf_dc·Rd_dc 블록 2·4 `F_step[per_step_simple]`·`DF_step`(NODE_DISCOUNT_CONV); 이산 1/(1+F) 병기 = state `fwd.df_step_alt`(XLSX_COLUMNS 에 열 없음, 본 문서 §7); CONVENTION_REASONS["NODE_DISCOUNT_CONV"] | 1 |
| C35 | 관측 YTM 에서 Zero Coupon rate(Spot rate) Bootstrapping 방법은 적절한가? | Yes — 연간YTM/4 | 04_bootstrap.csv / Rf_dc·Rd_dc 블록 3(`n, t, c[per_period_m*], price_target, spot_pp[per_period_m*], DF, denominator`); COUPON_CONV·RF_FREQ·RD_FREQ·BOOTSTRAP_MODE·PRICE_MODE(CONVENTIONS); RF 분기 변형 = FREQ_SENSITIVITY_SET → 11_sensitivity.csv | 1 |
| C36 | 신용도 및 기간구조를 고려한 Spot rate & Forward rate 가 유의적 차이가 없는가? | Yes — Rd_dc 시트 | 07_par_residuals.csv / PAR_CHECK(`curve, t, n, price, target, residual, residual_x_face`) + 11_sensitivity.csv / SENSITIVITY(교차 보간법·주기 DF 상대차); 독립 재계산 대조 = fixture C(REVIEWER_2024 프로필) 골든 테스트(TOL_GOLDEN_ABS 의 C_* 키) | 1 |
| C37 | 만기가 동일하지 않은 경우 보간법을 적용하여 잔존만기에 해당하는 수익률을 적용하였는가? | Yes — 잔존만기에 정확히 일치하는 Tenor 가 없어 관측가능한 Tenor 수익률 간 직선보간법 적용 | README_conventions.md / CONVENTIONS(INTERP_METHOD·INTERP_SPACE_PRE·INTERP_SPACE_GRID·EXTRAP_LEFT·EXTRAP_RIGHT + CONVENTION_REASONS["INTERP_METHOD"]); 03_knots.csv; 10_headline.json `rule` | 1 |
| C38 | 회사의 신용등급 및 옵션 잔존만기에 해당하는 회사채 이자율을 사용하였는가 | Yes — 발행사의 신용도·유동성·부가옵션·담보/보증·금리변동 등 채권 특성을 고려해 Yield Curve 결정; Kisline 등에서 조회되는 각 평가기준일 신용등급 인용 | 02_rows_used.csv / ROWS_USED(RD 행: 등급·블록) + PROVENANCE(instrument.rating·rating_evidence) + 10_headline.json / HEADLINE(`rating_applied`, `rd_ytm_remaining`) | 1 |
| C39 | 위험할인율은 독립적으로 조회 및 산출한 위험이자율 커브와 유의적 차이가 없는가? | Yes — Rd_dc 시트 | 05_spot_table.csv(RD) / Rd_dc 블록 3·2·4 + PAR_CHECK(curve=RD); 독립 대조 = fixture C Rd 골든 | 1 |
| C40 | 무위험할인율은 독립적으로 조회한 국고채수익률과 일치하는가? | Yes — Rf_dc 시트 | 01_raw_matrix.csv / INPUT_RAW(국고채 행 원문) + 02_rows_used.csv / ROWS_USED(RF) + PROVENANCE(file_sha256·raw_copy_path) | 1 |
| C41 | (분류 B41 '일반사채(Straight bond) 가치의 검토') 전환사채 발행회사의 신용등급이 독립적으로 조회한 신용등급과 일치하는가? | Yes — KIS | PROVENANCE(instrument.rating·rating_evidence.{source_agency, lookup_date, capture_path, sha256}·prior_rating_basis) + 09_flags.csv / FLAGS(RATING_CHANGED) + HEADLINE `rating_applied` | 1 |
| C42 | 이자지급주기와 계산방식 가정이 계약서와 일치하는가? | Yes — 무이자 조건 | (2단계: 일반사채 현금흐름 — `STEP2_EVIDENCE_ITEMS`) | 2 |
| C43 | 일반사채 현금흐름 할인 시 사용된 할인율이 감사인이 독립적으로 재계산한 할인율과 일치하는가? | Yes — Bond Value | 05_spot_table.csv / Rd_dc 블록 2·4(`t, D-SPOT[annual_eff], C-SPOT[continuous], DF`) + 10_headline.json(`rd_spot_remaining_annual`); 임의 시점 spot(t) 조회 규약 = `result.next_step_interface.spot_lookup`(method·space·basis) | 1 |
| C44 | 만기가 동일하지 않은 경우 보간법을 적용하여 잔존만기에 해당하는 수익률을 적용하였는가? (일반사채 항목) | Yes — C37 과 같은 문구(직선보간) | 10_headline.json / HEADLINE(`rule`=HEADLINE_RULE, `rf_ytm_remaining`, `rd_ytm_remaining`, `candidates` = HEADLINE_DEFS 진단표) + CONVENTIONS | 1 |
| C45 | 일반사채 평가 시 사용된 수식이 적정하며, 독립적으로 재계산한 일반사채 현재가치와 일치하는가? | Yes — 유의적 차이 범위 내(별첨 Bond value) | (2단계) | 2 |
| C46 | (분류 B46 '상환권(Put Option) 검토') 풋옵션 평가모형은 일반적으로 인정되는 모형인가? | Yes — 각 이항모형 Node 에서 Max[보유가치, 풋가치] 로 산출 | (2단계) | 2 |
| C47 | 조기상환 최적시점의 예측 근거는 적정한가? | Yes — 위험할인율과 조기상환청구이자율이 유의적으로 차이 나므로 조기상환가능기간 중 가장 이른 시점 행사 가정 | (2단계) | 2 |
| C48 | 조기상환금액의 현재가치 산정 시 사용된 할인율은 조기상환 최적시점에 해당하는 잔존만기 할인율(Spot rate)이 사용되었는가? | Yes — Comment 없음(E48 빈칸) | 05_spot_table.csv / Rd_dc 블록 2·4 의 spot·DF at `grid.tree.event_times`(풋 행사일) + `result.next_step_interface.spot_lookup`·`event_times` | 1 |

## 4. 입력변수 헤드라인 (*1)(*3) (`질의서` 파일의 `입력변수` 시트; No.19 질의 D28 '실제 투입변수 데이터 제출', G28 위치 `입력변수!C6`)

시트 구조: 열 B/C/D = 평가기준일 B9/C9/D9(2023-12-31 / 2024-06-21 / 2024-12-31). 아래는 참조 모형(KBI) 2024-12-31(D열) 기재값만 옮겼고, B·C열(전기·반기)은 원문에만 둔다. 각주 A43 '(*1)(무)위험이자율 : 잔여만기에 해당하는 YTM(연)', A45 '(*3)공모/사모 구분기재'.

| 코드(EVIDENCE_REQUIRED_ITEMS 키) | 원문 요지 | 회신 요지(참조 모형(KBI) 기재값) | 1단계 증빙 위치(EVIDENCE_FILES/XLSX_SHEETS 기준) | 단계(1/2) |
|---|---|---|---|---|
| HEADLINE_RF | A26 '무위험이자율(*1)' — 잔여만기 YTM(연) | D26 = 0.02765 | 10_headline.json / HEADLINE(`rule`, `rf_ytm_remaining`, `reported_rf`, `match_ok`); 보고서 값 입력 = `provenance.instrument.reported_headline.rf_pct`; 불일치 → HEADLINE_MISMATCH 승인(GRAPH_SPEC §5), 비교 안 됨 → 엣지 `헤드라인미비교` FAIL | 1 |
| HEADLINE_RD | A27 '위험이자율(*1)' — 잔여만기 YTM(연) | D27 = 0.11854 | HEADLINE(`rd_ytm_remaining`, `reported_rd`, `match_ok`); `reported_headline.rd_pct` | 1 |
| HEADLINE_RATING | A34 '적용신용등급(*3)' | D34 = 공모BB+ | HEADLINE(`rating_applied`) + ROWS_USED(RD 행 등급·notch) + PROVENANCE(instrument.rating) | 1 |
| HEADLINE_BLOCK | 각주 A45 '(*3)공모/사모 구분기재' | D34 접두 '공모' (Q13 회신: 사모 미고시로 공모 준용) | HEADLINE(`block_applied`) + ROWS_USED(`rd_fallback_used`·`rd_fallback_reason`) + FLAGS(ROW_FALLBACK·BLOCK_CHANGED) + PROVENANCE(instrument.issuance_type·prior_block_basis) | 1 |

## 5. 원문 질의가 없는 시스템 항목

| 코드(EVIDENCE_REQUIRED_ITEMS 키) | 원문 요지(근거) | 회신 요지 | 1단계 증빙 위치(EVIDENCE_FILES/XLSX_SHEETS 기준) | 단계(1/2) |
|---|---|---|---|---|
| KICPA_INTERP_DISCLOSURE | 한공회 실무사례 §3.7.3.6 보간 공시(CONVENTION_REASONS["INTERP_METHOD"]; FORMULA_REFERENCE·INTERPOLATION_METHODS) | — | README_conventions.md / CONVENTIONS: 보간 방법 1개·PRE/GRID 공간·부트스트랩 내부와 트리 매핑 동일 적용·연속복리 변환 규칙(RF_FREQ·RD_FREQ)·외삽 규칙·프로필(PROFILE_NAME)·상수 fingerprint | 1 |
| RUN_PATH | 지나온 경로가 곧 감사조서(GRAPH_SPEC §8; state `run.path`) | — | RUN_PATH 시트(`seq, from, condition, to, ts_utc, resume_n`) | 1 |
| APPROVALS | 사람승인 3곳 기록(GRAPH_SPEC §6) | — | 12_approvals.json / APPROVALS 시트(`kind, requested_at, snapshot_sha256, flags_seen, decision, approver, timestamp, comment, acknowledged_codes`) | 1 |

## 6. 배분 요약 (코드와 1:1 — 2026-09-07 `Constants` 대조)

- **1단계 `EVIDENCE_REQUIRED_ITEMS` 27개**: Q1, Q8, Q9_FWD_INPUT, Q10_1, Q10_2, Q11, Q12, Q13 (8) · C33, C34, C35, C36, C37, C38, C39, C40, C41, C43, C44, C48 (12) · HEADLINE_RF, HEADLINE_RD, HEADLINE_RATING, HEADLINE_BLOCK (4) · KICPA_INTERP_DISCLOSURE, RUN_PATH, APPROVALS (3). 전항목이 `export.cell_map` 에 유효한 위치 문자열로 있어야 엣지 `내보내기완료` 로 `done` 에 도달한다(누락·형식 오류 → `증빙불완전`, 시나리오 E46·E47).
- **2단계 `STEP2_EVIDENCE_ITEMS` 5개**: Q9, C42, C45, C46, C47 — 1단계 checklist 에 포함하지 않는다(GRAPH_SPEC §9·§10).
- 매핑 규칙: Q9 → Q9_FWD_INPUT(1단계, 트리 입력용 선도·DF) + Q9(2단계, 트리 자체 검증); Q10 → Q10_1(표) + Q10_2(이표율 환산 방식).

## 7. 관찰 사항 (판단 아님 — 결정은 사람 몫, 코드 반영은 Constants·EDGES 로만)

1. **Q8·Q9 회신 두 열 불일치**: E열 = ③ exp(−fwd·dt) / ④, F열 = ① / ①. FORMULA_REFERENCE §5 '노드 할인 규약(AUD Q8)' 항목(평가인 E열=③ XL BM 연속, F열=①)과 일치하며, 검토자 Check list E34('1/(1+fwd)^dt로 할인' = Q8 ①)·E19('p*=((1+rf fwd)^dt−하락비율)/(상승비율−하락비율)' = Q9 ①; 추출 기록은 본 문서 §1)는 ① 을 수용. 앱은 NODE_DISCOUNT_CONV 를 선언하고 이산값을 병기한다(CONVENTION_REASONS). 2단계 Q9 의 p* 형태도 같은 병기 원칙.
2. **Q10-2 미답변**: 평가인 회신에 환산 방식·사유가 없다. COUPON_CONV 선언과 사유(CONVENTION_REASONS["COUPON_CONV"])가 앱 몫이며 검토자 E35 '연간YTM/4' 와 같은 관례다.
3. **Q12·Q13 캡처 없음**: 평가인은 엑셀 직접 다운로드라 캡처가 없다고 회신했고 등급 캡처는 회신이 없다. 앱은 `provenance.capture_path`·`instrument.rating_evidence.capture_path`(PROVENANCE_APPROVAL_FIELDS)를 승인 항목(CAPTURE_MISSING)으로 둔다 — 캡처 없이 통과하려면 승인자가 ack 해야 한다.
4. **Q13 사모 미고시 → 공모 준용**: BLOCK_FALLBACK 규칙의 출처. 대체 사용 시 ROW_FALLBACK 승인, 전기 블록과 다르면 BLOCK_CHANGED 승인.
5. **`df_step_alt` 열 부재**: XLSX_DC_BLOCKS 블록 4(Rf_dc/Rd_dc) 에 이산 1/(1+F) 할인계수 열이 없다(state `fwd.df_step_alt` 에는 있음). C34·Q8 병기를 시트에서 직접 보이려면 열 추가가 필요 — 열린 결정.
6. **Q1 트리 시트 요구**: 노드별 데이터 시트 제출 요구는 2단계 산출물이지만 STEP2_EVIDENCE_ITEMS 에 대응 키가 없다 — 열린 결정.
7. **헤드라인 재현 불가**: 참조 모형(KBI) 2024-12-31 헤드라인은 검토자 매트릭스의 직선보간(HEADLINE_RULE 기본)으로 재현되지 않는다(`tests/fixtures/README.md`: stale BOOT 5Y knot; 대안 ceil_tenor 는 EXCEL_REF 프로필 전용). HEADLINE_MISMATCH 승인 경로가 이를 다룬다.
8. **Q11 회신 위치**(현물이자율 Tab H,I열 4행)는 평가인 워킹파일 안의 위치이며 여기서는 추출하지 않았다. 검토자 측 대조값은 fixture C 에 있다(본 문서 §2 Q11 행).
9. 질의서 H~K 열(2차·3차 질의/회신)은 비어 있다. Check list D열은 C33~C48 전항목 'Yes' 이다.
