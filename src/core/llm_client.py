import time
import json
from typing import List, Dict, Type, TypeVar
from pydantic import BaseModel
import openai
from openai import OpenAI
from rich.console import Console

console = Console()
T = TypeVar("T", bound=BaseModel)


class TrackedLLMClient:
  def __init__(
          self,
          model_name: str = "qwen2.5-coder:7b",
          base_url: str = "http://localhost:11434/v1",
          temperature: float = 0.0,
          seed: int = 42,
          num_ctx: int = 8192,
          max_tokens: int = 1024,
          timeout_sec: float = 180.0,
  ):
    self.model_name = model_name
    self.temperature = temperature
    self.seed = seed
    self.num_ctx = num_ctx
    self.max_tokens = max_tokens
    self.client = OpenAI(
      base_url=base_url,
      api_key="ollama",
      timeout=timeout_sec,
      max_retries=0,
    )
    self.reset_metrics()

  def reset_metrics(self):
    """Resets counters before each new TaskSample."""
    self.prompt_tokens = 0
    self.completion_tokens = 0
    self.total_latency_sec = 0.0
    self.calls_count = 0
    self.message_log = []

  def generate_structured(
          self,
          messages: List[Dict[str, str]],
          response_model: Type[T],
  ) -> T:
    """
    Attempt 1: 100% pure model call (no prompt alterations, no repeat penalty distortion).
    Attempt 2: Triggered ONLY if Attempt 1 gets stuck in an infinite repetition loop
               and hits max_tokens (LengthFinishReasonError) or times out.
    """
    # 1. Explicitly show the JSON schema in the system prompt so Ollama doesn't fly blind
    schema_json = json.dumps(response_model.model_json_schema(), indent=2)
    current_messages = [dict(m) for m in messages]
    if current_messages and current_messages[0]["role"] == "system":
      current_messages[0]["content"] += (
        f"\n\nRespond strictly in valid JSON matching this schema (do not use unescaped newlines inside strings):\n{schema_json}"
      )

    for attempt in range(2):
      start_time = time.perf_counter()

      if attempt == 0:
        call_temp = self.temperature
        extra_options = {
          "num_ctx": self.num_ctx,
          "num_predict": self.max_tokens,
          "repeat_penalty": 1.05,  # Micro-penalty prevents infinite phrase loops without hurting code identifiers
        }
      else:
        call_temp = 0.2
        extra_options = {
          "num_ctx": self.num_ctx,
          "num_predict": self.max_tokens,
          "repeat_penalty": 1.15,
        }

      try:
        response = self.client.beta.chat.completions.parse(
          model=self.model_name,
          messages=current_messages,
          response_format=response_model,
          temperature=call_temp,
          seed=self.seed + attempt,
          max_tokens=self.max_tokens,
          extra_body={"options": extra_options},
        )

        elapsed = time.perf_counter() - start_time
        self.total_latency_sec += elapsed
        self.calls_count += 1

        if response.usage:
          self.prompt_tokens += response.usage.prompt_tokens
          self.completion_tokens += response.usage.completion_tokens

        parsed_output = response.choices[0].message.parsed
        self.message_log.append({
          "call_index": self.calls_count,
          "attempt": attempt + 1,
          "finish_reason": response.choices[0].finish_reason,
          "input_messages": current_messages,
          "output": parsed_output.model_dump() if parsed_output else None,
          "latency_sec": round(elapsed, 4),
        })

        return parsed_output

      except (openai.LengthFinishReasonError, openai.APITimeoutError, Exception) as err:
        elapsed = time.perf_counter() - start_time
        self.total_latency_sec += elapsed
        self.calls_count += 1

        # Capture tokens burned during a truncated LengthFinishReasonError call
        if isinstance(err, openai.LengthFinishReasonError) and getattr(err, "completion", None):
          usage = getattr(err.completion, "usage", None)
          if usage:
            self.prompt_tokens += usage.prompt_tokens
            self.completion_tokens += usage.completion_tokens

        console.print(
          f"    [bold yellow][LOOP DETECTED][/bold yellow] Call hit {type(err).__name__} "
          f"after {elapsed:.1f}s (Attempt {attempt + 1}/2)."
        )
        if attempt == 0:
          current_messages[-1] = {
            "role": current_messages[-1]["role"],
            "content": (
              current_messages[-1]["content"]
              + "\n\nNOTE: Keep your reasoning concise (under 4 sentences) and close all JSON fields properly."
            ),
          }
          continue

        console.print("    [bold red][FALLBACK][/bold red] Returning default fallback after 2 failed attempts.")
        fallback_instance = self._build_fallback(response_model)
        self.message_log.append({
          "call_index": self.calls_count,
          "attempt": attempt + 1,
          "finish_reason": f"error_fallback: {type(err).__name__}",
          "input_messages": current_messages,
          "output": fallback_instance.model_dump(),
          "latency_sec": round(elapsed, 4),
        })
        return fallback_instance

  @staticmethod
  def _build_fallback(response_model: Type[T]) -> T:
    schema_name = response_model.__name__
    if schema_name == "AgentPrediction":
      return response_model(
        code_flow_analysis="[Fallback: Model exceeded token cap due to generation loop]",
        mitigation_and_trigger_analysis="[Fallback: Unable to complete verification]",
        vulnerability_type=None,
        is_vulnerable=False,
        confidence_score=1,
      )
    if schema_name == "ActorReport":
      return response_model(
        evidence_and_trigger="[Fallback: Actor output truncated due to generation loop]",
        vulnerability_name=None,
        suspected_vulnerable=False,
      )
    if schema_name == "CriticEvaluation":
      from src.core.schemas import AgentPrediction
      return response_model(
        refutation_or_confirmation="[Fallback: Critic output truncated]",
        is_claim_valid=False,
        final_verdict=AgentPrediction(
          code_flow_analysis="[Fallback: Critic output truncated]",
          mitigation_and_trigger_analysis="[Fallback: Critic output truncated]",
          vulnerability_type=None,
          is_vulnerable=False,
          confidence_score=1,
        ),
      )
    if schema_name == "SecurityResearcherOutput":
      return response_model(claims=[])
    if schema_name == "CodeAuthorOutput":
      return response_model(responses=[])
    if schema_name == "ModeratorSummary":
      return response_model(
        security_researcher_summary="No valid claims.",
        author_summary="No responses.",
      )
    if schema_name == "ReviewBoardOutput":
      return response_model(verdicts=[])
    raise RuntimeError(f"Cannot build fallback for unknown schema: {schema_name}")