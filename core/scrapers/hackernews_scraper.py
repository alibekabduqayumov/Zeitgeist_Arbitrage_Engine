import requests
from datetime import datetime, timezone
from loguru import logger
from sqlalchemy import text
from database.connection import SessionLocal

BASE_URL = "https://hacker-news.firebaseio.com/v0"

def fetch_top_stories(limit: int = 50) -> list[dict]:
    """Fetch top story IDs from HackerNews."""
    try:
        response = requests.get(f"{BASE_URL}/topstories.json", timeout=10)
        response.raise_for_status()
        story_ids = response.json()[:limit]
        logger.info(f"GOt {len(story_ids)} story IDs")
        return story_ids
    except Exception as e:
        logger.error(f"Failed to fetch story IDs: {e}")
        return[]
    
def fetch_story(story_id: int) -> dict | None:
    """Fetch a single story by ID."""
    try:
        response = requests.get(f"{BASE_URL}/item/{story_id}.json", timeout=10)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        logger.error(f"Story {story_id} failed: {e}")
        return None

def classify_tier(score: int) -> str:
    if score < 100:
        return "niche"
    elif score < 500:
        return "mid"
    else:
        return "mainstream"

def save_to_db(signals: list[dict]):
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
                s
            )
        db.commit()
        logger.success(f"Saved {len(signals)} signals to database")
    except Exception as e:
        db.rollback()
        logger.error(f"DB save failed: {e}")
    finally:
        db.close()

def run():
    logger.info("Starting HackerNews scraper...")
    story_ids = fetch_top_stories(limit=50)
    signals = []

    for story_id in story_ids:
        story = fetch_story(story_id)
        if not story or story.get("type") != "story":
            continue
        title = story.get("title", "")
        score = story.get("score", 0)
        comments = story.get("descendants", 0)
        if not title:
            continue
        signals.append({
            "platform":    "hackernews",
            "topic_text":  title,
            "engagement":  score + comments,
            "region":      "GLOBAL",
            "source_tier": classify_tier(score),
            "scraped_at":  datetime.now(timezone.utc)
        })

    save_to_db(signals)
    logger.success(f"Done. Total signals collected: {len(signals)}")

if __name__ == "__main__":
    run()