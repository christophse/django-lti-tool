class LTIError(Exception):
    pass


class LTIValidationError(LTIError):
    pass


class LTIContextError(LTIError):
    pass


class LTIImproperlyConfigured(LTIError):
    pass


class LTIRequestError(LTIError):
    pass


class LTIKeyRetrieveError(LTIRequestError):
    pass


class LTITokenRetrieveError(LTIRequestError):
    pass
