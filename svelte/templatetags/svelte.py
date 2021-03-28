from django import template

register = template.Library()


@register.inclusion_tag("svelte_include_generated.html")
def svelte_include(component):
    return {}
