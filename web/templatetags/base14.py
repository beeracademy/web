from django import template
from games.utils import format_sips, format_float_sips

register = template.Library()


@register.filter
def base14(value, places=None):
    if value == None:
        return None

    if places != None:
        return format_float_sips(value, places)
    else:
        return format_sips(value)
