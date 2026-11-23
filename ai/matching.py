"""AI #2 Matching and ranking (Design Document Section 4 services 2 and 3, Section 8.8, Section 11; UC-32).

    rank_matches(user, purpose, specs, quantity, required_by, urgency, preferred_condition) -> Ranking
    save_matches(request, ai_record_id, chosen)  -> the requester's choice (gate 2) stored with the ranking

Steps (Section 8.8):
  1. Filter. Only units the requester may ask for (catalogue, another department)
     that contain every mandatory specification. Similarity never brings a
     filtered-out unit back (BR-04).
  2. Embed. The request text and each unit's text become vectors with the local
     MiniLM model. A unit's vector is stored in Asset.embedding and made again
     when its text changes.
  3. Score (Section 11). Five factors between 0 and 1:
       S function   0.45  (similarity - 0.40) / 0.50, kept between 0 and 1
       T condition  0.20  1 at or above the preferred grade, 0.5 one grade lower, 0 lower
                          (Prototype 1 has no preferred specifications, so T is the condition part)
       R ready      0.15  1 if ready at least the urgency slack before the date (High 5, Normal 2,
                          Low 0 days); otherwise 0.5 + 0.5 x days early / slack. Catalogue units are ready today.
       C cost       0.10  repair and transfer cost are not recorded in Prototype 1 -> dropped for all
       E benefit    0.10  this unit's mass / the largest mass in the set; dropped for all if any unit has no mass
     A dropped factor's weight is shared out so the weights add up to 1 again.
     Score = 100 x sum(weight x value), rounded. Ties: Asset ID.
  4. Explain. Two strongest reasons from fixed sentences (no language model), warnings.
     Below 70: "Weak match" and no top pick.
  5. Record. One AIRecord (D7). If the model cannot be used: the eligible units in Asset ID
     order, labelled "not ranked".
"""

import hashlib
import re
import time
from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal

from assets.models import Asset
from circular_campus.choices import AIDecision, AITask, Condition, MatchDecision, ModelKind, Urgency

from .embeddings import MODEL_NAME, EmbeddingUnavailable, cosine, get_embedder
from .gateway import model_version, record, record_decision

RANKING_NAME = "weighted score v1"
WEIGHTS = {"S": 0.45, "T": 0.20, "R": 0.15, "C": 0.10, "E": 0.10}
THRESHOLDS = {"strong_score": 70, "weak_similarity": 0.40}
FACTOR_LABELS = {"S": "Function and purpose", "T": "Condition fit", "R": "Ready by date",
                 "C": "Repair + transfer cost", "E": "Environmental benefit"}
DROPPED_BECAUSE = {"C": "repair and transfer cost are not recorded in Prototype 1",
                   "E": "at least one unit has no recorded mass"}
GRADES = [Condition.NEEDS_REPAIR, Condition.FAIR, Condition.GOOD, Condition.NEW]  # worst to best
SLACK_DAYS = {Urgency.HIGH: 5, Urgency.NORMAL: 2, Urgency.LOW: 0}


@dataclass
class Match:
    asset: Asset
    similarity: float
    factors: dict          # {"S": 0.8, ..., "C": None} None = not compared
    score: int
    rank: int = 0
    reasons: list = field(default_factory=list)
    warnings: list = field(default_factory=list)

    @property
    def label(self):
        return "Strong match" if self.score >= THRESHOLDS["strong_score"] else "Weak match"

    @property
    def bars(self):
        """[(letter, label, weight, value or None, percent)] for the factor bars."""
        return [(k, FACTOR_LABELS[k], WEIGHTS[k], v, round(100 * v) if v is not None else 0)
                for k, v in self.factors.items()]


@dataclass
class Ranking:
    record_id: int | None = None
    matches: list = field(default_factory=list)
    excluded: list = field(default_factory=list)   # [(Asset, reason)]
    dropped: dict = field(default_factory=dict)    # {"C": reason}
    top_pick: Match | None = None
    fallback: bool = False
    message: str = ""
    warnings: list = field(default_factory=list)


def _clamp(value):
    return max(0.0, min(1.0, value))


#: Words the seed data adds to every demo record. They say nothing about the item, so they are left
#: out of the text that is compared (otherwise every record looks alike and similarity drops).
SEED_NOISE = [r"\(synthetic[^)]*\)", r"SYNTHETIC test record #?\d*\.?", r"for Circular Campus development\.?",
              r"\(synthetic test data\)", r"\(top category, synthetic test data\)"]
