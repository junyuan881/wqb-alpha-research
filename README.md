# WorldQuant BRAIN Paper-to-Alpha Research Project



> **研究論文 PDF → LLM 理解論文 → 自動搜尋 WQB data fields → 自動選 REGULAR operators → 產生 Alpha template → deterministic validation → Genetic Search → BRAIN simulation**


預設 WQB 環境：

- Instrument: `EQUITY`
- Region: `GLB`
- Delay: `1`
- Universe: `TOPDIV3000`
- Alpha type: `REGULAR`
- Language: `FASTEXPR`

專案內已包含你提供的：

- `data/REGULAR_operators.json`
- `data/GLB_D1_TOPDIV3000_data_fields.json`

---

版則是：

```text
Research PDF
    ↓
paper_reader.py
    ↓
paper_analyzer.py
    ↓
LLM #1：抽取論文 hypothesis / concepts
    ↓
field_search.py
    ↓
從 28,863 個 GLB fields 擷取最相關的一小批
    ↓
operator_search.py
    ↓
從 REGULAR operators 擷取可用集合
    ↓
template_generator.py
    ↓
LLM #2：Paper hypothesis → WQB Alpha template
    ↓
validator.py
    ↓
檢查 field / operator / placeholder / VECTOR type
    ↓
若不合法 → LLM 自動 repair（最多 N 次）
    ↓
generated/template.json
    ↓
Genetic Search
    ↓
FakeWorker 或真實 BRAIN Simulation
```

LLM 只負責「研究理解和設計」。真正決定 template 能不能進 simulation 的是 Python validator。

---

## 2. LLM 是怎麼運作的？

預設支援兩個 provider：

### `openai`

你的 Python 程式直接呼叫 OpenAI Responses API。

```text
你的電腦
   ↓
run.py
   ↓
OPENAI_API_KEY
   ↓
OpenAI Responses API
   ↓
structured JSON
```

不是去操作你瀏覽器裡的 ChatGPT 對話，也不是使用 ChatGPT Plus 的聊天額度。

此專案沒有安裝 OpenAI SDK，而是直接用既有的 `requests` 呼叫 API，所以仍維持非常乾淨的 dependency。

### `mock`

完全不連網的假 LLM，專門測整條 pipeline 是否正常：

```bash
python run.py research \
  --paper /absolute/path/to/papers/example_factor_paper.txt \
  --llm-provider mock \
  --simulate fake \
  --generations 2 \
  --population 6 \
  --reset-db
```

這個 command 我已經實際跑過，可以從論文階段一路跑到 GA/Fake Simulation。

---

## 3. 為什麼 PDF 不需要另外裝 pypdf？

OpenAI Responses API 本身可以接收 PDF file input，所以 `openai_client.py` 會把 PDF 轉成 base64 file input 直接交給模型。

因此：

```text
PDF
 ↓
base64
 ↓
Responses API input_file
 ↓
LLM 同時理解 PDF 文字與頁面內容
```

專案目前對 PDF 的限制是：

- 必須是 `.pdf`
- 單一 PDF 必須小於 50 MB
- 需要設定 `OPENAI_API_KEY`

文字研究稿也支援：

- `.txt`
- `.md`
- `.markdown`
- `.rst`
- `.tex`

文字檔會直接在本機讀取，不會先轉成 PDF。

---

## 4. 專案結構

