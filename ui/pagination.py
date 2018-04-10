"""
Custom pagination classes
"""
from django.conf import settings
from rest_framework.pagination import PageNumberPagination


class CollectionSetPagination(PageNumberPagination):
    """ Custom pagination class for collections """
    page_size = settings.PAGE_SIZE_COLLECTIONS
    page_size_query_param = settings.PAGE_SIZE_QUERY_PARAM
    max_page_size = settings.PAGE_SIZE_MAXIMUM
