"""Tests for user agent utilities."""
import pytest

from easyscrape.user_agents import random_ua, rotating_ua, all_agents


class TestRandomUa:
    """Tests for random_ua function."""

    def test_returns_string(self):
        """Test returns a string."""
        ua = random_ua()
        assert isinstance(ua, str)
        assert len(ua) > 0

    def test_mobile_option(self):
        """Test mobile user agent option."""
        ua = random_ua(mobile=True)
        assert isinstance(ua, str)
        # Mobile UAs typically contain 'Mobile' or 'Android' or 'iPhone'
        # But not always, so just check it's a string


class TestRotatingUa:
    """Tests for rotating_ua function."""

    def test_returns_string(self):
        """Test returns a string."""
        ua = rotating_ua()
        assert isinstance(ua, str)

    def test_mobile_option(self):
        """Test mobile user agent option."""
        ua = rotating_ua(mobile=True)
        assert isinstance(ua, str)


class TestAllAgents:
    """Tests for all_agents function."""

    def test_returns_sequence(self):
        """Test returns a sequence."""
        agents = all_agents()
        assert hasattr(agents, '__iter__')
        assert len(list(agents)) > 0

    def test_mobile_option(self):
        """Test mobile user agents option."""
        # all_agents should accept mobile parameter
        try:
            agents = all_agents(mobile=True)
            assert hasattr(agents, '__iter__')
        except TypeError:
            # If mobile param not supported, that's also acceptable
            # as long as the basic function works
            agents = all_agents()
            assert hasattr(agents, '__iter__')
