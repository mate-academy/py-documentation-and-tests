# Documentation, throttling, JWT and tests

- Read [the guideline](https://github.com/mate-academy/py-task-guideline/blob/main/README.md) before start

## In this task you will add tests and some advanced things to your project

1. Add Swagger documentation for the whole project. It should include 
all query params described, such as filtering by title, genres, actors for 
movie; filtering by date, movie for movie session.
2. Add throttling settings, it should allow:
    - 10 requests per minute for unauthorized users
    - 30 requests per minute for authorized ones
3. Add a JWT support for the project.
4. Cover the whole MovieViewSet with tests.
