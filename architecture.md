# Architecture

## Overview

This project is a Python-based blood report processing pipeline focused on CBC-style PDF reports. The current implementation is strongest in the extraction and validation stages: it reads a text-based PDF, cleans the extracted text, identifies patient context, parses supported CBC markers, validates the resulting structure, checks extraction plausibility, and decides whether the report is safe to move to a later interpretation stage.

Today, the codebase is best understood as two layers:

1. Implemented runtime pipeline
2. Scaffolded interpretation/knowledge layers for future work


## High-Level Flow

```text
PDF report
  ->
extraction.pdf_reader.extract_pdf_text
  ->
extraction.text_cleaner.clean_pdf_text
  ->
+-------------------------------+
| parallel logical consumers    |
| - patient_parser              |
| - parser (CBC markers)        |
+-------------------------------+
  ->
extraction.coverage.check_cbc_coverage
  ->
extraction.validator.validate_report
  ->
optional user correction loop
  ->
extraction.plausibility.check_report_plausibility
  ->
system decision: stop / review / ready for next stage
```


## Full Repository Structure

```text
.
|-- architecture.md
|-- main.py
|-- extraction/
|   |-- pdf_reader.py
|   |-- text_cleaner.py
|   |-- patient_parser.py
|   |-- parser.py
|   |-- validator.py
|   |-- plausibility.py
|   `-- coverage.py
|-- interpretation/
|   |-- __init__.py
|   |-- age_boundary.py
|   `-- reference_resolver.py
|-- medical_reference/
|   |-- provider.py
|   |-- models.py
|   `-- mayo/
|       |-- cbc.py
|       |-- diabetes.py
|       |-- kidney.py
|       |-- lipid.py
|       |-- liver.py
|       |-- thyroid.py
|       `-- __init__.py
|-- knowledge_engine/
|   |-- engine.py
|   |-- generator.py
|   |-- matcher.py
|   |-- models.py
|   |-- registry.py
|   |-- scorer.py
|   |-- knowledge/
|   |   |-- cbc/
|   |   |-- diabetes/
|   |   |-- kidney/
|   |   |-- lipid/
|   |   |-- liver/
|   |   `-- thyroid/
|   `-- models/
|       |-- evidence.py
|       |-- finding.py
|       |-- interpretation.py
|       |-- lab_result.py
|       |-- match_result.py
|       |-- patient.py
|       |-- pattern.py
|       |-- report.py
|       `-- __init__.py
|-- samples/
|   `-- reports/
|       |-- sample.pdf
|       `-- sample2.pdf
`-- tests/
    |-- test_age_boundary.py
    |-- test_coverage.py
    |-- test_patient_parser.py
    |-- test_plausibility.py
    |-- test_reference_resolver.py
    `-- test_validator.py
