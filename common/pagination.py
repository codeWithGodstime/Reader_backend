from rest_framework.exceptions import NotFound
from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response

from common.exceptions import APIError


class ReaderPagination(PageNumberPagination):
    page_size = 12
    page_query_param = "page"
    page_size_query_param = "page_size"
    max_page_size = 50

    def paginate_queryset(self, queryset, request, view=None):
        try:
            return super().paginate_queryset(queryset, request, view=view)
        except NotFound as exc:
            message = str(exc.detail) if isinstance(exc.detail, str) else "Invalid page."
            raise APIError(message, code="validation_error", status_code=400) from exc

    def get_paginated_response(self, data):
        return Response(
            {
                "count": self.page.paginator.count,
                "page": self.page.number,
                "page_size": self.get_page_size(self.request),
                "next": self.get_next_link(),
                "previous": self.get_previous_link(),
                "results": data,
            }
        )
