<div align="center">

# WQB Alpha Research

**An AI-assisted paper-to-alpha research pipeline for WorldQuant BRAIN.**

將研究論文轉換成可追蹤、可驗證，並可在 WorldQuant BRAIN 模擬的 Alpha 策略。

[快速開始](#快速開始) · [CLI 指令](#cli-指令總覽) · [運作流程](#運作流程) · [輸出檔案](#輸出檔案)

</div>

## 簡介

WQB Alpha Research 將論文閱讀、WQB 資料欄位搜尋、Alpha template 生成、規則驗證、Genetic Search 與 BRAIN simulation 串成一條可重複執行的研究流程。

你只需要提供一篇 PDF 或文字研究稿，系統就能抽取可交易假設、尋找相關的 WorldQuant BRAIN data fields 與 REGULAR operators、產生 Alpha template，並在通過 Python validator 後選擇是否執行模擬。

```text
Research Paper
      ↓
Hypothesis Extraction
      ↓
WQB Field & Operator Retrieval
      ↓
Alpha Template Generation
      ↓
Deterministic Validation
      ↓
Genetic Search
      ↓
WorldQuant BRAIN Simulation
```

### 核心功能

- 從 PDF、TXT、Markdown、RST 或 TEX 研究稿擷取可交易假設
- 從本地 WQB catalog 搜尋相關 data fields 與 REGULAR operators
- 使用結構化 JSON 產生可追蹤的 Alpha template
- 驗證 field、operator、placeholder 與 VECTOR/MATRIX 類型
- 在 template 不合法時要求 LLM 修復，未通過驗證就停止模擬
- 使用 Genetic Search 搜尋欄位與參數組合
- 支援完全離線的 Mock LLM、Fake Simulation 與真實 BRAIN Simulation
- 保存研究中間產物、模擬結果及錯誤資訊，方便重現與除錯

預設研究環境為 `EQUITY / GLB / Delay 1 / TOPDIV3000 / REGULAR / FASTEXPR`。

## 快速開始

### 1. 安裝

需要 Python 3.10 或以上版本。

```bash
git clone https://github.com/junyuan881/WQB_alpha_research.git
cd WQB_alpha_research
python -m venv .venv
```

Windows PowerShell：

```powershell
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

Linux / macOS：

```bash
source .venv/bin/activate
pip install -r requirements.txt
```

### 2. 設定環境變數

複製 `.env.example`：

```bash
cp .env.example .env
```

Windows PowerShell 可使用：

```powershell
Copy-Item .env.example .env
```

只有使用 OpenAI 或真實 BRAIN Simulation 時才需要填入對應設定：

```dotenv
OPENAI_API_KEY=your_openai_api_key
LLM_PROVIDER=openai
LLM_MODEL=gpt-5.6

WQB_USERNAME=your_wqb_username
WQB_PASSWORD=your_wqb_password
```

`.env` 已被 `.gitignore` 排除，請勿將真實憑證提交到 GitHub。

### 3. 先跑離線流程

以下流程不需要 OpenAI API key 或 WorldQuant BRAIN 帳號：

```bash
python run.py validate
python tests/research_pipeline_test.py
python run.py research \
  --paper papers/example_factor_paper.txt \
  --llm-provider mock \
  --simulate fake \
  --generations 2 \
  --population 6 \
  --reset-db
```

### 4. 使用真實論文

先產生並驗證 template，不要立即執行真實模擬：

```bash
python run.py research \
  --paper /path/to/your_paper.pdf \
  --llm-provider openai \
  --simulate none
```

確認 `generated/templates/` 的結果後，再用小規模 population 測試 BRAIN：

```bash
python run.py run-generated \
  generated/templates/your_paper_template.json \
  --mode real \
  --generations 1 \
  --population 4 \
  --reset-db
```

## CLI 指令總覽

所有功能都從 `run.py` 進入：

| 指令 | 功能 |
| --- | --- |
| `research` | 論文 → LLM → WQB mapping → template → validation，可選擇接續 simulation |
| `validate` | 驗證專案內建的手動 Alpha template |
| `validate-generated` | 驗證已產生的 template JSON |
| `run-generated` | 使用既有 template 執行 Genetic Search 與 simulation，不重複呼叫 LLM |
| `run` | 使用內建手動 template 執行傳統研究流程 |
| `fields` | 搜尋 GLB D1 TOPDIV3000 data fields |
| `operators` | 搜尋 REGULAR operators |
| `login` | 測試 WorldQuant BRAIN 登入與 Persona 流程 |

查看完整參數：

```bash
python run.py --help
python run.py research --help
```

## 常見使用方式

### 只產生 template

適合第一次處理真實論文。研究產物會被保存，但不會啟動 Genetic Search 或 simulation。

```bash
python run.py research \
  --paper /path/to/paper.pdf \
  --llm-provider openai \
  --simulate none
```

### 論文一路執行到 Fake Simulation

```bash
python run.py research \
  --paper /path/to/paper.pdf \
  --llm-provider openai \
  --simulate fake \
  --generations 2 \
  --population 10 \
  --reset-db
```

### 重複使用已產生的 template

將 LLM generation 與 simulation 分開，可以避免重複支付 LLM API 成本。

```bash
python run.py validate-generated generated/templates/your_paper_template.json

python run.py run-generated \
  generated/templates/your_paper_template.json \
  --mode fake \
  --generations 2 \
  --population 10 \
  --reset-db
```

將 `--mode fake` 改成 `--mode real` 即可使用 WorldQuant BRAIN。

### 使用手動 template

不使用論文或 LLM 時，仍可執行 `wqb_alpha/alpha_template.py` 的傳統流程：

```bash
python run.py run \
  --mode fake \
  --generations 2 \
  --population 10 \
  --reset-db
```

### 搜尋 fields 與 operators

```bash
python run.py fields "free cash flow" --type MATRIX --limit 20
python run.py fields debt --dataset fundamental23 --limit 30
python run.py operators rank
python run.py operators --category "Time Series" --limit 30
```

### 測試 BRAIN 登入

```bash
python run.py login
```

若 BRAIN 要求 Persona、MFA 或其他官方驗證，程式會保留互動式流程，不會繞過驗證機制。

## 運作流程

### 1. 理解論文

LLM 將論文整理成研究問題、經濟直覺、可交易假設、預期方向與相關概念。這一階段不直接產生 Alpha expression，讓每個 Alpha 都能追蹤回原始研究想法。

### 2. 搜尋 WQB 資源

Python 先從本地 catalog 搜尋與論文概念相關的 data fields 及 REGULAR operators，只將 shortlist 提供給 LLM。這能縮小 prompt 並降低使用不存在資源的機率。

### 3. 產生與驗證 template

LLM 依據 hypothesis 與 shortlist 產生結構化 template。Python validator 會檢查：

- field 與 operator 是否存在且位於允許清單
- placeholder 是否完整、唯一且有被使用
- FIELD 與 PARAMETER 的設定是否合法
- MATRIX 與 VECTOR 類型是否被正確處理
- template 內是否包含不合法的固定 operator

若驗證失敗，系統最多依 `--max-repairs` 設定要求 LLM 修復；仍未通過時不會進入 simulation。

### 4. 搜尋與模擬

驗證完成後，Genetic Search 會探索 template 中的 field 與 parameter variants。`fake` 模式適合測試流程；`real` 模式則將候選 Alpha 送至 WorldQuant BRAIN。

| 元件 | 責任 |
| --- | --- |
| LLM | 理解論文、提出 hypothesis、設計受限 template |
| Python retrieval | 搜尋可用 fields 與 operators |
| Python validator | 擔任 simulation 前的 hard gate |
| Genetic Search | 探索 field 與 parameter 組合 |
| BRAIN | 執行真實 simulation 並回傳結果 |

## 輸入與輸出

### 支援的研究稿格式

- `.pdf`：透過 OpenAI Responses API 讀取文字與頁面內容，單檔需小於 50 MB
- `.txt`
- `.md` / `.markdown`
- `.rst`
- `.tex`

文字格式會在本機讀取。PDF 模式需要有效的 OpenAI API key。

### 輸出檔案

```text
generated/
├── hypotheses/   # 論文分析與可交易假設
├── candidates/   # data-field 與 operator shortlist
└── templates/    # template JSON 與可讀的 Python 版本

db/
├── pending/      # 等待處理的 simulations
├── complete/     # 已完成的 simulations
└── error/        # 錯誤內容與 pipeline_error

output/           # 排序後的 simulation CSV
```

## 專案結構

```text
.
├── run.py                    # CLI entry point
├── data/                     # WQB fields 與 REGULAR operators catalog
├── papers/                   # 範例與本地研究稿
├── prompts/                  # analysis、generation 與 repair prompts
├── generated/                # pipeline 中間產物
├── output/                   # simulation 結果
├── tests/                    # smoke 與 end-to-end tests
├── reference/                # 原始研究 notebook
└── wqb_alpha/
    ├── cli.py                # CLI commands
    ├── paper_reader.py       # PDF / text input
    ├── paper_analyzer.py     # hypothesis extraction
    ├── field_search.py       # data-field retrieval
    ├── operator_search.py    # operator retrieval
    ├── template_generator.py # template generation / repair
    ├── validator.py          # deterministic validation
    ├── genetic_search.py     # Genetic Search
    ├── worker.py             # Fake / BRAIN workers
    └── llm/                  # OpenAI 與 mock clients
```

## 進階設定

`research` 常用參數：

| 參數 | 預設值 | 說明 |
| --- | ---: | --- |
| `--field-limit` | `80` | 提供給 LLM 的 field shortlist 大小 |
| `--operator-limit` | `50` | 提供給 LLM 的 operator shortlist 大小 |
| `--max-repairs` | `2` | template 驗證失敗後的修復次數 |
| `--simulate` | `none` | `none`、`fake` 或 `real` |
| `--generations` | `2` | Genetic Search generations |
| `--population` | `10` | 每個 generation 的 population |
| `--seed` | `123` | 隨機種子 |
| `--single-sim` | 關閉 | 停用 multi-simulation |

環境變數與完整 runtime tuning 請參考 [`.env.example`](.env.example)。

## 測試

```bash
python tests/smoke_test.py
python tests/research_pipeline_test.py
```

`research_pipeline_test.py` 使用 Mock LLM 與本地資料，適合在設定真實 API 前確認整條 pipeline。

## 注意事項

- LLM 產生的 hypothesis 或 Alpha template 不代表具有投資價值，仍需實驗與人工判斷。
- 真實 BRAIN Simulation 會使用你的 WorldQuant BRAIN 帳號與 API 配額，建議先以小型 population 測試。
- 專案目前針對 `GLB / Delay 1 / TOPDIV3000 / REGULAR / FASTEXPR` catalog 設計。
- 請勿提交 `.env`、session cache、真實帳號密碼或 API key。

