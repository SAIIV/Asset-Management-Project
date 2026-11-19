"""AI gateway: the EmbeddingModel adapter (Design Document 10.3, decision AD-3).

    get_embedder().embed(["text", ...]) -> one list of 384 numbers per text

The model (all-MiniLM-L6-v2) runs locally on the PC, so asset text never
leaves it and no API key is needed. It is loaded once, on first use. If the
library or the model is missing, EmbeddingUnavailable is raised and every
caller uses its fallback (classification: "Suggestions unavailable").

Setting AI_EMBEDDINGS=off in .env switches it off.
"""

import math

from django.conf import settings

MODEL_ID = "sentence-transformers/all-MiniLM-L6-v2"
MODEL_NAME = "all-MiniLM-L6-v2"
MAX_WORDS = 256  # the model reads at most 256 word pieces


class EmbeddingUnavailable(Exception):
    """The embedding model cannot be used right now."""


class MiniLMEmbedder:
    name = MODEL_NAME

    def __init__(self):
        try:
            from sentence_transformers import SentenceTransformer
        except ImportError as error:
            raise EmbeddingUnavailable("the sentence-transformers library is not installed") from error
        try:
            self._model = SentenceTransformer(MODEL_ID, device="cpu")
        except Exception as error:  # no internet on first download, damaged files, ...
            raise EmbeddingUnavailable(f"the {MODEL_NAME} model could not be loaded ({error})") from error

    def embed(self, texts):
        clipped = [" ".join(str(text).split()[:MAX_WORDS]) for text in texts]
        vectors = self._model.encode(clipped, normalize_embeddings=True, show_progress_bar=False)
        return [[float(x) for x in vector] for vector in vectors]


_embedder = None


def get_embedder():
    """The shared embedding model (loaded once per server process)."""
    global _embedder
    if str(getattr(settings, "AI_EMBEDDINGS", "minilm")).lower() == "off":
        raise EmbeddingUnavailable("embeddings are switched off (AI_EMBEDDINGS=off)")
    if _embedder is None:
        _embedder = MiniLMEmbedder()
    return _embedder


def cosine(a, b):
    """Cosine similarity from -1 to 1 (0 when a vector is all zeros). Not a probability."""
    a, b = [float(x) for x in a], [float(x) for x in b]
    dot = sum(x * y for x, y in zip(a, b))
    norm = math.sqrt(sum(x * x for x in a)) * math.sqrt(sum(y * y for y in b))
    return dot / norm if norm else 0.0
