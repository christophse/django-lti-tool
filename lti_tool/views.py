from jwcrypto import jwk
from secrets import token_hex
from urllib.parse import urlencode

from django.apps import apps
from django.http import HttpResponse
from django.middleware.csrf import get_token
from django.shortcuts import get_object_or_404, redirect
from django.utils.decorators import method_decorator
from django.views import View
from django.views.decorators.csrf import csrf_exempt, ensure_csrf_cookie
from django.views.generic.base import TemplateView

from lti_tool.jwt import form_jwt
from lti_tool.models import Key, Platform, ResourceLink
from lti_tool.mixins import LTIMessageMixin


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


class DeeplinkView(LTIMessageMixin, TemplateView):
    template_name = 'deeplink.html'

    def post(self, request, claims, *args, **kwargs):
        resources = []
        for cls in ResourceLink.__subclasses__():
            objects = cls.objects.all()
            for obj in objects:
                resources.append(
                    {
                        'desc': f'{obj._meta.app_label}.{obj._meta.model_name}#{obj.id}',
                        'obj': obj,
                    }
                )
        settings = claims['https://purl.imsglobal.org/spec/lti-dl/claim/deep_linking_settings']
        redirect_url = settings['deep_link_return_url']
        data = settings.get('data', None)

        return super(DeeplinkView, self).render_to_response(
            {
                'redirect_url': redirect_url,
                'data': data,
                'resources': resources,
            }
        )


class DeeplinkRedirectView(TemplateView):
    template_name = 'deeplink_redirect.html'

    def post(self, request):
        platform = Platform.objects.get(pk=request.session['lti-platform'])

        resource_desc = request.POST['resource'].split('#', maxsplit=1)
        model_meta, obj_id = resource_desc[0], resource_desc[1]
        model = apps.get_model(model_meta)

        resource = model.objects.get(pk=obj_id)

        content_item = {
            'type': 'ltiResourceLink',
            'title': resource.title,
            'url': request.build_absolute_uri(resource.get_absolute_url())
        }

        resp_claims = {
            'https://purl.imsglobal.org/spec/lti/claim/message_type': 'LtiDeepLinkingResponse',
            'https://purl.imsglobal.org/spec/lti/claim/version': '1.3.0',
            'https://purl.imsglobal.org/spec/lti/claim/deployment_id': platform.deployment_id,
            'https://purl.imsglobal.org/spec/lti-dl/claim/content_items': [content_item],
        }

        data = request.POST.get('data', None)
        if data:
            resp_claims.update({
                'https://purl.imsglobal.org/spec/lti-dl/claim/data': data
            })

        return super(DeeplinkRedirectView, self).render_to_response(
            {
                'redirect_url': request.POST['redirect_url'],
                'jwt': form_jwt(platform, resp_claims)
            }
        )
