from rest_framework import serializers
from cinema.models import (
    Movie,
    MovieSession,
    Ticket,
    Order,
    Genre,
    Actor,
    CinemaHall,
)


# ---- Довідники ----
class GenreSerializer(serializers.ModelSerializer):
    class Meta:
        model = Genre
        fields = ("id", "name")


class ActorSerializer(serializers.ModelSerializer):
    full_name = serializers.CharField(
        source="full_name", read_only=True
    )

    class Meta:
        model = Actor
        fields = ("id", "first_name", "last_name", "full_name")


class CinemaHallSerializer(serializers.ModelSerializer):
    capacity = serializers.IntegerField(read_only=True)

    class Meta:
        model = CinemaHall
        fields = ("id", "name", "rows", "seats_in_row", "capacity")


# ---- Movie ----
class MovieSerializer(serializers.ModelSerializer):
    class Meta:
        model = Movie
        fields = (
            "id",
            "title",
            "description",
            "duration",
            "genres",
            "actors",
            "image",
        )


class MovieListSerializer(serializers.ModelSerializer):
    image = serializers.ImageField(read_only=True)

    class Meta:
        model = Movie
        fields = (
            "id",
            "title",
            "description",
            "duration",
            "genres",
            "actors",
            "image",
        )


class MovieDetailSerializer(serializers.ModelSerializer):
    image = serializers.ImageField(read_only=True)

    class Meta:
        model = Movie
        fields = (
            "id",
            "title",
            "description",
            "duration",
            "genres",
            "actors",
            "image",
        )


class MovieCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Movie
        fields = (
            "id",
            "title",
            "description",
            "duration",
            "genres",
            "actors",
            "image",
        )
    # image не можна передавати на POST
    read_only_fields = ("image",)
    # genres/actors не обов'язкові в payload
    extra_kwargs = {
        "genres": {"required": False},
        "actors": {"required": False},
    }


class MovieImageSerializer(serializers.ModelSerializer):
    class Meta:
        model = Movie
        fields = ("id", "image")
        read_only_fields = ("id",)


# ---- MovieSession ----
class MovieSessionListSerializer(serializers.ModelSerializer):
    movie_title = serializers.CharField(
        source="movie.title", read_only=True
    )
    cinema_hall_name = serializers.CharField(
        source="cinema_hall.name", read_only=True
    )
    cinema_hall_capacity = serializers.IntegerField(
        source="cinema_hall.capacity", read_only=True
    )
    movie_image = serializers.SerializerMethodField()
    tickets_available = serializers.SerializerMethodField()

    class Meta:
        model = MovieSession
        fields = (
            "id",
            "show_time",
            "movie_title",
            "cinema_hall_name",
            "cinema_hall_capacity",
            "movie_image",
            "tickets_available",
        )

    def get_movie_image(self, obj):
        img = getattr(obj.movie, "image", None)
        if not img:
            return None
        request = self.context.get("request")
        url = img.url
        return request.build_absolute_uri(url) if request else url

    def get_tickets_available(self, obj):
        hall = obj.cinema_hall
        cap = hall.rows * hall.seats_in_row
        taken = obj.tickets.count()
        return cap - taken


class MovieNestedSerializer(serializers.ModelSerializer):
    image = serializers.ImageField(read_only=True)

    class Meta:
        model = Movie
        fields = (
            "id",
            "title",
            "description",
            "duration",
            "genres",
            "actors",
            "image",
        )


class MovieSessionDetailSerializer(serializers.ModelSerializer):
    movie = MovieNestedSerializer(read_only=True)
    cinema_hall = serializers.SerializerMethodField()
    taken_places = serializers.SerializerMethodField()

    class Meta:
        model = MovieSession
        fields = (
            "id",
            "show_time",
            "movie",
            "cinema_hall",
            "taken_places",
        )

    def get_cinema_hall(self, obj):
        hall = obj.cinema_hall
        return {
            "id": hall.id,
            "name": hall.name,
            "rows": hall.rows,
            "seats_in_row": hall.seats_in_row,
            "capacity": hall.capacity,
        }

    def get_taken_places(self, obj):
        qs = obj.tickets.values("row", "seat").order_by("row", "seat")
        return list(qs)


class MovieSessionSerializer(serializers.ModelSerializer):
    class Meta:
        model = MovieSession
        fields = ("id", "movie", "cinema_hall", "show_time")


# ---- Orders & Tickets ----
class TicketCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Ticket
        fields = ("row", "seat", "movie_session")


class TicketReadSerializer(serializers.ModelSerializer):
    movie_session = MovieSessionListSerializer(read_only=True)

    class Meta:
        model = Ticket
        fields = ("id", "row", "seat", "movie_session")


class OrderListSerializer(serializers.ModelSerializer):
    tickets = TicketReadSerializer(many=True, read_only=True)

    class Meta:
        model = Order
        fields = ("id", "tickets", "created_at")


class OrderSerializer(serializers.ModelSerializer):
    tickets = TicketCreateSerializer(many=True, write_only=True)

    class Meta:
        model = Order
        fields = ("id", "tickets")

    def create(self, validated_data):
        tickets_data = validated_data.pop("tickets", [])
        user = self.context["request"].user
        order = Order.objects.create(user=user)
        for ticket_data in tickets_data:
            Ticket.objects.create(order=order, **ticket_data)
        return order
