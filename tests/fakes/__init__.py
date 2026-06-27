"""Fakes for the external boundaries — no Jenkins / Oracle / network in the offline suite."""

from .jenkins import FakeJenkinsClient
from .oracle import FakeTrackingFeed

__all__ = ["FakeJenkinsClient", "FakeTrackingFeed"]
