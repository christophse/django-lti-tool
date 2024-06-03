from django.contrib import admin

from lti_tool.forms import KeyForm
from lti_tool.models import Key, Platform, Resource


@admin.register(Platform)
class PlatformAdmin(admin.ModelAdmin):
    list_display = ('issuer', 'deployment_id', 'key')


@admin.register(Key)
class KeyAdmin(admin.ModelAdmin):
    form = KeyForm
    list_display = ('kid',)


class ResourceInline(admin.TabularInline):
    model = Resource
    verbose_name = "LTI Resource Usage"
    max_num = 0  # Disables 'Add another *' button
    readonly_fields = ["title", "description"]
    fieldsets = [
        (
            None,
            {"fields": ["title"]},
        )
    ]

    def get_extra(self, request, obj=None, **kwargs):
        return 0


class ResourceLinkAdmin(admin.ModelAdmin):
    def get_fields(self, request, obj=None):
        fields = super().get_fields(request, obj)
        fields.remove("title")
        return fields

    def get_fieldsets(self, request, obj=None):
        fieldsets = super().get_fieldsets(request, obj)
        fieldsets.append(
            (
                "LTI Resource Link Information",
                {"classes": ["inline-group"], "fields": ["title"]},
            )
        )
        return fieldsets

    def get_inlines(self, request, obj):
        inlines = super().get_inlines(request, obj)
        if inlines:
            return list(inlines).append(ResourceInline)
        return [ResourceInline]
