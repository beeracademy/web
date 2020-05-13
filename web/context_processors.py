from django.urls import Resolver404, resolve, reverse
from django.views.generic.detail import SingleObjectMixin
from django.views.generic.list import MultipleObjectMixin


def admin_url(request):
    def aux(request):
        try:
            r = resolve(request.path)
        except Resolver404:
            return None

        view_class = getattr(r.func, "view_class", None)
        model = getattr(view_class, "model", None)

        if not model:
            return None

        if issubclass(view_class, MultipleObjectMixin):
            page = "changelist"
            args = []
        elif issubclass(view_class, SingleObjectMixin):
            page = "change"
            view = view_class()
            view.setup(request, *r.args, **r.kwargs)
            args = [view.get_object().pk]
        else:
            return None

        url_name = f"admin:{model._meta.app_label}_{model._meta.model_name}_{page}"
        return reverse(url_name, args=args)

    return {"admin_url": aux(request) or reverse("admin:index")}
