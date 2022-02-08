from jwcrypto import jwk

from django.contrib.auth.models import User
from django.db import models

from lti_tool.ags import LineItem, LineItemManager
from lti_tool.exceptions import LTIRequestError, LTIKeyRetrieveError
from lti_tool.httpclient import HTTPClient


class Updatable(models.Model):
    class Meta:
        abstract = True

    def update(self, fields):
        """ Updates only modified fields

        :param fields: dictionary representing model fields
        """
        updated = []
        for (key, value) in fields.items():
            if getattr(self, key) != value:
                setattr(self, key, value)
                updated.append(key)

        self.save(update_fields=updated)


class Key(models.Model):
    # Key in RFC 7517 representation
    _jwk = models.JSONField(db_column='jwk')

    def __str__(self):
        return f'KID: {self.kid}'

    @property
    def jwk(self):
        return jwk.JWK().from_json(self._jwk)

    @jwk.setter
    def jwk(self, pem):
        if not pem:
            key = jwk.JWK().generate(kty='RSA')
            key.kid = key.thumbprint()
        else:
            key = jwk.JWK().from_pem(bytes(pem, 'ascii'))

        self._jwk = key.export()

    @property
    def kid(self):
        return self.jwk.kid

    def pem(self, private=False):
        pem = self.jwk.export_to_pem(private_key=private, password=None)
        return pem.decode('ascii')


class Platform(Updatable):
    issuer = models.CharField(max_length=255)
    deployment_id = models.CharField(max_length=255)
    client_id = models.CharField(max_length=255)
    auth_req_url = models.URLField(max_length=255,
                                   verbose_name='Authentification request URL')
    pub_key_url = models.URLField(max_length=255,
                                  verbose_name='Public keyset URL')
    access_token_url = models.URLField(max_length=255,
                                       verbose_name='Access token URL')
    platform_claim = models.JSONField(editable=False, default=dict)
    key = models.ForeignKey(Key, on_delete=models.CASCADE)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['issuer', 'deployment_id'],
                name='unique_lti_platform'
            )
        ]

    def __init__(self, *args, **kwargs):
        self.client = HTTPClient()
        super().__init__(*args, **kwargs)

    def __str__(self):
        return f'{self.issuer} (deployment ID: {self.deployment_id})'

    @property
    def keyset(self):
        try:
            resp = self.client.get(self.pub_key_url)
        except LTIRequestError as e:
            raise LTIKeyRetrieveError(
                'Could not retrieve platform keyset.'
            ) from e

        return jwk.JWKSet.from_json(resp.text)

    @staticmethod
    def get_fields(claims):
        claim = claims.get(
            'https://purl.imsglobal.org/spec/lti/claim/tool_platform'
        )

        if claim:
            return {'platform_claim': claim}

        return None


class Context(Updatable):
    context_id = models.CharField(max_length=255, editable=False)
    platform = models.ForeignKey(Platform, editable=False,
                                 on_delete=models.CASCADE)
    label = models.CharField(max_length=255, editable=False, default='',
                             blank=True)
    title = models.CharField(max_length=255, editable=False, default='',
                             blank=True)
    context_type = models.JSONField(editable=False, default=list)
    scope = models.JSONField(editable=False, default=list)
    _lineitems = models.CharField(max_length=255, editable=False, default='',
                                  blank=True)

    @property
    def lineitems(self):
        return LineItemManager(self, self.platform.client)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['context_id', 'platform'],
                name='unique_lti_context'
            )
        ]

    def __str__(self):
        return f'{self.title} ({self.label})'

    @staticmethod
    def get_fields(claims):
        context = claims.get(
            'https://purl.imsglobal.org/spec/lti/claim/context',
        )

        if not context:
            return None

        ags = claims.get(
            'https://purl.imsglobal.org/spec/lti-ags/claim/endpoint',
            {}
        )

        return {
            'id': context['id'],  # Mandatory
            'label': context.get('label'),
            'title': context.get('title'),
            'context_type': context.get('type'),
            'scope': ags.get('scope'),
            '_lineitems': ags.get('lineitems')
        }


class Resource(Updatable):
    resource_id = models.CharField(editable=False, max_length=255)
    platform = models.ForeignKey(Platform, editable=False,
                                 on_delete=models.CASCADE)
    context = models.ForeignKey(Context, editable=False, null=True,
                                on_delete=models.CASCADE)
    title = models.CharField(max_length=255, editable=False, null=True)
    description = models.CharField(max_length=255, editable=False, null=True)
    lineitem_id = models.CharField(max_length=255, editable=False, null=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['resource_id', 'platform'],
                name='unique_lti_resource'
            )
        ]

    def get_lineitem(self, lazy=True):
        """Returns the associated lineitem.

        :param lazy: Will load auxillary lineitem information from platform
            (HTTP request), if false.
        """
        data = {'id': self.lineitem_id}
        lineitem = LineItem(self.context.lineitems, data)

        if not lazy:
            lineitem.load()

        return lineitem

    def __str__(self):
        context = self.context if self.context else 'N/A'

        return (f'{self.title}, Context: {context}, '
                f' Platform: {self.platform}')

    @staticmethod
    def get_fields(claims):
        msg_type = claims[
            'https://purl.imsglobal.org/spec/lti/claim/message_type'
        ]

        if not msg_type == 'LtiResourceLinkRequest':
            return None

        resource_link = claims[
            'https://purl.imsglobal.org/spec/lti/claim/resource_link'
        ]

        ags = claims.get(
            'https://purl.imsglobal.org/spec/lti-ags/claim/endpoint',
            {}
        )

        return {
            'id': resource_link['id'],
            'title': resource_link.get('title'),
            'description': resource_link.get('description'),
            'lineitem_id': ags.get('lineitem')
        }


class LTIUser(Updatable):
    user = models.OneToOneField(User, on_delete=models.CASCADE,
                                related_name='lti')
    platform = models.ForeignKey(Platform, on_delete=models.CASCADE,
                                 null=True)
    identifier = models.CharField(max_length=255, editable=False, null=True)
    ext = models.JSONField(editable=False, null=True)  # Not in LTI 1.3 spec

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['identifier', 'platform'],
                name='unique_lti_user'
            )
        ]

    @staticmethod
    def get_base_fields(claims):
        mail_oidc = claims.get('email')
        mail_ext = claims.get(
            'https://purl.imsglobal.org/spec/lti/claim/ext', {}
        ).get('email')

        return {
            'first_name': claims['given_name'],
            'last_name': claims['family_name'],
            'email': mail_ext if mail_ext else mail_oidc,
        }

    @staticmethod
    def get_lti_fields(claims, platform):
        return {
            'identifier': claims['sub'],
            'platform': platform,
            'ext': claims.get('https://purl.imsglobal.org/spec/lti/claim/ext')
        }

    def roles(self, context):
        obj = Roles.objects.get(lti_user=self, context=context)
        return obj.roles


class Roles(Updatable):
    lti_user = models.ForeignKey(LTIUser, on_delete=models.CASCADE)
    context = models.ForeignKey(Context, on_delete=models.CASCADE,
                                null=True)
    roles = models.JSONField(editable=False, default=list)

    @staticmethod
    def get_fields(claims):
        return {
            'roles': claims[
                'https://purl.imsglobal.org/spec/lti/claim/roles'
            ]
        }

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['lti_user', 'context'],
                name='unique_lti_role'
            )
        ]
