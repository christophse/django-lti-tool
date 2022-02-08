from jwcrypto import jwk
from secrets import token_hex
from urllib.parse import urlencode

from django.http import HttpResponse
from django.middleware.csrf import get_token
from django.shortcuts import get_object_or_404, redirect
from django.utils.decorators import method_decorator
from django.views import View
from django.views.decorators.csrf import csrf_exempt, ensure_csrf_cookie

from lti_tool.models import Key, Platform


class KeysView(View):
    def get(self, request, *args, **kwargs):
        key_set = jwk.JWKSet()
        keys = Key.objects.all()

        for key in keys:
            key_set.add(key.jwk)

        return HttpResponse(
            key_set.export(private_keys=False),
            headers={'Content-Type': 'application/json'}
        )


@method_decorator(csrf_exempt, name='dispatch')
@method_decorator(ensure_csrf_cookie, name='dispatch')
class LoginView(View):
    def post(self, request, *args, **kwargs):
        platform = get_object_or_404(
                Platform,
                issuer=request.POST['iss'],
                deployment_id=request.POST['lti_deployment_id']
        )

        # client_id is optional in login POST
        client_id = request.POST.get('client_id', platform.client_id)
        nonce = token_hex()

        request.session['lti-nonce'] = nonce
        request.session['lti-platform'] = platform.id

        params = {
            'scope': 'openid',
            'response_type': 'id_token',
            'response_mode': 'form_post',
            'prompt': 'none',
            'client_id': client_id,
            'redirect_uri': request.POST['target_link_uri'],
            'state': get_token(request),
            'nonce': nonce,
            'login_hint': request.POST['login_hint'],
            'lti_message_hint': request.POST['lti_message_hint'],
        }

        url = '{}?{}'.format(platform.auth_req_url, urlencode(params))
        return redirect(url)
