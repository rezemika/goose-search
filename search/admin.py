from django.contrib import admin
from search.models import SearchPreset, Filter

class SearchPresetAdmin(admin.ModelAdmin):
    list_display   = ("name", "id")

class FilterAdmin(admin.ModelAdmin):
    list_display   = ("name", "id")

admin.site.register(SearchPreset, SearchPresetAdmin)
admin.site.register(Filter, FilterAdmin)
