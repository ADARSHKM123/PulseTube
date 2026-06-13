"""Aggregate comment sentiment via VADER — free, in-process, no API spend.

VADER is tuned for short social-media text (slang, emphasis, emoji),
which matches YouTube comments far better than formal-text models.
"""

from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer

# Standard VADER convention: |compound| < 0.05 is neutral.
POSITIVE_THRESHOLD = 0.05
NEGATIVE_THRESHOLD = -0.05
# Persist every analyzed comment (most-liked first) so the dashboard can show
# and filter the full set by sentiment — capped only to bound the stored JSON.
STORED_COMMENTS_MAX = 200
MAX_COMMENT_CHARS = 500

_analyzer = SentimentIntensityAnalyzer()


def score_text(text: str) -> float:
    return _analyzer.polarity_scores(text)["compound"]


def label_for(compound: float) -> str:
    if compound >= POSITIVE_THRESHOLD:
        return "positive"
    if compound <= NEGATIVE_THRESHOLD:
        return "negative"
    return "neutral"


def analyze_comments(comments: list[dict]) -> dict | None:
    """Returns aggregate distribution + a sample of the most-liked comments,
    or None when there is nothing to analyze."""
    if not comments:
        return None

    scored = []
    counts = {"positive": 0, "negative": 0, "neutral": 0}
    compound_sum = 0.0
    for c in comments:
        compound = score_text(c["text"])
        label = label_for(compound)
        counts[label] += 1
        compound_sum += compound
        scored.append({**c, "compound": round(compound, 4), "label": label})

    total = len(scored)
    # Keep all analyzed comments, most-liked first (natural reading order), so
    # the UI can list and filter every one — not just a handful.
    stored = sorted(scored, key=lambda c: c.get("like_count", 0), reverse=True)[:STORED_COMMENTS_MAX]
    for c in stored:
        c["text"] = c["text"][:MAX_COMMENT_CHARS]

    return {
        "comments_analyzed": total,
        "positive_pct": round(counts["positive"] / total * 100, 1),
        "negative_pct": round(counts["negative"] / total * 100, 1),
        "neutral_pct": round(counts["neutral"] / total * 100, 1),
        "avg_compound": round(compound_sum / total, 4),
        "sample_comments": stored,
    }
