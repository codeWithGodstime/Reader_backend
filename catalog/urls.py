from django.urls import path

from catalog.views import (
    BookDetailView,
    BookListView,
    CollectionDetailView,
    CollectionListView,
    GenreListView,
    RelatedBooksView,
    ReviewListView,
    SaveBookView,
    ShelfBookDetailView,
    ShelfBooksView,
    ShelfDetailView,
    ShelfListView,
)

urlpatterns = [
    path("genres", GenreListView.as_view()),
    path("books", BookListView.as_view()),
    path("books/<uuid:book_id>", BookDetailView.as_view()),
    path("books/<uuid:book_id>/related", RelatedBooksView.as_view()),
    path("books/<uuid:book_id>/reviews", ReviewListView.as_view()),
    path("books/<uuid:book_id>/save", SaveBookView.as_view()),
    path("collections", CollectionListView.as_view()),
    path("collections/<slug:slug>", CollectionDetailView.as_view()),
    path("shelves", ShelfListView.as_view()),
    path("shelves/<uuid:shelf_id>", ShelfDetailView.as_view()),
    path("shelves/<uuid:shelf_id>/books", ShelfBooksView.as_view()),
    path("shelves/<uuid:shelf_id>/books/<uuid:book_id>", ShelfBookDetailView.as_view()),
]
