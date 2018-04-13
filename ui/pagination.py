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

    def get_paginated_response(self, data):
        """Decorate standard response with start/end indices."""
        response = super().get_paginated_response(data)
        response.data['start_index'] = self.page.start_index()
        response.data['end_index'] = self.page.end_index()
        return response
