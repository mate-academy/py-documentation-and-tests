from drf_spectacular.utils import (
    extend_schema_view,
    extend_schema,
)


actor_viewset_schema = extend_schema_view(
    list=extend_schema(
        description="Get a list of all actors.",
    ),
    create=extend_schema(
        description="Add a new actor",
    ),
)
