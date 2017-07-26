from django.contrib import admin
from search.models import SearchPreset

class SearchPresetAdmin(admin.ModelAdmin):
    list_display   = ("name", )

admin.site.register(SearchPreset, SearchPresetAdmin)
