import json
from pathlib import Path
from typing import Union
from datasets import load_dataset
from huggingface_hub import hf_hub_download
from rich.console import Console
import re

console = Console()

# Pinned revisions on Hugging Face Hub for 100% reproducibility
SVEN_HF_REPO = "bstee615/sven"
PRIMEVUL_HF_REPO = "colin/PrimeVul"
PRIMEVUL_REVISION = "4fd7158322872d711e90f091dbd8673ef32cb1be"


def is_test_function(file_name: str, code_snippet: str) -> bool:
  """CleanVul Heuristic (Section 3 & Appendix A): Excludes unit test files and test_* methods."""
  fname = (file_name or "").lower()
  if "test" in fname:
    return True
  if re.search(r'^\s*(?:def|void|int|bool)\s+test_[a-zA-Z0-9_]*\s*\(', code_snippet, re.MULTILINE):
    return True
  return False

def detect_language(file_name: str, default: str = "c") -> str:
  """Detects language from file extension (.py, .cpp/.cc/.cxx/.hpp, .c/.h)."""
  fname = (file_name or "").lower().strip()
  if fname.endswith(".py"):
    return "python"
  if fname.endswith((".cpp", ".cc", ".cxx", ".hpp", ".hh", ".hxx")):
    return "cpp"
  if fname.endswith((".c", ".h")):
    return "c"
  if fname.endswith(".java"):
    return "java"
  return default


def prepare_sven_paired(
        output_path: Union[str, Path],
        split: str = "val",
        max_pairs: int = 50,
        max_lines: int = 120,
):
  """
  Downloads the SVEN dataset from Hugging Face (bstee615/sven).
  Valid splits are 'train' (720 rows) and 'val' (83 rows).
  """
  output_path = Path(output_path)
  if split not in ("train", "val", "all"):
    raise ValueError(f"Invalid split '{split}' for bstee615/sven. Use 'train', 'val', or 'all'.")

  hf_split = "train+val" if split == "all" else split
  console.print(f"[bold cyan]Loading SVEN ({SVEN_HF_REPO}, split='{hf_split}')...[/bold cyan]")
  ds = load_dataset(SVEN_HF_REPO, split=hf_split)

  samples = []
  pair_count = 0

  for row in ds:
    if pair_count >= max_pairs:
      break

    vuln_code = (row.get("func_src_before") or "").strip()
    benign_code = (row.get("func_src_after") or "").strip()
    cwe = (row.get("vul_type") or "Unknown").strip()
    file_name = (row.get("file_name") or "").strip()

    if is_test_function(file_name, vuln_code):
      continue

    if not vuln_code or not benign_code:
      continue

    # Filter the pair atomically so both versions stay aligned
    if len(vuln_code.splitlines()) > max_lines or len(benign_code.splitlines()) > max_lines:
      continue

    lang = detect_language(file_name, default="c")
    pair_id = f"sven_{split}_pair_{pair_count + 1:04d}"

    samples.append({
      "sample_id": f"{pair_id}_vuln",
      "pair_id": pair_id,
      "dataset": f"sven_{split}",
      "language": lang,
      "cwe_id": cwe,
      "ground_truth_vulnerable": True,
      "code_snippet": vuln_code,
    })
    samples.append({
      "sample_id": f"{pair_id}_benign",
      "pair_id": pair_id,
      "dataset": f"sven_{split}",
      "language": lang,
      "cwe_id": cwe,
      "ground_truth_vulnerable": False,
      "code_snippet": benign_code,
    })
    pair_count += 1

  output_path.parent.mkdir(parents=True, exist_ok=True)
  with open(output_path, "w", encoding="utf-8") as f:
    for s in samples:
      f.write(json.dumps(s) + "\n")

  console.print(
    f"[bold green]Saved {len(samples)} SVEN functions ({pair_count} pairs) to {output_path}[/bold green]"
  )


