from django import template

register = template.Library()


@register.inclusion_tag("svelte_include.html")
def svelte_include(component):
    return {"script": f"svelte/{component}_init.js"}