```text
wqb_alpha_research_project_llm/
├── README.md
├── requirements.txt
├── .env.example
├── .gitignore
├── run.py
│
├── papers/
│   ├── .gitkeep
│   └── example_factor_paper.txt
│
├── prompts/
│   ├── paper_analysis.txt
│   ├── template_generation.txt
│   └── template_repair.txt
│
├── data/
│   ├── REGULAR_operators.json
│   └── GLB_D1_TOPDIV3000_data_fields.json
│
├── wqb_alpha/
│   ├── __init__.py
│   ├── config.py
│   │
│   ├── auth.py
│   ├── api_client.py
│   │
│   ├── paper_reader.py
│   ├── hypothesis.py
│   ├── paper_analyzer.py
│   │
│   ├── field_search.py
│   ├── operator_search.py
│   │
│   ├── template_schema.py
│   ├── template_generator.py
│   ├── validator.py
│   │
│   ├── llm/
│   │   ├── __init__.py
│   │   ├── base.py
│   │   ├── openai_client.py
│   │   └── mock_client.py
│   │
│   ├── research_pipeline.py
│   │
│   ├── alpha.py
│   ├── alpha_list.py
│   ├── alpha_template.py
│   ├── template_engine.py
│   ├── data_field_catalog.py
│   ├── operator_catalog.py
│   ├── storage.py
│   ├── worker.py
│   ├── scorer.py
│   ├── genetic_search.py
│   ├── exporter.py
│   └── cli.py
│
├── generated/
│   ├── hypotheses/
│   ├── candidates/
│   └── templates/
│
├── db/
│   ├── pending/
│   ├── complete/
│   └── error/
│
├── output/
│
├── tests/
│   ├── smoke_test.py
│   └── research_pipeline_test.py
│
└── reference/
    └── original_notebook.ipynb
```

---

## 5. 安裝

建議 Python 3.10+。

### Windows PowerShell

```powershell
cd C:\你的路徑\wqb_alpha_research_project_llm
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

### WSL / Linux / macOS

```bash
cd /你的/絕對路徑/wqb_alpha_research_project_llm
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

目前 dependencies 仍只有：

```text
requests
numpy
pandas
tqdm
```

---

## 6. 設定 `.env`

先複製：

### Windows PowerShell

```powershell
Copy-Item .env.example .env
```

### Linux / WSL / macOS

```bash
cp .env.example .env
```

然後編輯 `.env`：

```text
OPENAI_API_KEY=你的_OpenAI_API_Key
LLM_PROVIDER=openai
LLM_MODEL=gpt-5.6

WQB_USERNAME=你的_WQB_帳號
WQB_PASSWORD=你的_WQB_密碼
```

`config.py` 有一個小型 `.env` reader，因此不需要另外裝 `python-dotenv`。

`.env` 已被 `.gitignore` 排除，不會打包進 Git。

---

## 7. 先確認原本 WQB template 沒壞

```bash
python run.py validate
```

預期：

```text
Template validation: PASS
```

---

## 8. 先測完整 Paper-to-Alpha pipeline（不用任何 API）

先跑：

```bash
python run.py research \
  --paper /absolute/path/to/wqb_alpha_research_project_llm/papers/example_factor_paper.txt \
  --llm-provider mock \
  --simulate none
```

會得到：

```text
[1/7] Reading/analyzing paper with LLM...
[2/7] Retrieving relevant WQB data fields...
[3/7] Retrieving relevant REGULAR operators...
[4/7] Asking LLM to design an Alpha template...
[5/7] Validating generated fields/operators/template...
[6/7] Simulation skipped (--simulate none).
[7/7] Research artifacts saved.
```

產物會放在：

```text
generated/hypotheses/
generated/candidates/
generated/templates/
```

---

## 9. 真正把 PDF 論文交給 OpenAI

假設論文是：

```text
/home/lenovo/papers/my_factor_paper.pdf
```

執行：

```bash
python run.py research \
  --paper /home/lenovo/papers/my_factor_paper.pdf \
  --llm-provider openai \
  --simulate none
```

如果 `.env` 已經寫：

```text
LLM_PROVIDER=openai
LLM_MODEL=gpt-5.6
```

那也可以簡化：

```bash
python run.py research \
  --paper /home/lenovo/papers/my_factor_paper.pdf \
  --simulate none
```

---

## 10. Paper analysis 會產生什麼？

例如：

```json
{
  "title": "...",
  "research_question": "...",
  "summary": "...",
  "tradable_claims": [
    {
      "id": "H1",
      "source_hint": "Section 3 empirical result",
      "hypothesis": "...",
      "economic_intuition": "...",
      "predictor_concepts": [
        "free cash flow",
        "net debt",
        "leverage"
      ],
      "expected_direction": "POSITIVE",
      "horizon": "1-6 months",
      "implementation_notes": "..."
    }
  ],
  "global_concepts": [
    "cash flow",
    "debt"
  ],
  "risks": []
}
```

這一層故意不直接產生 Alpha expression。

流程一定是：

