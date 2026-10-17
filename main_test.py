import json
from pathlib import Path

from rich.console import Console
from rich.table import Table

from src.configurations.baseline1_direct import Baseline1Direct
from src.configurations.baseline2_langgraph import Baseline2LangGraphReAct
from src.configurations.config3_langgraph_actor_critic import Config3LangGraphActorCritic
from src.configurations.config4_langgraph_vultrial import Config4LangGraphVulTrial
from src.configurations.config5_langgraph_voting import Config5LangGraphVoting
from src.core.llm_client import TrackedLLMClient
from src.core.schemas import TaskSample
from src.evaluation.metrics import compute_benchmark_metrics

console = Console()


def load_samples(filepath: str):
  samples = []
  with open(filepath, "r", encoding="utf-8") as f:
    for line in f:
      if line.strip():
        samples.append(TaskSample(**json.loads(line)))
  return samples


def main():
  # choose the model to be used
  llm_client = TrackedLLMClient(model_name="qwen2.5-coder:7b", temperature=0.0)
  samples = load_samples("data/sample_test.jsonl")

  configurations = [
    Baseline1Direct(llm_client),
    Baseline2LangGraphReAct(llm_client, max_iterations=1),
    Config3LangGraphActorCritic(llm_client, max_rounds=1),
    Config4LangGraphVulTrial(llm_client, max_rounds=1),
    Config5LangGraphVoting(llm_client),
  ]

  all_records = []
  summary_metrics = []

  for config in configurations:
    console.print(f"\n[bold cyan] Running Configuration: [/bold cyan] {config.config_name}")
    config_records = []

    for sample in samples:
      record = config.evaluate_sample(sample)
      config_records.append(record)
      all_records.append(record)

      status = "[bold green]PASS[/bold green]" if record.is_correct else "[bold red]FAIL[/bold red]"
      console.print(
        f"  -> {sample.sample_id}: GT={sample.ground_truth_vulnerable} | "
        f"Pred={record.prediction.is_vulnerable} ({status}) | "
        f"Calls={record.llm_calls_count} | Tokens={record.total_tokens} | "
        f"Latency={record.latency_sec:.2f}s"
      )

    metrics = compute_benchmark_metrics(config_records)
    summary_metrics.append(metrics)

  # Academic Comparison Table
  comp_table = Table(title="\nCS 401 Empirical Evaluation: Single Call vs. LangGraph Agents")
  comp_table.add_column("Configuration", style="cyan", no_wrap=True)
  comp_table.add_column("Acc (%)", justify="right", no_wrap=True)
  comp_table.add_column("P-C ↑ (%)", justify="right", style="bold green", no_wrap=True)
  comp_table.add_column("P-V ↓ (%)", justify="right", no_wrap=True)
  comp_table.add_column("P-B ↓ (%)", justify="right", no_wrap=True)
  comp_table.add_column("P-R ↓ (%)", justify="right", no_wrap=True)
  comp_table.add_column("Avg Calls", justify="right", no_wrap=True)
  comp_table.add_column("Avg Tokens", justify="right", no_wrap=True)
  comp_table.add_column("Avg Latency", justify="right", no_wrap=True)

  for m in summary_metrics:
    comp_table.add_row(
      m["config_name"],
      f"{m['accuracy']:.1f}%",
      f"{m['P-C']:.1f}%",
      f"{m['P-V']:.1f}%",
      f"{m['P-B']:.1f}%",
      f"{m['P-R']:.1f}%",
      str(m["avg_llm_calls"]),
      str(m["avg_tokens"]),
      f"{m['avg_latency_sec']:.2f}s"
    )

  console.print(comp_table)

  Path("results").mkdir(exist_ok=True)
  with open("results/langgraph_comparison.jsonl", "w", encoding="utf-8") as out_f:
    for r in all_records:
      out_f.write(r.model_dump_json() + "\n")
  console.print("\n[dim]All detailed traces saved to results/langgraph_comparison.jsonl[/dim]")


if __name__ == "__main__":
  main()
