"""
Task 7.1 Model Registry — 统一模型元数据与动态注册。
"""

from app.model_registry.loader import DEFAULT_MODELS_FILE
from app.model_registry.loader import load_models_from_yaml
from app.model_registry.manager import ModelRegistryManager
from app.model_registry.manager import get_model_registry_manager
from app.model_registry.manager import reset_model_registry_manager
from app.model_registry.models import ModelCost
from app.model_registry.models import ModelInfo
from app.model_registry.models import ModelVendor
from app.model_registry.repository import ModelRegistryRepository

__all__ = [
    "DEFAULT_MODELS_FILE",
    "ModelCost",
    "ModelInfo",
    "ModelRegistryManager",
    "ModelRegistryRepository",
    "ModelVendor",
    "get_model_registry_manager",
    "load_models_from_yaml",
    "reset_model_registry_manager",
]
