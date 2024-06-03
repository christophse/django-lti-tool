from django.urls import path

from lti_tool.views import (DeeplinkView, DeeplinkRedirectView, KeysView,
                            LoginView)

urlpatterns = [
    path('keys/', KeysView.as_view()),
    path('login/', LoginView.as_view()),
    path('deeplink/', DeeplinkView.as_view()),
    path('deeplink_redirect/', DeeplinkRedirectView.as_view(), {},
         'deeplink_redirect'),
]
