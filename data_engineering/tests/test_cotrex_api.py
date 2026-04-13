"""
Tests for the COTREX API connector.
These are integration tests that hit the live COTREX FeatureServer.
Mark with pytest.mark.integration if you want to skip in CI.
"""

import pytest

from data_engineering.connectors.cotrex_api import (
    fetch_all_trails,
    fetch_all_trailheads,
    fetch_trail_count,
)


def test_fetch_trail_count():
    """Verify we can get a count of named trails from COTREX."""
    count = fetch_trail_count()
    assert isinstance(count, int)
    assert count > 1000, f"Expected >1000 named trails, got {count}"


def test_fetch_trails_small_batch():
    """Fetch a small batch of trails and verify structure."""
    trails = fetch_all_trails(max_records=5)
    assert len(trails) == 5

    # Check that each record has expected fields
    for trail in trails:
        assert "name" in trail
        assert "FID" in trail
        assert isinstance(trail["name"], str)


def test_fetch_trailheads_small_batch():
    """Fetch a small batch of trailheads and verify structure."""
    trailheads = fetch_all_trailheads(max_records=5)
    assert len(trailheads) == 5

    for th in trailheads:
        assert "name" in th
        assert "geometry" in th  # return_geometry=True by default
