# Documentation, throttling, JWT and tests

- **Read** [the guideline](https://github.com/mate-academy/py-task-guideline/blob/main/README.md) before start
- After loading data from fixture you can use following superuser (or create another one by yourself):
  - Email: `admin.user@cinema.com`
  - Password: `1qazcde3`

In this task you will add tests and some advanced things to your project:
1. Add Swagger documentation for the whole project. 
It should include all query params described, such as:
   - filtering by title, genres, actors for movie
   - filtering by date, movie for movie session

**Remember:** don't forget to add `description` to your `OpenApiParameter`.

2. Add throttling settings, it should allow:
    - 10 requests per minute for unauthorized users
    - 30 requests per minute for authorized ones
3. Add a JWT support for the project.
4. Cover the whole `MovieViewSet` with tests.
5. Check if your code is clean. Delete imports, if you are not using them.

## Running and using the API

Install `requirements.txt`, run `python manage.py migrate`, and start the
server with `python manage.py runserver`.

- OpenAPI schema: `/api/schema/`
- Swagger UI: `/api/swagger/`
- ReDoc: `/api/redoc/`

Register at `POST /api/user/register/`. Send `email` and `password` to
`POST /api/user/login/` to receive JWT `access` and `refresh` tokens.
Authenticate requests using `Authorization: Bearer <access>`.
Send `{"refresh": "<refresh>"}` to `POST /api/user/token/refresh/` for a new
access token. Verify a token with `POST /api/user/token/verify/`.

Anonymous users may make 10 requests per minute; authenticated users may make
30 requests per minute. These limits apply across API endpoints.

Movie lists support `title` (case-insensitive substring), `genres`, and
`actors` (comma-separated IDs). Session lists support `date` (YYYY-MM-DD)
and `movie` (movie ID). Swagger describes these parameters and all endpoints.

Run the test suite with `python manage.py test`. Validate the schema with
`python manage.py spectacular --validate --fail-on-warn`.
