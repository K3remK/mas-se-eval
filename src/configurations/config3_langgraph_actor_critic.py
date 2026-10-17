from typing import TypedDict, Optional

from langgraph.graph import START, END, StateGraph

from src.core.base_configuration import BaseAgentConfiguration
from src.core.prompts import FUNCTION_SCOPE_PRINCIPLES
from src.core.schemas import TaskSample, ActorReport, CriticEvaluation, AgentPrediction


class ActorCriticState(TypedDict):
  sample: TaskSample
  actor_report: Optional[ActorReport]
  critic_eval: Optional[CriticEvaluation]
  round_num: int
  max_rounds: int


class Config3LangGraphActorCritic(BaseAgentConfiguration):
  """
  Proposal Config 3: LangGraph Actor-Critic MultiAgent Architecture
  - Actor Agent: Produces vulnerability report and evidence based on the code snippet
  - Critic Agent: Evaluates the Actor report and confirms or refutes the vulnerability
  """

  def __init__(self, llm_client, max_rounds: int = 1):
    super().__init__(llm_client)
    self.max_rounds = max_rounds
    self.graph = self._build_graph()

  @property
  def config_name(self) -> str:
    return f"Config3_LangGraph_ActorCritic_r{self.max_rounds}"

  def _actor_node(self, state: ActorCriticState) -> dict:
    sample = state["sample"]
    feedback_context = ""
    if state.get("critic_eval"):
      feedback_context = (
        f"\n\n[Previous Critic Feedback]:\n"
        f"{state['critic_eval'].refutation_or_confirmation}\n"
        "Re-evaluate the code carefully addressing the Critic's feedback."
      )

    messages = [
      {
        "role": "system",
        "content": (
          "You are the Security Auditor (Actor Agent). Inspect the function for concrete security vulnerabilities "
          "or functional bugs.\n"
          f"{FUNCTION_SCOPE_PRINCIPLES}\n"
          "If you find a real flaw, explain the exact code path and input/state that triggers it and set "
          "`suspected_vulnerable: true`. If the function is safe or protected by helpers/safe APIs, set `suspected_vulnerable: false`."
        )
      },
      {
        "role": "user",
        "content": (
          f"Language: {sample.language}\n"
          f"Code:\n```{sample.language}\n{sample.code_snippet}\n```"
          f"{feedback_context}"
        )
      }
    ]

    report = self.llm.generate_structured(messages, ActorReport)
    return {"actor_report": report}

  def _critic_node(self, state: ActorCriticState) -> dict:
    sample = state["sample"]
    actor_json = state["actor_report"].model_dump_json(indent=2)

    messages = [
      {
        "role": "system",
        "content": (
          "You are the Chief Security Critic Agent. Critically verify the Actor Agent's report against the source code:\n"
          f"{FUNCTION_SCOPE_PRINCIPLES}\n"
          "- If the Actor identified a genuine, unmitigated flaw in this function, confirm it (`is_vulnerable: true`).\n"
          "- If the Actor flagged a false alarm that is already mitigated by a helper function, argument list, parameterized query, "
          "or guard check—or nitpicked a non-issue—refute the Actor and set `is_vulnerable: false`.\n"
          "- If the Actor missed a real vulnerability in the code (such as string-formatted SQL/commands, missing bounds/null checks, "
          "or reachable CHECK/DCHECK crash macros), override the Actor and set `is_vulnerable: true`."
        )
      },
      {
        "role": "user",
        "content": (
          f"Source Code:\n```{sample.language}\n{sample.code_snippet}\n```\n\n"
          f"Actor Agent's Report:\n{actor_json}\n\n"
          "Verify the Actor's report and output the final JSON evaluation."
        )
      }
    ]
    critique = self.llm.generate_structured(messages, CriticEvaluation)
    return {
      "critic_eval": critique,
      "round_num": state["round_num"] + 1
    }

  @staticmethod
  def _route_after_critic(state: ActorCriticState) -> str:
    if state["round_num"] < state["max_rounds"]:
      return "actor"
    return END

  def _build_graph(self):
    builder = StateGraph(ActorCriticState)
    builder.add_node("actor", self._actor_node)
    builder.add_node("critic", self._critic_node)

    builder.add_edge(START, "actor")
    builder.add_edge("actor", "critic")
    builder.add_conditional_edges("critic", self._route_after_critic)

    return builder.compile()

  def run_inference(self, sample: TaskSample) -> AgentPrediction:
    initial_state: ActorCriticState = {
      "sample": sample,
      "actor_report": None,
      "critic_eval": None,
      "round_num": 0,
      "max_rounds": self.max_rounds
    }

    final_state = self.graph.invoke(initial_state)
    return final_state["critic_eval"].final_verdict
