from typing import Optional, List, Dict, Any
import enum
from pydantic import BaseModel
from sqlalchemy import select, func
from ..database.models import ModelFeedbackModel
from sqlalchemy.ext.asyncio import AsyncSession
import datetime
import structlog

logger = structlog.get_logger()

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
                id="deepseek-reasoner",
                provider="deepseek",
                reasoning_score=0.98,
                cost_per_1k_tokens=0.002,
                speed_score=0.6,
                context_window=64000
            ),
            ModelInfo(
                id="deepseek-chat",
                provider="deepseek",
                reasoning_score=0.9,
                cost_per_1k_tokens=0.0002,
                speed_score=0.9,
                context_window=128000
            ),
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

    async def route(
        self,
        complexity: float,
        context_size: int,
        priority: ModelCapability = ModelCapability.REASONING,
        prefer_local: bool = False,
        db: Optional[AsyncSession] = None
    ) -> ModelInfo:
        """
        Routes to the best model based on requirements and historical performance.
        """
        available_models = self.models
        
        if prefer_local:
            local_models = [m for m in available_models if m.is_local]
            if local_models:
                return local_models[0]

        # Filter by context window
        available_models = [m for m in available_models if m.context_window >= context_size]
        if not available_models:
            return max(self.models, key=lambda x: x.context_window)

        # Fetch performance data if DB is available
        scores = {}
        if db:
            scores = await self._get_performance_scores(db)

        def get_adjusted_score(model: ModelInfo) -> float:
            base_score = 0.0
            if priority == ModelCapability.REASONING:
                base_score = model.reasoning_score
            elif priority == ModelCapability.SPEED:
                base_score = model.speed_score
            elif priority == ModelCapability.COST:
                # Inverse of cost
                base_score = 1.0 / (1.0 + model.cost_per_1k_tokens * 100)
            
            # Adjust based on historical success rate
            perf = scores.get(model.id)
            if perf:
                success_rate = perf.get("success_rate", 1.0)
                # Weighted average: 70% base, 30% historical performance
                return (base_score * 0.7) + (success_rate * 0.3)
            
            return base_score

        return max(available_models, key=get_adjusted_score)

    async def _get_performance_scores(self, db: AsyncSession) -> Dict[str, Dict[str, float]]:
        """Fetch recent model performance from DB."""
        try:
            # Last 100 entries
            since = datetime.datetime.utcnow() - datetime.timedelta(days=7)
            query = (
                select(
                    ModelFeedbackModel.model_id,
                    func.avg(ModelFeedbackModel.success.cast(func.Integer)).label("success_rate"),
                    func.avg(ModelFeedbackModel.latency).label("avg_latency")
                )
                .where(ModelFeedbackModel.created_at > since)
                .group_by(ModelFeedbackModel.model_id)
            )
            result = await db.execute(query)
            return {
                row.model_id: {"success_rate": float(row.success_rate), "avg_latency": float(row.avg_latency)}
                for row in result.all()
            }
        except Exception as e:
            logger.warning("failed_to_fetch_performance_scores", error=str(e))
            return {}

    async def log_feedback(self, model_id: str, success: bool, latency: float, tokens_used: int, db: Optional[AsyncSession] = None):
        """
        Log feedback about model performance.
        """
        if not db:
            logger.warning("no_db_session_for_feedback", model_id=model_id)
            return

        try:
            feedback = ModelFeedbackModel(
                model_id=model_id,
                success=success,
                latency=int(latency * 1000), # convert to ms
                tokens_used=tokens_used
            )
            db.add(feedback)
            await db.commit()
            logger.info("model_feedback_logged", model_id=model_id, success=success)
        except Exception as e:
            logger.error("failed_to_log_feedback", model_id=model_id, error=str(e))
