"""Diagnostic (no Anthropic calls): fetch RSS feeds for given countries and
report, per feed, how many items have a parseable publication date and the
age distribution of those items.

Usage: python3.11 scripts/diagnose_stale_articles.py --country uruguay --country bolivia
"""

import argparse
import os
import sys
from datetime import datetime, timezone

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.dirname(SCRIPT_DIR)
sys.path.insert(0, REPO_ROOT)

import yaml
import feedparser
from email.utils import parsedate_to_datetime

CONFIG_BY_COUNTRY = {
    "argentina": "config.yaml",
    "brazil": "config_brazil.yaml",
    "chile": "config_chile.yaml",
    "uruguay": "config_uruguay.yaml",
    "paraguay": "config_paraguay.yaml",
    "bolivia": "config_bolivia.yaml",
}


def _parse_date_raw(entry):
    """Same logic as ingestion.rss_fetcher._parse_date, but returns None on failure
    instead of falling back to now() — we want to see the no-date items separately."""
    for attr in ("published", "updated"):
        raw = getattr(entry, attr, None)
        if raw:
            try:
                return parsedate_to_datetime(raw)
            except Exception:
                pass
    return None


def bucket(age_hours):
    if age_hours is None:
        return "no_date"
    days = age_hours / 24
    if days < 2:
        return "under_2d"
    elif days < 7:
        return "2_7d"
    elif days < 30:
        return "7_30d"
    else:
        return "over_30d"


def main():
    parser = argparse.ArgumentParser(description="Diagnose RSS feed age distribution (no API calls).")
    parser.add_argument("--country", action="append", required=True, choices=sorted(CONFIG_BY_COUNTRY))
    args = parser.parse_args()

    now = datetime.now(timezone.utc)

    for country in args.country:
        config_path = os.path.join(REPO_ROOT, CONFIG_BY_COUNTRY[country])
        with open(config_path, encoding="utf-8") as f:
            config = yaml.safe_load(f)

        print(f"\n=== {country.upper()} ({CONFIG_BY_COUNTRY[country]}) ===")
        for feed_cfg in config.get("rss_feeds", []):
            name = feed_cfg["name"]
            url = feed_cfg["url"]
            feed = feedparser.parse(url)

            counts = {"under_2d": 0, "2_7d": 0, "7_30d": 0, "over_30d": 0, "no_date": 0}
            with_date = 0
            total = len(feed.entries)

            for entry in feed.entries:
                dt = _parse_date_raw(entry)
                if dt is None:
                    counts["no_date"] += 1
                    continue
                with_date += 1
                if dt.tzinfo is None:
                    dt = dt.replace(tzinfo=timezone.utc)
                age_hours = (now - dt).total_seconds() / 3600
                counts[bucket(age_hours)] += 1

            print(f"\n  {name}")
            print(f"    url: {url}")
            print(f"    total items: {total}  |  with date: {with_date}  |  no date: {counts['no_date']}")
            print(f"    age distribution (of items with a date):")
            print(f"      < 2 days   : {counts['under_2d']}")
            print(f"      2-7 days   : {counts['2_7d']}")
            print(f"      7-30 days  : {counts['7_30d']}")
            print(f"      > 30 days  : {counts['over_30d']}")


if __name__ == "__main__":
    main()
