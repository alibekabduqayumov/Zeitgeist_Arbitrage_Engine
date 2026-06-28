from datetime import datetime, timezone, timedelta
from loguru import logger
from sqlalchemy import text
from database.connection import SessionLocal

def get_raw_signals(hours_back: int = 24) -> list[dict]:
    """Fetch recent unprocessed signals from DB."""
    db = SessionLocal()
    try:
        cutoff = datetime.now(timezone.utc) - timedelta(hours=hours_back)
        result = db.execute(
            text("""
                SELECT id, topic_text, engagement, source_tier, platform, scraped_at
                FROM raw_signals
                WHERE scraped_at >= :cutoff
                ORDER BY scraped_at ASC
            """),
            {"cutoff": cutoff}
        )
        rows = result.mappings().all()
        return [dict(r) for r in rows]
    finally:
        db.close()

def extract_keywords(text_content: str) -> list[str]:
    """Extract simple keywords from title (no ML needed yet)."""
    stopwords = {
    "a", "an", "the", "is", "in", "on", "at", "to", "for",
    "of", "and", "or", "but", "with", "from", "by", "has",
    "are", "was", "be", "it", "this", "that", "have", "not",
    "you", "your", "its", "will", "how", "why", "what", "who",
    "does", "into", "show", "public", "case", "make", "take",
    "just", "more", "over", "about", "after", "their", "they",
    "been", "than", "then", "when", "some", "time", "next",
    "also", "only", "using", "used", "new", "can", "all",
    "were", "which", "there", "would", "could", "should",
    "says", "said", "like", "get", "use", "now", "one",
    "first", "last", "long", "very", "still", "back", "even",
    "good", "well", "never", "every", "most", "other", "way",
    "because", "while", "being", "same", "here", "need",
    "generation", "previewing", "sol", "based", "open",
    "model", "models", "system", "data", "code", "work"
    }
    words = text_content.lower().replace("'", "").replace("-", " ").split()
    keywords = [w.strip(".,!?:;\"'()[]") for w in words if len(w) > 3]
    return [k for k in keywords if k not in stopwords]

TIER_WEIGHTS = {"niche": 3.0, "mid": 2.0, "mainstream": 1.0}

def calculate_velocity(signals: list[dict]) -> list[dict]:
    """
    Group signals by keyword and calculate velocity score.
    Velocity = engagement_sum x tier_weight x frequency
    Higher = faster emerging trend.
    """
    keyword_map = {}

    for signal in signals:
        keywords = extract_keywords(signal["topic_text"])
        tier_weight = TIER_WEIGHTS.get(signal["source_tier"], 1.0)
        engagement = signal["engagement"]

        for keyword in keywords:
            if keyword not in keyword_map:
                keyword_map[keyword] = {
                    "keyword":        keyword,
                    "total_engagement": 0,
                    "frequency":      0,
                    "weighted_score": 0.0,
                    "tiers_seen":     set(),
                    "platforms":      set(),
                }
            keyword_map[keyword]["total_engagement"] += engagement
            keyword_map[keyword]["frequency"]        += 1
            keyword_map[keyword]["weighted_score"]   += engagement * tier_weight
            keyword_map[keyword]["tiers_seen"].add(signal["source_tier"])
            keyword_map[keyword]["platforms"].add(signal["platform"])

    results = []
    for kw, data in keyword_map.items():
        # bonus multiplier if trend spans multiple tiers (niche + mainstream = real signal)
        tier_spread = len(data["tiers_seen"])
        final_velocity = data["weighted_score"] * (1 + tier_spread * 0.2)

        results.append({
            "keyword":      kw,
            "velocity":     round(final_velocity, 2),
            "frequency":    data["frequency"],
            "engagement":   data["total_engagement"],
            "tier_spread":  tier_spread,
            "platforms":    ", ".join(data["platforms"]),
        })

    # sort by velocity descending
    results.sort(key=lambda x: x["velocity"], reverse=True)
    return results

def save_velocity_scores(scored: list[dict]):
    """Save top velocity scores to trend_signals table."""
    db = SessionLocal()
    try:
        top = scored[:50]  # save top 50
        for item in top:
            db.execute(
                text("""
                    INSERT INTO trend_signals
                        (topic_slug, platform, velocity, engagement, source_tier, region, signal_at)
                    VALUES
                        (:topic_slug, :platform, :velocity, :engagement, :source_tier, :region, :signal_at)
                """),
                {
                    "topic_slug":  item["keyword"],
                    "platform":    item["platforms"],
                    "velocity":    item["velocity"],
                    "engagement":  item["engagement"],
                    "source_tier": "mid",
                    "region":      "GLOBAL",
                    "signal_at":   datetime.now(timezone.utc),
                }
            )
        db.commit()
        logger.success(f"Saved {len(top)} velocity scores to trend_signals")
    except Exception as e:
        db.rollback()
        logger.error(f"Failed to save velocity scores: {e}")
    finally:
        db.close()

def run():
    logger.info("⚡ Running Trend Velocity Scorer...")
    signals = get_raw_signals(hours_back=24)
    logger.info(f"Processing {len(signals)} signals...")

    if not signals:
        logger.warning("No signals found. Run the scraper first.")
        return

    scored = calculate_velocity(signals)
    save_velocity_scores(scored)

    # print top 15 trending keywords
    logger.info("\nTOP 15 TRENDING KEYWORDS RIGHT NOW:")
    for i, item in enumerate(scored[:15], 1):
        logger.info(
            f"  {i:02d}. {item['keyword']:<20} "
            f"velocity={item['velocity']:<10} "
            f"freq={item['frequency']}"
        )

if __name__ == "__main__":
    run()