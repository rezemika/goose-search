from modeltranslation.translator import translator, TranslationOptions
from search.models import SearchPreset

class SearchPresetTranslationOptions(TranslationOptions):
    fields = ("name", "processing_rules")

translator.register(SearchPreset, SearchPresetTranslationOptions)
