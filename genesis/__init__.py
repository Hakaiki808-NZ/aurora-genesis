from .model import Genesis
from .cognition import CognitionEngine
from .cognition_patch import apply_patch

apply_patch(CognitionEngine)

__all__=["Genesis"]
__version__="v0.1"
