# LangGraph State Definition
import json
from typing import TypedDict, Optional

from langgraph.graph import StateGraph, START, END

from src.core.base_configuration import BaseAgentConfiguration
from src.core.prompts import FUNCTION_SCOPE_PRINCIPLES
from src.core.schemas import TaskSample, ActorReport, AgentPrediction
from src.tools.code_inspector import StaticCodeInspectorTool



class SingleAgentState(TypedDict):
  sample: TaskSample
  tool_output: str
  draft_report: Optional[ActorReport]
  final_prediction: Optional[AgentPrediction]
  iteration: int
  max_iterations: int


class Baseline2LangGraphReAct(BaseAgentConfiguration):
  """
  Proposal Baseline 2: LangGraph based Tool Use and Iterative Self-Refinement single agent
  """

  def __init__(self, llm_client, max_iterations: int = 1):
    super().__init__(llm_client)
    self.max_iterations = max_iterations
    self.tool = StaticCodeInspectorTool()
    self.graph = self._build_graph()

  @property
  def config_name(self) -> str:
    return f"Baseline2_LangGraph_SelfRefine_i{self.max_iterations}"

  # ---- Nodes ---
  def _tool_node(self, state: SingleAgentState) -> dict:
    report = self.tool.execute(
      code_snippet=state["sample"].code_snippet,
      language=state["sample"].language
    )
    return {"tool_output": json.dumps(report, indent=2)}

  def _draft_node(self, state: SingleAgentState) -> dict:
    sample = state["sample"]
    messages = [
      {
        "role": "system",
        "content": (
          "You are an autonomous software security and bug detection agent.\n"
          f"{FUNCTION_SCOPE_PRINCIPLES}\n"
          "Combine the structural observations from the static inspector with your own semantic trace of the code. "
          "Do NOT write replacement code snippets. Set `suspected_vulnerable: true` only if a concrete flaw is triggerable."
        )
      },
      {
        "role": "user",
        "content": (
          f"Language: {sample.language}\n"
          f"Code:\n```{sample.language}\n{sample.code_snippet}\n```\n\n"
          f"Static Inspector Output:\n{state['tool_output']}"
        )
      }
    ]

    draft = self.llm.generate_structured(messages, ActorReport)
    return {"draft_report": draft, "iteration": 0}

  def _self_refine_node(self, state: SingleAgentState) -> dict:
    sample = state["sample"]
    prev_content = (
      state["final_prediction"].model_dump_json(indent=2)
      if state.get("final_prediction")
      else state["draft_report"].model_dump_json(indent=2)
    )

    messages = [
      {
        "role": "system",
        "content": (
          "You are performing a Self-Reflection verification step on your initial analysis.\n"
          f"{FUNCTION_SCOPE_PRINCIPLES}\n"
          "Verify your initial claim against the exact lines of the Original Code:\n"
          "- Confirm `is_vulnerable: true` if a concrete exploit, crash macro, memory/bounds error, resource leak on error path, "
          "or unescaped injection/traversal path is genuinely present.\n"
          "- Set `is_vulnerable: false` if the code already mitigates the issue via helper functions, argument lists, "
          "parameterized queries, RAII cleanup, or explicit bounds/null checks."
        )
      },
      {
        "role": "user",
        "content": (
          f"Original Code:\n```{sample.language}\n{sample.code_snippet}\n```\n\n"
          f"Static Inspector Output:\n{state['tool_output']}\n\n"
          f"Initial Draft Analysis:\n{prev_content}\n\n"
          "Verify against the Original Code and output your final JSON verdict."
        )
      }
    ]

    refined = self.llm.generate_structured(messages, AgentPrediction)
    return {
      "final_prediction": refined,
      "iteration": state["iteration"] + 1
    }

  # --- CONDITIONAL EDGE ---
  @staticmethod
  def _should_continue(state: SingleAgentState) -> str:
    if state["iteration"] < state["max_iterations"]:
      return "self_refine"
    return END

  def _build_graph(self):
    builder = StateGraph(SingleAgentState)
    builder.add_node("run_tool", self._tool_node)
    builder.add_node("draft_analysis", self._draft_node)
    builder.add_node("self_refine", self._self_refine_node)

    builder.add_edge(START, "run_tool")
    builder.add_edge("run_tool", "draft_analysis")
    builder.add_edge("draft_analysis", "self_refine")
    builder.add_conditional_edges("self_refine", self._should_continue)

    return builder.compile()

  def run_inference(self, sample: TaskSample) -> AgentPrediction:
    initial_state = SingleAgentState = {
      "sample": sample,
      "tool_output": "",
      "draft_report": None,
      "final_prediction": None,
      "iteration": 0,
      "max_iterations": self.max_iterations
    }

    result_state = self.graph.invoke(initial_state)
    return result_state["final_prediction"]
