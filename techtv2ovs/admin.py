"""Admin for techtv2ovs"""

from django.contrib import admin

from techtv2ovs.models import TechTVCollection, TechTVVideo


@admin.register(TechTVCollection)
class TechTVCollectionAdmin(admin.ModelAdmin):
    """Customized collection admin model"""

    model = TechTVCollection
    list_display = ("id", "name", "description")
    readonly_fields = ("id", "name", "description")
    search_fields = (
        "name",
        "description",
        "collection__title",
    )


@admin.register(TechTVVideo)
class TechTVVideoAdmin(admin.ModelAdmin):
    """Customized Video admin model"""

    model = TechTVVideo
    list_display = (
        "id",
        "title",
        "description",
        "status",
    )
    readonly_fields = (
        "id",
        "ttv_id",
        "title",
        "description",
        "errors",
        "private",
        "private_token",
        "external_id",
    )
    list_filter = ("status", "thumbnail_status", "videofile_status", "subtitle_status")
    search_fields = (
        "ttv_id",
        "title",
        "ttv_collection__name",
    )
