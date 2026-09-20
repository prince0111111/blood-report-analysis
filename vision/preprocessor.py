"""
vision/preprocessor.py

Image preprocessing pipeline for blood report images.

PURPOSE
-------
Accept a raw image (file path or numpy array) and return
a cleaned, OCR-ready image without modifying the original.

PIPELINE ORDER
--------------
1. Load
2. Validate
3. Resolution check / upscale if needed
4. Grayscale conversion
5. Noise reduction
6. Contrast enhancement (CLAHE)
7. Adaptive thresholding / binarization
8. Deskew
9. Border cleanup

IMPORTANT
---------
- The original input is NEVER modified or overwritten.
- Every function is independently usable.
- Aggressive processing that destroys thin text is avoided.
- All functions accept and return numpy arrays (BGR or
  grayscale depending on stage).
"""

import logging
import math
from pathlib import Path
from typing import Optional, Union

import cv2
import numpy as np


# =========================================================
# LOGGER
# =========================================================

logger = logging.getLogger(__name__)


# =========================================================
# CONSTANTS
# =========================================================

# Minimum DPI equivalent — images below this pixel density
# are upscaled before OCR.
# 300 DPI on A4 ≈ 2480 × 3508 px.
# We use a simpler short-edge threshold.

MIN_SHORT_EDGE_PX = 1000

# Target short edge when upscaling a low-resolution image.
TARGET_SHORT_EDGE_PX = 1400

# Maximum skew angle (degrees) we attempt to correct.
# Beyond this the image is likely not a document scan.
MAX_DESKEW_ANGLE_DEG = 45.0

# Border crop fraction — remove this fraction of the image
# on each side to eliminate scanner borders.
BORDER_CROP_FRACTION = 0.01


# =========================================================
# RESULT CONTAINER
# =========================================================

class PreprocessingResult:
    """
    Holds the output of the preprocessing pipeline.

    Attributes
    ----------
    image : np.ndarray
        The processed image (grayscale, uint8).
    original_shape : tuple
        (height, width, channels) of the input image.
    final_shape : tuple
        (height, width) of the processed image.
    steps_applied : list[str]
        Ordered list of processing steps that ran.
    warnings : list[str]
        Non-fatal issues encountered during processing.
    """

    def __init__(
        self,
        image: np.ndarray,
        original_shape: tuple,
        steps_applied: list,
        warnings: list
    ):
        self.image = image
        self.original_shape = original_shape
        self.final_shape = image.shape[:2]
        self.steps_applied = steps_applied
        self.warnings = warnings

    def __repr__(self) -> str:
        return (
            f"PreprocessingResult("
            f"original={self.original_shape}, "
            f"final={self.final_shape}, "
            f"steps={self.steps_applied})"
        )


# =========================================================
# STEP 1 — LOAD
# =========================================================

def load_image(
    source: Union[str, Path, np.ndarray]
) -> np.ndarray:
    """
    Load an image from a file path or pass through a
    numpy array unchanged.

    Parameters
    ----------
    source : str | Path | np.ndarray
        File path to an image, or an already-loaded array.

    Returns
    -------
    np.ndarray
        BGR image array (uint8).

    Raises
    ------
    FileNotFoundError
        If the path does not exist.
    ValueError
        If the file cannot be decoded as an image, or if
        the array is not a valid image.
    """

    if isinstance(source, np.ndarray):

        if source.ndim not in (2, 3):
            raise ValueError(
                "Array must be 2-D (grayscale) or "
                "3-D (colour)."
            )

        if source.size == 0:
            raise ValueError(
                "Image array is empty."
            )

        logger.debug("load_image: received numpy array")

        return source.copy()

    path = Path(source)

    if not path.exists():
        raise FileNotFoundError(
            f"Image not found: {path}"
        )

    image = cv2.imread(str(path), cv2.IMREAD_COLOR)

    if image is None:
        raise ValueError(
            f"Could not decode image: {path}. "
            "The file may be corrupted or in an "
            "unsupported format."
        )

    logger.debug(
        "load_image: loaded %s shape=%s",
        path.name,
        image.shape
    )

    return image


# =========================================================
# STEP 2 — VALIDATE
# =========================================================

