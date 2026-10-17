# Multi-Agent Systems for Software Vulnerability Detection (`mas-se-eval`)

An empirical evaluation framework benchmarking **Single-Agent** vs. **Multi-Agent System (MAS)** LLM architectures on real-world software vulnerability detection. Built with **LangGraph**, **Pydantic**, and **OpenAI/Ollama Structured Outputs**, this framework evaluates how agent topology, tool augmentation, adversarial debate, and model scale (`7B`, `14B`, `32B`) impact vulnerability detection across paired pre-commit (vulnerable) and post-commit (benign) code benchmarks (**SVEN / CleanVul** and **PrimeVul**).

---

## 1. Project Overview & Architecture Taxonomy

Standard accuracy metrics often mask whether an LLM truly understands a security patch or merely guesses "vulnerable" on every function with similar syntax. Following recent software engineering literature (**PrimeVul**, ICSE 2025; **CleanVul**, 2024; **VulTrial**, ICSE 2026), this project evaluates **five distinct agent configurations** on **paired functions** (the exact same function immediately *before* and *after* a vulnerability-fixing commit):

| Configuration ID | Architecture Type | Agents / Nodes | Tool Use | Core Mechanism |
| :--- | :--- | :---: | :---: | :--- |
| **`Baseline1_Direct_LLM`** | Single-Agent Direct | 1 | No | Zero-shot structured Chain-of-Thought (`code_flow_analysis` $\rightarrow$ `mitigation_and_trigger_analysis` $\rightarrow$ `is_vulnerable`). |
| **`Baseline2_LangGraph_SelfRefine_i1`** | Single-Agent + Tool + Self-Reflection | 2 steps | **Yes** (`StaticCodeInspectorTool`) | Extracts structural code facts (crash macros, string interpolation, argument lists, bounds) $\rightarrow$ Drafts audit $\rightarrow$ Self-verifies against raw source lines. |
| **`Config3_LangGraph_ActorCritic_r1`** | 2-Agent Adversarial (GPTLens-style) | 2 (`Actor` + `Critic`) | No | **Actor (Auditor)** searches for concrete exploit paths; **Critic** verifies claims against existing guards/helpers to filter false positives or catch missed flaws. |
| **`Config4_LangGraph_VulTrial_r1`** | 4-Agent Role-Playing Courtroom (VulTrial) | 4 (`Researcher`, `Author`, `Moderator`, `ReviewBoard`) | No | **Security Researcher** prosecutes flaws; **Code Author** defends with `exact_code_quote` evidence; **Moderator** summarizes; **Review Board (Jury)** renders final verdict. |
| **`Config5_LangGraph_Voting_3Agents`** | 3-Agent Homogeneous/Persona Majority Voting | 3 Voters + Aggregator | No | Three specialized auditors (*Memory/Bounds/Assertions*, *Injection/Traversal/APIs*, *Control-Flow/Lifecycle*) vote independently; majority rule determines the verdict. |

---

## 2. Evaluation Metrics

In addition to standard **Accuracy (`Acc %`)**, the benchmark computes the four mutually exclusive **Pairwise Evaluation Metrics** introduced in *PrimeVul* and *VulTrial*:

* **`P-C` $\uparrow$ (Pair-wise Correct %):** The agent **correctly** identifies the pre-commit function as *Vulnerable* (`True`) **AND** the post-commit patched function as *Benign* (`False`). *(Primary metric of true security reasoning).*
* **`P-V` $\downarrow$ (Pair-wise Vulnerable %):** The agent flags **both** the vulnerable and patched versions as *Vulnerable* (False Positive / over-flagging error).
* **`P-B` $\downarrow$ (Pair-wise Benign %):** The agent marks **both** the vulnerable and patched versions as *Benign* (False Negative / missed vulnerability error).
* **`P-R` $\downarrow$ (Pair-wise Reversed %):** The agent marks the vulnerable version as *Benign* and the patched version as *Vulnerable* (inverted reasoning).
* **Efficiency Telemetry:** Tracks **Average LLM Calls**, **Average Total Tokens (Prompt + Completion)**, and **Average Latency (seconds)** per function sample.

