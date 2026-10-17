# Technical Challenges, Anomalies, and Engineering Solutions

During the development and empirical evaluation of our Multi-Agent System (MAS) vulnerability detection benchmark (`mas-se-eval`), we encountered eight critical engineering and methodological challenges. Below is a systematic breakdown of each anomaly, its root cause in LLM/agent mechanics, and the general architectural solution implemented to resolve it.

---

## Summary Matrix of Anomalies & Resolutions

| # | Anomaly / Challenge | Phase Encountered | Root Cause | Architectural Solution | Empirical Impact |
| :- | :--- | :--- | :--- | :--- | :--- |
| **1** | **Polarity Inversion (`P-R` Spike)** | Synthetic & Early Real Runs | Boolean verdict fields placed *before* reasoning fields in Pydantic schemas forced premature token commitment. | Reordered all Pydantic schemas (`AgentPrediction`, `JuryVerdictItem`) so step-by-step reasoning precedes boolean verdicts. | Eliminated logical contradictions; reduced `P-R` to `0.0%–10.0%`. |
| **2** | **Self-Refinement Code Hallucination** | `Baseline 2` (Self-Refine) | Model interpreted "self-refine" as a code-patching task and evaluated its own rewritten code instead of the input snippet. | Reframed `Baseline 2` prompts into a two-stage static audit & verification workflow prohibiting code generation. | Achieved `76.7%` Acc and `56.7% P-C` on SVEN (`32b`). |
| **3** | **Dataset Hub & Pairing Misalignment** | Real Dataset Preparation | Unverified Hugging Face repo ID (`sri-lab/sven`) and independent list filtering (`zip(vuln, benign)`) caused silent pair drift. | Verified exact Hub repos (`bstee615/sven`, `colin/PrimeVul`), pinned git commit hashes, and enforced atomic consecutive pairing `(2*i, 2*i+1)`. | Guaranteed 100% pre-/post-commit alignment across all 60 pairs. |
| **4** | **Context-Shift Death Spiral & 10-Min Freezes** | Local `7b` Inference on 4GB VRAM | Ollama's GBNF grammar blocked `<|im_end|>` inside open JSON strings; exceeding `num_ctx=4096` evicted opening JSON tokens. | Injected explicit Pydantic JSON schemas into system prompts, added a `1.05` micro `repeat_penalty`, and built a 2-attempt loop-breaker in `TrackedLLMClient`. | 0 infinite loops across 1,800 evaluations (`Calls` = exact integers). |
| **5** | **"Colon Cutoff" Premature Termination** | `Baseline 1` on SVEN (`P-C = 0%`) | `qwen2.5-coder:7b` wrote `"Here is a step-by-step analysis:"`, and JSON grammar closed the string at the colon `:`, defaulting `is_vulnerable` to `false`. | Replaced single `reasoning` string with a mandatory 2-step schema: `code_flow_analysis` + `mitigation_and_trigger_analysis`. | Restored `Baseline 1` `P-C` from `0.0%` to `43.3%` on SVEN. |
| **6** | **Residual Prompt Overfitting ("4-Item Checklist Trap")** | First Real Dataset Run | Early prompts listed 4 synthetic examples (array bounds, `strcpy`, SQL, div-by-zero); 7B agents ignored CWE-022/078/617 bugs outside that list. | Removed all toy examples and centralized general static analysis rules in `src/core/prompts.py` (`FUNCTION_SCOPE_PRINCIPLES`). | Enabled zero-shot generalization across C, C++, and Python CWEs. |
| **7** | **Defense Hallucination & Prompt Copy-Pasting** | `Config 4` (VulTrial) on SVEN | Code Author agent copied example helper names (e.g., `os.path.basename`) from the system prompt and falsely claimed they existed in vulnerable code. | Removed all function-name examples from prompts and added a mandatory `exact_code_quote` field in `AuthorRebuttalItem`. | Stopped hallucinated refutations; boosted `7b` VulTrial to `75.0%` Acc (`53.3% P-C`). |
| **8** | **Token Accounting Loss on Truncated Calls** | `TrackedLLMClient` Telemetry | `openai.LengthFinishReasonError` raised an exception before token usage counters were incremented, under-reporting tokens on retried calls. | Extracted `err.completion.usage` inside the `except` handler to record tokens burned during failed attempts. | 100% accurate token and cost telemetry across all runs. |

---

## Detailed Breakdown of Challenges

### 1. Schema Field Ordering & Polarity Inversion
* **The Problem:** In early iterations of `Config 4 (VulTrial)` and `Config 3 (Actor-Critic)`, the Review Board / Jury frequently wrote reasoning confirming a vulnerability, yet output `is_vulnerable: false` (or vice versa), causing high Pairwise Reversed (`P-R`) error rates.
* **Root Cause:** Autoregressive LLMs generate tokens sequentially from left to right. In `JuryVerdictItem`, `code_has_protection: bool` was defined *before* `reason: str`. Under constrained decoding, the LLM was forced to commit to `true` or `false` on its first token before performing Chain-of-Thought reasoning, and subsequently rationalized its premature boolean choice.
* **The Fix:** We restructured every Pydantic model in `src/core/schemas.py` (`AgentPrediction`, `ActorReport`, `CriticEvaluation`, `AuthorRebuttalItem`, `JuryVerdictItem`) so that analytical text fields (`code_flow_analysis`, `mitigation_and_trigger_analysis`, `exact_code_quote`, `reason`) are generated **before** any boolean verdict (`code_has_protection`, `is_vulnerable`).

