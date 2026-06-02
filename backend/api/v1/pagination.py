from rest_framework.pagination import PageNumberPagination


class CustomPagination(PageNumberPagination):
    """Пагинатор с возможностью динамического изменения размера страницы."""

    page_size = 6
    page_size_query_param = 'limit'