---

## 3. Repository Structure

```text
mas-se-eval/
├── configs/
│   └── experiment.yaml                         # Central configuration (models, datasets, LLM parameters, active configs)
├── src/
│   ├── core/
│   │   ├── base_configuration.py               # Abstract base class handling per-sample metric resets and timing
│   │   ├── llm_client.py                       # TrackedLLMClient: structured JSON parsing, schema injection, loop recovery
│   │   ├── prompts.py                          # Shared FUNCTION_SCOPE_PRINCIPLES for fair cross-config evaluation
│   │   └── schemas.py                          # Pydantic schemas enforcing reasoning-before-verdict ordering
│   ├── tools/
│   │   └── code_inspector.py                   # StaticCodeInspectorTool: AST/regex structural fact extractor (C/C++/Python/Java)
│   ├── configurations/
│   │   ├── baseline1_direct.py                 # Config 1: Direct Single-LLM call
│   │   ├── baseline2_langgraph.py              # Config 2: LangGraph Tool + Self-Refinement pipeline
│   │   ├── config3_langgraph_actor_critic.py   # Config 3: LangGraph 2-Agent Actor-Critic debate
│   │   ├── config4_langgraph_vultrial.py       # Config 4: LangGraph 4-Agent VulTrial courtroom debate
│   │   └── config5_langgraph_voting.py         # Config 5: LangGraph 3-Agent Majority Voting ensemble
│   └── evaluation/
│       ├── metrics.py                          # Pairwise (P-C, P-V, P-B, P-R) calculator
│       └── reporter.py                         # JSONL reporter for per-sample metrics and efficiency telemetry
├── prepare_real_datasets.py                    # Automated downloader & atomic pair formatter for SVEN and PrimeVul
├── run_benchmark.py                            # Main execution harness with incremental JSONL checkpointing & caching
├── ollama_colab_setup.ipynb                    # Google Colab GPU server notebook (Ollama + Cloudflare Tunnel)
├── PROJECT_CHALLENGES_AND_SOLUTIONS.md         # Documentation of engineering anomalies and solutions
├── requirements.txt                            # Python dependencies
└── README.md
```
---

## 4. Prerequisites and Installation

### Step 1: Clone the Repository

```bash
git clone https://github.com/<your-username>/<your-repo-name>.git
cd <your-repo-name>
```

### Step 2: Create a Virtual Environment and Install Dependencies

Requires **Python 3.10+**.

**On Windows (PowerShell):**

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
pip install datasets huggingface_hub pyyaml rich
```

**On Linux / macOS:**

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
pip install datasets huggingface_hub pyyaml rich
```

---

## 5. Dataset Preparation (SVEN and PrimeVul)

The repository does not store large raw dataset files in Git. Instead, run the automated dataset builder script. It downloads pinned revisions of SVEN (`bstee615/sven`) and the PrimeVul Paired Test set (`colin/PrimeVul`) directly from Hugging Face Hub, filters out unit-test noise, and builds balanced `.jsonl` pair files inside `data/`:

```bash
python prepare_real_datasets.py
```

This generates:

- `data/sven_val_paired_30.jsonl` (60 functions / 30 vulnerability-fixing pairs in Python, C, and C++)
- `data/primevul_test_paired_30.jsonl` (60 functions / 30 vulnerability-fixing pairs in C and C++)

---

## 6. How to Run the Benchmark (Local PC vs. Google Colab GPU)

You can run the LLM inference backend either locally on your own PC/GPU (**Option A**) or remotely on Google Colab's T4/A100 GPU while executing the Python code locally on your PC (**Option B**).

### Option A: Running Models Locally with Ollama