### 2. The "Context-Shift Death Spiral" Under Constrained JSON Decoding
* **The Problem:** During local execution of `qwen2.5-coder:7b` on an NVIDIA GTX 1650 (4 GB VRAM), inference occasionally hung for over 10 minutes on long C++ functions (`sven_val_pair_0002_vuln`), generating 4,300+ tokens for a single agent call.
* **Root Cause:** Unlike cloud APIs, Ollama compiles Pydantic schemas into a GBNF grammar mask without injecting the JSON schema definition into the system prompt. When the 7B model finished its thought inside a JSON string field and attempted to emit `<|im_end|>`, the GBNF mask blocked the stop token because trailing required JSON fields had not yet been generated. With greedy decoding (`temperature=0.0`, `repeat_penalty=1.0`), the model entered an infinite phrase-repetition loop. Once `prompt + generated_tokens` exceeded `n_ctx = 4096`, `llama.cpp` triggered a `slot context shift` (`n_discard = 2045`), evicting the system prompt and opening `{` from the KV cache—making termination impossible.
* **The Fix:**
    1. **Schema Visibility:** `TrackedLLMClient.generate_structured()` automatically appends `response_model.model_json_schema()` to the system prompt so the model sees the required JSON keys ahead of time.
    2. **Hardware-Agnostic Retry Architecture:** Attempt 1 runs with pure scientific settings (`temperature=0.0`, `repeat_penalty=1.05`) and configurable `num_ctx`/`max_tokens` in `experiment.yaml`. Only if Attempt 1 hits `LengthFinishReasonError` or `APITimeoutError` does Attempt 2 engage loop-breaker parameters (`temperature=0.2`, `repeat_penalty=1.15`, and a brevity instruction), falling back to a safe default object if Attempt 2 also fails.
    3. **Cloud GPU Offloading:** Created a seamless Google Colab A100/T4 setup using `cloudflared` tunnels, reducing per-sample multi-agent latency from ~110s to ~3.5s.

### 3. "Colon Cutoff" Syndrome in Structured Output
* **The Problem:** When moving to the real SVEN benchmark, `Baseline1_Direct_LLM` suddenly predicted `False` on 100% of samples (`P-B = 100%`, `P-C = 0%`).
* **Root Cause:** Inspection of `raw_traces.jsonl` revealed that `qwen2.5-coder:7b` began its `reasoning` string with `"The provided function appears well-structured. Here is a step-by-step analysis:"`. In standard chat mode, the model would follow the colon `:` with `\n1. ...`. However, inside a single JSON string with a prohibition on unescaped newlines, the model immediately closed the string `",` right after the colon `:` and defaulted `is_vulnerable` to `false` without ever analyzing the code.
* **The Fix:** We replaced the single `reasoning` field in `AgentPrediction` with two distinct, mandatory analytical stages: `code_flow_analysis` (tracing inputs to sensitive sinks) and `mitigation_and_trigger_analysis` (evaluating guards and exploit triggers), exposing a backward-compatible `@property def reasoning` for reporting.

### 4. Adversarial Hallucination & The "Patch Critique" Paradox in Multi-Agent Debate
* **The Problem:** In `Config 4 (VulTrial)`, the Code Author (Defense Agent) successfully tricked the Moderator and Jury into acquitting vulnerable functions while convicting benign patched functions.
* **Root Cause:**
    1. **Prompt Copy-Pasting:** When `FUNCTION_SCOPE_PRINCIPLES` listed example sanitization functions (such as `os.path.basename`), the 7B Code Author copied `os.path.basename` directly out of the system prompt and claimed the vulnerable function called it.
    2. **Existence vs. Sanitization Confusion:** On path traversal bugs, the Code Author argued that `os.path.isdir()` or `QFileInfo` sanitized paths.
    3. **The Patch Critique Paradox:** On benign patched functions where developers added comments like `// remove ".." from path` and `qfile_name.replace("../", "")`, the Prosecutor attacked the patch as "incomplete against absolute paths," and the Author agreed.
* **The Fix:**
    1. Removed all specific function/API names from `FUNCTION_SCOPE_PRINCIPLES` so agents could not copy-paste them into hallucinations.
    2. Added `exact_code_quote: str` as the first required field of `AuthorRebuttalItem`, forcing the Code Author to copy-paste literal lines from the snippet (or write `"NONE"`).
    3. Explicitly distinguished routine filesystem queries (`isdir`/`isfile`) from active sanitization/parameterization in `FUNCTION_SCOPE_PRINCIPLES`.

### 5. Dataset Hygiene & Atomic Pair Alignment (`SVEN` & `PrimeVul`)
* **The Problem:** Filtering functions by line length (`<= 120` lines) after splitting a dataset into separate `vuln_items` and `benign_items` lists silently misaligns pairs whenever one version of a function is 119 lines and its counterpart is 121 lines. Additionally, raw commit datasets contain unit test methods (`def test_*`) modified alongside security fixes (shown by the *CleanVul* paper to account for 41.2% of false-positive label noise).
* **The Fix:** Rewrote `prepare_real_datasets.py` to iterate over paired datasets in strict atomic steps of 2, apply line-length and target-label checks (`{0, 1}`) to both functions simultaneously, and filter out unit test files/functions (`is_test_function`) per the *CleanVul* heuristic.