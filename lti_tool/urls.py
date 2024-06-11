from django.urls import path

from lti_tool.views import (DeeplinkView, DeeplinkRedirectView, KeysView,
                            LoginView, RedirectView)

urlpatterns = [
    path('keys/', KeysView.as_view()),
    path('login/', LoginView.as_view()),
    path('deeplink/', DeeplinkView.as_view(), {}, 'lti_deeplink'),
    path('deeplink_redirect/', DeeplinkRedirectView.as_view(), {},
         'deeplink_redirect'),
    path('redirect/', RedirectView.as_view(), {}, 'lti_redirect'),
]
