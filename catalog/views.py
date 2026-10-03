from django.utils import timezone
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from catalog.models import Book, Collection, Genre, Review, Shelf
from catalog.present import book_detail, book_summary, review_payload
from catalog.queries import book_queryset, filter_books, genre_counts, saved_book_ids
from catalog.serializers import ReviewCreateSerializer, ShelfBookSerializer, ShelfWriteSerializer
from commerce.models import OrderItem
from common.exceptions import APIError
from common.pagination import ReaderPagination


def _summaries(books, user):
    counts = genre_counts()
    saved = saved_book_ids(user)
    return [book_summary(book, counts, saved) for book in books]


def _book_or_404(book_id):
    book = (
        Book.objects.select_related("author", "genre")
        .prefetch_related("formats", "images", "contents")
        .filter(pk=book_id)
        .first()
    )
    if book is None:
        raise APIError("Book not found.", code="not_found", status_code=404)
    return book


def _shelf_or_404(user, shelf_id):
    shelf = user.shelves.filter(pk=shelf_id).first()
    if shelf is None:
        raise APIError("Shelf not found.", code="not_found", status_code=404)
    return shelf


def _shelf_payload(shelf, user, *, with_books):
    payload = {
        "id": str(shelf.id),
        "name": shelf.name,
        "is_default": shelf.is_default,
        "book_count": shelf.books.count(),
    }
    if with_books:
        books = shelf.books.select_related("author", "genre").prefetch_related("formats").order_by("title")
        payload["books"] = _summaries(books, user)
    return payload


def _default_shelf(user):
    shelf = user.shelves.filter(is_default=True).first()
    if shelf is not None:
        return shelf
    named = user.shelves.filter(name__iexact="Saved").first()
    if named is not None:
        named.is_default = True
        named.save(update_fields=["is_default"])
        return named
    return Shelf.objects.create(user=user, name="Saved", is_default=True)


class GenreListView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        counts = genre_counts()
        return Response(
            [
                {"slug": genre.slug, "name": genre.name, "book_count": counts.get(genre.slug, 0)}
                for genre in Genre.objects.all()
            ]
        )


class BookListView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        paginator = ReaderPagination()
        page = paginator.paginate_queryset(filter_books(request.query_params), request, view=self)
        return paginator.get_paginated_response(_summaries(page, request.user))


class BookDetailView(APIView):
    permission_classes = [AllowAny]

    def get(self, request, book_id):
        book = _book_or_404(book_id)
        return Response(book_detail(book, genre_counts(), saved_book_ids(request.user)))


class RelatedBooksView(APIView):
    permission_classes = [AllowAny]

    def get(self, request, book_id):
        book = _book_or_404(book_id)
        related = [
            link.related
            for link in book.related_links.select_related("related__author", "related__genre").prefetch_related(
                "related__formats"
            )
        ]
        return Response(_summaries(related, request.user))


class ReviewListView(APIView):
    permission_classes = [AllowAny]

    def get(self, request, book_id):
        book = _book_or_404(book_id)
        paginator = ReaderPagination()
        page = paginator.paginate_queryset(book.reviews.all(), request, view=self)
        return paginator.get_paginated_response([review_payload(row) for row in page])

    def post(self, request, book_id):
        if not request.user.is_authenticated:
            raise APIError(
                "Authentication credentials were not provided.",
                code="not_authenticated",
                status_code=401,
            )
        book = _book_or_404(book_id)
        serializer = ReviewCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        if Review.objects.filter(book=book, user=request.user).exists():
            raise APIError("You have already reviewed this book.", code="conflict", status_code=409)
        data = serializer.validated_data
        verified = OrderItem.objects.filter(order__user=request.user, book=book).exists()
        review = Review.objects.create(
            book=book,
            user=request.user,
            reviewer_name=request.user.name,
            reviewer_title="Reader",
            rating=data["rating"],
            body=data["body"],
            edition=data.get("edition") or "",
            verified_purchase=verified,
            created_at=timezone.now(),
        )
        book.review_count += 1
        book.save(update_fields=["review_count"])
        return Response(review_payload(review), status=201)


