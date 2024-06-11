from hashlib import sha1

from django.contrib.auth.backends import BaseBackend
from django.contrib.auth.models import User

from lti_tool.models import LTIUser, Roles


class LTIBackend(BaseBackend):
    def authenticate(self, request, claims, context, platform):
        # The concatination of issuer (iss) und subject (sub) should be unique.
        # To use it as Django username (limited to 150 chars w/o some special
        # chars), we hash it.

        iss = claims["iss"]
        sub = claims["sub"]

        username = sha1(bytes(f"{iss}{sub}", "ascii")).hexdigest()

        user, created = User.objects.get_or_create(
            username=username, defaults=LTIUser.get_base_fields(claims)
        )

        fields = LTIUser.get_lti_fields(claims, platform)
        lti_user, created = LTIUser.objects.get_or_create(user=user, defaults=fields)

        if not created:
            lti_user.update(fields)

        fields = Roles.get_fields(claims)
        roles, created = Roles.objects.get_or_create(
            lti_user=lti_user, context=context, defaults=fields
        )

        if not created:
            roles.update(fields)

        return user

    def get_user(self, user_id):
        try:
            return User.objects.get(pk=user_id)
        except User.DoesNotExist:
            return None
