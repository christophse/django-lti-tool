from django.contrib import admin

from lti_tool.forms import KeyForm
from lti_tool.models import Key, Platform


@admin.register(Platform)
class PlatformAdmin(admin.ModelAdmin):
    list_display = ('issuer', 'deployment_id', 'key')


@admin.register(Key)
class KeyAdmin(admin.ModelAdmin):
    form = KeyForm
    list_display = ('kid',)