SEED_TAGS = {"synthetic"}


def clean_seed_text(text):
    for pattern in SEED_NOISE:
        text = re.sub(pattern, " ", text, flags=re.IGNORECASE)
    return " ".join(text.split())


def asset_text(asset):
    tags = ", ".join(t for t in asset.tags if t.lower() not in SEED_TAGS)
    return clean_seed_text(f"{asset.name}. {asset.description} Category: {asset.category.name}. {tags}")


_stamps = {}  # asset id -> hash of the text its stored vector was made from (per server process)


def asset_vectors(embedder, assets):
    texts = {a.pk: asset_text(a) for a in assets}
    stamp = {pk: hashlib.sha1(f"{embedder.name}|{t}".encode()).hexdigest()[:12] for pk, t in texts.items()}
    stale = [a for a in assets if a.embedding is None or _stamps.get(a.pk) != stamp[a.pk]]
    if stale:
        for asset, vector in zip(stale, embedder.embed([texts[a.pk] for a in stale])):
            Asset.objects.filter(pk=asset.pk).update(embedding=vector)  # not a user edit: no version bump
            asset.embedding = vector
            _stamps[asset.pk] = stamp[asset.pk]
    return {a.pk: a.embedding for a in assets}


def missing_specs(asset, specs):
    text = f"{asset.name} {asset.description} {' '.join(asset.tags)}".lower()
    return [spec for spec in specs if spec.lower() not in text]


def condition_fit(condition, preferred):
    if not preferred:
        return 1.0
    gap = GRADES.index(preferred) - GRADES.index(condition)
    return 1.0 if gap <= 0 else 0.5 if gap == 1 else 0.0


def ready_fit(required_by, urgency, today):
    slack, early = SLACK_DAYS.get(urgency, 2), (required_by - today).days
    if early >= slack:
        return 1.0
    return _clamp(0.5 + 0.5 * early / slack) if slack else 0.0


def _reasons(match, preferred, required_by, today):
    sentences = {
        "S": f"close in purpose to your request (similarity {match.similarity:.2f})",
        "T": (f"{match.asset.get_condition_display()} condition meets your preferred "
              f"{Condition(preferred).label}" if preferred
              else f"{match.asset.get_condition_display()} condition"),
        "R": f"available now, {(required_by - today).days} day(s) before your date",
        "E": f"{match.asset.mass_kg} kg kept out of disposal",
    }
    weights = _weights(match.factors)
    strongest = sorted((k for k, v in match.factors.items() if v and k in sentences),
                       key=lambda k: -(weights[k] * match.factors[k]))
    return [sentences[k] for k in strongest[:2]]


def _weights(factors):
    kept = {k: WEIGHTS[k] for k, v in factors.items() if v is not None}
    total = sum(kept.values())
    return {k: w / total for k, w in kept.items()}


def eligible_units(user, specs):
    from exchange.requests import eligible_candidates

    units, excluded = [], []
    for asset in eligible_candidates(user).select_related("category").order_by("id"):
        missing = missing_specs(asset, specs)
        if missing:
            excluded.append((asset, f"does not mention: {', '.join(missing)}"))
        else:
            units.append(asset)
    return units, excluded


