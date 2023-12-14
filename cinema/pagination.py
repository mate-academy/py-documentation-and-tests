from rest_framework import pagination


class UniversalPagination(pagination.PageNumberPagination):
    page_size = 5