class SaveBookView(APIView):
    def post(self, request, book_id):
        book = _book_or_404(book_id)
        shelf = _default_shelf(request.user)
        shelf.books.add(book)
        return Response({"book_id": str(book.id), "saved": True, "shelf_id": str(shelf.id)})

    def delete(self, request, book_id):
        book = _book_or_404(book_id)
        Shelf.books.through.objects.filter(shelf__user=request.user, book=book).delete()
        return Response({"book_id": str(book.id), "saved": False, "shelf_id": None})


class CollectionListView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        rows = []
        for collection in Collection.objects.all():
            rows.append(
                {
                    "slug": collection.slug,
                    "name": collection.name,
                    "description": collection.description,
                    "book_count": collection.books.count(),
                }
            )
        return Response(rows)


class CollectionDetailView(APIView):
    permission_classes = [AllowAny]

    def get(self, request, slug):
        collection = Collection.objects.filter(slug=slug).first()
        if collection is None:
            raise APIError("Collection not found.", code="not_found", status_code=404)
        books = (
            collection.books.select_related("author", "genre")
            .prefetch_related("formats")
            .order_by("collectionbook__position", "title")
        )
        return Response(
            {
                "slug": collection.slug,
                "name": collection.name,
                "description": collection.description,
                "book_count": books.count(),
                "books": _summaries(books, request.user),
            }
        )


class ShelfListView(APIView):
    def get(self, request):
        return Response([_shelf_payload(shelf, request.user, with_books=False) for shelf in request.user.shelves.all()])

    def post(self, request):
        serializer = ShelfWriteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        name = serializer.validated_data["name"]
        if request.user.shelves.filter(name__iexact=name).exists():
            raise APIError(
                "You already have a shelf with that name.",
                details=[{"field": "name", "message": "You already have a shelf with that name."}],
            )
        shelf = Shelf.objects.create(user=request.user, name=name, is_default=False)
        return Response(_shelf_payload(shelf, request.user, with_books=True), status=201)


class ShelfDetailView(APIView):
    def get(self, request, shelf_id):
        shelf = _shelf_or_404(request.user, shelf_id)
        return Response(_shelf_payload(shelf, request.user, with_books=True))

    def patch(self, request, shelf_id):
        shelf = _shelf_or_404(request.user, shelf_id)
        serializer = ShelfWriteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        name = serializer.validated_data["name"]
        if request.user.shelves.filter(name__iexact=name).exclude(pk=shelf.pk).exists():
            raise APIError(
                "You already have a shelf with that name.",
                details=[{"field": "name", "message": "You already have a shelf with that name."}],
            )
        shelf.name = name
        shelf.save(update_fields=["name"])
        return Response(_shelf_payload(shelf, request.user, with_books=True))

    def delete(self, request, shelf_id):
        shelf = _shelf_or_404(request.user, shelf_id)
        if shelf.is_default:
            raise APIError("The default Saved shelf cannot be deleted.", code="conflict", status_code=409)
        shelf.delete()
        return Response(status=204)


class ShelfBooksView(APIView):
    def post(self, request, shelf_id):
        shelf = _shelf_or_404(request.user, shelf_id)
        serializer = ShelfBookSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        book = book_queryset().filter(pk=serializer.validated_data["book_id"]).first()
        if book is None:
            raise APIError("Book not found.", code="not_found", status_code=404)
        shelf.books.add(book)
        return Response(_shelf_payload(shelf, request.user, with_books=True))


class ShelfBookDetailView(APIView):
    def delete(self, request, shelf_id, book_id):
        shelf = _shelf_or_404(request.user, shelf_id)
        if not shelf.books.filter(pk=book_id).exists():
            raise APIError("That book is not on this shelf.", code="not_found", status_code=404)
        shelf.books.remove(book_id)
        return Response(status=204)
