from goose import settings

def meta_processor(request):
    """
        Adds the GOOSE_META variable to all templates.
    """
    meta = settings.GOOSE_META
    return {'GOOSE_META': meta}
