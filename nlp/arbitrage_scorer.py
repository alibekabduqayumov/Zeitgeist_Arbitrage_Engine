from datetime import datetime, timezone
from loguru import logger
from sqlalchemy import text
from database.connection import SessionLocal

# Scoring weights (tune this over time)
WEIGHT_VELOCITY = 0.5 # how fast the trend is growing
WEIGHT_FREQUENCY = 0.3 # how many times it appeared
WEIGHT_TIER = 0.2 # bonus if spotted in niche tier first

SCORE_THRESHOLD = 3.0

NOISE_KEYWORDS = {
    "apple", "google", "microsoft", "amazon", "facebook",
    "github", "linux", "python", "javascript", "software",
    "internet", "website", "computer", "server", "database",
    "security", "privacy", "hacker", "anonymous", "leaked",
    "court", "legal", "lawsuit", "government", "police",
    "died", "death", "killed", "attack", "war", "crisis",
    "mythos", "claude", "openai", "anthropic", "gemini",
    "bitcoin", "crypto", "blockchain", "nft", "token",
}

UZ_MARKET_KEYWORDS = {
    # beauty & personal care
    "skincare", "serum", "moisturizer", "sunscreen", "retinol",
    "collagen", "vitamin", "supplement", "protein", "probiotic",
    # food & beverage
    "matcha", "kombucha", "oatmeal", "granola", "vegan",
    "organic", "keto", "smoothie", "coffee", "snack",
    # fitness
    "fitness", "workout", "yoga", "pilates", "gym",
    "resistance", "band", "dumbbell", "running", "cycling",
    # lifestyle & home
    "minimalist", "aesthetic", "decor", "plant", "candle",
    "journal", "planner", "productivity", "ergonomic", "desk",
    # fashion
    "streetwear", "vintage", "thrift", "sneaker", "hoodie",
    "linen", "oversized", "accessory", "jewelry", "watch",
    # tech gadgets
    "wireless", "bluetooth", "portable", "charger", "earbuds",
    "keyboard", "monitor", "webcam", "camera", "drone",
    # education & self-improvement
    "course", "learning", "skill", "book", "reading",
    "language", "english", "design", "marketing", "finance",
}

def get_top_velocity_signals() -> list[dict]:
    """Fetch top velocity singals from trend_signals table."""
    db = SessionLocal()
    try:
        result = db.execute(text("""
            SELECT
                topic_slug,
                AVG(velocity) AS avg_velocity,
                SUM(engagement) AS total_engagement,
                COUNT(*)        AS frequency,
                MAX(source_tier) AS top_tier,
                STRING_AGG(DISTINCT platform, ', ') AS platforms
            FROM trend_signals
            GROUP BY topic_slug
            ORDER BY AVG(velocity) DESC
            LIMIT 100
        """))
        rows = result.mappings().all()
        return [dict(r) for r in rows]
    finally:
        db.close()

def score_opportunity(signal: dict) -> float:
    """
    Calculate final opportunity score for a keyword.
    Combines velocity, frequency, tier bonus, and UZ market fit.
    """
    keyword = signal["topic_slug"].lower()

    # filter out noise immediately
    if keyword in NOISE_KEYWORDS:
        return 0.0
    
    velocity = float(signal["avg_velocity"] or 0)
    frequency = int(signal["frequency"] or 0)
    tier = signal["top_tier"] or "mainstream"
    
    # normalize score to 0-10 range
    velocity_score = min(velocity / 500, 10.0)
    frequency_score = min(frequency / 10, 10.0)
    tier_bonus = 3.0 if tier == "niche" else 1.5 if tier == "mid" else 1.0

    # uzbekistan market fit multipler
    uz_multiplier = 2.0 if keyword in UZ_MARKET_KEYWORDS else 1.0

    raw_score = (
        velocity_score  * WEIGHT_VELOCITY +
        frequency_score * WEIGHT_FREQUENCY +
        tier_bonus      * WEIGHT_TIER
    ) * uz_multiplier

    return round(raw_score, 3)

def classify_entry_strategy(score: float, frequency: int) -> str:
    """Recommend entry strategy based on score and data confidence."""
    if score >= 7.0:
        return "dropship"     # high confidence, move fast
    elif score >= 4.0:
        return "reseller"     # medium confidence
    else:
        return "monitor"      # watch and wait

def save_opportunities(opportunities: list[dict]):
    """Save scored opportunities to the opportunities table."""
    if not opportunities:
        logger.warning("No opportunities to save.")
        return

    db = SessionLocal()
    try:
        # clear old opportunities before inserting fresh ones
        db.execute(text("DELETE FROM opportunities"))

        for opp in opportunities:
            db.execute(
                text("""
                    INSERT INTO opportunities
                        (topic_slug, region, demand_score, supply_gap,
                         cultural_fit, final_score, window_weeks,
                         entry_strategy, detected_at)
                    VALUES
                        (:topic_slug, :region, :demand_score, :supply_gap,
                         :cultural_fit, :final_score, :window_weeks,
                         :entry_strategy, :detected_at)
                """),
                opp
            )
        db.commit()
        logger.success(f"Saved {len(opportunities)} opportunities")
    except Exception as e:
        db.rollback()
        logger.error(f"Failed to save opportunities: {e}")
    finally:
        db.close()

def run():
    logger.info("Running Arbitrage Scorer...")

    signals = get_top_velocity_signals()
    logger.info(f"Scoring {len(signals)} signals...")

    opportunities = []
    for signal in signals:
        score = score_opportunity(signal)
        if score < SCORE_THRESHOLD:
            continue

        frequency = int(signal["frequency"] or 0)
        opportunities.append({
            "topic_slug":     signal["topic_slug"],
            "region":         "UZ",
            "demand_score":   float(signal["avg_velocity"] or 0),
            "supply_gap":     5.0,   # placeholder until we build supply scraper
            "cultural_fit":   1.0,
            "final_score":    score,
            "window_weeks":   12,
            "entry_strategy": classify_entry_strategy(score, frequency),
            "detected_at":    datetime.now(timezone.utc),
        })

    # sort by final score
    opportunities.sort(key=lambda x: x["final_score"], reverse=True)
    save_opportunities(opportunities)

    # print results
    logger.info(f"\nTOP ARBITRAGE OPPORTUNITIES FOR UZBEKISTAN:")
    logger.info(f"{'Rank':<5} {'Keyword':<20} {'Score':<8} {'Strategy':<12}")
    logger.info("─" * 50)
    for i, opp in enumerate(opportunities[:10], 1):
        logger.info(
            f"  {i:<4} {opp['topic_slug']:<20} "
            f"{opp['final_score']:<8} "
            f"{opp['entry_strategy']}"
        )

    if not opportunities:
        logger.warning("No opportunities above threshold yet. Need more data — keep scraper running.")

if __name__ == "__main__":
    run()