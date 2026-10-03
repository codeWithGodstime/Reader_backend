import uuid
from datetime import date, datetime, timezone as dt_timezone
from decimal import Decimal

from django.core.management.base import BaseCommand

from accounts.models import Address, PaymentMethod, User, Voucher
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
from commerce.models import Cart, Faq, Order
from commerce.services import add_line, create_order, edition_for

EMAIL = "elena.rostova@reader.example"
PASSWORD = "shelf-reader-4802"


def cover(isbn):
    return f"https://covers.openlibrary.org/b/isbn/{isbn}-L.jpg"


GENRES = [
    ("fiction", "Fiction"),
    ("memoir", "Memoir"),
    ("nonfiction", "Nonfiction"),
    ("thriller", "Thriller"),
    ("essays", "Essays"),
    ("poetry", "Poetry"),
]

AUTHORS = {
    "james-clear": (
        "James Clear",
        "James Clear writes about habits, decisions, and small daily improvements. His newsletter and talks are widely used by readers rebuilding a routine.",
    ),
    "tara-westover": (
        "Tara Westover",
        "Tara Westover is a memoirist and historian. Educated recounts leaving a survivalist family in Idaho and finding a life through formal learning.",
    ),
    "kazuo-ishiguro": (
        "Kazuo Ishiguro",
        "Kazuo Ishiguro is a novelist whose books often follow memory, care, and what people are willing to overlook. He received the Nobel Prize in Literature.",
    ),
    "andy-weir": (
        "Andy Weir",
        "Andy Weir writes science fiction grounded in engineering problems. Project Hail Mary follows a lone astronaut who wakes without his mission briefing.",
    ),
    "daniel-kahneman": (
        "Daniel Kahneman",
        "Daniel Kahneman was a psychologist who studied judgment and decision-making. Thinking, Fast and Slow sets out the two modes he used to explain bias.",
    ),
    "madeline-miller": (
        "Madeline Miller",
        "Madeline Miller retells classical myth as character-driven fiction. Circe follows the witch of Aiaia from exile to a life she chooses.",
    ),
    "matt-haig": (
        "Matt Haig",
        "Matt Haig writes novels about regret, mental health, and second chances. The Midnight Library opens on the night between lives.",
    ),
    "robin-wall-kimmerer": (
        "Robin Wall Kimmerer",
        "Robin Wall Kimmerer is a botanist and member of the Citizen Potawatomi Nation. Braiding Sweetgrass joins indigenous knowledge with plant science.",
    ),
}

