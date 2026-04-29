"""ORM model registry.

Import all models here so that Base.metadata sees them when Alembic
generates migration scripts. Any new model added to src/backend/models/
must be imported in this module.
"""

from src.backend.models.dataset import Dataset
from src.backend.models.experiment import Experiment
from src.backend.models.paper import Paper
from src.backend.models.prediction import Prediction
from src.backend.models.trained_model import TrainedModel

__all__ = [
    "Dataset",
    "Experiment",
    "Paper",
    "Prediction",
    "TrainedModel",
]
