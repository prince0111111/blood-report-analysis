"""
vision/ocr_config.py

OCR engine configuration and factory.

PURPOSE
-------
Centralise all OCR engine selection and configuration so
that callers never import engine-specific classes directly.

USAGE
-----
    from vision.ocr_config import create_ocr_engine

    engine = create_ocr_engine()          # default
    engine = create_ocr_engine("paddle")  # explicit
    result = engine.extract(image)

ADDING A NEW ENGINE
-------------------
1. Create a new module in vision/ (e.g. ocr_tesseract.py)
2. Subclass BaseOCREngine and implement extract()
3. Register the engine name in _ENGINE_REGISTRY below
"""

from __future__ import annotations

import logging
from typing import Optional

from vision.ocr_base import BaseOCREngine, OCREngineConfig


# =========================================================
# LOGGER
# =========================================================

logger = logging.getLogger(__name__)


# =========================================================
# SUPPORTED ENGINE NAMES
# =========================================================

ENGINE_PADDLE = "paddle"

DEFAULT_ENGINE = ENGINE_PADDLE

SUPPORTED_ENGINES = {
    ENGINE_PADDLE,
}


# =========================================================
# ENGINE REGISTRY
# =========================================================
#
# Maps engine name -> (module path, class name).
#
# Engines are imported lazily so that missing optional
# dependencies do not break the import of this module.
# =========================================================

_ENGINE_REGISTRY = {
    ENGINE_PADDLE: (
        "vision.ocr_paddle",
        "PaddleOCREngine"
    ),
}


# =========================================================
# FACTORY
# =========================================================

def create_ocr_engine(
    engine_name: str = DEFAULT_ENGINE,
    config: Optional[OCREngineConfig] = None
) -> BaseOCREngine:
    """
    Create and return an OCR engine instance.

    Parameters
    ----------
    engine_name : str
        Name of the engine to create.
        Currently supported: "paddle".
        Default: "paddle".
    config : OCREngineConfig | None
        Engine configuration.
        If None, default configuration is used.

    Returns
    -------
    BaseOCREngine
        A concrete OCR engine instance.

    Raises
    ------
    ValueError
        If engine_name is not in SUPPORTED_ENGINES.
    ImportError
        If the engine's dependencies are not installed.
    """

    if engine_name not in _ENGINE_REGISTRY:
        raise ValueError(
            f"Unknown OCR engine: {engine_name!r}. "
            f"Supported engines: "
            f"{sorted(SUPPORTED_ENGINES)}"
        )

    module_path, class_name = (
        _ENGINE_REGISTRY[engine_name]
    )

    # -------------------------------------------------
    # Lazy import — only load the engine module when
    # it is actually requested.
    # -------------------------------------------------

    import importlib

    try:

        module = importlib.import_module(module_path)

    except ImportError as error:
        raise ImportError(
            f"Could not import OCR engine "
            f"{engine_name!r} from {module_path!r}. "
            f"Ensure the required dependencies are "
            f"installed. Original error: {error}"
        ) from error

    engine_class = getattr(module, class_name)

    engine = engine_class(config=config)

    logger.debug(
        "create_ocr_engine: created %s with config=%s",
        engine_name,
        config
    )

    return engine
