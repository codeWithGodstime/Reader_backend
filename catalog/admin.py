from django.contrib import admin

from catalog.models import (
    Author,
    Book,
    BookFormat,
    BookImage,
    Collection,
    CollectionBook,
    Genre,
    RelatedBook,
    Review,
    Shelf,
    TocEntry,
)


class BookFormatInline(admin.TabularInline):
    model = BookFormat
    extra = 0
    show_change_link = True
    ordering = ("position",)
    fields = (
        "code",
        "label",
        "detail",
        "price",
        "compare_at_price",
        "in_stock",
        "rare",
        "position",
    )


class BookImageInline(admin.TabularInline):
    model = BookImage
    extra = 0
    show_change_link = True
    ordering = ("position",)
    fields = ("label", "url", "position")


class TocEntryInline(admin.TabularInline):
    model = TocEntry
    extra = 0
    show_change_link = True
    ordering = ("position",)
    fields = ("title", "page", "position")


class RelatedBookInline(admin.TabularInline):
    model = RelatedBook
    fk_name = "book"
    extra = 0
    show_change_link = True
    ordering = ("position",)
    autocomplete_fields = ("related",)
    fields = ("related", "position")


class CollectionBookInline(admin.TabularInline):
    model = CollectionBook
    extra = 0
    show_change_link = True
    ordering = ("position",)
    autocomplete_fields = ("book",)
    fields = ("book", "position")


@admin.register(Genre)
class GenreAdmin(admin.ModelAdmin):
    list_display = ("name", "slug")
    search_fields = ("name", "slug")
    ordering = ("name",)


@admin.register(Author)
class AuthorAdmin(admin.ModelAdmin):
    list_display = ("name", "slug")
    search_fields = ("name", "slug")
    ordering = ("name",)


@admin.register(Book)
class BookAdmin(admin.ModelAdmin):
    list_display = (
        "title",
        "author",
        "genre",
        "sku",
        "price",
        "in_stock",
        "featured_rank",
    )
    list_filter = ("in_stock", "genre", "language")
    search_fields = ("title", "sku", "isbn13", "slug", "author__name")
    ordering = ("featured_rank", "title")
    readonly_fields = ("created_at",)
    autocomplete_fields = ("author", "genre")
    list_select_related = ("author", "genre")
    inlines = (BookFormatInline, BookImageInline, TocEntryInline, RelatedBookInline)


@admin.register(BookFormat)
class BookFormatAdmin(admin.ModelAdmin):
    list_display = ("book", "code", "label", "price", "in_stock", "rare", "position")
    list_filter = ("code", "in_stock", "rare")
    search_fields = ("code", "label", "book__title", "book__sku")
    ordering = ("position",)
    autocomplete_fields = ("book",)
    list_select_related = ("book",)


@admin.register(BookImage)
class BookImageAdmin(admin.ModelAdmin):
    list_display = ("book", "label", "position")
    search_fields = ("label", "book__title", "book__sku")
    ordering = ("position",)
    autocomplete_fields = ("book",)
    list_select_related = ("book",)


@admin.register(TocEntry)
class TocEntryAdmin(admin.ModelAdmin):
    list_display = ("book", "title", "page", "position")
    search_fields = ("title", "book__title", "book__sku")
    ordering = ("position",)
    autocomplete_fields = ("book",)
    list_select_related = ("book",)


@admin.register(RelatedBook)
class RelatedBookAdmin(admin.ModelAdmin):
    list_display = ("book", "related", "position")
    search_fields = ("book__title", "related__title", "book__sku", "related__sku")
    ordering = ("position",)
    autocomplete_fields = ("book", "related")
    list_select_related = ("book", "related")


@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    list_display = ("book", "reviewer_name", "rating", "verified_purchase", "created_at")
    list_filter = ("rating", "verified_purchase")
    search_fields = ("reviewer_name", "body", "book__title", "user__email")
    ordering = ("-created_at",)
    autocomplete_fields = ("book", "user")
    list_select_related = ("book", "user")
    date_hierarchy = "created_at"


@admin.register(Collection)
class CollectionAdmin(admin.ModelAdmin):
    list_display = ("name", "slug")
    search_fields = ("name", "slug", "description")
    ordering = ("name",)
    inlines = (CollectionBookInline,)


@admin.register(CollectionBook)
class CollectionBookAdmin(admin.ModelAdmin):
    list_display = ("collection", "book", "position")
    search_fields = ("collection__name", "book__title", "book__sku")
    ordering = ("position",)
    autocomplete_fields = ("book",)
    list_select_related = ("collection", "book")


@admin.register(Shelf)
class ShelfAdmin(admin.ModelAdmin):
    list_display = ("name", "user", "is_default", "created_at")
    list_filter = ("is_default",)
    search_fields = ("name", "user__email", "user__name")
    ordering = ("-is_default", "name")
    readonly_fields = ("created_at",)
    autocomplete_fields = ("user",)
    filter_horizontal = ("books",)
    list_select_related = ("user",)
