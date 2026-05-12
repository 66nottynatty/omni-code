from typing import Optional, List, Dict, Any
import enum
from pydantic import BaseModel

class ModelCapability(enum.Enum):
    REASONING = "reasoning"
    SPEED = "speed"
    COST = "cost"
    CONTEXT = "context"

class ModelInfo(BaseModel):
    id: str
    provider: str
    reasoning_score: float  # 0 to 1
    cost_per_1k_tokens: float
    speed_score: float  # 0 to 1
    context_window: int
    is_local: bool = False

class ModelRouter:
    def __init__(self):
        self.models = [
            ModelInfo(
                id="gpt-4o",
                provider="openai",
                reasoning_score=0.95,
                cost_per_1k_tokens=0.01,
                speed_score=0.8,
                context_window=128000
            ),
            ModelInfo(
                id="claude-3-5-sonnet-20240620",
                provider="anthropic",
                reasoning_score=0.96,
                cost_per_1k_tokens=0.015,
                speed_score=0.85,
                context_window=200000
            ),
            ModelInfo(
                id="gpt-4-turbo",
                provider="openai",
                reasoning_score=0.9,
                cost_per_1k_tokens=0.03,
                speed_score=0.6,
                context_window=128000
            ),
            ModelInfo(
                id="deepseek-coder",
                provider="deepseek",
                reasoning_score=0.85,
                cost_per_1k_tokens=0.002,
                speed_score=0.7,
                context_window=32000
            ),
            ModelInfo(
                id="qwen2.5-coder-7b",
                provider="ollama",
                reasoning_score=0.7,
                cost_per_1k_tokens=0.0,
                speed_score=0.95,
                context_window=32000,
                is_local=True
            ),
        ]

    def route(
        self,
        complexity: float,
        context_size: int,
        priority: ModelCapability = ModelCapability.REASONING,
        prefer_local: bool = False
    ) -> ModelInfo:
        """
        Routes to the best model based on requirements.
        """
        available_models = self.models
        
        if prefer_local:
            local_models = [m for m in available_models if m.is_local]
            if local_models:
                return local_models[0]

        # Filter by context window
        available_models = [m for m in available_models if m.context_window >= context_size]
        if not available_models:
            # Return the one with the largest context window if none fit
            return max(self.models, key=lambda x: x.context_window)

        if priority == ModelCapability.REASONING:
            return max(available_models, key=lambda x: x.reasoning_score)
        elif priority == ModelCapability.SPEED:
            return max(available_models, key=lambda x: x.speed_score)
        elif priority == ModelCapability.COST:
            return min(available_models, key=lambda x: x.cost_per_1k_tokens)
        else:
            return available_models[0]

    def log_feedback(self, model_id: str, success: bool, latency: float, tokens_used: int):
        """
        Placeholder for implementing feedback loop to adjust model weights.
        """
        pass
