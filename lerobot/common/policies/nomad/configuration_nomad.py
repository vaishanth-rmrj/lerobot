
from dataclasses import dataclass, field

from lerobot.configs.policies import PreTrainedConfig

@PreTrainedConfig.register_subclass("nomad")
@dataclass
class NomadConfig(PreTrainedConfig):
    """Configuration class for NomadPolicy.
    """

    # Inputs / output structure.
    n_obs_steps: int = 4
    horizon: int = 8
    n_action_steps: int = 8

    # Architecture / modeling.
    # Vision backbone.
    vision_backbone: str = "efficientnet-b0"