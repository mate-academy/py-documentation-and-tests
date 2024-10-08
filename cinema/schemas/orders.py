from drf_spectacular.utils import (
    extend_schema_view,
    extend_schema,
)


order_viewset_schema = extend_schema_view(
    list=extend_schema(
        description="Get a list of all orders.",
    ),
    create=extend_schema(
        description="Add a new order.",
    ),
)
