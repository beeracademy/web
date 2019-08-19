def show_toolbar(request):
    return request.user and request.user.is_superuser and 'djdt' in request.GET
