"""User agent utilities.

Provides random and rotating user agent strings for web scraping.

Example
-------
    from easyscrape.user_agents import random_ua, rotating_ua

    ua = random_ua()
    mobile_ua = random_ua(mobile=True)
"""
from __future__ import annotations

import random
from typing import Final, List, Sequence

__all__: Final[tuple[str, ...]] = (
    "random_ua",
    "rotating_ua",
    "all_agents",
    "DESKTOP_AGENTS",
    "MOBILE_AGENTS",
)

# Desktop user agents
DESKTOP_AGENTS: Final[List[str]] = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Safari/605.1.15",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 Edg/120.0.0.0",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:121.0) Gecko/20100101 Firefox/121.0",
]

# Mobile user agents
MOBILE_AGENTS: Final[List[str]] = [
    "Mozilla/5.0 (iPhone; CPU iPhone OS 17_2 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Mobile/15E148 Safari/604.1",
    "Mozilla/5.0 (iPhone; CPU iPhone OS 17_1 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) CriOS/120.0.6099.119 Mobile/15E148 Safari/604.1",
    "Mozilla/5.0 (Linux; Android 14; Pixel 8) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.6099.144 Mobile Safari/537.36",
    "Mozilla/5.0 (Linux; Android 14; SM-S918B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.6099.144 Mobile Safari/537.36",
    "Mozilla/5.0 (iPad; CPU OS 17_2 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Mobile/15E148 Safari/604.1",
]

# Index for round-robin rotation
_rotation_index: int = 0
_mobile_rotation_index: int = 0


def random_ua(mobile: bool = False) -> str:
    """Get a random user agent string.

    Parameters
    ----------
    mobile : bool
        If True, return a mobile user agent.

    Returns
    -------
    str
        A random user agent string.

    Example
    -------
        >>> ua = random_ua()
        >>> 'Mozilla' in ua
        True
    """
    agents = MOBILE_AGENTS if mobile else DESKTOP_AGENTS
    return random.choice(agents)


def rotating_ua(mobile: bool = False) -> str:
    """Get a user agent using round-robin rotation.

    Parameters
    ----------
    mobile : bool
        If True, return a mobile user agent.

    Returns
    -------
    str
        A user agent string.

    Example
    -------
        >>> ua1 = rotating_ua()
        >>> ua2 = rotating_ua()
        >>> ua1 != ua2 or len(DESKTOP_AGENTS) == 1
        True
    """
    global _rotation_index, _mobile_rotation_index

    if mobile:
        agents = MOBILE_AGENTS
        idx = _mobile_rotation_index % len(agents)
        _mobile_rotation_index += 1
    else:
        agents = DESKTOP_AGENTS
        idx = _rotation_index % len(agents)
        _rotation_index += 1

    return agents[idx]


def all_agents(mobile: bool = False) -> Sequence[str]:
    """Get all available user agents.

    Parameters
    ----------
    mobile : bool
        If True, return mobile user agents.

    Returns
    -------
    Sequence[str]
        List of all user agent strings.

    Example
    -------
        >>> agents = all_agents()
        >>> len(agents) > 0
        True
    """
    return MOBILE_AGENTS if mobile else DESKTOP_AGENTS
