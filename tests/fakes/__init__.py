"""Fakes for the external boundaries — no Jenkins / Oracle / network in the offline suite."""

from .jenkins import FakeJenkinsClient
from .oracle import FakeTrackingFeed
from .svn import FakeSvnBlameClient

__all__ = ["FakeJenkinsClient", "FakeSvnBlameClient", "FakeTrackingFeed"]
