from django import template

register = template.Library()


@register.inclusion_tag("svelte_include_generated.html", takes_context=True)
def svelte_include(context, component):
    context["component"] = component
    return context
