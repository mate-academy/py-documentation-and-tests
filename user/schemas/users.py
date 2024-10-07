from drf_spectacular.utils import (
    extend_schema_view,
    extend_schema,
)


user_create_schema = extend_schema_view(
    post=extend_schema(
        description="Register a new user.",
    )
)

user_manage_schema = extend_schema_view(
    get=extend_schema(
        description="Retrieve information about current user.",
    ),
    put=extend_schema(
        description="Update information about current user.",
    ),
    patch=extend_schema(
        description="Update information about current user.",
    ),
)
