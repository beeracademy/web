def updated_query_url(request, updates):
    query = request.GET.copy()
    for k, v in updates.items():
        if v is None:
            if k in query:
                del query[k]
        else:
            query[k] = v
    return request.path + "?" + query.urlencode()
