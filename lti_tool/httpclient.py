from jwcrypto import jwt
import requests

from django.core.cache import cache

from lti_tool.exceptions import LTIRequestError, LTITokenRetrieveError
from lti_tool.jwt import bearer_jwt


class HTTPClient:
    def __init__(self):
        self.session = requests.Session()

    def _request(self, method, url, context, headers=None, **kwargs):
        headers = headers or {}

        if context:
            auth_header = self._auth_header(context)
            headers.update(auth_header)

        try:
            response = self.session.request(
                method=method,
                url=url,
                headers=headers,
                **kwargs
            )

            response.raise_for_status()
        except requests.exceptions.RequestException as e:
            # NOTE Platform error handling is not specified. Raise every error
            # for now.
            raise LTIRequestError from e

        return response

    def get(self, url, context=None, **kwargs):
        return self._request('GET', url, context, **kwargs)

    def post(self, url, context=None, **kwargs):
        return self._request('POST', url, context, **kwargs)

    def delete(self, url, context=None, **kwargs):
        return self._request('DELETE', url, context, **kwargs)

    def put(self, url, context=None, **kwargs):
        return self._request('PUT', url, context, **kwargs)

    def _access_token(self, platform, scope):
        data = {
            'grant_type': 'client_credentials',
            'client_assertion_type':
                'urn:ietf:params:oauth:client-assertion-type:jwt-bearer',
            'client_assertion': bearer_jwt(platform),
            'scope': ' '.join(s for s in scope)
        }

        try:
            data = self.post(
                platform.access_token_url,
                data=data
            ).json()
        except LTIRequestError as e:
            raise LTITokenRetrieveError(
                'Could not retrieve access token.'
            ) from e

        return data

    def _auth_header(self, context):
        cache_key = f'context_{context.pk}_token'
        access_token, scope = cache.get(cache_key, (None, None))

        # Update if token has expired or scope has changed
        if not access_token or scope != context.scope:
            data = self._access_token(context.platform, context.scope)

            access_token = data['access_token']
            timeout = data['expires_in'] - 300  # Compensate clock skew

            cache.set(cache_key, (access_token, context.scope),
                      timeout=timeout)

        return {'Authorization': f'Bearer {access_token}'}