```text
Paper
 ↓
Hypothesis
 ↓
WQB Mapping
 ↓
Alpha Template
```

這樣將來回頭 debug 才知道是哪一層出問題。

---

## 11. 為什麼不把 28,863 個 fields 全塞進 LLM？

`field_search.py` 會先在本機做 retrieval。

例如 paper analysis 抽出：

```text
free cash flow
operating cash flow
net debt
leverage
```

程式會掃描本地：

```text
data/GLB_D1_TOPDIV3000_data_fields.json
```

然後只留下例如前 80 個候選 fields。

你可以調：

```bash
--field-limit 120
```

例如：

```bash
python run.py research \
  --paper /home/lenovo/papers/paper.pdf \
  --field-limit 120 \
  --operator-limit 60 \
  --simulate none
```

這樣可以大幅減少 prompt 大小，也降低 LLM 亂挑 field 的機率。

---

## 12. Template 的 JSON 格式

LLM 不直接輸出 Python code，而是固定輸出 schema，例如：

```json
{
  "name": "cashflow_debt_resilience",
  "description": "...",
  "source_hypothesis_id": "H1",
  "expression_template": "cash = ts_backfill(<cash_field>, <backfill_days>); ...",
  "variables": [
    {
      "placeholder": "<cash_field>",
      "kind": "FIELD",
      "values": [
        "free_cash_flow_firm",
        "free_cash_flow_annual"
      ],
      "rationale": "..."
    },
    {
      "placeholder": "<lookback>",
      "kind": "PARAMETER",
      "values": ["21", "63", "126", "252"],
      "rationale": "..."
    }
  ],
  "design_notes": []
}
```

`template_schema.py` 再把它轉成：

```python
ALPHA_TEMPLATE
ALPHA_SPACE
```

所以模型不會直接寫或覆蓋專案核心程式。

---

## 13. Validator 會檢查什麼？

模型產生 template 後，一定要先通過 `validator.py`。

它檢查：

1. 所有 FIELD 是否真的存在於 GLB catalog。
2. FIELD 是否屬於本次 retrieval shortlist。
3. 所有 OPERATOR 是否真的在 REGULAR operators。
4. operator 是否屬於本次 allowed shortlist。
5. template 內固定 literal operator 是否合法。
6. 每個 `<placeholder>` 是否都有 variable definition。
7. 是否有 duplicate placeholder。
8. FIELD placeholder 是否混用 `MATRIX` 與 `VECTOR`。
9. `VECTOR` field 是否有先用 `vec_*` reducer。
10. variable 是否定義但沒有使用。

如果 validation fail：

```text
LLM template
   ↓
validator FAIL
   ↓
template_repair.txt
   ↓
LLM repair
   ↓
validator again
```

預設最多修兩次：

```bash
--max-repairs 2
```

如果兩次後還失敗，就不會進 simulation。

---

## 14. 只產生 template，不跑 BRAIN

這是我最推薦的第一步：

```bash
python run.py research \
  --paper /home/lenovo/papers/paper.pdf \
  --simulate none
```

確認以下東西：

```text
generated/hypotheses/<paper>_paper_analysis.json
generated/candidates/<paper>_fields.json
generated/candidates/<paper>_operators.json
generated/templates/<paper>_template.json
generated/templates/<paper>_alpha_template.py
```

---

## 15. 檢查已經產生好的 template

```bash
python run.py validate-generated \
  /absolute/path/to/generated/templates/my_paper_template.json
```

預期：

```text
Generated template validation: PASS
```

---

## 16. 之後直接拿舊 template 跑，不要再花一次 LLM API

這個 command 很重要：

```bash
python run.py run-generated \
  /absolute/path/to/generated/templates/my_paper_template.json \
  --mode fake \
  --generations 2 \
  --population 10 \
  --reset-db
```

真實 BRAIN：

```bash
python run.py run-generated \
  /absolute/path/to/generated/templates/my_paper_template.json \
  --mode real \
  --generations 2 \
  --population 10 \
  --reset-db
```

因此你可以把 expensive LLM generation 和 simulation 完全拆開。

---

## 17. 論文直接一路跑到 Fake Simulation

```bash
python run.py research \
  --paper /home/lenovo/papers/paper.pdf \
  --llm-provider openai \
  --simulate fake \
  --generations 2 \
  --population 10 \
  --reset-db
```

