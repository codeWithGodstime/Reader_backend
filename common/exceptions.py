from rest_framework.exceptions import (
    APIException,
    AuthenticationFailed,
    NotAuthenticated,
    NotFound,
    PermissionDenied,
    ValidationError,
)
from rest_framework.response import Response
from rest_framework.views import exception_handler


class APIError(APIException):
    status_code = 400
    default_detail = "Invalid request."
    default_code = "validation_error"

    def __init__(self, message, *, code="validation_error", status_code=400, details=None):
        self.status_code = status_code
        self.reader_code = code
        self.reader_message = message
        self.reader_details = details
        super().__init__(detail=message, code=code)


def _flatten(detail, prefix=""):
    rows = []
    if isinstance(detail, dict):
        for key, value in detail.items():
            path = f"{prefix}.{key}" if prefix else str(key)
            rows.extend(_flatten(value, path))
        return rows
    if isinstance(detail, list):
        if detail and isinstance(detail[0], (dict, list)):
            for index, value in enumerate(detail):
                rows.extend(_flatten(value, f"{prefix}[{index}]"))
            return rows
        message = " ".join(str(item) for item in detail)
        rows.append({"field": prefix or "non_field_errors", "message": message})
        return rows
    rows.append({"field": prefix or "non_field_errors", "message": str(detail)})
    return rows


def reader_exception_handler(exc, context):
    if isinstance(exc, APIError):
        body = {"code": exc.reader_code, "message": exc.reader_message}
        if exc.reader_details:
            body["details"] = exc.reader_details
        return Response({"error": body}, status=exc.status_code)

    response = exception_handler(exc, context)
    if response is None:
        return None

    details = None
    if isinstance(exc, NotAuthenticated):
        code = "not_authenticated"
        message = "Authentication credentials were not provided."
    elif isinstance(exc, AuthenticationFailed):
        code = "authentication_failed"
        message = str(exc.detail) if isinstance(exc.detail, str) else "Authentication failed."
    elif isinstance(exc, PermissionDenied):
        code = "permission_denied"
        message = "You do not have permission to do that."
    elif isinstance(exc, NotFound):
        code = "not_found"
        message = str(exc.detail) if isinstance(exc.detail, str) else "Not found."
    elif isinstance(exc, ValidationError):
        code = "validation_error"
        message = "Invalid request."
        details = _flatten(exc.detail)
    else:
        code = getattr(exc, "default_code", "error")
        message = str(exc.detail) if isinstance(getattr(exc, "detail", None), str) else "Request failed."

    body = {"code": code, "message": message}
    if details:
        body["details"] = details
    return Response({"error": body}, status=response.status_code)
