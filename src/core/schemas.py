from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any, Literal

class TaskSample(BaseModel):
  sample_id: str
  pair_id: Optional[str] = None
  dataset: str
  language: str
  code_snippet: str
  ground_truth_vulnerable: bool
  cwe_id: Optional[str] = None

class AgentPrediction(BaseModel):
  code_flow_analysis: str = Field(
    description="Step 1: Identify untrusted inputs/state and trace how they reach sensitive operations (memory, pointers, files, commands, queries, assertions, or resource cleanup)."
  )
  mitigation_and_trigger_analysis: str = Field(
    description="Step 2: Examine all guards, validation helpers, and API patterns. Explain whether they safely prevent flaws or how a specific input/state bypasses them."
  )
  vulnerability_type: Optional[str] = Field(
    default=None,
    description="Short name or CWE of the confirmed bug/vulnerability, or None if benign."
  )
  is_vulnerable: bool = Field(
    description="Final verdict: True ONLY if a concrete security vulnerability or functional bug exists in this function, False if benign."
  )
  confidence_score: int = Field(
    ge=1, le=4,
    description="Certainty score from 1 (low) to 4 (high)."
  )

  @property
  def reasoning(self) -> str:
    """Backward-compatible property for reporters and logs."""
    return f"{self.code_flow_analysis} | {self.mitigation_and_trigger_analysis}"

# --- Actor-Critic Schemas (Reasoning First) ---
class ActorReport(BaseModel):
  evidence_and_trigger: str = Field(
    description="Step-by-step trace of how input parameters flow through the code, and the exact input values that trigger a flaw (or why inputs are safely guarded)."
  )
  vulnerability_name: Optional[str] = Field(
    default=None,
    description="Name of the suspected vulnerability/bug, or None if safe."
  )
  suspected_vulnerable: bool = Field(
    description="True if a real bug or vulnerability is suspected, False if the code is safe."
  )

class CriticEvaluation(BaseModel):
  refutation_or_confirmation: str = Field(
    description="Detailed verification of the Actor's report against the exact lines of source code."
  )
  is_claim_valid: bool = Field(
    description="True if the Actor's assessment matches the actual code behavior, False if the Actor hallucinated or missed a check."
  )
  final_verdict: AgentPrediction

# --- VULTRIAL (4-Agent Courtroom) Schemas (Reasoning First) ---
class VulnerabilityClaim(BaseModel):
  vulnerability: str = Field(description="Short name or description of the alleged vulnerability or bug.")
  reason: str = Field(description="Detailed explanation of which line is flawed and what concrete input triggers it.")
  impact: str = Field(description="Potential consequences if this vulnerability were triggered.")

class SecurityResearcherOutput(BaseModel):
  claims: List[VulnerabilityClaim] = Field(
    description="List of identified potential vulnerabilities (empty list if the code is completely safe)."
  )

class AuthorRebuttalItem(BaseModel):
  vulnerability: str = Field(description="The same vulnerability name from the Security Researcher's claim.")
  exact_code_quote: str = Field(
    description="Copy-paste the exact line of code from the snippet that prevents this bug, or write 'NONE' if no such line exists in the snippet."
  )
  reason: str = Field(
    description="Fact-based explanation of whether the quoted line actually blocks the exploit, or an admission that the code lacks protection."
  )
  response_type: Literal["refutation", "mitigation"] = Field(
    description="Choose 'refutation' ONLY if `exact_code_quote` is a real sanitization/validation/guard line in the snippet. If `exact_code_quote` is 'NONE', you MUST choose 'mitigation'."
  )

class CodeAuthorOutput(BaseModel):
  responses: List[AuthorRebuttalItem]

class ModeratorSummary(BaseModel):
  security_researcher_summary: str = Field(
    description="Concise summary of the vulnerabilities and trigger conditions presented by the Security Researcher."
  )
  author_summary: str = Field(
    description="Concise summary of the Code Author's response, explicitly stating whether `exact_code_quote` actually exists in the code snippet and truly blocks the bug."
  )

class JuryVerdictItem(BaseModel):
  vulnerability: str = Field(description="The same vulnerability name as given by the Security Researcher.")
  reason: str = Field(
    description="Step-by-step independent verification against the raw source code: check if the Author's `exact_code_quote` is genuinely in the code and actually prevents the bug."
  )
  code_has_protection: bool = Field(
    description="Set to true ONLY if you verified in `reason` that the code snippet literally contains a real guard, sanitization, or safe API that prevents this bug. Otherwise false."
  )
  is_vulnerable_verdict: bool = Field(
    description="Set to true if `code_has_protection` is false and the bug is triggerable; set to false if `code_has_protection` is true."
  )
  severity: Literal["low", "medium", "high", "none"] = Field(
    description="Set to 'high' or 'medium' when `is_vulnerable_verdict` is true; set to 'none' when `is_vulnerable_verdict` is false."
  )

class ReviewBoardOutput(BaseModel):
  verdicts: List[JuryVerdictItem]

class BenchmarkRecord(BaseModel):
  sample_id: str
  pair_id: Optional[str] = None
  config_name: str
  model_name: str
  prediction: AgentPrediction
  ground_truth: bool
  is_correct: bool
  prompt_tokens: int
  completion_tokens: int
  total_tokens: int
  latency_sec: float
  llm_calls_count: int
  raw_messages: List[Dict[str, Any]] = []