from django.contrib.auth import authenticate, login
from django.core.exceptions import PermissionDenied
from django.views.generic.detail import SingleObjectMixin

from lti_tool.exceptions import LTIContextError, LTIImproperlyConfigured
from lti_tool.models import Context, Platform, Resource, ResourceLink


class LTIResourceMixin(SingleObjectMixin):
    def get_context(self, claims, platform):
        id, fields = Context.get_fields(claims)

        if not id:
            return None

        context, created = Context.objects.get_or_create(
            context_id=id,
            platform=platform,
            defaults=fields
        )

        if not created:
            context.update(fields)

        return context

    def get_resource(self, claims, context, platform):
        id, fields = Resource.get_fields(claims)

        if not id:
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
            resource_id=id,
            platform=platform,
            defaults=fields
        )

        if not created:
            resource.update(fields)

        return resource

    def dispatch(self, request, *args, **kwargs):
        platform = Platform.objects.get(pk=request.session['lti-platform'])
        claims = request.session['lti-claims']

        platform_fields = platform.get_fields(claims)
        if platform_fields:
            platform.update(platform_fields)

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
                                  f'the LTIResourceMixin is applied.')

        roles = request.user.lti.roles(context)
        if self.role and self.role not in roles:
            raise PermissionDenied

        return super().dispatch(request, *args, **kwargs)
