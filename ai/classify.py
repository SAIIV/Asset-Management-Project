"""AI #1 Classification and tagging (Design Document Section 4, service 1; UC-31).

    classify_asset(name, description) -> Suggestion

How it works (text only in Prototype 1; photo and PDF are a later increment):
  1. Each leaf category gets a vector of its text: "Top > Sub. description.
     Examples: <names of up to 10 assets already in it>". The vector is stored
     in Category.embedding and made again when the category text changes.
  2. The asset's name and description become a vector with the same local model.
  3. Each category's score is the best cosine similarity (not a probability)
     to its own text or to one of its example assets, so a new "Lenovo
     ThinkPad" is close to an existing "Dell Latitude laptop".
  4. Unsure if the top similarity is below 0.60, or less than 0.10 ahead of the
     next category: "Low confidence, please choose", nothing is preselected.
  5. Tags: the most used tags of assets in the suggested category.
     Material: a known material word found in the text (for furniture).
  6. Every call is written to AIRecord (D7). Nothing is saved to the asset until
     the custodian presses Register; then the answer (Accepted or Corrected) is added.
"""

import hashlib
import re
import time
from collections import Counter
from dataclasses import dataclass, field
from decimal import Decimal

from assets.models import Category
from circular_campus.choices import AIDecision, AITask, ModelKind

from .embeddings import MODEL_NAME, EmbeddingUnavailable, cosine, get_embedder
from .gateway import model_version, record, record_decision
from .matching import SEED_TAGS, clean_seed_text


PROMPT_VERSION = "classify-text v1"
THRESHOLDS = {"min_similarity": 0.60, "min_lead": 0.10}
TOP_N = 3
EXAMPLES_PER_CATEGORY = 10
MATERIALS = ("wood", "oak", "pine", "steel", "metal", "aluminium", "aluminum", "plastic", "glass",
             "fabric", "leather", "laminate", "mdf", "mesh")


@dataclass
class Suggestion:
    record_id: int | None = None
    ranked: list = field(default_factory=list)  # [(Category, similarity)], best first
    category: Category | None = None            # None when unsure or unavailable
    top_similarity: float | None = None
    unsure: bool = False
    fallback: bool = False
    message: str = ""
    tags: list = field(default_factory=list)
    material: str = ""


def _path(category):
    names, node = [], category
    while node is not None:
        names.append(node.name)
        node = node.parent_category
    return " > ".join(reversed(names))


def category_text(category):
    examples = list(category.assets.order_by("id").values_list("name", flat=True)[:EXAMPLES_PER_CATEGORY])
    text = f"{_path(category)}. {category.description}".strip()
    text = f"{text} Examples: {', '.join(examples)}." if examples else text
    return clean_seed_text(text)  # the seed's "(synthetic test data)" says nothing about the category


def leaf_categories():
    return list(Category.objects.filter(children__isnull=True).select_related("parent_category__parent_category"))


def category_vectors(embedder, categories):
    """{category id: vector}. A vector is (re)made only when the category text changed."""
    texts = {c.pk: category_text(c) for c in categories}
    stamp = {pk: hashlib.sha1(f"{embedder.name}|{t}".encode()).hexdigest()[:12] for pk, t in texts.items()}
    stale = [c for c in categories if c.embedding is None or _stamps.get(c.pk) != stamp[c.pk]]
    if stale:
        for category, vector in zip(stale, embedder.embed([texts[c.pk] for c in stale])):
            category.embedding = vector
            category.save(update_fields=["embedding"])
            _stamps[category.pk] = stamp[category.pk]
    return {c.pk: c.embedding for c in categories}


_stamps = {}  # category id -> hash of the text its stored vector was made from (per server process)
_example_vectors = {}  # (model name, asset name) -> vector, kept in memory for this server process