1. **Install Ollama:** Download and install Ollama from [https://ollama.com](https://ollama.com).

2. **Pull your target model(s):**

   ```bash
   ollama pull qwen2.5-coder:7b
   # Optional for 16GB+ / 24GB+ VRAM systems:
   ollama pull qwen2.5-coder:14b
   ollama pull qwen2.5-coder:32b
   ```

3. **(Optional, for 4GB to 6GB VRAM laptops)** Enable Flash Attention and 8-bit KV cache quantization in PowerShell before starting Ollama:

   ```powershell
   [System.Environment]::SetEnvironmentVariable("OLLAMA_FLASH_ATTENTION", "1", "User")
   [System.Environment]::SetEnvironmentVariable("OLLAMA_KV_CACHE_TYPE", "q8_0", "User")
   ```

4. **Configure `configs/experiment.yaml`:** Ensure `base_url` points to your local Ollama server:

   ```yaml
   llm_settings:
     base_url: "http://localhost:11434/v1"
     temperature: 0.0
     seed: 42
     num_ctx: 8192
     max_tokens: 1024
     timeout_sec: 180.0
   ```

5. **Run the benchmark:**

   ```bash
   python run_benchmark.py --config configs/experiment.yaml
   ```

### Option B: Running Models on Google Colab GPU (`ollama_colab_setup.ipynb`)

If your local machine has limited VRAM, you can host Ollama on a free Google Colab T4 GPU (16 GB VRAM) or a Colab Pro A100 GPU (40/80 GB VRAM) and connect to it from your local IDE (PyCharm / VS Code) via an encrypted Cloudflare Quick Tunnel.

1. **Upload the notebook to Google Colab:**
    - Open [Google Colab](https://colab.research.google.com).
    - Click **File → Upload notebook** and select `ollama_colab_setup.ipynb` from the root of this repository.

2. **Select a GPU runtime:**
    - In Colab, go to **Runtime → Change runtime type** and select **T4 GPU** or **A100 GPU**.

3. **Run the setup cell:**
    - Run the notebook cell. It will install Ollama, pull the required `qwen2.5-coder` models (7b, 14b, 32b), start the Ollama server, and launch a `cloudflared` tunnel.
    - At the bottom of the cell output, copy the generated tunnel URL:

   ```text
   ======================================================================
   COLAB GPU SERVER READY!
   Paste this into configs/experiment.yaml under base_url:
     base_url: "https://random-words-here.trycloudflare.com/v1"
   ======================================================================
   ```

4. **Update `configs/experiment.yaml` locally:** Paste that URL into `configs/experiment.yaml` on your PC:

   ```yaml
   llm_settings:
     base_url: "https://random-words-here.trycloudflare.com/v1"
     temperature: 0.0
     seed: 42
     num_ctx: 8192
     max_tokens: 1024
     timeout_sec: 180.0
   ```

5. **Execute the benchmark from your local terminal:**

   ```bash
   python run_benchmark.py --config configs/experiment.yaml
   ```

---

## 7. Checkpointing, Resuming, and Viewing Results

**Automatic checkpointing and resume:** `run_benchmark.py` writes every completed function evaluation immediately to `<output_dir>/raw_traces.jsonl`. If a run is interrupted, simply re-run:

```bash
python run_benchmark.py --config configs/experiment.yaml
```

Completed `(model, dataset, config, sample_id)` entries are loaded from cache (`[CACHED]`) instantaneously.

**Starting a fresh run:** Pass `--no-resume` to ignore existing checkpoints and overwrite results:

```bash
python run_benchmark.py --config configs/experiment.yaml --no-resume
```

**Outputs generated:**

- `<output_dir>/summary_report.md`: Markdown table of all accuracy, pairwise (P-C, P-V, P-B, P-R), token, and latency metrics.
- `<output_dir>/raw_traces.jsonl`: Complete per-sample JSONL logs containing every agent prompt, intermediate rebuttal, tool output, and final verdict.