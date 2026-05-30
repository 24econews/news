"""Save the daily digest as a dated Markdown file."""

import logging
import os
from datetime import date

logger = logging.getLogger(__name__)


def publish_digest(content: str, digest_date: date, output_dir: str = "digests/") -> str:
    """Write the digest Markdown to output_dir/digest_YYYY-MM-DD.md.

    Returns the path of the written file.
    """
    os.makedirs(output_dir, exist_ok=True)
    filename = f"digest_{digest_date.isoformat()}.md"
    path = os.path.join(output_dir, filename)

    with open(path, "w", encoding="utf-8") as f:
        f.write(content)

    logger.info(f"Digest published to {path}")
    return path