```

Notes:

- This is the full source-level repo structure, including folders that are currently empty or not yet used by the runtime pipeline.
- Generated cache folders such as `__pycache__/` are intentionally omitted because they are build/runtime artifacts rather than authored architecture.


## Implemented vs Scaffolded Areas

The repo contains both active code and forward-looking structure.

Implemented and used now:

- `main.py`
- most of `extraction/`
- `interpretation/reference_resolver.py`
- `interpretation/age_boundary.py`
- the current test files

Present in the repo but currently empty, lightly populated, or not wired into the main runtime flow:

- `knowledge_engine/*.py`
- `knowledge_engine/models/*.py`
- `knowledge_engine/knowledge/*`
- `medical_reference/provider.py`
- `medical_reference/models.py`

In this document, “scaffolded” means those files and directories are intentionally part of the planned architecture even if the implementation is still minimal or absent today.


## Runtime Architecture

### 1. Entry Point

[`main.py`](/C:/Users/sanja/Downloads/Desktop/hiiee/blood-report-analysis-ai/main.py) is the orchestration layer. It is a CLI-style script that coordinates the full report-processing sequence.

Responsibilities:

- Defines the input PDF path
- Executes the pipeline in ordered steps
- Prints operator-facing status and diagnostics
- Loops for missing patient data correction when needed
- Makes the final go/no-go decision for downstream analysis

This file currently contains orchestration and presentation logic together. That is acceptable for a prototype, but it also means `main.py` is acting as both controller and console UI.


### 2. Extraction Layer

The `extraction/` package owns conversion from raw PDF content into structured report data.

#### `pdf_reader.py`

Purpose:

- Opens a PDF using PyMuPDF (`fitz`)
- Extracts embedded text page by page
- Inserts page markers into the combined text

Key architectural note:

- This module supports text-based PDFs only.
- Scanned/image-only reports are explicitly rejected.

#### `text_cleaner.py`

Purpose:

- Removes page markers added by the reader
- Normalizes whitespace
- Removes some known PDF artifacts
- Produces a line-oriented text block suitable for rule-based parsing

This is a normalization boundary between low-level PDF extraction and domain parsing.

#### `patient_parser.py`

Purpose:

- Extracts patient age and sex from cleaned report text
- Normalizes age units such as `years`, `months`, `weeks`, and `days`
- Preserves both:
  - legacy `age` in years
  - precise `age_value` + `age_unit`

Important current behavior:

- Infants and neonates are preserved in original units instead of being converted to years.
- This is a good design choice for future age-aware reference resolution.

#### `parser.py`

Purpose:

- Detects a fixed set of CBC marker labels
- Maps raw labels to canonical internal names
- Reads nearby lines for value, unit, and raw reference range text

Current parser strategy:

- Rule-based
- Layout-sensitive
- Designed around a known report format

Important limitation:

- The parser only supports the aliases listed in `TEST_ALIASES`.
- It assumes the result value, unit, and reference appear in the next few lines after the test name.


### 3. Validation and Quality Gates

After extraction, the pipeline applies several quality gates before allowing downstream analysis.

#### `coverage.py`

Purpose:

- Measures how many supported CBC markers were successfully extracted
- Detects missing markers, duplicates, and unknown canonical names

Architectural role:

- Coverage is a parser completeness metric, not a clinical completeness metric.

#### `validator.py`

Purpose:

- Validates patient context
- Validates test completeness and structure
- Validates units against expected unit families
- Parses simple min/max lab reference ranges
- Produces report-level status and user-facing correction prompts

Outputs include:

- report status
- list of validated tests
- issue list
- `can_analyze`
- `user_questions`

Important current limitation:

- Patient validation still depends on `patient["age"]`, which means it effectively expects age in years.
- Although `patient_parser.py` supports `days`, `weeks`, and `months`, the validation gate is still adult/years-oriented.

#### `plausibility.py`

Purpose:

- Applies broad extraction sanity bounds to numeric values
- Flags suspiciously extreme values for manual verification

Architectural role:

- This is not interpretation.
- It is a defensive layer against OCR/parsing mistakes and malformed extraction.


### 4. Interpretation Utilities

The `interpretation/` package contains logic that bridges extraction output to future medical reasoning.

#### `reference_resolver.py`

Purpose:

- Normalizes raw reference text
- Resolves direct ranges like `13-18`
- Resolves sex-specific ranges
- Resolves age-banded ranges
- Supports the newer age representation (`age_value`, `age_unit`) while remaining backward compatible with legacy `age`

Architectural role:

- This is the strongest implemented piece of the interpretation side.
- It converts heterogeneous lab reference text into a structured interval that later reasoning engines can use.

#### `age_boundary.py`

Purpose:

- Supports age band comparison behavior for interpretation logic

This module is part of the age-aware interpretation foundation, even if the end-to-end engine is not wired yet.


## Future/Scaffolded Layers

### `medical_reference/`

This package appears intended to hold curated medical reference providers and domain-specific datasets. The `mayo/` subpackage suggests a plan to organize reference knowledge by panel or condition area.

Current state:

- `provider.py` and `models.py` are empty scaffolds
- the package is not currently active in the runtime path in `main.py`

Likely future role:

- source-of-truth medical ranges or interpretation knowledge
- provider abstraction for multiple reference datasets
- normalization layer between extracted analytes and knowledge sources

### `knowledge_engine/`

This package appears designed for the eventual interpretation engine.

Current state:

- engine, matcher, scorer, generator, registry, and model files are present but empty

Likely future role:

- match extracted lab results against patterns
- score relevance/severity/confidence
- generate findings and explanations
- produce a structured interpretation report

The directory structure already suggests a clean target architecture:

- `registry`: rule/pattern registration
- `matcher`: identify candidate patterns
- `scorer`: rank or weight findings
- `generator`: turn findings into readable output
- `models`: shared interpretation domain objects


## Data Model Shape

The current pipeline mostly passes plain Python dictionaries and lists rather than formal typed models.

Examples:

- `patient`
  - `age`
  - `age_value`
  - `age_unit`
  - `sex`
- `test`
  - `raw_name`
  - `canonical_name`
  - `value`
  - `unit`
  - `reference_raw`
  - optional `reference_parsed` after validation

Advantages:

- fast to prototype
- simple function boundaries

Tradeoffs:

- weak schema guarantees
- easy to drift field names across modules
- harder to evolve safely as the interpretation layer grows

The empty `knowledge_engine/models/` package suggests the project is already moving toward more formal domain models.


## Control Flow and Decision Gates

The current system is intentionally conservative. A report is only considered ready when all major gates pass.

Decision sequence in `main.py`:

1. Extraction must succeed
2. Validation must produce analyzable structure
3. Missing patient fields may trigger a user correction loop
4. Plausibility must not require manual verification
5. CBC coverage must be complete for the currently supported marker set
6. Duplicate markers must not remain
7. Partially valid test sets are rejected for next-stage analysis

This makes the architecture safety-first: the system prefers to stop rather than over-interpret incomplete or questionable input.


## Testing Architecture

The `tests/` directory currently focuses on rule-level validation for core parsing and interpretation helpers.

Covered areas include:

- age boundary handling
- CBC coverage
- patient parsing
- plausibility checks
- reference range resolution
- validator behavior

Architecturally, this is a good sign: most implemented business logic is factored into pure functions, which makes it easy to test without needing full PDF runs.

One caveat:

- Some test files are script-style and print-heavy rather than standard `pytest` test functions, so the suite may mix executable checks with formal automated tests.


## Current Strengths

- Clear staged pipeline from raw document to validated structure
- Conservative safety gates before interpretation
- Good separation between extraction, validation, and reference resolution
- Backward-compatible age model that still supports more precise pediatric handling
- Obvious extension points for a richer interpretation engine


## Current Constraints

- Runtime is tightly coupled to one CLI script
- Parser is format-specific and CBC-specific
- No OCR path for scanned reports
- Domain objects are still mostly untyped dictionaries
- Interpretation engine is scaffolded but not implemented
- Validation is not fully aligned yet with the newer age representation


## Recommended Next Architectural Steps

1. Move the pipeline in `main.py` into a service function such as `process_report(pdf_path) -> result`.
2. Introduce typed models for `Patient`, `LabTest`, `ValidationResult`, and `Report`.
3. Update validation to use `age_value` + `age_unit` instead of relying on `age` alone.
4. Make parser profiles explicit so multiple report layouts can be supported cleanly.
5. Wire `reference_resolver.py` into a first real interpretation service.
6. Decide whether `medical_reference/` will be static data, provider adapters, or both.
7. Build the `knowledge_engine/` around structured inputs and outputs rather than free-form dict passing.


## Summary

The project currently implements a solid extraction-and-safety pipeline for CBC blood report PDFs. The architecture is modular where it matters most today: document ingestion, normalization, parsing, validation, coverage checking, and plausibility checking are separated into focused modules. The interpretation layer is only partially realized, but the repository already contains the right seams for evolving into a fuller medical reasoning system.
