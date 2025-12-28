"""Terminal dashboard for real-time scraping statistics.

Provides a live-updating terminal UI showing:
- Request counts and success rates
- Response times (min/avg/max)
- Cache hit rates
- Per-domain statistics
- Recent requests

Requires: pip install rich

Example
-------
    from easyscrape.dashboard import Dashboard

    with Dashboard() as dash:
        for url in urls:
            result = scrape(url)
            dash.update()  # Refresh display

    # Or use the standalone viewer
    from easyscrape.dashboard import live_stats
    live_stats()  # Shows stats for current session
"""
from __future__ import annotations

import time
from typing import Any, Final

__all__: Final[tuple[str, ...]] = (
    "Dashboard",
    "live_stats",
    "print_summary",
)


def _format_bytes(n: int) -> str:
    """Format bytes as human-readable string."""
    for unit in ["", "KB", "MB", "GB"]:
        if abs(n) < 1024:
            return f"{n:.1f}{unit}"
        n /= 1024
    return f"{n:.1f}TB"


def _format_duration(ms: float) -> str:
    """Format milliseconds as human-readable string."""
    if ms < 1000:
        return f"{ms:.0f}ms"
    return f"{ms/1000:.2f}s"


def print_summary() -> None:
    """Print a summary of scraping statistics.

    Uses the global metrics collector to display:
    - Total requests and success rate
    - Cache hit rate
    - Total bytes downloaded
    - Per-domain breakdown

    Example:
        from easyscrape.dashboard import print_summary

        # After scraping...
        print_summary()
    """
    from .stats import get_metrics_collector

    collector = get_metrics_collector()
    summary = collector.summary()
    domains = collector.domain_stats()

    print("\n" + "=" * 60)
    print("  EASYSCRAPE SUMMARY")
    print("=" * 60)

    print(f"\n  Uptime:        {summary['uptime_s']:.1f}s")
    print(f"  Total Requests: {summary['requests']}")
    print(f"  Successful:     {summary['successful']} ({summary['success_rate']*100:.1f}%)")
    print(f"  Cache Hits:     {summary['cache_hits']} ({summary['cache_rate']*100:.1f}%)")
    print(f"  Total Data:     {_format_bytes(summary['bytes'])}")

    if domains:
        print(f"\n  Domains ({len(domains)}):")
        print("  " + "-" * 56)
        print(f"  {'Domain':<30} {'Reqs':>6} {'OK%':>6} {'Avg':>8}")
        print("  " + "-" * 56)

        for domain, stats in sorted(domains.items()):
            ok_pct = stats['success_rate'] * 100
            avg = _format_duration(stats['avg_ms'])
            print(f"  {domain:<30} {stats['total']:>6} {ok_pct:>5.1f}% {avg:>8}")

    print("\n" + "=" * 60 + "\n")


class Dashboard:
    """Live terminal dashboard for scraping statistics.

    Displays a continuously updating view of scraping progress
    using the rich library for beautiful terminal output.

    Example
    -------
        from easyscrape.dashboard import Dashboard
        from easyscrape import scrape

        with Dashboard() as dash:
            for url in urls:
                result = scrape(url)
                # Dashboard auto-updates

    Note:
        Requires the rich library: pip install rich
    """

    def __init__(self, refresh_rate: float = 0.5) -> None:
        """Initialize dashboard.

        Args:
            refresh_rate: Seconds between display updates.
        """
        self._refresh_rate = refresh_rate
        self._live = None
        self._started = False

    def _make_table(self) -> Any:
        """Create the stats table."""
        from rich.table import Table
        from rich.panel import Panel
        from rich.layout import Layout
        from rich.text import Text

        from .stats import get_metrics_collector

        collector = get_metrics_collector()
        summary = collector.summary()
        domains = collector.domain_stats()
        recent = collector.recent(5)

        # Main stats
        stats_table = Table(show_header=False, box=None, padding=(0, 2))
        stats_table.add_column("Label", style="cyan")
        stats_table.add_column("Value", style="green")

        stats_table.add_row("Requests", str(summary['requests']))
        stats_table.add_row("Success Rate", f"{summary['success_rate']*100:.1f}%")
        stats_table.add_row("Cache Rate", f"{summary['cache_rate']*100:.1f}%")
        stats_table.add_row("Data", _format_bytes(summary['bytes']))
        stats_table.add_row("Uptime", f"{summary['uptime_s']:.1f}s")

        # Domain table
        domain_table = Table(title="Domains", box=None)
        domain_table.add_column("Domain", style="cyan", max_width=25)
        domain_table.add_column("Reqs", justify="right")
        domain_table.add_column("OK%", justify="right")
        domain_table.add_column("Avg", justify="right")

        for domain, stats in list(domains.items())[:5]:
            domain_table.add_row(
                domain[:25],
                str(stats['total']),
                f"{stats['success_rate']*100:.0f}%",
                _format_duration(stats['avg_ms']),
            )

        # Recent requests
        recent_table = Table(title="Recent", box=None)
        recent_table.add_column("URL", style="dim", max_width=40)
        recent_table.add_column("Status", justify="right")
        recent_table.add_column("Time", justify="right")

        for req in recent:
            status_style = "green" if req['ok'] else "red"
            recent_table.add_row(
                req['url'][:40],
                Text(str(req['status']), style=status_style),
                _format_duration(req['ms']),
            )

        # Combine into layout
        from rich.console import Group
        return Group(
            Panel(stats_table, title="EasyScrape Dashboard", border_style="blue"),
            domain_table,
            recent_table,
        )

    def start(self) -> None:
        """Start the live dashboard."""
        try:
            from rich.live import Live
        except ImportError:
            raise ImportError(
                "Dashboard requires rich: pip install rich"
            )

        self._live = Live(
            self._make_table(),
            refresh_per_second=1 / self._refresh_rate,
        )
        self._live.start()
        self._started = True

    def update(self) -> None:
        """Update the dashboard display."""
        if self._live and self._started:
            self._live.update(self._make_table())

    def stop(self) -> None:
        """Stop the live dashboard."""
        if self._live:
            self._live.stop()
            self._started = False

    def __enter__(self) -> Dashboard:
        self.start()
        return self

    def __exit__(self, *args: Any) -> None:
        self.stop()


def live_stats(duration: float = 0) -> None:
    """Display live statistics in the terminal.

    Args:
        duration: How long to display (0 = until Ctrl+C)

    Example:
        # In another terminal while scraping:
        from easyscrape.dashboard import live_stats
        live_stats()
    """
    try:
        from rich.live import Live
    except ImportError:
        print("Dashboard requires rich: pip install rich")
        return

    dash = Dashboard()

    try:
        with dash:
            if duration > 0:
                time.sleep(duration)
            else:
                while True:
                    time.sleep(0.5)
                    dash.update()
    except KeyboardInterrupt:
        pass
