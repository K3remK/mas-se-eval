from typing import TypedDict, List

from langgraph.graph import StateGraph, START, END

from src.core.base_configuration import BaseAgentConfiguration
from src.core.prompts import FUNCTION_SCOPE_PRINCIPLES
from src.core.schemas import TaskSample, AgentPrediction


# TODO: update the prompts so that it is more general, not specific to a single case

class VotingState(TypedDict):
  sample: TaskSample
  votes: List[AgentPrediction]
  final_decision: AgentPrediction


class Config5LangGraphVoting(BaseAgentConfiguration):
  """
  Voting-based Cooperation (Majority Vote):
  3 different agents vote independently on whether the code snippet is vulnerable or not
  """

  def __init__(self, llm_client):
    super().__init__(llm_client)
    self.voter_personas = [
      (
        "Voter1_Memory_And_Arithmetic_Auditor",
        "You are a Memory, Bounds & Arithmetic Safety Auditor. Analyze the code for memory corruption, "
        "buffer overflows, out-of-bounds array reads/writes (checking both negative and upper bounds), "
        "null pointer dereferences, integer overflows, and division by zero. Vote `is_vulnerable: true` "
        "if any input parameter can trigger these flaws."
        f"\n{FUNCTION_SCOPE_PRINCIPLES}"
      ),
      (
        "Voter2_DataFlow_And_API_Auditor",
        "You are a Data-Flow & Secure API Specialist. Trace how untrusted parameters flow through the function "
        "into sensitive sinks (e.g., SQL queries, command execution, string/buffer copies, file I/O). "
        "Check whether unsafe functions or unparameterized queries are used without proper sanitization or bounds."
        f"\n{FUNCTION_SCOPE_PRINCIPLES}"
      ),
      (
        "Voter3_Precondition_And_Logic_Verifier",
        "You are a Formal Precondition & Control-Flow Verifier. Examine every conditional guard (`if/else`, loop conditions) "
        "in the function. Determine whether the guards completely block all invalid parameter states (such as null arrays, "
        "zero/negative counts or indices, or oversized inputs) before sensitive operations execute."
        f"\n{FUNCTION_SCOPE_PRINCIPLES}"
      )
    ]
    self.graph = self._build_graph()

  @property
  def config_name(self) -> str:
    return "Config5_LangGraph_Voting_3Agents"

  def _collect_votes_node(self, state: VotingState) -> dict:
    sample = state["sample"]
    collected_votes = []

    for name, persona_prompt in self.voter_personas:
      messages = [
        {"role": "system", "content": persona_prompt},
        {
          "role": "user",
          "content": f"Language: {sample.language}\nCode:\n```{sample.language}\n{sample.code_snippet}\n```"
        }
      ]
      vote = self.llm.generate_structured(messages, AgentPrediction)
      collected_votes.append(vote)
    return {"votes": collected_votes}

  @staticmethod
  def _aggregator_node(state: VotingState) -> dict:
    votes = state["votes"]
    vuln_votes = sum(1 for v in votes if v.is_vulnerable)
    majority_is_vuln = vuln_votes >= (len(votes) / 2.0)

    matching_votes = [v for v in votes if v.is_vulnerable == majority_is_vuln]
    avg_conf = round(sum(v.confidence_score for v in matching_votes) / len(matching_votes))
    combined_flow = " | ".join(
      f"Voter {i + 1}: {v.code_flow_analysis}" for i, v in enumerate(matching_votes)
    )
    combined_trigger = " | ".join(
      f"Voter {i + 1} ({v.is_vulnerable}): {v.mitigation_and_trigger_analysis}" for i, v in enumerate(matching_votes)
    )

    final = AgentPrediction(
      code_flow_analysis=combined_flow,
      mitigation_and_trigger_analysis=f"[Vote Tally: {vuln_votes}/{len(votes)} Vulnerable] {combined_trigger}",
      vulnerability_type=matching_votes[0].vulnerability_type if majority_is_vuln else None,
      is_vulnerable=majority_is_vuln,
      confidence_score=min(max(avg_conf, 1), 4),
    )
    return {"final_decision": final}

  def _build_graph(self):
    builder = StateGraph(VotingState)
    builder.add_node("collect_votes", self._collect_votes_node)
    builder.add_node("aggregate", self._aggregator_node)

    builder.add_edge(START, "collect_votes")
    builder.add_edge("collect_votes", "aggregate")
    builder.add_edge("aggregate", END)

    return builder.compile()

  def run_inference(self, sample: TaskSample) -> AgentPrediction:
    initial_state = {
      "sample": sample,
      "votes": [],
      "final_decision": None
    }
    result_state = self.graph.invoke(initial_state)
    return result_state["final_decision"]
