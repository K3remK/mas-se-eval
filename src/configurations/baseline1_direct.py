from src.core.base_configuration import BaseAgentConfiguration
from src.core.prompts import FUNCTION_SCOPE_PRINCIPLES
from src.core.schemas import TaskSample, AgentPrediction



class Baseline1Direct(BaseAgentConfiguration):
  @property
  def config_name(self) -> str:
    return "Baseline1_Direct_LLM"

  def run_inference(self, sample: TaskSample) -> AgentPrediction:
    system_prompt = (
      "You are an expert software security researcher and static analysis engine.\n"
      f"{FUNCTION_SCOPE_PRINCIPLES}\n"
      "Complete both `code_flow_analysis` and `mitigation_and_trigger_analysis` thoroughly "
      "before setting `is_vulnerable`."
    )
    user_prompt = (
      f"Programming Language: {sample.language}\n"
      f"Code Snippet:\n```{sample.language}\n{sample.code_snippet}\n```"
    )
    messages = [
      {"role": "system", "content": system_prompt},
      {"role": "user", "content": user_prompt}
    ]
    return self.llm.generate_structured(messages, AgentPrediction)
