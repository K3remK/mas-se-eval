from typing import TypedDict, Optional
from langgraph.graph import StateGraph, START, END

from src.core.base_configuration import BaseAgentConfiguration
from src.core.prompts import FUNCTION_SCOPE_PRINCIPLES
from src.core.schemas import (
  TaskSample, SecurityResearcherOutput, CodeAuthorOutput,
  ReviewBoardOutput, ModeratorSummary, AgentPrediction
)

class VulTrialState(TypedDict):
  sample: TaskSample
  researcher_out: Optional[SecurityResearcherOutput]
  author_out: Optional[CodeAuthorOutput]
  moderator_out: Optional[ModeratorSummary]
  review_board_out: Optional[ReviewBoardOutput]
  round_num: int
  max_rounds: int

class Config4LangGraphVulTrial(BaseAgentConfiguration):
  """
  VULTRIAL (ICSE 2026) 4-agent courtroom architecture.
  """

  def __init__(self, llm_client, max_rounds: int = 1):
    super().__init__(llm_client)
    self.max_rounds = max_rounds
    self.graph = self._build_graph()

  @property
  def config_name(self) -> str:
    return f"Config4_LangGraph_VulTrial_r{self.max_rounds}"

  # Agent 1: Security Researcher (Prosecutor)
  def _researcher_node(self, state: VulTrialState) -> dict:
    sample = state["sample"]
    history_str = ""
    if state.get("moderator_out"):
      history_str = (
        f"\n\n[Chat History - Moderator Summary]:\n"
        f"{state['moderator_out'].model_dump_json(indent=2)}"
      )

    messages = [
      {
        "role": "system",
        "content": (
          "You are the Security Researcher (Prosecutor). Analyze the given code snippet and identify "
          "any concrete security vulnerabilities or functional bugs.\n"
          f"{FUNCTION_SCOPE_PRINCIPLES}\n"
          "For each claim, state the exact code path and input/state that triggers the flaw. "
          "If the code is safe or protected by helpers/safe APIs, return an empty claims list `[]`."
        )
      },
      {
        "role": "user",
        "content": f"Language: {sample.language}\nCode:\n```{sample.language}\n{sample.code_snippet}\n```{history_str}"
      }
    ]
    out = self.llm.generate_structured(messages, SecurityResearcherOutput)
    return {"researcher_out": out}

  # Agent 2: Code Author (Defender)
  def _author_node(self, state: VulTrialState) -> dict:
    sample = state["sample"]
    claims_json = state["researcher_out"].model_dump_json(indent=2)

    messages = [
      {
        "role": "system",
        "content": (
          "You are the Code Author reviewing the Security Researcher's claims against your code.\n"
          f"{FUNCTION_SCOPE_PRINCIPLES}\n"
          "For each claim, fill out `reason` and `response_type` ('refutation' or 'mitigation') honestly:\n"
          "- Set `response_type` to 'refutation' ONLY IF the existing code ALREADY contains a guard, validation helper, "
          "or safe API pattern that prevents the bug. Quote that exact protection in `reason`.\n"
          "- Set `response_type` to 'mitigation' IF your code genuinely lacks the protection and can be exploited or crashed. "
          "In `reason`, admit the bug and state how to fix it."
        )
      },
      {
        "role": "user",
        "content": (
          f"Code:\n```{sample.language}\n{sample.code_snippet}\n```\n\n"
          f"Security Researcher's Claims:\n{claims_json}"
        )
      }
    ]
    out = self.llm.generate_structured(messages, CodeAuthorOutput)
    return {"author_out": out}

  # Agent 3: Moderator (Judge)
  def _moderator_node(self, state: VulTrialState) -> dict:
    sample = state["sample"]
    messages = [
      {
        "role": "system",
        "content": (
          "You are the Moderator (Judge). Summarize the Security Researcher's claims and the Code Author's responses. "
          "Verify directly from the code snippet whether the guard/helper or vulnerability exists: "
          "note clearly if the Code Author admitted the bug exists or successfully pointed out an existing protection."
        )
      },
      {
        "role": "user",
        "content": (
          f"Code:\n```{sample.language}\n{sample.code_snippet}\n```\n\n"
          f"Security Researcher:\n{state['researcher_out'].model_dump_json(indent=2)}\n\n"
          f"Code Author:\n{state['author_out'].model_dump_json(indent=2)}"
        )
      }
    ]
    out = self.llm.generate_structured(messages, ModeratorSummary)
    return {"moderator_out": out, "round_num": state["round_num"] + 1}

  # Agent 4: Review Board (Jury)
  def _review_board_node(self, state: VulTrialState) -> dict:
    sample = state["sample"]
    messages = [
      {
        "role": "system",
        "content": (
          "You are the Review Board (Jury). For each alleged vulnerability, inspect the actual source code and fill out the JSON fields strictly as follows:\n"
          f"{FUNCTION_SCOPE_PRINCIPLES}\n"
          "1. `code_has_protection` (boolean): Set to `true` if the code snippet contains a guard, validation helper, or safe API that blocks this specific bug. Otherwise set to `false`.\n"
          "2. `reason` (string): Explain step-by-step whether the bug can be triggered in the code.\n"
          "3. `is_vulnerable_verdict` (boolean): MUST be `true` if the bug is genuinely triggerable (`code_has_protection` is `false`), and `false` if the code is already protected (`code_has_protection` is `true`).\n"
          "4. `severity`: Set to 'high' when `is_vulnerable_verdict` is `true`, and 'none' when `is_vulnerable_verdict` is `false`."
        )
      },
      {
        "role": "user",
        "content": (
          f"Code:\n```{sample.language}\n{sample.code_snippet}\n```\n\n"
          f"Moderator Summary:\n{state['moderator_out'].model_dump_json(indent=2)}\n\n"
          f"Security Researcher Claims:\n{state['researcher_out'].model_dump_json(indent=2)}\n\n"
          f"Code Author Responses:\n{state['author_out'].model_dump_json(indent=2)}"
        )
      }
    ]
    out = self.llm.generate_structured(messages=messages, response_model=ReviewBoardOutput)
    return {"review_board_out": out}

  @staticmethod
  def _route_after_moderator(state: VulTrialState) -> str:
    if state["round_num"] < state["max_rounds"]:
      return "researcher"
    return "review_board"

  def _build_graph(self):
    builder = StateGraph(VulTrialState)
    builder.add_node("researcher", self._researcher_node)
    builder.add_node("author", self._author_node)
    builder.add_node("moderator", self._moderator_node)
    builder.add_node("review_board", self._review_board_node)

    builder.add_edge(START, "researcher")
    builder.add_edge("researcher", "author")
    builder.add_edge("author", "moderator")
    builder.add_conditional_edges("moderator", self._route_after_moderator)
    builder.add_edge("review_board", END)

    return builder.compile()

  def run_inference(self, sample: TaskSample) -> AgentPrediction:
    initial_state: VulTrialState = {
      "sample": sample,
      "researcher_out": None,
      "author_out": None,
      "moderator_out": None,
      "review_board_out": None,
      "round_num": 0,
      "max_rounds": self.max_rounds
    }
    final_state = self.graph.invoke(initial_state)
    mod_summary = final_state["moderator_out"]
    verdicts = final_state["review_board_out"].verdicts

    confirmed_vulns = [
      v for v in verdicts
      if v.is_vulnerable_verdict is True and v.severity in ("high", "medium")
    ]

    if confirmed_vulns:
      top_v = confirmed_vulns[0]
      return AgentPrediction(
        code_flow_analysis=mod_summary.security_researcher_summary,
        mitigation_and_trigger_analysis=f"[VulTrial Jury Verdict: VULNERABLE/{top_v.severity.upper()}] {top_v.reason}",
        vulnerability_type=top_v.vulnerability,
        is_vulnerable=True,
        confidence_score=4
      )
    else:
      reasons = "; ".join(
        [f"{v.vulnerability}: protected={v.code_has_protection} ({v.reason})" for v in verdicts]
      ) or "No vulnerabilities found."
      return AgentPrediction(
        code_flow_analysis=mod_summary.author_summary,
        mitigation_and_trigger_analysis=f"[VulTrial Jury Verdict: BENIGN] {reasons}",
        vulnerability_type=None,
        is_vulnerable=False,
        confidence_score=4
      )