def validate_image(image: np.ndarray) -> dict:
    """
    Perform basic structural validation on a loaded image.

    Parameters
    ----------
    image : np.ndarray
        Image array to validate.

    Returns
    -------
    dict
        {
            "valid": bool,
            "reason": str | None
        }
    """

    if not isinstance(image, np.ndarray):
        return {
            "valid": False,
            "reason": "Input is not a numpy array."
        }

    if image.size == 0:
        return {
            "valid": False,
            "reason": "Image array is empty."
        }

    if image.ndim not in (2, 3):
        return {
            "valid": False,
            "reason": (
                f"Unexpected array dimensions: {image.ndim}. "
                "Expected 2 (grayscale) or 3 (colour)."
            )
        }

    height, width = image.shape[:2]

    if height < 10 or width < 10:
        return {
            "valid": False,
            "reason": (
                f"Image is too small: {width}×{height} px. "
                "Minimum is 10×10 px."
            )
        }

    if image.dtype != np.uint8:
        return {
            "valid": False,
            "reason": (
                f"Unexpected dtype: {image.dtype}. "
                "Expected uint8."
            )
        }

    return {
        "valid": True,
        "reason": None
    }


# =========================================================
# STEP 3 — RESOLUTION HANDLING / UPSCALE
# =========================================================

def ensure_minimum_resolution(
    image: np.ndarray
) -> np.ndarray:
    """
    Upscale the image if its short edge is below the
    minimum threshold required for reliable OCR.

    Uses INTER_CUBIC for upscaling (better text sharpness
    than INTER_LINEAR at moderate scale factors).

    Parameters
    ----------
    image : np.ndarray
        Input image (any colour space).

    Returns
    -------
    np.ndarray
        Original image if already large enough, or an
        upscaled copy.
    """

    height, width = image.shape[:2]

    short_edge = min(height, width)

    if short_edge >= MIN_SHORT_EDGE_PX:
        logger.debug(
            "ensure_minimum_resolution: "
            "short edge %d px — no upscale needed",
            short_edge
        )
        return image

    scale = TARGET_SHORT_EDGE_PX / short_edge

    new_width = int(width * scale)
    new_height = int(height * scale)

    upscaled = cv2.resize(
        image,
        (new_width, new_height),
        interpolation=cv2.INTER_CUBIC
    )

    logger.debug(
        "ensure_minimum_resolution: "
        "upscaled %dx%d -> %dx%d (scale=%.2f)",
        width, height,
        new_width, new_height,
        scale
    )

    return upscaled


# =========================================================
# STEP 4 — GRAYSCALE CONVERSION
# =========================================================

def to_grayscale(image: np.ndarray) -> np.ndarray:
    """
    Convert a BGR colour image to grayscale.

    If the image is already grayscale (2-D or single-
    channel 3-D), it is returned as-is.

    Parameters
    ----------
    image : np.ndarray
        BGR or grayscale image.

    Returns
    -------
    np.ndarray
        Single-channel grayscale image (uint8).
    """

    if image.ndim == 2:
        logger.debug("to_grayscale: already grayscale")
        return image

    if image.ndim == 3 and image.shape[2] == 1:
        logger.debug(
            "to_grayscale: single-channel 3-D, squeezing"
        )
        return image[:, :, 0]

    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

    logger.debug("to_grayscale: converted BGR -> gray")

    return gray


# =========================================================
# STEP 5 — NOISE REDUCTION
# =========================================================

def reduce_noise(image: np.ndarray) -> np.ndarray:
    """
    Apply a light Gaussian blur to reduce high-frequency
    noise before thresholding.

    Kernel size 3×3 is intentionally conservative — it
    smooths salt-and-pepper noise without blurring thin
    text strokes.

    Parameters
    ----------
    image : np.ndarray
        Grayscale image.

    Returns
    -------
    np.ndarray
        Denoised grayscale image.
    """

    denoised = cv2.GaussianBlur(
        image,
        (3, 3),
        sigmaX=0
    )

    logger.debug("reduce_noise: Gaussian blur 3x3 applied")

    return denoised


# =========================================================
# STEP 6 — CONTRAST ENHANCEMENT
# =========================================================

def enhance_contrast(image: np.ndarray) -> np.ndarray:
    """
    Apply CLAHE (Contrast Limited Adaptive Histogram
    Equalization) to improve local contrast.

    CLAHE is preferred over global histogram equalization
    because it avoids over-amplifying noise in uniform
    regions (e.g. blank margins of a lab report).

    Parameters
    ----------
    image : np.ndarray
        Grayscale image.

    Returns
    -------
    np.ndarray
        Contrast-enhanced grayscale image.
    """

    clahe = cv2.createCLAHE(
        clipLimit=2.0,
        tileGridSize=(8, 8)
    )

    enhanced = clahe.apply(image)

    logger.debug(
        "enhance_contrast: CLAHE applied "
        "(clipLimit=2.0, tileGrid=8x8)"
    )

    return enhanced


