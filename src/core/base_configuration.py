from abc import ABC, abstractmethod

from src.core.llm_client import TrackedLLMClient
from src.core.schemas import TaskSample, AgentPrediction, BenchmarkRecord


class BaseAgentConfiguration(ABC):
  def __init__(self, llm_client: TrackedLLMClient):
    self.llm = llm_client

  @property
  @abstractmethod
  def config_name(self) -> str:
    pass

  @abstractmethod
  def run_inference(self, sample: TaskSample) -> AgentPrediction:
    """All the subclasses must implement this method."""
    pass

  def evaluate_sample(self, sample: TaskSample) -> BenchmarkRecord:
    """Resets the counters, gets the prediction and returns the benchmark record."""
    self.llm.reset_metrics()
    prediction = self.run_inference(sample)

    return BenchmarkRecord(
      sample_id=sample.sample_id,
      pair_id=sample.pair_id,
      config_name=self.config_name,
      model_name=self.llm.model_name,
      prediction=prediction,
      ground_truth=sample.ground_truth_vulnerable,
      is_correct=prediction.is_vulnerable == sample.ground_truth_vulnerable,
      prompt_tokens=self.llm.prompt_tokens,
      completion_tokens=self.llm.completion_tokens,
      total_tokens=self.llm.prompt_tokens + self.llm.completion_tokens,
      latency_sec=round(self.llm.total_latency_sec, 4),
      llm_calls_count=self.llm.calls_count,
      raw_messages=self.llm.message_log
    )
