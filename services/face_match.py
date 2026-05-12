"""
Module 1 — Face Match AI (Layer 1)
====================================
Biometric identity verification using facenet-pytorch.

Uses MTCNN for face detection and InceptionResnetV1 (pre-trained on
VGGFace2) for 512-d face embedding generation. Cosine similarity
between the live selfie embedding and the official ID photo embedding
determines whether the same person is present in both images.

Threshold of 0.82 was chosen based on empirical fintech KYC benchmarks
for balancing false-accept vs. false-reject rates.
"""

import base64
import io
import logging
from typing import Any

import numpy as np
import torch
from facenet_pytorch import MTCNN, InceptionResnetV1
from PIL import Image

logger = logging.getLogger("clearpass.face_match")

# ---------------------------------------------------------------------------
# Model Initialisation (runs once at import / startup)
# ---------------------------------------------------------------------------
_device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
logger.info("Face-match device: %s", _device)

_mtcnn = MTCNN(
    image_size=160,
    margin=20,
    keep_all=False,         # return only highest-probability face
    min_face_size=40,
    thresholds=[0.6, 0.7, 0.7],
    device=_device,
)

_resnet = InceptionResnetV1(pretrained="vggface2").eval().to(_device)

FACE_MATCH_THRESHOLD = 0.82


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _decode_b64_image(b64_string: str) -> Image.Image:
    """Decode a base64-encoded image string into a PIL Image (RGB)."""
    try:
        image_bytes = base64.b64decode(b64_string)
        image = Image.open(io.BytesIO(image_bytes)).convert("RGB")
        return image
    except Exception as exc:
        logger.error("Failed to decode base64 image: %s", exc)
        raise ValueError(f"Image decode failure: {exc}") from exc


def _get_embedding(image: Image.Image) -> np.ndarray:
    """Detect a face and return its 512-d embedding vector."""
    face_tensor = _mtcnn(image)
    if face_tensor is None:
        raise ValueError("No face detected in the provided image.")

    # face_tensor shape: (3, 160, 160) — add batch dim
    face_batch = face_tensor.unsqueeze(0).to(_device)
    with torch.no_grad():
        embedding = _resnet(face_batch)

    return embedding.cpu().numpy().flatten()


def _cosine_similarity(vec_a: np.ndarray, vec_b: np.ndarray) -> float:
    """Compute cosine similarity between two 1-D vectors."""
    dot = np.dot(vec_a, vec_b)
    norm = np.linalg.norm(vec_a) * np.linalg.norm(vec_b)
    if norm == 0:
        return 0.0
    return float(dot / norm)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def match_faces(live_image_b64: str, official_image_b64: str) -> dict[str, Any]:
    """
    Compare a live selfie against an official ID photo.

    Parameters
    ----------
    live_image_b64 : str
        Base64-encoded JPEG/PNG of the live selfie.
    official_image_b64 : str
        Base64-encoded JPEG/PNG of the official ID photo.

    Returns
    -------
    dict
        {
            "score": float,       # cosine similarity (0–1)
            "pass": bool,         # True if score >= threshold
            "threshold": float    # the threshold used
        }

    Raises
    ------
    ValueError
        If an image cannot be decoded or no face is detected.
    """
    logger.info("Starting face-match comparison")

    live_img = _decode_b64_image(live_image_b64)
    official_img = _decode_b64_image(official_image_b64)

    live_embedding = _get_embedding(live_img)
    official_embedding = _get_embedding(official_img)

    similarity = _cosine_similarity(live_embedding, official_embedding)
    passed = similarity >= FACE_MATCH_THRESHOLD

    logger.info(
        "Face-match result — similarity: %.4f, threshold: %.2f, pass: %s",
        similarity,
        FACE_MATCH_THRESHOLD,
        passed,
    )

    return {
        "score": round(similarity, 4),
        "pass": passed,
        "threshold": FACE_MATCH_THRESHOLD,
    }
