from django import template

register = template.Library()

@register.filter()
def render_coordinate(coord):
    """
        Returns a rounded and stringified number from a float.
        Used to render short GPS coordinates.
    """
    return str(round(coord, 5))

@register.filter()
def render_bool_js(value):
    """
        Returns a stringified boolean value, suitable for JS.
    """
    if value is True:
        return "true"
    else:
        return "false"
