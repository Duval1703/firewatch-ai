"""Select usable direct links from NASA CMR granule entries."""

from typing import Any

DATA_REL = "http://esipfed.org/ns/fedsearch/1.1/data#"
BROWSE_REL = "http://esipfed.org/ns/fedsearch/1.1/browse#"


def select_link(links: list[dict[str, Any]], relation: str) -> str | None:
    candidates = [
        link for link in links
        if link.get("rel") == relation
        and not link.get("inherited", False)
        and str(link.get("href", "")).startswith("https://")
    ]
    if relation == DATA_REL:
        candidates = [
            link for link in candidates
            if "search.earthdata.nasa.gov/search/granules" not in link.get("href", "")
        ]
    return candidates[0].get("href") if candidates else None
