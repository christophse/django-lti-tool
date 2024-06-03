class LTIError(Exception):
    pass


class LTIContextError(LTIError):
    pass


class LTIImproperlyConfigured(LTIError):
    pass


class LTINoLineItem(LTIError):
    pass


class LTIRequestError(LTIError):
    pass


class LTIResourceError(LTIError):
    pass


class LTIValidationError(LTIError):
    pass


class LTIKeyRetrieveError(LTIRequestError):
    pass


class LTITokenRetrieveError(LTIRequestError):
    pass
