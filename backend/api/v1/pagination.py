from rest_framework.pagination import PageNumberPagination


PG_SIZE = 6


class LimitPageNumberPagination(PageNumberPagination):
    """Пагинатор с возможностью динамического изменения размера страницы."""

    page_size = PG_SIZE
    page_size_query_param = 'limit'