def rank_matches(user, purpose, specs, quantity, required_by, urgency, preferred_condition="", today=None):
    today = today or date.today()
    version = model_version(ModelKind.RANKING, RANKING_NAME, MODEL_NAME, weights=WEIGHTS, thresholds=THRESHOLDS)
    units, excluded = eligible_units(user, specs)
    inputs = {"purposeWords": len(purpose.split()), "specs": specs, "quantity": quantity,
              "requiredBy": str(required_by), "urgency": urgency, "preferredCondition": preferred_condition,
              "unitIds": [a.pk for a in units]}
    started = time.monotonic()
    warnings = [f"Only {len(units)} eligible unit(s) for the {quantity} you need."] if len(units) < quantity else []
    try:
        embedder = get_embedder()
        vectors = asset_vectors(embedder, units)
        [request_vector] = embedder.embed([f"{purpose}. {', '.join(specs)}".strip(". ")])
    except EmbeddingUnavailable as error:
        item = record(version, AITask.RANK_MATCHES, input_refs=inputs, fallback=True, output={"error": str(error)},
                      latency_ms=int((time.monotonic() - started) * 1000))
        return Ranking(record_id=item.pk, excluded=excluded, fallback=True, warnings=warnings,
                       matches=[Match(asset=a, similarity=0, factors={}, score=0, rank=0) for a in units],
                       message=f"Not ranked: {error}. Eligible units are shown in Asset ID order.")

    dropped = {"C": DROPPED_BECAUSE["C"]}
    masses = [a.mass_kg for a in units]
    if not units or any(m is None for m in masses):
        dropped["E"] = DROPPED_BECAUSE["E"]
    largest = max(masses) if "E" not in dropped else None

    matches = []
    for asset in units:
        similarity = cosine(request_vector, vectors[asset.pk])
        factors = {
            "S": _clamp((similarity - THRESHOLDS["weak_similarity"]) / 0.50),
            "T": condition_fit(asset.condition, preferred_condition),
            "R": ready_fit(required_by, urgency, today),
            "C": None,
            "E": float(asset.mass_kg / largest) if "E" not in dropped and largest else None,
        }
        weights = _weights(factors)
        score = round(100 * sum(weights[k] * v for k, v in factors.items() if v is not None))
        matches.append(Match(asset=asset, similarity=similarity, factors=factors, score=score))
    # Section 4 service 2: a unit whose purpose is not similar (below 0.40) is listed after the similar
    # ones as a weak match, whatever its other factors; then by score; ties by Asset ID.
    matches.sort(key=lambda m: (m.similarity < THRESHOLDS["weak_similarity"], -m.score, m.asset.pk))

    for position, match in enumerate(matches, start=1):
        match.rank = position
        match.reasons = _reasons(match, preferred_condition, required_by, today)
        if match.score < THRESHOLDS["strong_score"]:
            match.warnings.append("Weak match")
        if match.similarity < THRESHOLDS["weak_similarity"]:
            match.warnings.append("Purpose is not similar (below 0.40)")

    top = matches[0] if matches and matches[0].score >= THRESHOLDS["strong_score"] else None
    if matches and top is None:
        warnings.append("No strong match (all scores below 70), so no unit is marked as the top pick.")
    item = record(version, AITask.RANK_MATCHES, input_refs=inputs, unsure=top is None,
                  score=Decimal(matches[0].score) if matches else None,
                  latency_ms=int((time.monotonic() - started) * 1000), output={
                      "ranked": [{"assetId": m.asset.pk, "score": m.score, "rank": m.rank,
                                  "similarity": round(m.similarity, 3),
                                  "factors": {k: (round(v, 3) if v is not None else None) for k, v in m.factors.items()},
                                  "reasons": m.reasons} for m in matches],
                      "excluded": [{"assetId": a.pk, "reason": r} for a, r in excluded],
                      "dropped": dropped,
                  })
    return Ranking(record_id=item.pk, matches=matches, excluded=excluded, dropped=dropped, top_pick=top,
                   warnings=warnings)


def save_matches(request, ai_record_id, chosen):
    """Gate 2: store the ranked list with the request, mark the chosen units, and answer the AI record.

    Accepted = the requester chose the top-ranked units; Corrected = chose other units;
    Rejected = chose none of the ranked units.
    """
    from exchange.models import MatchRecommendation

    from .models import AIRecord

    item = AIRecord.objects.filter(pk=ai_record_id, task=AITask.RANK_MATCHES, fallback=False).first()
    if item is None or request.matches.filter(ai_record=item).exists():
        return None
    chosen_ids = {asset.pk for asset in chosen}
    ranked = item.output.get("ranked", [])
    for row in ranked:
        reasons = "; ".join(row["reasons"])
        MatchRecommendation.objects.create(
            request=request, asset_id=row["assetId"], ai_record=item, score=row["score"],
            rank_position=row["rank"], model_version=f"{RANKING_NAME} / {MODEL_NAME}",
            factor_scores=row["factors"], explanation=reasons[:2000],
            decision=MatchDecision.ACCEPTED if row["assetId"] in chosen_ids else None,
        )
    ranked_ids = [row["assetId"] for row in ranked]
    if not chosen_ids & set(ranked_ids):
        decision = AIDecision.REJECTED
    elif chosen_ids == set(ranked_ids[:len(chosen_ids)]):
        decision = AIDecision.ACCEPTED
    else:
        decision = AIDecision.CORRECTED
    return record_decision(item.pk, AITask.RANK_MATCHES, decision)
