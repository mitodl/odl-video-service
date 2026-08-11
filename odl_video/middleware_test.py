"""Tests for odl_video.middleware"""


def test_admin_login_has_noindex_header(client):
    """The X-Robots-Tag header should be present even on pages that don't
    extend base.html, such as the Django admin (see mitodl/hq#12798)
    """
    response = client.get("/admin/login/")
    assert response["X-Robots-Tag"] == "noindex, nofollow"