BOOKS = [
    {
        "id": "3c52c712-092d-46c1-8c71-1bcc451f1f7c",
        "slug": "atomic-habits",
        "title": "Atomic Habits",
        "subtitle": "An Easy & Proven Way to Build Good Habits & Break Bad Ones",
        "description": "A practical guide to building better habits and breaking the ones that hold you back.",
        "about": "James Clear argues that lasting change comes from small systems, not a burst of willpower. The book lays out four laws for making a habit obvious, attractive, easy, and satisfying.",
        "author": "james-clear",
        "genre": "nonfiction",
        "rating": "4.9",
        "review_count": 2418,
        "isbn13": "9780735211292",
        "sku": "BK-884920",
        "pages": 320,
        "publisher": "Penguin",
        "language": "English",
        "dimensions": "6 x 9 in",
        "published_on": "2018-10-16",
        "badges": ["bestseller", "staff_favorite"],
        "default_format": "paperback",
        "featured_rank": 1,
        "curator_quote": "We consider this foundational modern canon. Clear replaces dogmatic willpower with environmental design and a kinder daily practice.",
        "curator_name": "Elena Chen",
        "curator_role": "Senior Bookbuyer, Reader San Francisco",
        "formats": [
            ("hardcover", "Hardcover", "Embossed Spine", "24.00", None, False),
            ("paperback", "Paperback", "Cream Laid Sheet", "16.99", "24.00", False),
            ("ebook", "eBook", "EPUB + Kindle", "11.99", None, False),
            ("signed", "Signed Edition", "Numbered Plate", "38.00", None, True),
        ],
        "toc": [
            ("The Fundamentals: How Your Habits Shape You", 1),
            ("The 1st Law: Make It Obvious", 45),
            ("The 2nd Law: Make It Attractive", 91),
            ("The 3rd Law: Make It Easy", 143),
            ("The 4th Law: Make It Satisfying", 185),
            ("Advanced Tactics: Going from Good to Great", 235),
        ],
    },
    {
        "id": "b0e0c226-52de-4aa1-b190-7cf226c220a2",
        "slug": "educated",
        "title": "Educated",
        "subtitle": "A Memoir",
        "description": "A memoir of leaving a survivalist family and finding a new life through learning.",
        "about": "Tara Westover recounts a childhood without school in the Idaho mountains and the university education that followed. It is a story about family loyalty and the cost of leaving.",
        "author": "tara-westover",
        "genre": "memoir",
        "rating": "4.8",
        "review_count": 940,
        "isbn13": "9780399590504",
        "sku": "BK-220184",
        "pages": 334,
        "publisher": "Random House",
        "language": "English",
        "dimensions": "6.2 x 9.2 in",
        "published_on": "2018-02-20",
        "badges": ["staff_favorite"],
        "default_format": "paperback",
        "featured_rank": 2,
        "formats": [
            ("paperback", "Paperback", "French flaps", "15.99", None, False),
            ("hardcover", "Hardcover", "Clothbound", "22.00", None, False),
            ("ebook", "eBook", "EPUB", "12.99", None, False),
        ],
        "toc": [],
    },
    {
        "id": "1250f7e4-0708-4676-8057-89df5e17f928",
        "slug": "klara-and-the-sun",
        "title": "Klara and the Sun",
        "subtitle": None,
        "description": "An Artificial Friend watches the world with wonder — and a quiet devotion to the sun.",
        "about": "Klara is an Artificial Friend who studies the people who might take her home. Ishiguro uses her careful attention to ask what devotion looks like when it is built, not born.",
        "author": "kazuo-ishiguro",
        "genre": "fiction",
        "rating": "4.7",
        "review_count": 810,
        "isbn13": "9780593318171",
        "sku": "BK-331817",
        "pages": 303,
        "publisher": "Knopf",
        "language": "English",
        "dimensions": "6.3 x 9.5 in",
        "published_on": "2021-03-02",
        "badges": [],
        "default_format": "hardcover",
        "featured_rank": 3,
        "formats": [
            ("hardcover", "Hardcover", "First printing", "17.99", None, False),
            ("paperback", "Paperback", "Trade paperback", "16.00", None, False),
            ("ebook", "eBook", "EPUB", "11.99", None, False),
        ],
        "toc": [],
    },
    {
        "id": "5f0cc17e-043c-46ea-a969-452431857e7d",
        "slug": "project-hail-mary",
        "title": "Project Hail Mary",
        "subtitle": None,
        "description": "A lone astronaut wakes on a spaceship with no memory — and a mission to save Earth.",
        "about": "Ryland Grace wakes light-years from home with a dead crew and a problem in the stars. Weir builds the novel out of experiments, friendship, and the next solvable step.",
        "author": "andy-weir",
        "genre": "thriller",
        "rating": "4.9",
        "review_count": 2400,
        "isbn13": "9780593135204",
        "sku": "BK-313520",
        "pages": 496,
        "publisher": "Ballantine",
        "language": "English",
        "dimensions": "6.3 x 9.5 in",
        "published_on": "2021-05-04",
        "badges": ["bestseller"],
        "default_format": "paperback",
        "featured_rank": 4,
        "formats": [
            ("paperback", "Paperback", "Trade paperback", "19.99", None, False),
            ("hardcover", "Hardcover", "Clothbound with foil", "24.00", None, False),
            ("ebook", "eBook", "EPUB", "13.99", None, False),
        ],
        "toc": [],
    },
    {
        "id": "6f1c2a40-7b51-4c0e-9d3a-1a2b3c4d5e6f",
        "slug": "thinking-fast-and-slow",
        "title": "Thinking, Fast and Slow",
        "subtitle": None,
        "description": "A tour of the quick judgments and slow reasoning that shape everyday decisions.",
        "about": "Kahneman introduces two systems of thought and the biases that follow when the quick one answers first. It is a field guide for readers who want to notice their own shortcuts.",
        "author": "daniel-kahneman",
        "genre": "nonfiction",
        "rating": "4.6",
        "review_count": 3200,
        "isbn13": "9780374533557",
        "sku": "BK-453355",
        "pages": 499,
        "publisher": "Farrar, Straus and Giroux",
        "language": "English",
        "dimensions": "6.1 x 9.2 in",
        "published_on": "2011-10-25",
        "badges": [],
        "default_format": "paperback",
        "featured_rank": 5,
        "formats": [
            ("paperback", "Paperback", "Trade paperback", "19.99", None, False),
            ("hardcover", "Hardcover", "Cloth", "28.00", None, False),
        ],
        "toc": [],
    },
    {
        "id": "8e2d3b51-8c62-4d1f-ae4b-2b3c4d5e6f70",
        "slug": "circe",
        "title": "Circe",
        "subtitle": None,
        "description": "The witch of Aiaia chooses a life of her own in this retelling of the Odyssey's island.",
        "about": "Miller gives Circe the centuries the myths usually skip. The novel follows her from a slighted nymph in her father's halls to the island where she learns her craft.",
        "author": "madeline-miller",
        "genre": "fiction",
        "rating": "4.8",
        "review_count": 1500,
        "isbn13": "9780316556347",
        "sku": "BK-655634",
        "pages": 393,
        "publisher": "Little, Brown",
        "language": "English",
        "dimensions": "5.5 x 8.2 in",
        "published_on": "2018-04-10",
        "badges": ["staff_favorite"],
        "default_format": "paperback",
        "featured_rank": 6,
        "formats": [
            ("paperback", "Paperback", "Trade paperback", "16.50", None, False),
            ("hardcover", "Hardcover", "Clothbound", "21.00", None, False),
        ],
        "toc": [],
    },
    {
        "id": "9f3e4c62-9d73-4e20-bf5c-3c4d5e6f7081",
        "slug": "the-midnight-library",
        "title": "The Midnight Library",
        "subtitle": None,
        "description": "Between life and death, a library of other lives waits to be tried on.",
        "about": "Nora Seed arrives at a library where each book is a life she might have lived. Haig uses the premise to ask what regret is worth once you can walk around inside it.",
        "author": "matt-haig",
        "genre": "fiction",
        "rating": "4.3",
        "review_count": 2100,
        "isbn13": "9780525559474",
        "sku": "BK-555947",
        "pages": 304,
        "publisher": "Viking",
        "language": "English",
        "dimensions": "5.5 x 8.2 in",
        "published_on": "2020-08-13",
        "badges": [],
        "default_format": "paperback",
        "featured_rank": 7,
        "formats": [
            ("paperback", "Paperback", "Trade paperback", "14.99", None, False),
            ("hardcover", "Hardcover", "Cloth", "18.00", None, False),
            ("ebook", "eBook", "EPUB", "9.99", None, False),
        ],
        "toc": [],
    },
    {
        "id": "a04f5d73-ae84-4f31-806d-4d5e6f708192",
        "slug": "braiding-sweetgrass",
        "title": "Braiding Sweetgrass",
        "subtitle": "Indigenous Wisdom, Scientific Knowledge, and the Teachings of Plants",
        "description": "Essays on reciprocity, from sweetgrass and maple to the work of paying attention.",
        "about": "Kimmerer writes as both a botanist and a Potawatomi teacher. The essays ask what it means to take a gift from the living world and give something back.",
        "author": "robin-wall-kimmerer",
        "genre": "essays",
        "rating": "4.9",
        "review_count": 1800,
        "isbn13": "9781571313560",
        "sku": "BK-131356",
        "pages": 408,
        "publisher": "Milkweed Editions",
        "language": "English",
        "dimensions": "6 x 9 in",
        "published_on": "2013-10-15",
        "badges": ["staff_favorite"],
        "default_format": "paperback",
        "featured_rank": 8,
        "formats": [
            ("paperback", "Paperback", "Trade paperback", "18.00", None, False),
            ("hardcover", "Hardcover", "Cloth", "22.00", None, False),
        ],
        "toc": [],
    },
]


