import uuid

from django.conf import settings
from django.db import models


class Genre(models.Model):
    slug = models.SlugField(primary_key=True)
    name = models.CharField(max_length=80)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name


class Author(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    slug = models.SlugField(unique=True)
    name = models.CharField(max_length=160)
    bio = models.TextField(blank=True)

    def __str__(self):
        return self.name


class Book(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    slug = models.SlugField(unique=True)
    title = models.CharField(max_length=200)
    subtitle = models.CharField(max_length=300, blank=True)
    description = models.TextField()
    about = models.TextField()
    author = models.ForeignKey(Author, related_name="books", on_delete=models.PROTECT)
    genre = models.ForeignKey(Genre, related_name="books", on_delete=models.PROTECT)
    rating = models.DecimalField(max_digits=2, decimal_places=1, default=0)
    review_count = models.PositiveIntegerField(default=0)
    cover_url = models.URLField(max_length=500)
    sku = models.CharField(max_length=32, unique=True)
    in_stock = models.BooleanField(default=True)
    pages = models.PositiveIntegerField()
    publisher = models.CharField(max_length=120)
    language = models.CharField(max_length=40)
    isbn13 = models.CharField(max_length=13)
    dimensions = models.CharField(max_length=40)
    published_on = models.DateField()
    badges = models.JSONField(default=list)
    default_format = models.CharField(max_length=20)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    compare_at_price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    featured_rank = models.PositiveIntegerField(default=100)
    curator_quote = models.TextField(blank=True)
    curator_name = models.CharField(max_length=120, blank=True)
    curator_role = models.CharField(max_length=160, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["featured_rank", "title"]

    def __str__(self):
        return self.title


class BookFormat(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    book = models.ForeignKey(Book, related_name="formats", on_delete=models.CASCADE)
    code = models.CharField(max_length=20)
    label = models.CharField(max_length=40)
    detail = models.CharField(max_length=80, blank=True)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    compare_at_price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    in_stock = models.BooleanField(default=True)
    rare = models.BooleanField(default=False)
    position = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["position"]
        constraints = [
            models.UniqueConstraint(fields=["book", "code"], name="unique_book_format"),
        ]


class BookImage(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    book = models.ForeignKey(Book, related_name="images", on_delete=models.CASCADE)
    label = models.CharField(max_length=40)
    url = models.URLField(max_length=500)
    position = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["position"]


class TocEntry(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    book = models.ForeignKey(Book, related_name="contents", on_delete=models.CASCADE)
    title = models.CharField(max_length=200)
    page = models.PositiveIntegerField()
    position = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["position"]


class RelatedBook(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    book = models.ForeignKey(Book, related_name="related_links", on_delete=models.CASCADE)
    related = models.ForeignKey(Book, related_name="related_from", on_delete=models.CASCADE)
    position = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["position"]
        constraints = [
            models.UniqueConstraint(fields=["book", "related"], name="unique_related_book"),
        ]


class Review(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    book = models.ForeignKey(Book, related_name="reviews", on_delete=models.CASCADE)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        related_name="reviews",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
    )
    reviewer_name = models.CharField(max_length=120)
    reviewer_title = models.CharField(max_length=160, blank=True)
    rating = models.PositiveSmallIntegerField()
    body = models.TextField()
    edition = models.CharField(max_length=80, blank=True)
    verified_purchase = models.BooleanField(default=False)
    created_at = models.DateTimeField()

    class Meta:
        ordering = ["-created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["book", "user"],
                condition=models.Q(user__isnull=False),
                name="unique_user_review",
            ),
        ]


class Collection(models.Model):
    slug = models.SlugField(primary_key=True)
    name = models.CharField(max_length=120)
    description = models.TextField(blank=True)
    books = models.ManyToManyField(Book, through="CollectionBook", related_name="collections")

    class Meta:
        ordering = ["name"]


class CollectionBook(models.Model):
    collection = models.ForeignKey(Collection, on_delete=models.CASCADE)
    book = models.ForeignKey(Book, on_delete=models.CASCADE)
    position = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["position"]
        constraints = [
            models.UniqueConstraint(fields=["collection", "book"], name="unique_collection_book"),
        ]


class Shelf(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, related_name="shelves", on_delete=models.CASCADE)
    name = models.CharField(max_length=80)
    is_default = models.BooleanField(default=False)
    books = models.ManyToManyField(Book, related_name="shelves", blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-is_default", "name"]
        constraints = [
            models.UniqueConstraint(fields=["user", "name"], name="unique_shelf_name"),
        ]
