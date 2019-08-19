def show_toolbar(request):
    if not (request.user and request.user.is_superuser):
        return False

    if "djdt" in request.GET:
        return True

    if request.path.startswith("/__debug__/"):
        return True

    return False
