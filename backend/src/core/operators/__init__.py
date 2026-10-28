"""Business-agnostic operator kernel.

Import order matters: each module registers its operators through the SDK at
import time, then :func:`register_operators` attaches them to the microkernel
registry.
"""
from src.core.operators import entity as _entity  # noqa: F401
from src.core.operators import external as _external  # noqa: F401
from src.core.operators import guard as _guard  # noqa: F401
from src.core.operators import response as _response  # noqa: F401
from src.core.operators import side_effects as _side_effects  # noqa: F401
from src.core.operators import transform as _transform  # noqa: F401
from src.core.operators import validate as _validate  # noqa: F401
from src.core.operators.sdk import REGISTRY, OperatorDefinition, operator, register_operators

__all__ = ["REGISTRY", "OperatorDefinition", "operator", "register_operators"]