# =========================================================
# STEP 7 — THRESHOLDING / BINARIZATION
# =========================================================

def binarize(image: np.ndarray) -> np.ndarray:
    """
    Convert a grayscale image to a binary (black/white)
    image using adaptive Gaussian thresholding.

    Adaptive thresholding is used instead of a global
    threshold because blood report scans often have
    uneven illumination across the page.

    Block size 31 and C=10 are tuned for typical A4
    lab report text at 300 DPI equivalent.

    Parameters
    ----------
    image : np.ndarray
        Grayscale image.

    Returns
    -------
    np.ndarray
        Binary image (0 = black, 255 = white).
    """

    binary = cv2.adaptiveThreshold(
        image,
        maxValue=255,
        adaptiveMethod=cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
        thresholdType=cv2.THRESH_BINARY,
        blockSize=31,
        C=10
    )

    logger.debug(
        "binarize: adaptive Gaussian threshold applied "
        "(blockSize=31, C=10)"
    )

    return binary


# =========================================================
# STEP 8 — DESKEW
# =========================================================

def _compute_skew_angle(image: np.ndarray) -> float:
    """
    Estimate the skew angle of a document image using
    the Hough line transform on edge-detected content.

    Returns 0.0 if the angle cannot be reliably estimated.

    Parameters
    ----------
    image : np.ndarray
        Grayscale or binary image.

    Returns
    -------
    float
        Estimated skew angle in degrees.
        Positive = clockwise tilt.
        Negative = counter-clockwise tilt.
    """

    # Edge detection
    edges = cv2.Canny(image, 50, 150, apertureSize=3)

    # Probabilistic Hough lines
    lines = cv2.HoughLinesP(
        edges,
        rho=1,
        theta=np.pi / 180,
        threshold=100,
        minLineLength=100,
        maxLineGap=10
    )

    if lines is None or len(lines) == 0:
        logger.debug(
            "_compute_skew_angle: no lines detected, "
            "returning 0.0"
        )
        return 0.0

    angles = []

    for line in lines:

        # OpenCV 4 returns shape (N, 1, 4).
        # OpenCV 5 returns shape (N, 4).
        # Flatten to (4,) to handle both.
        coords = np.array(line).flatten()
        x1, y1, x2, y2 = int(coords[0]), int(coords[1]), int(coords[2]), int(coords[3])

        if x2 == x1:
            continue

        angle = math.degrees(
            math.atan2(y2 - y1, x2 - x1)
        )

        # Only consider near-horizontal lines
        if abs(angle) < MAX_DESKEW_ANGLE_DEG:
            angles.append(angle)

    if not angles:
        logger.debug(
            "_compute_skew_angle: no usable angles, "
            "returning 0.0"
        )
        return 0.0

    median_angle = float(np.median(angles))

    logger.debug(
        "_compute_skew_angle: median angle = %.2f deg "
        "from %d lines",
        median_angle,
        len(angles)
    )

    return median_angle


def deskew(image: np.ndarray) -> np.ndarray:
    """
    Rotate the image to correct document skew.

    Uses the median angle of detected Hough lines.
    If the estimated angle is negligible (< 0.5°) or
    exceeds MAX_DESKEW_ANGLE_DEG, the image is returned
    unchanged.

    Rotation fills the background with white (255) to
    avoid introducing black borders that confuse OCR.

    Parameters
    ----------
    image : np.ndarray
        Grayscale image.

    Returns
    -------
    np.ndarray
        Deskewed grayscale image.
    """

    angle = _compute_skew_angle(image)

    if abs(angle) < 0.5:
        logger.debug(
            "deskew: angle %.2f° is negligible, "
            "skipping rotation",
            angle
        )
        return image

    if abs(angle) > MAX_DESKEW_ANGLE_DEG:
        logger.warning(
            "deskew: angle %.2f° exceeds maximum "
            "%.1f° — skipping rotation",
            angle,
            MAX_DESKEW_ANGLE_DEG
        )
        return image

    height, width = image.shape[:2]

    center = (width / 2.0, height / 2.0)

    rotation_matrix = cv2.getRotationMatrix2D(
        center,
        angle,
        scale=1.0
    )

    rotated = cv2.warpAffine(
        image,
        rotation_matrix,
        (width, height),
        flags=cv2.INTER_CUBIC,
        borderMode=cv2.BORDER_CONSTANT,
        borderValue=255
    )

    logger.debug(
        "deskew: rotated by %.2f°",
        angle
    )

    return rotated


