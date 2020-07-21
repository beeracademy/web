from django.urls import Resolver404, resolve, reverse
from django.views.generic.detail import SingleObjectMixin
from django.views.generic.list import MultipleObjectMixin

from .utils import get_admin_object_url, get_admin_url


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

        if issubclass(view_class, SingleObjectMixin):
            view = view_class()
            view.setup(request, *r.args, **r.kwargs)
            try:
                obj = view.get_object()
                return get_admin_object_url(obj)
            except AttributeError:
                pass

        return get_admin_url(model)

    return {"admin_url": aux(request) or reverse("admin:index")}
