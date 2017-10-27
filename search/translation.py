from modeltranslation.translator import translator, TranslationOptions
from search.models import SearchPreset, Filter

class SearchPresetTranslationOptions(TranslationOptions):
    fields = ("name", "processing_rules")

class FilterTranslationOptions(TranslationOptions):
    fields = ("name", "processing_rules")

translator.register(SearchPreset, SearchPresetTranslationOptions)
translator.register(Filter, FilterTranslationOptions)
