from decimal import Decimal

from django.db.models import Count, Q

from catalog.models import Book, Genre, Shelf
from common.exceptions import APIError

PRICE_FILTERS = {"any", "under_16", "from_16_to_18", "over_18"}
SORTS = {"featured", "title", "price_asc", "price_desc", "newest", "rating"}
FORMATS = {"paperback", "hardcover", "ebook", "signed"}


def book_queryset():
    return Book.objects.select_related("author", "genre").prefetch_related("formats")


def genre_counts():
    return dict(Genre.objects.annotate(total=Count("books")).values_list("slug", "total"))


def saved_book_ids(user):
    if not getattr(user, "is_authenticated", False):
        return set()
    ids = Shelf.objects.filter(user=user).values_list("books__id", flat=True)
    return {book_id for book_id in ids if book_id is not None}


def filter_books(params):
    qs = book_queryset()
    query = (params.get("q") or "").strip()
    if query:
        qs = qs.filter(
            Q(title__icontains=query)
            | Q(author__name__icontains=query)
            | Q(description__icontains=query)
        )
    genre = (params.get("genre") or "").strip()
    if genre:
        if not Genre.objects.filter(slug=genre).exists():
            raise APIError(
                "Unknown genre.",
                details=[{"field": "genre", "message": "Unknown genre."}],
            )
        qs = qs.filter(genre_id=genre)
    price = params.get("price") or "any"
    if price not in PRICE_FILTERS:
        raise APIError(
            "Unknown price filter.",
            details=[{"field": "price", "message": "Use any, under_16, from_16_to_18, or over_18."}],
        )
    if price == "under_16":
        qs = qs.filter(price__lt=Decimal("16"))
    elif price == "from_16_to_18":
        qs = qs.filter(price__gte=Decimal("16"), price__lte=Decimal("18"))
    elif price == "over_18":
        qs = qs.filter(price__gt=Decimal("18"))
    edition = (params.get("format") or "").strip()
    if edition:
        if edition not in FORMATS:
            raise APIError(
                "Unknown format.",
                details=[{"field": "format", "message": "Use paperback, hardcover, ebook, or signed."}],
            )
        qs = qs.filter(formats__code=edition)
    stock = params.get("in_stock")
    if stock not in (None, ""):
        if str(stock).lower() in {"true", "1"}:
            qs = qs.filter(in_stock=True)
        elif str(stock).lower() in {"false", "0"}:
            qs = qs.filter(in_stock=False)
        else:
            raise APIError(
                "Invalid in_stock value.",
                details=[{"field": "in_stock", "message": "Use true or false."}],
            )
    sort = params.get("sort") or "featured"
    if sort not in SORTS:
        raise APIError(
            "Unknown sort.",
            details=[{"field": "sort", "message": "Use featured, title, price_asc, price_desc, newest, or rating."}],
        )
    ordering = {
        "featured": ("featured_rank", "title"),
        "title": ("title",),
        "price_asc": ("price", "title"),
        "price_desc": ("-price", "title"),
        "newest": ("-published_on", "title"),
        "rating": ("-rating", "title"),
    }[sort]
    return qs.distinct().order_by(*ordering)
