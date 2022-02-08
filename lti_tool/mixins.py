from jwcrypto import jwt
from jwcrypto.common import json_decode, JWException

from django.contrib.auth import authenticate, login
from django.core.exceptions import PermissionDenied

from lti_tool.exceptions import LTIContextError, LTIValidationError
from lti_tool.models import Context, Platform, Resource


class LTIMessageMixin:
    def validate(self, token, nonce, platform):
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

        return claims

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
        platform = Platform.objects.get(pk=request.session['lti-platform'])

        # Assume login
        if request.method.lower() == 'post' and 'id_token' in request.POST:
            token = request.POST['id_token']
            nonce = request.session['lti-nonce']
            claims = self.validate(token, nonce, platform)

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
                request.session['lti-context'] = context.id

        # No login
        else:
            claims = None
            resource = None
            context = None

            # Get context from session
            context_pk = request.session.get('lti-context')
            if context_pk:
                context = Context.objects.get(pk=context_pk)

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
