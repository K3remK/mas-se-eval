import argparse
import json
from pathlib import Path

import yaml
from rich.console import Console

from src.configurations import build_configuration
from src.core.llm_client import TrackedLLMClient
from src.core.schemas import TaskSample, BenchmarkRecord
from src.evaluation.metrics import compute_benchmark_metrics
from src.evaluation.reporter import generate_reports

console = Console()

def load_samples(filepath: str, max_samples: int = None):
  samples = []
  with open(filepath, "r", encoding="utf-8") as f:
    for line in f:
      if line.strip():
        samples.append(TaskSample(**json.loads(line)))
  if max_samples:
    return samples[:max_samples]
  return samples


def load_completed_traces(trace_file: Path):
  """Loads the completed (model, dataset, config, sample_id) records (Checkpointing)."""
  completed = {}
  if not trace_file.exists():
    return completed
  with open(trace_file, "r", encoding="utf-8") as f:
    for line in f:
      if line.strip():
        data = json.loads(line)
        record = BenchmarkRecord(**data)
        key = (record.model_name, record.config_name, record.sample_id)
        completed[key] = record
  return completed


def main():
  parser = argparse.ArgumentParser(description="Multi-Agent Benchmark Runner")
  parser.add_argument("--config", type=str, default="configs/experiment.yaml", help="Path to YAML config file")
  parser.add_argument("--no-resume", action="store_true", help="Ignore existing checkpoints and run from scratch")
  args = parser.parse_args()

  with open(args.config, "r", encoding="utf-8") as f:
    exp_cfg = yaml.safe_load(f)

  output_dir = Path(exp_cfg.get("output_dir", "results/default_run"))
  output_dir.mkdir(parents=True, exist_ok=True)
  trace_file = output_dir / "raw_traces.jsonl"

  if args.no_resume and trace_file.exists():
    trace_file.unlink()

  completed_cache = load_completed_traces(trace_file)
  llm_settings = exp_cfg.get("llm_settings", {})
  summary_rows = []

  for model_name in exp_cfg["models"]:
    llm_client = TrackedLLMClient(
      model_name=model_name,
      base_url=llm_settings.get("base_url", "http://localhost:11434/v1"),
      temperature=llm_settings.get("temperature", 0.0),
      seed=llm_settings.get("seed", 42),
      num_ctx=llm_settings.get("num_ctx", 8192),
      max_tokens=llm_settings.get("max_tokens", 1024),
      timeout_sec=llm_settings.get("timeout_sec", 180.0),
    )

    for ds_cfg in exp_cfg["datasets"]:
      ds_name = ds_cfg["name"]
      samples = load_samples(ds_cfg["path"], max_samples=ds_cfg.get("max_samples", None))

      for cfg_item in exp_cfg["configurations"]:
        if not cfg_item.get("enabled", True):
          continue

        agent_config = build_configuration(
          name=cfg_item["id"],
          llm_client=llm_client,
          params=cfg_item.get("params", {})
        )

        console.print(
          f"\n[bold cyan]==> Model:[/bold cyan] {model_name} |"
          f"[bold cyan] Dataset:[/bold cyan] {ds_name} |"
          f"[bold green] Config:[/bold green] {agent_config.config_name}"
        )

        config_records = []

        for sample in samples:
          cache_key = (model_name, agent_config.config_name, sample.sample_id)
          if cache_key in completed_cache:
            record = completed_cache[cache_key]
            console.print(f"  [dim][CACHED] {sample.sample_id}: Pred={record.prediction.is_vulnerable}[/dim]")
          else:
            record = agent_config.evaluate_sample(sample)
            # Write to disk immediately
            with open(trace_file, "a", encoding="utf-8") as f:
              f.write(record.model_dump_json() + "\n")

            status = "[bold green]PASS[/bold green]" if record.is_correct else "[bold red]FAIL[/bold red]"
            console.print(
              f"  -> {sample.sample_id}: GT={sample.ground_truth_vulnerable} | "
              f"Pred={record.prediction.is_vulnerable} ({status}) | "
              f"Calls={record.llm_calls_count} | Tokens={record.total_tokens} | "
              f"Time={record.latency_sec:.2f}s"
            )

          config_records.append(record)

        metrics = compute_benchmark_metrics(config_records)
        metrics["dataset_name"] = ds_name
        summary_rows.append(metrics)

  generate_reports(summary_rows, output_dir)


if __name__ == "__main__":
  main()
