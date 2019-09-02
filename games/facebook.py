from django.conf import settings
from facebook import GraphAPI, GraphAPIError


def post_to_page(msg, link):
    if settings.DEBUG:
        print("Facebook page post")
        print("\n------------------------------")
        print(msg)
        print("------------------------------\n")
    else:
        if hasattr(settings, "FACEBOOK_PAGE_ID") and hasattr(
            settings, "FACEBOOK_ACCESS_TOKEN"
        ):
            try:
                graph = GraphAPI(settings.FACEBOOK_ACCESS_TOKEN)
                graph.put_object(
                    settings.FACEBOOK_PAGE_ID, "feed", message=msg, link=link
                )
            except GraphAPIError as e:
                print("Failed to post to facebook page:", e)
        else:
            print("WARNING: missing facebook page id or token.")
