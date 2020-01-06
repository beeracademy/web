from django import template

register = template.Library()


@register.inclusion_tag("svelte_include.html")
def svelte_include(component):
    return {"stylesheet": f"svelte/{component}.css", "script": f"svelte/{component}.js"}
