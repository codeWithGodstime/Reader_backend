from datetime import timezone as dt_timezone

from common.money import money_str


def isoformat_z(value):
    if value is None:
        return None
    value = value.astimezone(dt_timezone.utc).replace(microsecond=0)
    return value.strftime("%Y-%m-%dT%H:%M:%SZ")


def default_edition(book):
    formats = list(book.formats.all())
    for edition in formats:
        if edition.code == book.default_format:
            return edition
    return formats[0] if formats else None


def book_summary(book, genre_counts, saved_ids):
    edition = default_edition(book)
    compare = None
    if edition is not None and edition.compare_at_price is not None:
        compare = money_str(edition.compare_at_price)
    elif book.compare_at_price is not None:
        compare = money_str(book.compare_at_price)
    return {
        "id": str(book.id),
        "slug": book.slug,
        "title": book.title,
        "subtitle": book.subtitle or None,
        "description": book.description,
        "author_name": book.author.name,
        "genre": {
            "slug": book.genre_id,
            "name": book.genre.name,
            "book_count": genre_counts.get(book.genre_id, 0),
        },
        "rating": float(book.rating),
        "review_count": book.review_count,
        "price": money_str(edition.price if edition else book.price),
        "compare_at_price": compare,
        "currency": "USD",
        "format": edition.code if edition else book.default_format,
        "format_label": edition.label if edition else book.default_format.replace("_", " ").title(),
        "cover_url": book.cover_url,
        "badges": list(book.badges or []),
        "in_stock": book.in_stock,
        "saved": book.id in saved_ids,
    }


def book_detail(book, genre_counts, saved_ids):
    payload = book_summary(book, genre_counts, saved_ids)
    author = book.author
    payload.update(
        {
            "about": book.about,
            "author": {
                "id": str(author.id),
                "name": author.name,
                "bio": author.bio,
                "title_count": author.books.count(),
            },
            "sku": book.sku,
            "pages": book.pages,
            "publisher": book.publisher,
            "language": book.language,
            "isbn13": book.isbn13,
            "dimensions": book.dimensions,
            "published_on": book.published_on.isoformat(),
            "formats": [
                {
                    "code": edition.code,
                    "label": edition.label,
                    "detail": edition.detail,
                    "price": money_str(edition.price),
                    "compare_at_price": (
                        money_str(edition.compare_at_price)
                        if edition.compare_at_price is not None
                        else None
                    ),
                    "currency": "USD",
                    "in_stock": edition.in_stock,
                    "rare": edition.rare,
                }
                for edition in book.formats.all()
            ],
            "gallery": [{"label": image.label, "url": image.url} for image in book.images.all()],
            "table_of_contents": [
                {"title": entry.title, "page": entry.page} for entry in book.contents.all()
            ],
            "curator_note": (
                None
                if not book.curator_quote
                else {
                    "quote": book.curator_quote,
                    "name": book.curator_name,
                    "role": book.curator_role,
                }
            ),
        }
    )
    return payload


def review_payload(review):
    return {
        "id": str(review.id),
        "reviewer_name": review.reviewer_name,
        "reviewer_title": review.reviewer_title or None,
        "rating": review.rating,
        "body": review.body,
        "edition": review.edition or None,
        "verified_purchase": review.verified_purchase,
        "created_at": isoformat_z(review.created_at),
    }
