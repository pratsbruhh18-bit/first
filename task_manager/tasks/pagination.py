from rest_framework.pagination import LimitOffsetPagination

class TaskLimitOffsetPagination(LimitOffsetPagination):
    default_limit = 10  # items per page by default
    max_limit = 50 