from src.configurations.baseline1_direct import Baseline1Direct
from src.configurations.baseline2_langgraph import Baseline2LangGraphReAct
from src.configurations.config3_langgraph_actor_critic import Config3LangGraphActorCritic
from src.configurations.config4_langgraph_vultrial import Config4LangGraphVulTrial
from src.configurations.config5_langgraph_voting import Config5LangGraphVoting

CONFIG_REGISTRY = {
  "baseline1_direct": Baseline1Direct,
  "baseline2_self_refine": Baseline2LangGraphReAct,
  "config3_actor_critic": Config3LangGraphActorCritic,
  "config4_vultrial": Config4LangGraphVulTrial,
  "config5_voting": Config5LangGraphVoting,
}


def build_configuration(name: str, llm_client, params: dict = None):
  params = params or {}
  if name not in CONFIG_REGISTRY:
    raise ValueError(f"Unknown configuration: {name}. Available configurations: {list(CONFIG_REGISTRY.keys())}")
  cls = CONFIG_REGISTRY[name]
  return cls(llm_client, **params)
