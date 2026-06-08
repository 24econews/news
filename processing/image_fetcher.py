"""Fetch a hero image from Unsplash for a digest."""

import logging
import os
import random

import requests

logger = logging.getLogger(__name__)

_STOP_WORDS = {"the", "a", "an", "as", "in", "of", "by", "to", "and", "or", "for", "on", "at"}
_UNSPLASH_URL = "https://api.unsplash.com/search/photos"


def _build_query(title: str, country: str) -> str:
    words = title.split()
    meaningful = [w for w in words if w.lower().strip(".,;:!?\"'") not in _STOP_WORDS]
    keywords = meaningful[:4]
    return " ".join(keywords) + " " + country


def _search(access_key: str, query: str) -> list:
    try:
        resp = requests.get(
            _UNSPLASH_URL,
            headers={"Authorization": f"Client-ID {access_key}"},
            params={"query": query, "orientation": "landscape", "per_page": 5},
            timeout=10,
        )
        resp.raise_for_status()
        return resp.json().get("results", [])
    except Exception as exc:
        logger.warning(f"Unsplash API error: {exc}")
        return []


def fetch_hero_image(query: str, country: str) -> dict | None:
    """Search Unsplash for a landscape photo matching query + country.

    Tries a specific query first, then falls back to country economy search.
    Returns a dict with url/thumb/photographer info, or None on failure.
    """
    access_key = os.getenv("UNSPLASH_ACCESS_KEY")
    if not access_key:
        logger.warning("UNSPLASH_ACCESS_KEY not set — skipping hero image fetch")
        return None

    candidates = [
        _build_query(query, country),
        f"{country} economy city",
        f"{country} landscape",
    ]

    results = []
    for search_query in candidates:
        results = _search(access_key, search_query)
        if results:
            logger.info(f"Unsplash hit with query: {search_query!r}")
            break
    else:
        logger.info(f"No Unsplash results for any query variant of: {query!r}")
        return None

    photo = random.choice(results)
    return {
        "url": photo["urls"]["regular"],
        "thumb": photo["urls"]["thumb"],
        "photographer": photo["user"]["name"],
        "photographer_url": photo["user"]["links"]["html"],
        "unsplash_url": photo["links"]["html"],
    }
