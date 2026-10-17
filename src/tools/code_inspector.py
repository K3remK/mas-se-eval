import re
from typing import Dict, Any, List


class StaticCodeInspectorTool:
  name = "static_code_inspector"

  @staticmethod
  def execute(code_snippet: str, language: str = "c") -> Dict[str, Any]:
    lines = [line.strip() for line in code_snippet.splitlines() if line.strip()]
    header = lines[0] if lines else ""
    # Handle Python decorators (@app.route, @staticmethod) before `def`
    for line in lines[:5]:
      if line.startswith("def ") or "(" in line and not line.startswith("@"):
        header = line
        break

    # 1. Accurate Parameter Extraction (strips default values `=False` and `self`)
    param_match = re.search(r'\(([^)]*)\)', header)
    param_str = param_match.group(1) if param_match else ""
    param_names: List[str] = []
    for part in param_str.split(","):
      # Strip default value assignment (e.g. `strict=False` -> `strict`)
      lhs = part.split("=")[0].strip()
      tokens = re.findall(r'[a-zA-Z_][a-zA-Z0-9_]*', lhs)
      if tokens:
        name = tokens[-1]
        if name not in ("self", "cls", "void"):
          param_names.append(name)

    observations: List[str] = []

    # 2. String Interpolation vs. List/Parameterized Calls (Python/C/Java)
    if re.search(r'[\'"][^\'"]*%[sdcr][^\'"]*[\'"]\s*%|(\.format\s*\()', code_snippet):
      observations.append(
        "STRUCTURAL FACT [String Interpolation]: `%` or `.format()` string formatting detected. "
        "Check if formatted string is passed to a shell/CLI command, SQL query, file path, or HTML response without escaping."
      )

    # 3. Subprocess / Command Execution Style
    if re.search(r'shell\s*=\s*True', code_snippet):
      observations.append(
        "STRUCTURAL FACT [Shell Execution]: `shell=True` detected in subprocess call (high risk if combined with string formatting)."
      )
    if re.search(r'\[\s*[\'"][a-zA-Z0-9_\-]+[\'"]\s*,', code_snippet):
      observations.append(
        "STRUCTURAL FACT [Argument List]: Command/query constructed as a discrete list `[cmd, arg, ...]`, which prevents shell token injection."
      )

    # 4. File Path Construction vs. Normalization
    if re.search(r'(os\.path\.join|open\s*\(|QDir|QFile|mkpath)', code_snippet):
      has_norm = re.search(
        r'(basename|replace\s*\(\s*[\'"]\.\./|_absolute_key|validate|is_valid)',
        code_snippet
      )
      if has_norm:
        observations.append(
          "STRUCTURAL FACT [Path Handling]: File/path operation detected WITH explicit path normalization/validation call (`basename`, `replace('../','')`, or validator)."
        )
      else:
        observations.append(
          "STRUCTURAL FACT [Path Handling]: File/path operation detected without visible `basename` or `../` stripping inside this function."
        )

    # 5. C/C++ Crash Macros (CWE-617) vs. Graceful Error Returns
    crash_macros = re.findall(r'\b(DCHECK(?:_EQ|_NE|_LT|_LE|_GT|_GE)?|CHECK(?:_EQ|_NE|_NOTNULL)?|TF_CHECK_OK|llvm_unreachable|assert)\s*\(', code_snippet)
    if crash_macros:
      observations.append(
        f"STRUCTURAL FACT [Crash Macros]: Hard assertion macros {list(set(crash_macros))} detected. "
        "In production C++ (e.g., TensorFlow/LLVM), if untrusted graph/tensor inputs can falsify a CHECK/DCHECK/TF_CHECK_OK instead of returning an error Status, that is a CWE-617 DoS bug."
      )

    # 6. C/C++ Pointer / Iterator Dereferences (`->` or `*`) and Map Lookups (`.find(`)
    if re.search(r'\.find\s*\([^)]+\)\s*->', code_snippet):
      observations.append(
        "STRUCTURAL FACT [Iterator Dereference]: Direct `.find(...)->` chain detected without checking `it != map.end()` first (CWE-476/CWE-125 risk)."
      )

    # 7. Array Indexing & Bounds
    array_accesses = re.findall(r'([a-zA-Z_][a-zA-Z0-9_]*)\s*\[\s*([a-zA-Z_][a-zA-Z0-9_]*)\s*\]', code_snippet)
    for arr_name, idx_var in array_accesses:
      if idx_var in param_names or re.search(rf'\b(?:int|s32|ssize_t|int32_t|int64_t)\s+{idx_var}\b', code_snippet):
        has_lower = re.search(rf'\b{idx_var}\s*(?:>=|>|<)\s*0\b', code_snippet)
        if not has_lower and not re.search(rf'for\s*\([^;]*\b{idx_var}\s*=\s*0\b', code_snippet):
          observations.append(
            f"STRUCTURAL FACT [Signed Indexing]: Array/buffer '{arr_name}' indexed by signed variable '{idx_var}' without a visible `< 0` or `>= 0` lower-bound check."
          )

    # 8. Unbounded C String/Memory Copies & Manual Resource Management
    for func in ["strcpy", "strcat", "sprintf", "gets"]:
      if re.search(rf'\b{func}\s*\(', code_snippet):
        observations.append(
          f"STRUCTURAL FACT [Memory Copy]: Unbounded `{func}()` call detected. Check whether source buffer size can exceed destination buffer size."
        )

    return {
      "language": language,
      "line_count": len(lines),
      "function_parameters": param_names,
      "structural_observations": observations or [
        "No special macro, string-interpolation, or raw-array patterns detected; rely on semantic control-flow and data-flow analysis."
      ],
    }