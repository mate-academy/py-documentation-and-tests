from django.db import transaction
from rest_framework import serializers
from rest_framework.exceptions import ValidationError

from cinema.models import (
    Genre,
    Actor,
    CinemaHall,
    Movie,
    MovieSession,
    Ticket,
    Order,
)


class GenreSerializer(serializers.ModelSerializer):
    """Serializer for movie genres"""
    class Meta:
        model = Genre
        fields = ("id", "name")


class ActorSerializer(serializers.ModelSerializer):
    """Serializer for actors"""
    class Meta:
        model = Actor
        fields = ("id", "first_name", "last_name", "full_name")


class CinemaHallSerializer(serializers.ModelSerializer):
    """Serializer for cinema halls"""
    class Meta:
        model = CinemaHall
        fields = ("id", "name", "rows", "seats_in_row", "capacity")


class MovieSerializer(serializers.ModelSerializer):
    """Base serializer for Movie model"""
    class Meta:
        model = Movie
        fields = (
            "id",
            "title",
            "description",
            "duration",
            "genres",
            "actors",
        )


class MovieListSerializer(serializers.ModelSerializer):
    """Serializer for listing movies with genres, actors, and image"""
    genres = serializers.SlugRelatedField(
        many=True, read_only=True, slug_field="name", help_text="Movie genres"
    )
    actors = serializers.SlugRelatedField(
        many=True,
        read_only=True,
        slug_field="full_name",
        help_text="Movie actors full names"
    )
    image = serializers.ImageField(read_only=True,
                                   help_text="URL of the movie image")

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
    """Serializer for movie detail view"""
    genres = GenreSerializer(many=True, read_only=True)
    actors = ActorSerializer(many=True, read_only=True)
    image = serializers.ImageField(read_only=True,
                                   help_text="URL of the movie image")

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


class MovieImageSerializer(serializers.ModelSerializer):
    """Serializer for uploading movie image"""
    image = serializers.ImageField(help_text="Upload a new movie image")

    class Meta:
        model = Movie
        fields = ("id", "image")


class MovieSessionSerializer(serializers.ModelSerializer):
    """Base serializer for movie session"""
    class Meta:
        model = MovieSession
        fields = ("id", "show_time", "movie", "cinema_hall")


class MovieSessionListSerializer(MovieSessionSerializer):
    """Serializer for listing movie sessions
        with related movie and hall info"""

    movie_title = serializers.CharField(source="movie.title",
                                        read_only=True,
                                        help_text="Movie title")
    movie_image = serializers.ImageField(
        source="movie.image",
        read_only=True,
        help_text="URL of the related movie image"
    )
    cinema_hall_name = serializers.CharField(
        source="cinema_hall.name", read_only=True, help_text="Cinema hall name"
    )
    cinema_hall_capacity = serializers.IntegerField(
        source="cinema_hall.capacity",
        read_only=True,
        help_text="Total capacity of the hall"
    )
    tickets_available = serializers.IntegerField(
        read_only=True, help_text="Number of available tickets"
    )

    class Meta:
        model = MovieSession
        fields = (
            "id",
            "show_time",
            "movie_title",
            "movie_image",
            "cinema_hall_name",
            "cinema_hall_capacity",
            "tickets_available",
        )


class TicketSerializer(serializers.ModelSerializer):
    """Serializer for tickets with validation of seat availability"""
    def validate(self, attrs):
        data = super(TicketSerializer, self).validate(attrs=attrs)
        Ticket.validate_ticket(
            attrs["row"],
            attrs["seat"],
            attrs["movie_session"].cinema_hall,
            ValidationError
        )
        return data

    class Meta:
        model = Ticket
        fields = ("id", "row", "seat", "movie_session")


class TicketListSerializer(TicketSerializer):
    """Serializer for ticket list including movie session info"""
    movie_session = MovieSessionListSerializer(many=False, read_only=True)


class TicketSeatsSerializer(TicketSerializer):
    """Serializer showing only row and seat"""
    class Meta:
        model = Ticket
        fields = ("row", "seat")


class MovieSessionDetailSerializer(MovieSessionSerializer):
    """Serializer for detailed movie session view with tickets"""
    movie = MovieListSerializer(many=False, read_only=True)
    cinema_hall = CinemaHallSerializer(many=False, read_only=True)
    taken_places = TicketSeatsSerializer(
        source="tickets", many=True, read_only=True, help_text="Booked seats"
    )

    class Meta:
        model = MovieSession
        fields = ("id", "show_time", "movie", "cinema_hall", "taken_places")


class OrderSerializer(serializers.ModelSerializer):
    """Serializer for creating orders with tickets"""
    tickets = TicketSerializer(many=True, read_only=False, allow_empty=False)

    class Meta:
        model = Order
        fields = ("id", "tickets", "created_at")

    def create(self, validated_data):
        with transaction.atomic():
            tickets_data = validated_data.pop("tickets")
            order = Order.objects.create(**validated_data)
            for ticket_data in tickets_data:
                Ticket.objects.create(order=order, **ticket_data)
            return order


class OrderListSerializer(OrderSerializer):
    """Serializer for listing orders with detailed ticket info"""
    tickets = TicketListSerializer(many=True, read_only=True)
