"""Tests for the site's robots.txt"""

import os

from django.conf import settings


def test_robots_txt_disallows_all():
    """robots.txt should block all crawlers (see mitodl/hq#12798)"""
    robots_path = os.path.join(settings.BASE_DIR, "static", "robots.txt")
    with open(robots_path) as robots_file:
        content = robots_file.read()
    assert "User-agent: *" in content
    assert "Disallow: /" in content
