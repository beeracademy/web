from django import template

from games.utils import format_float_sips_html, format_sips_html

register = template.Library()


@register.filter
def base14(value, places=None):
    if value is None:
        return None

    if places is not None:
        return format_float_sips_html(value, places)
    else:
        return format_sips_html(value)
