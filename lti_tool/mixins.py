from jwcrypto import jwt
from jwcrypto.common import json_decode, JWException

from django.contrib.auth import authenticate, login
from django.core.exceptions import PermissionDenied
from django.views.generic.detail import SingleObjectMixin

from lti_tool.exceptions import (LTIContextError, LTIImproperlyConfigured,
                                 LTIValidationError)
from lti_tool.models import Context, Platform, Resource, ResourceLink


def validate(request):
    platform = Platform.objects.get(pk=request.session['lti-platform'])

    if request.method.lower() != 'post' or 'id_token' not in request.POST:
        return None, None

    token = request.POST['id_token']
    nonce = request.session['lti-nonce']

    check_claims = {
        'aud': platform.client_id,
        'iss': platform.issuer
    }

    try:
        token_json = jwt.JWT(jwt=token, key=platform.keyset,
                             check_claims=check_claims)
    except JWException as e:
        raise LTIValidationError from e

    claims = json_decode(token_json.claims)

    if nonce != claims['nonce']:
        raise LTIValidationError('Nonce is invalid.')

    return claims, platform


class LTIMessageMixin:
    def dispatch(self, request, *args, **kwargs):
        claims, platform = validate(request)

        kwargs.update({
            'claims': claims
        })

        return super().dispatch(request, *args, **kwargs)


class LTIResourceMixin(SingleObjectMixin):
    def get_context(self, claims, platform):
        fields = Context.get_fields(claims)

        if not fields:
            return None

        context, created = Context.objects.get_or_create(
            context_id=fields.pop('id'),
            platform=platform,
            defaults=fields
        )

        if not created:
            context.update(fields)

        return context

    def get_resource(self, claims, context, platform):
        fields = Resource.get_fields(claims)

        if not fields:
            return None

        resource_link = self.get_object()
        if not isinstance(resource_link, ResourceLink):
            cls = resource_link.__class__.__name__
            raise LTIImproperlyConfigured(
                f'{cls} is not an instance of ResourceLink.'
                f'Define {cls} as {cls}(ResourceLink).'
            )

        fields['resource_link'] = resource_link
        fields['context'] = context

        resource, created = Resource.objects.get_or_create(
            resource_id=fields.pop('id'),
            platform=platform,
            defaults=fields
        )

        if not created:
            resource.update(fields)

        return resource

    def dispatch(self, request, *args, **kwargs):
        claims, platform = validate(request)

        if claims:
            # Update platform information
            platform_fields = platform.get_fields(claims)
            if platform_fields:
                platform.update(platform_fields)

            # Get optional entities
            context = self.get_context(claims, platform)
            resource = self.get_resource(claims, context, platform)

            user = authenticate(
                request,
                claims=claims,
                context=context,
                platform=platform
            )
            if user is not None:
                login(request, user)

                if context:
                    request.session['lti-context'] = context.id
                if resource:
                    request.session['lti-resource'] = resource.id
        else:
            context = None
            context_pk = request.session.get('lti-context')
            if context_pk:
                context = Context.objects.get(pk=context_pk)

            resource = None
            resource_pk = request.session.get('lti-resource')
            if resource_pk:
                resource = Resource.objects.get(pk=resource_pk)

        kwargs.update({
            'claims': claims,
            'context': context,
            'platform': platform,
            'resource': resource
        })

        return super().dispatch(request, *args, **kwargs)


class LTIRoleMixin:
    role = ''

    def dispatch(self, request, context, *args, **kwargs):
        if not context:
            cls = self.__class__.__name__
            raise LTIContextError(f'{cls} is missing LTI context. Make sure '
                                  f'the LTIMessageMixin is applied.')

        roles = request.user.lti.roles(context)
        if self.role and self.role not in roles:
            raise PermissionDenied

        return super().dispatch(request, *args, **kwargs)
