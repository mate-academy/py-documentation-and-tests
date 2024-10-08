from drf_spectacular.utils import (
    extend_schema_view,
    extend_schema,
)


cinema_hall_viewset_schema = extend_schema_view(
    list=extend_schema(
        description="Get a list of all cinema halls.",
    ),
    create=extend_schema(
        description="Add a new cinema hall.",
    ),
)
