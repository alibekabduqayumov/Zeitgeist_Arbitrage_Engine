#!/bin/bash
# Zeitgeist pipeline runner

PROJECT_DIR="/home/orangele/zeitgeist"
VENV="$PROJECT_DIR/venv/bin/python"
LOG="$PROJECT_DIR/logs/pipeline.log"

echo "========================================" >> $LOG
echo "▶ Pipeline started: $(date)" >> $LOG

# Step 1: scrape HackerNews
echo "→ Running HackerNews scraper..." >> $LOG
PYTHONPATH=$PROJECT_DIR $VENV $PROJECT_DIR/core/scrapers/hackernews_scraper.py >> $LOG 2>&1

# Step 2: calculate velocity scores
echo "→ Running velocity scorer..." >> $LOG
PYTHONPATH=$PROJECT_DIR $VENV $PROJECT_DIR/nlp/velocity.py >> $LOG 2>&1

echo "Pipeline done: $(date)" >> $LOG
echo "" >> $LOG