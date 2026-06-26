import requests
from datetime import datetime, timezone
from loguru import logger
from sqlalchemy import text
from database.connection import SessionLocal
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

HEADERS = {"User-Agent": "ZeitgeistEngine/1.0 (trend research bot)"}

SUBREDDITS = [
    "streetwear",
    "SkincareAddiction",
    "FitnessMentor",
    "food",
    "technology",
    "entrepreneur",
]

def fetch_subreddit(subreddit: str, limit: int = 25) -> list[dict]:
    """Fetch hot posts from a subreddit."""
    url = f"https://www.reddit.com/r/{subreddit}/hot.json?limit={limit}"
    try:
        response = requests.get(url, headers=HEADERS, timeout=10)
        response.raise_for_status()
        posts = response.json()["data"]["children"]
        results = []
        for post in posts:
            data = post["data"]
            results.append({
                "platform":    "reddit",
                "topic_text":  data["title"],
                "engagement":  data["score"] + data["num_comments"],
                "region":      "GLOBAL",
                "source_tier": classify_tier(data["score"]),
                "subreddit":   subreddit,
            })
        logger.info(f"r/{subreddit} -> {len(results)} posts fetched.")
        return results
    except Exception as e:
        logger.error(f"r/{subreddit} failed: {e}")
        return []

def classify_tier(score: int) -> str:
    """Classify post into niche / mid / mainstream by score."""
    if score < 500:
        return "niche"
    elif score < 5000:
        return "mid"
    else:
        return "mainstream"

def save_to_db(signals: list[dict]):
    """Save raw signals to PostgreSQL."""
    if not signals:
        return
    db = SessionLocal()
    try:
        for s in signals:
            db.execute(
                text("""
                INSERT INTO raw_signals
                    (platform, topic_text, engagement, region, source_tier, scraped_at)
                VALUES
                    (:platform, :topic_text, :engagement, :region, :source_tier, :scraped_at)
                """),
                {**s, "scraped_at": datetime.now(timezone.utc)}
            )
        db.commit()
        logger.success(f"Saved {len(signals)} signals to database")
    except Exception as e:
        db.rollback()
        logger.error(f"DB save failed: {e}")
    finally:
        db.close()

def run():
    """Run the Reddit scraper for all subreddits."""
    logger.info("Starting Reddit scraper...")
    all_signals = []
    for subreddit in SUBREDDITS:
        signals = fetch_subreddit(subreddit)
        all_signals.extend(signals)
    save_to_db(all_signals)
    logger.success(f"Done. Total signals collected: {len(all_signals)}")

if __name__ == "__main__":
    run()