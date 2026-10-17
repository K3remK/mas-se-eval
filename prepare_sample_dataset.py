import json
from pathlib import Path

SAMPLES = [
  # PAIR 1: C - Out-of-bounds Read via Negative Index (CWE-125)
  {
    "sample_id": "c_pair1_vuln", "pair_id": "pair_c_01", "dataset": "primevul_subset", "language": "c", "cwe_id": "CWE-125",
    "ground_truth_vulnerable": True,
    "code_snippet": "int get_element(int *arr, int len, int index) {\n    if (arr == NULL) return -1;\n    if (index < len) {\n        return arr[index];\n    }\n    return -1;\n}"
  },
  {
    "sample_id": "c_pair1_benign", "pair_id": "pair_c_01", "dataset": "primevul_subset", "language": "c", "cwe_id": "CWE-125",
    "ground_truth_vulnerable": False,
    "code_snippet": "int get_element(int *arr, int len, int index) {\n    if (arr == NULL) return -1;\n    if (index >= 0 && index < len) {\n        return arr[index];\n    }\n    return -1;\n}"
  },
  # PAIR 2: C - Classic Buffer Overflow via strcpy (CWE-120)
  {
    "sample_id": "c_pair2_vuln", "pair_id": "pair_c_02", "dataset": "primevul_subset", "language": "c", "cwe_id": "CWE-120",
    "ground_truth_vulnerable": True,
    "code_snippet": "void copy_username(char *input) {\n    if (input == NULL) return;\n    char buf[16];\n    strcpy(buf, input);\n}"
  },
  {
    "sample_id": "c_pair2_benign", "pair_id": "pair_c_02", "dataset": "primevul_subset", "language": "c", "cwe_id": "CWE-120",
    "ground_truth_vulnerable": False,
    "code_snippet": "void copy_username(char *input) {\n    if (input == NULL) return;\n    char buf[16];\n    strncpy(buf, input, sizeof(buf) - 1);\n    buf[sizeof(buf) - 1] = '\\0';\n}"
  },
  # PAIR 3: Java - SQL Injection vs PreparedStatement (CWE-89)
  {
    "sample_id": "java_pair3_vuln", "pair_id": "pair_java_03", "dataset": "cleanvul_subset", "language": "java", "cwe_id": "CWE-89",
    "ground_truth_vulnerable": True,
    "code_snippet": "public ResultSet getUser(Connection conn, String username) throws SQLException {\n    if (conn == null || username == null) return null;\n    Statement stmt = conn.createStatement();\n    String query = \"SELECT * FROM users WHERE username = '\" + username + \"'\";\n    return stmt.executeQuery(query);\n}"
  },
  {
    "sample_id": "java_pair3_benign", "pair_id": "pair_java_03", "dataset": "cleanvul_subset", "language": "java", "cwe_id": "CWE-89",
    "ground_truth_vulnerable": False,
    "code_snippet": "public ResultSet getUser(Connection conn, String username) throws SQLException {\n    if (conn == null || username == null) return null;\n    String query = \"SELECT * FROM users WHERE username = ?\";\n    PreparedStatement pstmt = conn.prepareStatement(query);\n    pstmt.setString(1, username);\n    return pstmt.executeQuery();\n}"
  },
  # PAIR 4: Java - Unchecked Division by Zero & Array Bounds (CWE-369)
  {
    "sample_id": "java_pair4_vuln", "pair_id": "pair_java_04", "dataset": "defects4j_subset", "language": "java", "cwe_id": "CWE-369",
    "ground_truth_vulnerable": True,
    "code_snippet": "public double computeAverage(int[] scores, int count) {\n    int sum = 0;\n    for (int i = 0; i < count; i++) {\n        sum += scores[i];\n    }\n    return (double) sum / count;\n}"
  },
  {
    "sample_id": "java_pair4_benign", "pair_id": "pair_java_04", "dataset": "defects4j_subset", "language": "java", "cwe_id": "CWE-369",
    "ground_truth_vulnerable": False,
    "code_snippet": "public double computeAverage(int[] scores, int count) {\n    if (scores == null || count <= 0 || count > scores.length) {\n        return 0.0;\n    }\n    int sum = 0;\n    for (int i = 0; i < count; i++) {\n        sum += scores[i];\n    }\n    return (double) sum / count;\n}"
  }
]

def main():
  Path("data").mkdir(exist_ok=True)
  out_path = Path("data/benchmark_pairs.jsonl")
  with open(out_path, "w", encoding="utf-8") as f:
    for item in SAMPLES:
      f.write(json.dumps(item) + "\n")
  print(f"Updated {len(SAMPLES)} clean benchmark samples at {out_path}")

if __name__ == "__main__":
  main()