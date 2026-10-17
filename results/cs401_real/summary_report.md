# Empirical Evaluation Results

| Model | Dataset | Configuration | Acc (%) | P-C ↑ (%) | P-V ↓ (%) | P-B ↓ (%) | P-R ↓ (%) | Avg Calls | Avg Tokens | Avg Latency (s) |
| :--- | :--- | :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| `qwen2.5-coder:7b` | `sven_real_pairs` | **Baseline1_Direct_LLM** | 66.7% | **43.3%** | 36.7% | 10.0% | 10.0% | 1.0 | 1247.8 | 1.65s |
| `qwen2.5-coder:7b` | `sven_real_pairs` | **Baseline2_LangGraph_SelfRefine_i1** | 68.3% | **43.3%** | 40.0% | 10.0% | 6.7% | 2.0 | 2614.5 | 2.71s |
| `qwen2.5-coder:7b` | `sven_real_pairs` | **Config3_LangGraph_ActorCritic_r1** | 53.3% | **16.7%** | 56.7% | 16.7% | 10.0% | 2.0 | 2778.1 | 3.27s |
| `qwen2.5-coder:7b` | `sven_real_pairs` | **Config4_LangGraph_VulTrial_r1** | 75.0% | **53.3%** | 23.3% | 20.0% | 3.3% | 4.0 | 4793.3 | 3.82s |
| `qwen2.5-coder:7b` | `sven_real_pairs` | **Config5_LangGraph_Voting_3Agents** | 66.7% | **36.7%** | 43.3% | 16.7% | 3.3% | 3.0 | 3781.8 | 4.85s |
| `qwen2.5-coder:7b` | `primevul_real_pairs` | **Baseline1_Direct_LLM** | 45.0% | **3.3%** | 16.7% | 66.7% | 13.3% | 1.0 | 1660.0 | 2.12s |
| `qwen2.5-coder:7b` | `primevul_real_pairs` | **Baseline2_LangGraph_SelfRefine_i1** | 63.3% | **26.7%** | 33.3% | 40.0% | 0.0% | 2.0 | 3446.0 | 3.43s |
| `qwen2.5-coder:7b` | `primevul_real_pairs` | **Config3_LangGraph_ActorCritic_r1** | 51.7% | **10.0%** | 20.0% | 63.3% | 6.7% | 2.0 | 3542.0 | 3.91s |
| `qwen2.5-coder:7b` | `primevul_real_pairs` | **Config4_LangGraph_VulTrial_r1** | 51.7% | **3.3%** | 6.7% | 90.0% | 0.0% | 4.0 | 5709.3 | 2.89s |
| `qwen2.5-coder:7b` | `primevul_real_pairs` | **Config5_LangGraph_Voting_3Agents** | 50.0% | **10.0%** | 20.0% | 60.0% | 10.0% | 3.0 | 5163.3 | 6.81s |
| `qwen2.5-coder:14b` | `sven_real_pairs` | **Baseline1_Direct_LLM** | 65.0% | **33.3%** | 43.3% | 20.0% | 3.3% | 1.0 | 1261.7 | 3.18s |
| `qwen2.5-coder:14b` | `sven_real_pairs` | **Baseline2_LangGraph_SelfRefine_i1** | 73.3% | **53.3%** | 26.7% | 13.3% | 6.7% | 2.0 | 2667.3 | 5.44s |
| `qwen2.5-coder:14b` | `sven_real_pairs` | **Config3_LangGraph_ActorCritic_r1** | 75.0% | **50.0%** | 16.7% | 33.3% | 0.0% | 2.0 | 2844.7 | 6.71s |
| `qwen2.5-coder:14b` | `sven_real_pairs` | **Config4_LangGraph_VulTrial_r1** | 70.0% | **46.7%** | 23.3% | 23.3% | 6.7% | 4.0 | 4614.0 | 6.28s |
| `qwen2.5-coder:14b` | `sven_real_pairs` | **Config5_LangGraph_Voting_3Agents** | 63.3% | **30.0%** | 53.3% | 13.3% | 3.3% | 3.0 | 3849.8 | 9.87s |
| `qwen2.5-coder:14b` | `primevul_real_pairs` | **Baseline1_Direct_LLM** | 48.3% | **3.3%** | 10.0% | 80.0% | 6.7% | 1.0 | 1660.8 | 3.89s |
| `qwen2.5-coder:14b` | `primevul_real_pairs` | **Baseline2_LangGraph_SelfRefine_i1** | 56.7% | **23.3%** | 26.7% | 40.0% | 10.0% | 2.0 | 3415.1 | 6.20s |
| `qwen2.5-coder:14b` | `primevul_real_pairs` | **Config3_LangGraph_ActorCritic_r1** | 51.7% | **3.3%** | 3.3% | 93.3% | 0.0% | 2.0 | 3560.0 | 7.17s |
| `qwen2.5-coder:14b` | `primevul_real_pairs` | **Config4_LangGraph_VulTrial_r1** | 50.0% | **0.0%** | 0.0% | 100.0% | 0.0% | 4.0 | 5576.1 | 4.69s |
| `qwen2.5-coder:14b` | `primevul_real_pairs` | **Config5_LangGraph_Voting_3Agents** | 50.0% | **3.3%** | 6.7% | 86.7% | 3.3% | 3.0 | 5153.2 | 13.20s |
| `qwen2.5-coder:32b` | `sven_real_pairs` | **Baseline1_Direct_LLM** | 68.3% | **43.3%** | 36.7% | 13.3% | 6.7% | 1.0 | 1262.7 | 5.99s |
| `qwen2.5-coder:32b` | `sven_real_pairs` | **Baseline2_LangGraph_SelfRefine_i1** | 76.7% | **56.7%** | 23.3% | 16.7% | 3.3% | 2.0 | 2633.1 | 9.42s |
| `qwen2.5-coder:32b` | `sven_real_pairs` | **Config3_LangGraph_ActorCritic_r1** | 75.0% | **53.3%** | 23.3% | 20.0% | 3.3% | 2.0 | 2761.2 | 10.80s |
| `qwen2.5-coder:32b` | `sven_real_pairs` | **Config4_LangGraph_VulTrial_r1** | 66.7% | **36.7%** | 46.7% | 13.3% | 3.3% | 4.0 | 4619.2 | 11.49s |
| `qwen2.5-coder:32b` | `sven_real_pairs` | **Config5_LangGraph_Voting_3Agents** | 60.0% | **30.0%** | 53.3% | 6.7% | 10.0% | 3.0 | 3856.5 | 18.26s |
| `qwen2.5-coder:32b` | `primevul_real_pairs` | **Baseline1_Direct_LLM** | 45.0% | **3.3%** | 10.0% | 73.3% | 13.3% | 1.0 | 1700.4 | 8.31s |
| `qwen2.5-coder:32b` | `primevul_real_pairs` | **Baseline2_LangGraph_SelfRefine_i1** | 56.7% | **16.7%** | 20.0% | 60.0% | 3.3% | 2.0 | 3471.4 | 12.47s |
| `qwen2.5-coder:32b` | `primevul_real_pairs` | **Config3_LangGraph_ActorCritic_r1** | 46.7% | **0.0%** | 0.0% | 93.3% | 6.7% | 2.0 | 3548.7 | 12.88s |
| `qwen2.5-coder:32b` | `primevul_real_pairs` | **Config4_LangGraph_VulTrial_r1** | 53.3% | **6.7%** | 3.3% | 90.0% | 0.0% | 4.0 | 5894.0 | 15.56s |
| `qwen2.5-coder:32b` | `primevul_real_pairs` | **Config5_LangGraph_Voting_3Agents** | 48.3% | **3.3%** | 26.7% | 63.3% | 6.7% | 3.0 | 5181.0 | 25.81s |