def prepare_primevul_paired(
        output_path: Union[str, Path],
        raw_jsonl_path: Union[str, Path, None] = None,
        max_pairs: int = 50,
        max_lines: int = 120,
):
  """
  Loads PrimeVul paired test data (primevul_test_paired.jsonl, 870 rows = 435 pairs).
  If raw_jsonl_path is not present locally, it automatically downloads the verified file
  from Hugging Face (colin/PrimeVul @ 4fd7158322872d711e90f091dbd8673ef32cb1be).
  """
  output_path = Path(output_path)

  if raw_jsonl_path is not None and Path(raw_jsonl_path).exists():
    local_file = Path(raw_jsonl_path)
    console.print(f"[bold cyan]Reading local PrimeVul file from {local_file}...[/bold cyan]")
  else:
    console.print(
      f"[bold cyan]Downloading primevul_test_paired.jsonl from Hugging Face "
      f"({PRIMEVUL_HF_REPO} @ {PRIMEVUL_REVISION[:8]})...[/bold cyan]"
    )
    downloaded_path = hf_hub_download(
      repo_id=PRIMEVUL_HF_REPO,
      filename="primevul_test_paired.jsonl",
      repo_type="dataset",
      revision=PRIMEVUL_REVISION,
    )
    local_file = Path(downloaded_path)

  with open(local_file, "r", encoding="utf-8") as f:
    rows = [json.loads(line) for line in f if line.strip()]

  samples = []
  pair_count = 0
  skipped_misaligned = 0

  # Pair strictly by consecutive entries (2*i, 2*i+1) to prevent silent misalignment
  for i in range(0, len(rows) - 1, 2):
    if pair_count >= max_pairs:
      break

    row_a, row_b = rows[i], rows[i + 1]
    targets = {row_a.get("target"), row_b.get("target")}

    # Ensure one is vulnerable (1) and one is benign (0)
    if targets != {0, 1}:
      skipped_misaligned += 1
      continue

    v_item = row_a if row_a.get("target") == 1 else row_b
    b_item = row_b if row_b.get("target") == 0 else row_a

    v_code = (v_item.get("func") or "").strip()
    b_code = (b_item.get("func") or "").strip()

    if not v_code or not b_code:
      continue

    # Filter atomically: both functions in the pair must be <= max_lines
    if len(v_code.splitlines()) > max_lines or len(b_code.splitlines()) > max_lines:
      continue

    file_name = (v_item.get("file_name") or "").strip()
    lang = detect_language(file_name, default="c")

    cwe_raw = v_item.get("cwe")
    if isinstance(cwe_raw, list) and len(cwe_raw) > 0:
      cwe_str = str(cwe_raw[0])
    elif cwe_raw:
      cwe_str = str(cwe_raw)
    else:
      cwe_str = "Unknown"

    pair_id = f"primevul_pair_{pair_count + 1:04d}"

    samples.append({
      "sample_id": f"{pair_id}_vuln",
      "pair_id": pair_id,
      "dataset": "primevul_paired",
      "language": lang,
      "cwe_id": cwe_str,
      "ground_truth_vulnerable": True,
      "code_snippet": v_code,
    })
    samples.append({
      "sample_id": f"{pair_id}_benign",
      "pair_id": pair_id,
      "dataset": "primevul_paired",
      "language": lang,
      "cwe_id": cwe_str,
      "ground_truth_vulnerable": False,
      "code_snippet": b_code,
    })
    pair_count += 1

  output_path.parent.mkdir(parents=True, exist_ok=True)
  with open(output_path, "w", encoding="utf-8") as f:
    for s in samples:
      f.write(json.dumps(s) + "\n")

  console.print(
    f"[bold green]Saved {len(samples)} PrimeVul functions ({pair_count} pairs, "
    f"{skipped_misaligned} misaligned skipped) to {output_path}[/bold green]"
  )


if __name__ == "__main__":
  # 1. Build 30 pairs (60 functions) from SVEN 'val' split
  prepare_sven_paired(
    output_path=Path("data/sven_val_paired_30.jsonl"),
    split="val",
    max_pairs=30,
    max_lines=120,
  )

  # 2. Automatically download & build 30 pairs (60 functions) from PrimeVul Paired Test
  prepare_primevul_paired(
    output_path=Path("data/primevul_test_paired_30.jsonl"),
    max_pairs=30,
    max_lines=120,
  )