def category_scores(embedder, categories, asset_vector):
    """{category id: best similarity to the category text or to one of its example assets}."""
    vectors = category_vectors(embedder, categories)
    examples = {c.pk: list(c.assets.order_by("id").values_list("name", flat=True)[:EXAMPLES_PER_CATEGORY])
                for c in categories}
    missing = sorted({n for names in examples.values() for n in names if (embedder.name, n) not in _example_vectors})
    if missing:
        for name, vector in zip(missing, embedder.embed([clean_seed_text(n) for n in missing])):
            _example_vectors[(embedder.name, name)] = vector
    return {c.pk: max([cosine(asset_vector, vectors[c.pk])]
                      + [cosine(asset_vector, _example_vectors[(embedder.name, n)]) for n in examples[c.pk]])
            for c in categories}


def suggested_tags(category, limit=3):
    counts = Counter(tag.lower() for tags in category.assets.values_list("tags", flat=True) for tag in tags
                     if tag.lower() not in SEED_TAGS)  # never suggest the seed-data tag "synthetic"
    return [tag for tag, _ in counts.most_common(limit)]


def find_material(text):
    words = set(re.findall(r"[a-z]+", text.lower()))
    return next((m for m in MATERIALS if m in words), "")


def classify_asset(name, description=""):
    text = f"{name}. {description}".strip(". ").strip()
    version = model_version(ModelKind.EMBEDDING, MODEL_NAME, PROMPT_VERSION, thresholds=THRESHOLDS)
    inputs = {"name": name[:200], "descriptionWords": len(description.split()), "sourceUsed": "text"}
    started = time.monotonic()
    try:
        embedder = get_embedder()
        categories = leaf_categories()
        [asset_vector] = embedder.embed([text])
        scores = category_scores(embedder, categories, asset_vector)
    except EmbeddingUnavailable as error:
        item = record(version, AITask.CLASSIFY_ASSET, input_refs=inputs, fallback=True,
                      output={"error": str(error)}, latency_ms=int((time.monotonic() - started) * 1000))
        return Suggestion(record_id=item.pk, fallback=True, message=f"Suggestions unavailable: {error}.")

    ranked = sorted(((c, scores[c.pk]) for c in categories),

                    key=lambda pair: (-pair[1], pair[0].name))
    top = ranked[0][1] if ranked else 0.0
    lead = top - ranked[1][1] if len(ranked) > 1 else top
    unsure = top < THRESHOLDS["min_similarity"] or lead < THRESHOLDS["min_lead"]
    best = None if unsure or not ranked else ranked[0][0]
    suggestion = Suggestion(ranked=ranked[:TOP_N], category=best, top_similarity=top, unsure=unsure,
                            tags=suggested_tags(best) if best else [], material=find_material(text),
                            message="Low confidence, please choose." if unsure else "")
    item = record(version, AITask.CLASSIFY_ASSET, input_refs=inputs, score=Decimal(str(round(top, 3))),
                  unsure=unsure, latency_ms=int((time.monotonic() - started) * 1000), output={
                      "categoryId": best.pk if best else None,
                      "ranked": [{"categoryId": c.pk, "name": c.name, "similarity": round(s, 3)}
                                 for c, s in ranked[:TOP_N]],
                      "tags": suggestion.tags, "material": suggestion.material, "sourceUsed": "text",
                  })
    suggestion.record_id = item.pk
    return suggestion


def answer(record_id, chosen_category_id):
    """After Register: Accepted if the custodian kept the suggested category, otherwise Corrected."""
    from .models import AIRecord

    item = AIRecord.objects.filter(pk=record_id, task=AITask.CLASSIFY_ASSET).first()
    if item is None:
        return None
    suggested = item.output.get("categoryId") or next(iter(item.output.get("ranked", [])), {}).get("categoryId")
    decision = AIDecision.ACCEPTED if suggested == chosen_category_id else AIDecision.CORRECTED
    return record_decision(record_id, AITask.CLASSIFY_ASSET, decision)
