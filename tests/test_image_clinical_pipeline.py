"""Integration tests for IMAGE -> ClinicalPipeline."""

from pathlib import Path
from unittest.mock import MagicMock, patch

import numpy as np

from clinical_pipeline import ClinicalPipeline
from extraction.pipeline import InputType
from knowledge_engine.services.engine import KnowledgeEngine
from knowledge_engine.services.registry import KnowledgeRegistry
from vision.ocr_result import OCRResult


ROOT = Path(__file__).resolve().parents[1]

PATTERN = (
    ROOT
    / "knowledge_engine"
    / "knowledge"
    / "cbc"
    / "patterns"
    / "microcytic_pattern.yaml"
)


def _engine() -> KnowledgeEngine:
    registry = KnowledgeRegistry()
    registry.load_file(PATTERN)
    return KnowledgeEngine(registry)


def _ocr_result() -> OCRResult:
    text = """Age / Gender : 34 Years/Male
Hemoglobin
11.0
g/dl
[13.0-18.0]
M.C.V.
65
fl
[80-100]
M.C.H.
20
pg
[27-32]
R.D.W.
16
%
[11.5-14.5]
"""

    return OCRResult(
        text=text,
        lines=[],
        page_number=0,
        engine="test",
        confidence=0.99,
    )


def _preprocessed():
    result = MagicMock()
    result.image = np.zeros(
        (100, 100),
        dtype=np.uint8,
    )
    result.warnings = []
    return result


def test_image_array_reaches_knowledge_engine():

    pipeline = ClinicalPipeline(
        _engine()
    )

    ocr_engine = MagicMock()

    ocr_engine.extract.return_value = (
        _ocr_result()
    )

    image = np.zeros(
        (100, 100, 3),
        dtype=np.uint8,
    )

    with patch(
        "vision.preprocessor.preprocess_image",
        return_value=_preprocessed(),
    ):

        result = pipeline.run(
            image,
            ocr_engine=ocr_engine,
        )

    assert (
        result.extraction.source.input_type
        is InputType.IMAGE
    )

    assert (
        result.extraction.source.ocr_pages
        == 1
    )

    assert (
        result.extraction.validation[
            "can_analyze"
        ]
        is True
    )

    mcv = next(
        finding
        for finding in result.findings
        if finding.test_name == "mcv"
    )

    mch = next(
        finding
        for finding in result.findings
        if finding.test_name == "mch"
    )

    assert mcv.status.value == "low"
    assert mch.status.value == "low"

    assert (
        mcv.result.reference.minimum
        == 80.0
    )

    assert (
        mcv.result.reference.maximum
        == 100.0
    )

    assert len(result.matches) == 1

    assert (
        result.matches[0].pattern.id
        == "microcytic_cbc_pattern"
    )

    assert (
        result.matches[0].matched
        is True
    )

    assert (
        ocr_engine.extract.call_count
        == 1
    )


def test_image_file_reaches_same_downstream_pipeline():

    pipeline = ClinicalPipeline(
        _engine()
    )

    image_path = (
        ROOT
        / "samples"
        / "reports"
        / "test_integration.png"
    )

    image_path.write_bytes(b"test")

    try:

        ocr_engine = MagicMock()

        ocr_engine.extract.return_value = (
            _ocr_result()
        )

        with patch(
            "vision.preprocessor.load_image",
            return_value=np.zeros(
                (100, 100, 3),
                dtype=np.uint8,
            ),
        ), patch(
            "vision.preprocessor.preprocess_image",
            return_value=_preprocessed(),
        ):

            result = pipeline.run(
                image_path,
                ocr_engine=ocr_engine,
            )

        assert (
            result.extraction.source.input_type
            is InputType.IMAGE
        )

        assert (
            result.extraction.source.path
            == str(image_path)
        )

        assert (
            result.extraction.validation[
                "can_analyze"
            ]
            is True
        )

        assert len(result.findings) >= 2

        assert (
            result.matches[0].pattern.id
            == "microcytic_cbc_pattern"
        )

        assert (
            result.matches[0].matched
            is True
        )

    finally:

        image_path.unlink(
            missing_ok=True
        )