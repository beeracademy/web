def updated_query_url(request, key, value):
    query = request.GET.copy()
    query[key] = value
    return request.path + "?" + query.urlencode()