def aware(year, month, day, hour=12, minute=0):
    return datetime(year, month, day, hour, minute, tzinfo=dt_timezone.utc)


class Command(BaseCommand):
    help = "Load Reader sample catalog, Elena's account, and her orders."

    def handle(self, *args, **options):
        genres = {slug: Genre.objects.update_or_create(slug=slug, defaults={"name": name})[0] for slug, name in GENRES}
        authors = {}
        for slug, (name, bio) in AUTHORS.items():
            authors[slug], _ = Author.objects.update_or_create(slug=slug, defaults={"name": name, "bio": bio})

        books = {}
        for raw in BOOKS:
            default = next(row for row in raw["formats"] if row[0] == raw["default_format"])
            book, _ = Book.objects.update_or_create(
                id=raw["id"],
                defaults={
                    "slug": raw["slug"],
                    "title": raw["title"],
                    "subtitle": raw["subtitle"] or "",
                    "description": raw["description"],
                    "about": raw["about"],
                    "author": authors[raw["author"]],
                    "genre": genres[raw["genre"]],
                    "rating": Decimal(raw["rating"]),
                    "review_count": raw["review_count"],
                    "cover_url": cover(raw["isbn13"]),
                    "sku": raw["sku"],
                    "in_stock": True,
                    "pages": raw["pages"],
                    "publisher": raw["publisher"],
                    "language": raw["language"],
                    "isbn13": raw["isbn13"],
                    "dimensions": raw["dimensions"],
                    "published_on": date.fromisoformat(raw["published_on"]),
                    "badges": raw["badges"],
                    "default_format": raw["default_format"],
                    "price": Decimal(default[3]),
                    "compare_at_price": Decimal(default[4]) if default[4] else None,
                    "featured_rank": raw["featured_rank"],
                    "curator_quote": raw.get("curator_quote", ""),
                    "curator_name": raw.get("curator_name", ""),
                    "curator_role": raw.get("curator_role", ""),
                },
            )
            book.formats.all().delete()
            book.images.all().delete()
            book.contents.all().delete()
            book.related_links.all().delete()
            for position, (code, label, detail, price, compare, rare) in enumerate(raw["formats"]):
                BookFormat.objects.create(
                    book=book,
                    code=code,
                    label=label,
                    detail=detail,
                    price=Decimal(price),
                    compare_at_price=Decimal(compare) if compare else None,
                    in_stock=True,
                    rare=rare,
                    position=position,
                )
            BookImage.objects.create(book=book, label="Front", url=book.cover_url, position=0)
            for position, (title, page) in enumerate(raw["toc"]):
                TocEntry.objects.create(book=book, title=title, page=page, position=position)
            books[raw["slug"]] = book

        for position, slug in enumerate(["educated", "project-hail-mary", "klara-and-the-sun", "thinking-fast-and-slow"]):
            RelatedBook.objects.create(book=books["atomic-habits"], related=books[slug], position=position)

        self._collections(books)
        self._reviews(books)
        user = self._user()
        self._shelves(user, books)
        self._commerce(user, books)
        self._faqs()
        self.stdout.write(self.style.SUCCESS(f"Seeded {EMAIL} / {PASSWORD}"))

    def _collections(self, books):
        specs = [
            ("bestsellers", "Bestsellers", "Titles our readers keep reordering.", ["atomic-habits", "project-hail-mary", "educated"]),
            (
                "staff-favorites",
                "Staff Favorites",
                "Books the buyers keep on their own desks.",
                ["atomic-habits", "klara-and-the-sun", "braiding-sweetgrass"],
            ),
        ]
        for slug, name, description, members in specs:
            collection, _ = Collection.objects.update_or_create(
                slug=slug, defaults={"name": name, "description": description}
            )
            CollectionBook.objects.filter(collection=collection).delete()
            for position, member in enumerate(members):
                CollectionBook.objects.create(collection=collection, book=books[member], position=position)

    def _reviews(self, books):
        rows = [
            (
                "atomic-habits",
                "Marcus Hale",
                "Architectural Director",
                5,
                "A practical companion. Clear writes with clarity and discipline, and the cloth binding on this edition is worth keeping out.",
                "Hardcover",
                aware(2024, 9, 12),
            ),
            (
                "atomic-habits",
                "Sarah Jenkins",
                "Reader",
                5,
                "The chapter on two-minute rules unlocked a reading habit I had been postponing for years.",
                "Paperback",
                aware(2024, 9, 1),
            ),
            (
                "atomic-habits",
                "David S. Lind",
                "Verified reader",
                4,
                "Uncluttered, science-backed guidance. I pull it down twice a year and start again.",
                "Paperback",
                aware(2024, 8, 2),
            ),
        ]
        for slug, name, title, rating, body, edition, created in rows:
            Review.objects.update_or_create(
                book=books[slug],
                reviewer_name=name,
                defaults={
                    "reviewer_title": title,
                    "rating": rating,
                    "body": body,
                    "edition": edition,
                    "verified_purchase": True,
                    "created_at": created,
                    "user": None,
                },
            )

    def _user(self):
        user = User.objects.filter(email=EMAIL).first()
        if user is None:
            user = User(
                id=uuid.uuid5(uuid.UUID("15422850-2694-4085-8467-250000000001"), "user:elena"),
                email=EMAIL,
                patron_number="4802",
                member_since=date(2023, 10, 1),
            )
        user.name = "Elena Rostova"
        user.phone = "+14155550198"
        user.member_since = date(2023, 10, 1)
        user.patron_number = "4802"
        user.loyalty_points = 480
        user.marketing_opt_in = True
        user.set_password(PASSWORD)
        user.save()
        address, _ = Address.objects.get_or_create(
            user=user,
            street="18 Clement Street",
            defaults={
                "full_name": "Elena Rostova",
                "line2": "",
                "city": "San Francisco",
                "state": "CA",
                "postal_code": "94118",
                "phone": "+14155550198",
                "is_default": True,
            },
        )
        user.addresses.exclude(pk=address.pk).update(is_default=False)
        address.is_default = True
        address.full_name = "Elena Rostova"
        address.city = "San Francisco"
        address.state = "CA"
        address.postal_code = "94118"
        address.phone = "+14155550198"
        address.save()
        payment, _ = PaymentMethod.objects.get_or_create(
            user=user,
            method=PaymentMethod.CARD,
            last4="4242",
            defaults={"brand": "visa", "exp_month": 12, "exp_year": 2028, "is_default": True},
        )
        user.payment_methods.exclude(pk=payment.pk).update(is_default=False)
        payment.brand = "visa"
        payment.exp_month = 12
        payment.exp_year = 2028
        payment.is_default = True
        payment.save()
        Voucher.objects.update_or_create(
            code="GUILD24",
            defaults={"amount": Decimal("24.00"), "user": user, "used": False},
        )
        return user

    def _shelves(self, user, books):
        specs = [
            ("Saved", True, ["educated", "circe"]),
            ("Bedside", False, ["atomic-habits"]),
            ("Finished", False, ["klara-and-the-sun", "project-hail-mary"]),
            ("Gifts", False, ["the-midnight-library"]),
        ]
        for name, is_default, slugs in specs:
            shelf, _ = Shelf.objects.get_or_create(user=user, name=name, defaults={"is_default": is_default})
            shelf.is_default = is_default
            shelf.save(update_fields=["is_default"])
            for slug in slugs:
                shelf.books.add(books[slug])

    def _commerce(self, user, books):
        address = {
            "full_name": "Elena Rostova",
            "street": "18 Clement Street",
            "line2": "",
            "city": "San Francisco",
            "state": "CA",
            "postal_code": "94118",
            "phone": "+14155550198",
        }
        payment = {"method": "card", "brand": "visa", "last4": "4242", "exp_month": 12, "exp_year": 2028}
        if not Order.objects.filter(number="RD-89410").exists():
            create_order(
                user=user,
                email=EMAIL,
                shipping_method="express",
                address=address,
                payment=payment,
                lines=[
                    self._line(books["atomic-habits"], "paperback", Decimal("16.99"), 1),
                    self._line(books["klara-and-the-sun"], "hardcover", Decimal("17.99"), 1),
                ],
                subtotal=Decimal("34.98"),
                discount=Decimal("0.00"),
                shipping=Decimal("0.00"),
                tax=Decimal("0.00"),
                total=Decimal("34.98"),
                status=Order.SHIPPED,
                placed_at=aware(2024, 10, 24, 9, 12),
                estimated_delivery=date(2024, 10, 27),
                number="RD-89410",
                carrier="Reader Shelf Post Express",
                tracking_number="RSP-9920-8441-NY",
                events=[
                    {
                        "code": "confirmed",
                        "label": "Confirmed",
                        "location": "Reader Bookshelf Warehouse",
                        "occurred_at": aware(2024, 10, 24, 9, 12),
                        "state": "completed",
                        "position": 0,
                    },
                    {
                        "code": "packed",
                        "label": "Curated & Bound",
                        "location": "San Francisco, CA",
                        "occurred_at": aware(2024, 10, 24, 15, 40),
                        "state": "completed",
                        "position": 1,
                    },
                    {
                        "code": "shipped",
                        "label": "Shipped",
                        "location": "Oakland, CA Distribution Hub",
                        "occurred_at": aware(2024, 10, 25, 8, 30),
                        "state": "current",
                        "position": 2,
                    },
                    {
                        "code": "out_for_delivery",
                        "label": "Out for Delivery",
                        "location": "",
                        "occurred_at": None,
                        "state": "upcoming",
                        "position": 3,
                    },
                    {
                        "code": "delivered",
                        "label": "Delivered",
                        "location": "",
                        "occurred_at": None,
                        "state": "upcoming",
                        "position": 4,
                    },
                ],
            )
        self._past_order(
            user,
            books,
            number="RD-76201",
            slug="educated",
            code="paperback",
            price="15.99",
            placed=aware(2024, 9, 11, 11, 0),
            delivered=date(2024, 9, 14),
            address=address,
            payment=payment,
        )
        self._past_order(
            user,
            books,
            number="RD-61094",
            slug="project-hail-mary",
            code="hardcover",
            price="19.99",
            placed=aware(2024, 6, 28, 15, 0),
            delivered=date(2024, 7, 2),
            address=address,
            payment=payment,
        )
        self._past_order(
            user,
            books,
            number="RD-44120",
            slug="the-midnight-library",
            code="paperback",
            price="14.99",
            placed=aware(2024, 4, 28, 16, 0),
            delivered=date(2024, 5, 2),
            address=address,
            payment=payment,
        )
        cart, _ = Cart.objects.get_or_create(user=user)
        cart.voucher = None
        cart.save(update_fields=["voucher"])
        cart.items.all().delete()
        add_line(cart, books["atomic-habits"], edition_for(books["atomic-habits"], "paperback"), 1)
        add_line(cart, books["project-hail-mary"], edition_for(books["project-hail-mary"], "paperback"), 1)

    def _past_order(self, user, books, *, number, slug, code, price, placed, delivered, address, payment):
        if Order.objects.filter(number=number).exists():
            return
        amount = Decimal(price)
        create_order(
            user=user,
            email=EMAIL,
            shipping_method="standard",
            address=address,
            payment=payment,
            lines=[self._line(books[slug], code, amount, 1)],
            subtotal=amount,
            discount=Decimal("0.00"),
            shipping=Decimal("0.00"),
            tax=Decimal("0.00"),
            total=amount,
            status=Order.DELIVERED,
            placed_at=placed,
            estimated_delivery=delivered,
            number=number,
        )

    def _line(self, book, code, price, quantity):
        edition = book.formats.get(code=code)
        return {
            "book": book,
            "title": book.title,
            "author_name": book.author.name,
            "cover_url": book.cover_url,
            "format": code,
            "format_label": edition.label,
            "quantity": quantity,
            "unit_price": price,
        }

    def _faqs(self):
        rows = [
            (
                "shipping",
                "When does standard shipping become free?",
                "Standard Ground is free when the merchandise total after discounts is $35 or more. Under that, it is $5.99. Priority Express is $4.99. Call 1 (800) 555-READ, Monday through Saturday, 9am–7pm EST.",
            ),
            (
                "returns",
                "How do 30-day returns work?",
                "Unread books can come back within 30 days. Write to support with your order number and we will send a label. Hand-stamped bookplates can stay with you.",
            ),
            (
                "packaging",
                "How are books packed?",
                "Each copy is hand-wrapped in recyclable paper with an archival cloth bookmark. We do not use plastic mailers.",
            ),
            (
                "orders",
                "Where is my parcel?",
                "Open the order and read the carrier timeline. Active shipments include a tracking number. If a book arrives damaged, contact Reader support with the order number.",
            ),
        ]
        for position, (topic, question, answer) in enumerate(rows):
            Faq.objects.update_or_create(
                question=question,
                defaults={"topic": topic, "answer": answer, "position": position},
            )