# =========================================================
# STEP 9 — BORDER CLEANUP
# =========================================================

def remove_border(image: np.ndarray) -> np.ndarray:
    """
    Crop a small fraction of each edge to remove scanner
    borders, dark margins, and page-edge artifacts.

    The crop fraction is intentionally small
    (BORDER_CROP_FRACTION = 1%) to avoid removing any
    content near the edges of the report.

    Parameters
    ----------
    image : np.ndarray
        Grayscale image.

    Returns
    -------
    np.ndarray
        Cropped image with border artifacts removed.
    """

    height, width = image.shape[:2]

    margin_y = max(1, int(height * BORDER_CROP_FRACTION))
    margin_x = max(1, int(width * BORDER_CROP_FRACTION))

    cropped = image[
        margin_y: height - margin_y,
        margin_x: width - margin_x
    ]

    logger.debug(
        "remove_border: cropped margins "
        "y=%d px, x=%d px",
        margin_y,
        margin_x
    )

    return cropped


# =========================================================
# FULL PIPELINE
# =========================================================

def preprocess_image(
    source: Union[str, Path, np.ndarray],
    upscale: bool = True,
    denoise: bool = True,
    enhance: bool = True,
    binarize_image: bool = True,
    deskew_image: bool = True,
    clean_border: bool = True
) -> PreprocessingResult:
    """
    Run the full preprocessing pipeline on a blood report
    image.

    The original source is never modified.

    Parameters
    ----------
    source : str | Path | np.ndarray
        File path or already-loaded image array.
    upscale : bool
        Upscale low-resolution images. Default True.
    denoise : bool
        Apply Gaussian noise reduction. Default True.
    enhance : bool
        Apply CLAHE contrast enhancement. Default True.
    binarize_image : bool
        Apply adaptive thresholding. Default True.
    deskew_image : bool
        Correct document skew. Default True.
    clean_border : bool
        Remove scanner border artifacts. Default True.

    Returns
    -------
    PreprocessingResult
        Contains the processed image and metadata.

    Raises
    ------
    FileNotFoundError
        If source is a path that does not exist.
    ValueError
        If the image cannot be loaded or fails validation.
    """

    steps_applied = []
    warnings = []

    # -------------------------------------------------
    # LOAD
    # -------------------------------------------------

    image = load_image(source)

    original_shape = image.shape

    steps_applied.append("load")

    logger.info(
        "preprocess_image: loaded image shape=%s",
        original_shape
    )

    # -------------------------------------------------
    # VALIDATE
    # -------------------------------------------------

    validation = validate_image(image)

    if not validation["valid"]:
        raise ValueError(
            f"Image validation failed: "
            f"{validation['reason']}"
        )

    steps_applied.append("validate")

    # -------------------------------------------------
    # UPSCALE
    # -------------------------------------------------

    if upscale:

        image = ensure_minimum_resolution(image)

        if image.shape[:2] != original_shape[:2]:
            steps_applied.append("upscale")

    # -------------------------------------------------
    # GRAYSCALE
    # -------------------------------------------------

    image = to_grayscale(image)

    steps_applied.append("grayscale")

    # -------------------------------------------------
    # DENOISE
    # -------------------------------------------------

    if denoise:

        image = reduce_noise(image)

        steps_applied.append("denoise")

    # -------------------------------------------------
    # CONTRAST
    # -------------------------------------------------

    if enhance:

        image = enhance_contrast(image)

        steps_applied.append("enhance_contrast")

    # -------------------------------------------------
    # BINARIZE
    # -------------------------------------------------

    if binarize_image:

        image = binarize(image)

        steps_applied.append("binarize")

    # -------------------------------------------------
    # DESKEW
    # -------------------------------------------------

    if deskew_image:

        image = deskew(image)

        steps_applied.append("deskew")

    # -------------------------------------------------
    # BORDER CLEANUP
    # -------------------------------------------------

    if clean_border:

        image = remove_border(image)

        steps_applied.append("remove_border")

    # -------------------------------------------------
    # RESULT
    # -------------------------------------------------

    logger.info(
        "preprocess_image: pipeline complete — "
        "steps=%s final_shape=%s",
        steps_applied,
        image.shape
    )

    return PreprocessingResult(
        image=image,
        original_shape=original_shape,
        steps_applied=steps_applied,
        warnings=warnings
    )
