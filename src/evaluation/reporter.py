import csv
from pathlib import Path
from typing import List, Dict, Any

from rich.console import Console
from rich.table import Table

console = Console()


def generate_reports(summary_rows: List[Dict[str, Any]], output_dir: Path):
  if not summary_rows:
    return

  output_dir.mkdir(parents=True, exist_ok=True)

  # Terminal Table
  table = Table(title="\nFinal Empirical Evaluation Summary")
  columns = [
    ("Model", "magenta"),
    ("Dataset", "yellow"),
    ("Config", "right"),
    ("Acc (%)", "right"),
    ("P-C ↑ (%)", "bold green"),
    ("P-V ↓ (%)", "right"),
    ("P-B ↓ (%)", "right"),
    ("P-R ↓ (%)", "right"),
    ("Calls", "right"),
    ("Avg Tokens", "right"),
    ("Avg Latency", "right"),
  ]
  for col_name, style in columns:
    table.add_column(col_name, style=style if style != "right" else None,
                     justify="right" if style in ["right", "bold green"] else "left", no_wrap=True)

  for r in summary_rows:
    table.add_row(
      r["model_name"],
      r["dataset_name"],
      r["config_name"],
      f"{r['accuracy']:.1f}%",
      f"{r['P-C']:.1f}%",
      f"{r['P-V']:.1f}%",
      f"{r['P-B']:.1f}%",
      f"{r['P-R']:.1f}%",
      str(r["avg_llm_calls"]),
      str(r["avg_tokens"]),
      f"{r['avg_latency_sec']:.2f}s"
    )

  console.print(table)

  # CSV record (for statistical analysis and graphs
  csv_path = output_dir / "summary_metrics.cvs"
  fieldnames = list(summary_rows[0].keys())
  with open(csv_path, "w", encoding="utf-8") as csv_file:
    writer = csv.DictWriter(csv_file, fieldnames=fieldnames)
    writer.writeheader()
    writer.writerows(summary_rows)

  # Markdown Report Record
  md_path = output_dir / "summary_report.md"
  with open(md_path, "w", encoding="utf-8") as md_file:
    md_file.write("# Empirical Evaluation Results\n\n")
    md_file.write(
      "| Model | Dataset | Configuration | Acc (%) | P-C ↑ (%) | P-V ↓ (%) | P-B ↓ (%) | P-R ↓ (%) | Avg Calls | Avg Tokens | Avg Latency (s) |\n")
    md_file.write("| :--- | :--- | :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |\n")
    for r in summary_rows:
      md_file.write(
        f"| `{r['model_name']}` | `{r['dataset_name']}` | **{r['config_name']}** | "
        f"{r['accuracy']:.1f}% | **{r['P-C']:.1f}%** | {r['P-V']:.1f}% | "
        f"{r['P-B']:.1f}% | {r['P-R']:.1f}% | {r['avg_llm_calls']} | "
        f"{r['avg_tokens']} | {r['avg_latency_sec']:.2f}s |\n"
      )

  console.print(f"\n[bold green]Reports saved:[/bold green]\n  - CSV: {csv_path}\n  - Markdown: {md_path}")
