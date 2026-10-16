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

## Run locally

Use Python 3.10, as in CI. Create and activate a virtual environment, then run:

```shell
pip install -r requirements.txt
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

## API documentation

With the development server running, open:

- Swagger UI: http://127.0.0.1:8000/api/doc/swagger/
- ReDoc: http://127.0.0.1:8000/api/doc/redoc/
- OpenAPI schema: http://127.0.0.1:8000/api/schema/

Swagger describes movie filters (`title`, comma-separated `genres` and `actors`
IDs) and movie-session filters (`date` in `YYYY-MM-DD` format and `movie` ID).
Staff can upload an image through the movie's `upload-image` action using
`multipart/form-data`.

## Authentication and request limits

Register at `POST /api/user/register/`. To obtain JWT access and refresh tokens,
send your email and password to `POST /api/user/token/`:

```json
{"email": "your@email.com", "password": "your-password"}
```

Pass the access token in the `Authorization: Bearer <access>` header. In Swagger,
use the **Authorize** button and enter the access token under `jwtAuth`.
Send `{"refresh": "<refresh>"}` to `POST /api/user/token/refresh/` for a new
access token, or `{"token": "<access>"}` to `POST /api/user/token/verify/` to
verify a token. The existing `/api/user/login/` endpoint and
`Authorization: Token <token>` authentication also remain available.

Anonymous clients can make 10 requests per minute and authenticated users can
make 30. Exceeding the limit returns HTTP `429` with a `Retry-After` header.
Cinema endpoints require authentication; creating movies and uploading their
images require a staff account.

## Checks

```shell
python manage.py test
python -m flake8
python manage.py spectacular --validate --fail-on-warn
```