這會：

```text
論文
 ↓
OpenAI
 ↓
Hypothesis
 ↓
Fields
 ↓
Operators
 ↓
Template
 ↓
Validator
 ↓
GA
 ↓
FakeWorker
 ↓
CSV
```

---

## 18. 論文直接一路跑到真實 WQB BRAIN

建議先用很小的 population：

```bash
python run.py research \
  --paper /home/lenovo/papers/paper.pdf \
  --llm-provider openai \
  --simulate real \
  --generations 1 \
  --population 4 \
  --reset-db
```

確認 4 個都沒有 API ERROR 後，再放大：

```bash
python run.py research \
  --paper /home/lenovo/papers/paper.pdf \
  --simulate real \
  --generations 5 \
  --population 30
```

---

## 19. 登入 WQB 仍然獨立

登入邏輯仍在：

```text
wqb_alpha/auth.py
```

獨立測試：

```bash
python run.py login
```

如果 WorldQuant BRAIN 要求 Persona / 官方驗證，程式會保留互動式流程，不會繞過 MFA、CAPTCHA 或生物辨識。

---

## 20. 原本手動 template 仍然保留

如果你不想用論文/LLM，舊流程仍然能跑：

```bash
python run.py run \
  --mode fake \
  --generations 2 \
  --population 10 \
  --reset-db
```

真實：

```bash
python run.py run \
  --mode real \
  --generations 2 \
  --population 10 \
  --reset-db
```

舊 template 仍位於：

```text
wqb_alpha/alpha_template.py
```

---

## 21. 搜尋 data fields

```bash
python run.py fields "free cash flow" --type MATRIX --limit 20
```

```bash
python run.py fields "net debt" --limit 20
```

```bash
python run.py fields debt --dataset fundamental23 --limit 30
```

---

## 22. 搜尋 REGULAR operators

```bash
python run.py operators rank
```

```bash
python run.py operators --category "Time Series" --limit 30
```

---

## 23. Output / database

### LLM / research intermediate outputs

```text
generated/hypotheses/
generated/candidates/
generated/templates/
```

### Simulation database

```text
db/pending/
db/complete/
db/error/
```

### 結果 CSV

```text
output/
```

每個 simulation ERROR 會保留：

```text
pipeline_error
```

所以不再只看到「全部 ERROR」卻不知道原因。

---

## 24. 建議你的實際使用順序

第一次：

```bash
pip install -r requirements.txt
```

```bash
cp .env.example .env
```

填 API key 後：

```bash
python run.py validate
```

離線完整測試：

```bash
python tests/research_pipeline_test.py
```

再測 Mock + Fake：

```bash
python run.py research \
  --paper /absolute/path/to/papers/example_factor_paper.txt \
  --llm-provider mock \
  --simulate fake \
  --generations 2 \
  --population 6 \
  --reset-db
```

真正論文先只做 template：

```bash
python run.py research \
  --paper /absolute/path/to/your_paper.pdf \
  --llm-provider openai \
  --simulate none
```

最後才小規模真實 BRAIN：

```bash
python run.py run-generated \
  /absolute/path/to/generated/templates/your_paper_template.json \
  --mode real \
  --generations 1 \
  --population 4 \
  --reset-db
```

---

## 25. 重要設計原則

這個專案刻意不是：

```text
LLM 隨便讀 PDF
 ↓
LLM 隨便寫 Alpha
 ↓
直接 BRAIN
```

而是：

```text
LLM：研究理解
        ↓
Python：WQB retrieval
        ↓
LLM：受限設計
        ↓
Python：hard validation
        ↓
GA：搜尋 parameter/field variants
        ↓
BRAIN：simulation
```

因此 LLM 是「researcher」，Python 是「retriever + gatekeeper」，WQB BRAIN 是「experiment environment」。

這樣做的目的就是降低：

- hallucinated data fields
- hallucinated operators
- VECTOR/MATRIX type error
- invalid placeholder
- 整批 simulation 全部 ERROR
- 每次手動複製 template

同時保留論文原始 hypothesis，讓之後可以追蹤 Alpha 到底是從哪個研究想法來的。
