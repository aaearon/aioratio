"""Tests for package metadata (version, user-agent)."""
from __future__ import annotations


def test_version_is_nonempty_string() -> None:
    import aioratio

    assert isinstance(aioratio.__version__, str)
    assert len(aioratio.__version__) > 0


def test_user_agent_starts_with_prefix() -> None:
    from aioratio.const import USER_AGENT

    assert USER_AGENT.startswith("aioratio/")
