from django.conf import settings


class LTIMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        request_csrf_token = request.POST.get('state', '')
        if request_csrf_token:
            request.META[settings.CSRF_HEADER_NAME] = request_csrf_token

        response = self.get_response(request)
        return response
