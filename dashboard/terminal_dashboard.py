from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.columns import Columns
from rich.text import Text
from rich import box
from sqlalchemy import text
from database.connection import SessionLocal
from datetime import datetime, timezone

console = Console()

def get_stats() -> dict:
    """Get summary stats from database."""
    db = SessionLocal()
    try:
        raw_count = db.execute(text("SELECT COUNT(*) FROM raw_signals")).scalar()
        trend_count = db.execute(text("SELECT COUNT(*) FROM trend_signals")).scalar()
        opp_count = db.execute(text("SELECT COUNT(*) FROM opportunities")).scalar()
        last_scrape = db.execute(
            text("SELECT MAX(scraped_at) FROM raw_signals")
        ).scalar()
        return {
            "raw_signals":   raw_count,
            "trend_signals": trend_count,
            "opportunities": opp_count,
            "last_scrape":   last_scrape,
        }
    finally:
        db.close()

def get_top_opportunities() -> list[dict]:
    """Get top opportunities from DB."""
    db = SessionLocal()
    try:
        result = db.execute(text("""
            SELECT topic_slug, final_score, entry_strategy, window_weeks, detected_at
            FROM opportunities
            ORDER BY final_score DESC
            LIMIT 10
        """))
        return [dict(r) for r in result.mappings().all()]
    finally:
        db.close()

def get_top_trends() -> list[dict]:
    """Get top trending keywords."""
    db = SessionLocal()
    try:
        result = db.execute(text("""
            SELECT topic_slug, AVG(velocity) as velocity, COUNT(*) as freq
            FROM trend_signals
            GROUP BY topic_slug
            ORDER BY AVG(velocity) DESC
            LIMIT 15
        """))
        return [dict(r) for r in result.mappings().all()]
    finally:
        db.close()

def get_recent_signals() -> list[dict]:
    """Get most recent raw signals."""
    db = SessionLocal()
    try:
        result = db.execute(text("""
            SELECT topic_text, engagement, source_tier, platform, scraped_at
            FROM raw_signals
            ORDER BY scraped_at DESC
            LIMIT 8
        """))
        return [dict(r) for r in result.mappings().all()]
    finally:
        db.close()

def render():
    console.clear()

    # HEADER 
    console.print(Panel(
        Text("⚡ ZEITGEIST ARBITRAGE ENGINE", justify="center", style="bold cyan") ,
        subtitle=f"[dim]{datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}[/dim]",
        border_style="cyan",
        padding=(0, 2)
    ))

    # STATS ROW
    stats = get_stats()
    last = str(stats["last_scrape"])[:16] if stats["last_scrape"] else "never"

    stat_panels = [
        Panel(f"[bold cyan]{stats['raw_signals']}[/bold cyan]\n[dim]raw signals[/dim]",
              border_style="dim", padding=(0, 3)),
        Panel(f"[bold yellow]{stats['trend_signals']}[/bold yellow]\n[dim]trend scores[/dim]",
              border_style="dim", padding=(0, 3)),
        Panel(f"[bold green]{stats['opportunities']}[/bold green]\n[dim]opportunities[/dim]",
              border_style="dim", padding=(0, 3)),
        Panel(f"[bold white]{last}[/bold white]\n[dim]last scrape[/dim]",
              border_style="dim", padding=(0, 3)),
    ]
    console.print(Columns(stat_panels))

    # OPPORTUNITIES TABLE
    opps = get_top_opportunities()
    opp_table = Table(
        title="Top Arbitrage Opportunities — Uzbekistan",
        box=box.SIMPLE_HEAVY,
        border_style="green",
        header_style="bold green",
        show_lines=False,
    )
    opp_table.add_column("Rank", style="dim", width=6)
    opp_table.add_column("Keyword", style="bold white", width=22)
    opp_table.add_column("Score", style="bold green", width=8)
    opp_table.add_column("Strategy", style="cyan", width=12)
    opp_table.add_column("Window", style="yellow", width=10)

    if opps:
        for i, opp in enumerate(opps, 1):
            score = f"{opp['final_score']:.2f}"
            opp_table.add_row(
                str(i),
                opp["topic_slug"],
                score,
                opp["entry_strategy"],
                f"{opp['window_weeks']}w",
            )
    else:
        opp_table.add_row("—", "No opportunities yet", "—", "—", "—")

    console.print(opp_table)

    # TRENDING KEYWORDS TABLE
    trends = get_top_trends()
    trend_table = Table(
        title="Trending Keywords by Velocity",
        box=box.SIMPLE_HEAVY,
        border_style="yellow",
        header_style="bold yellow",
        show_lines=False,
    )
    trend_table.add_column("Rank", style="dim", width=6)
    trend_table.add_column("Keyword", style="bold white", width=22)
    trend_table.add_column("Velocity", style="bold yellow", width=12)
    trend_table.add_column("Frequency", style="cyan", width=10)

    for i, t in enumerate(trends, 1):
        trend_table.add_row(
            str(i),
            t["topic_slug"],
            f"{float(t['velocity']):.1f}",
            str(t["freq"]),
        )

    console.print(trend_table)

    # RECENT SIGNALS 
    signals = get_recent_signals()
    sig_table = Table(
        title="Latest Raw Signals",
        box=box.SIMPLE_HEAVY,
        border_style="blue",
        header_style="bold blue",
        show_lines=False,
    )
    sig_table.add_column("Topic", style="white", width=55)
    sig_table.add_column("Engagement", style="cyan", width=12)
    sig_table.add_column("Tier", style="yellow", width=12)

    for s in signals:
        topic = str(s["topic_text"])[:52] + "..." if len(str(s["topic_text"])) > 52 else str(s["topic_text"])
        tier_color = {"niche": "green", "mid": "yellow", "mainstream": "red"}.get(s["source_tier"], "white")
        sig_table.add_row(
            topic,
            str(s["engagement"]),
            f"[{tier_color}]{s['source_tier']}[/{tier_color}]",
        )

    console.print(sig_table)
    console.print("[dim]Press Ctrl+C to exit[/dim]\n")

if __name__ == "__main__":
    render()