from collections import defaultdict
from typing import List, Dict, Any

from src.core.schemas import BenchmarkRecord


def compute_benchmark_metrics(records: List[BenchmarkRecord]) -> Dict[str, Any]:
  total = len(records)
  if total == 0:
    return {}

  correct_count = sum(1 for r in records if r.is_correct)
  accuracy = (correct_count / total) * 100.0

  total_tokens = sum(r.total_tokens for r in records)
  avg_tokens = total_tokens / total
  avg_latency = sum(r.latency_sec for r in records) / total
  avg_calls = sum(r.llm_calls_count for r in records) / total

  # Pair-wise Metrikler (PrimeVul / VULTRIAL standardı: P-C, P-V, P-B, P-R)
  pairs = defaultdict(dict)
  for r in records:
    if r.pair_id:
      key = "vuln" if r.ground_truth else "benign"
      pairs[r.pair_id][key] = r.prediction.is_vulnerable

  pc = pv = pb = pr = 0
  valid_pairs = 0
  for pid, pair_data in pairs.items():
    if "vuln" in pair_data and "benign" in pair_data:
      valid_pairs += 1
      pred_v = pair_data["vuln"]
      pred_b = pair_data["benign"]

      if pred_v is True and pred_b is False:
        pc += 1  # Pair-wise Correct
      elif pred_v is True and pred_b is True:
        pv += 1  # Pair-wise Vulnerable
      elif pred_v is False and pred_b is False:
        pb += 1  # Pair-wise Benign
      elif pred_v is False and pred_b is True:
        pr += 1  # Pair-wise Reversed

  return {
    "config_name": records[0].config_name,
    "model_name": records[0].model_name,
    "accuracy": round(accuracy, 2),
    "P-C": round((pc / valid_pairs) * 100, 2) if valid_pairs else 0.0,
    "P-V": round((pv / valid_pairs) * 100, 2) if valid_pairs else 0.0,
    "P-B": round((pb / valid_pairs) * 100, 2) if valid_pairs else 0.0,
    "P-R": round((pr / valid_pairs) * 100, 2) if valid_pairs else 0.0,
    "avg_tokens": round(avg_tokens, 1),
    "avg_latency_sec": round(avg_latency, 2),
    "avg_llm_calls": round(avg_calls, 1)
  }
