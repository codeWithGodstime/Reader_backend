# Reader API

Shared contract for the Reader bookstore mobile app and web app. The machine-readable source of truth is [`openapi.yaml`](openapi.yaml).

**Base URL:** `http://127.0.0.1:8001` (local `PORT`, default `8001`)

Interactive docs (when the server is running): `http://127.0.0.1:8001/api/docs/`

## What this API covers

Reader is an independent bookshop. A reader browses a curated catalog, opens a title, picks an edition, saves it to a shelf, adds it to a bag, checks out with a delivery address, and tracks the parcel.

## Auth

Header on protected routes:

```
Authorization: Bearer <access_token>
```

| | |
| --- | --- |
| Access token | JWT, 60 minutes |
| Refresh token | JWT, 7 days, rotated on refresh |
| Scheme | Email + password, or Google ID token |
| Google client IDs | `GOOGLE_OAUTH_CLIENT_IDS` (comma-separated, no client secret) |

`POST /api/v1/auth/register` and `POST /api/v1/auth/login` return `{ access, refresh, user }`. Send `refresh` to `POST /api/v1/auth/refresh`. Send it to `POST /api/v1/auth/logout` to revoke it.

`POST /api/v1/auth/google` with `{ "id_token": "<Google ID token JWT>" }` verifies the token on the server and returns the same `{ access, refresh, user }` shape. `401` if the token is missing, expired, for the wrong audience, or the Google email is not verified. An existing email is signed in and the Google `sub` is stored. A new email creates an account with no password.

Catalog reads are public. `saved` on a book is `false` until a token is sent. Cart, checkout, orders, shelves, addresses, payment methods, and profile require a token.

Payments are simulated. Never send a full card number or CVC. Card checkout sends `brand`, `last4`, `exp_month`, and `exp_year` for the receipt only.

## Conventions

- IDs are UUID strings.
- Money is a two-decimal string in USD, for example `"16.99"`.
- Timestamps are ISO-8601 UTC. Dates are `YYYY-MM-DD`.
- Lists use `{ count, page, page_size, next, previous, results }`. `page` starts at 1. Default `page_size` is 12 (max 50). Shop screens use `page_size=4`.
- Errors:

```json
{
  "error": {
    "code": "validation_error",
    "message": "Invalid request.",
    "details": [{ "field": "email", "message": "Enter a valid email address." }]
  }
}
```

`details` is omitted when the error is not field-specific. Status codes: 400 validation, 401 auth, 403 permission, 404 missing, 409 conflict (empty cart, out of stock, duplicate review, checkout not ready).

Tax is 8% of (subtotal − discount), rounded half up to cents. Standard shipping is `"0.00"` when that merchandise amount is at least `"35.00"`, otherwise `"5.99"`. Express is always `"4.99"`.

## Resources

| Resource | Notes |
| --- | --- |
| Profile | Name, patron number, loyalty points, unused voucher |
| Genre | Chip plus live book count |
| Book | Card summary and detail (editions, specs, gallery, contents, curator note) |
| Review | Verified-reader reviews on a book |
| Collection | Editorial shelves such as Bestsellers |
| Shelf | Reader-owned lists. Bookmark uses the default shelf named Saved |
| Cart | One cart per reader. Totals include standard shipping |
| Order | Placed checkout, tracking timeline, invoice, buy again |
| Address | Saved delivery addresses |
| Payment method | Display-only card, PayPal, or Google Pay record |
| Newsletter | The Literary Dispatch |
| Support | FAQs and a contact message |

## Endpoints

| Method | Path | Auth |
| --- | --- | --- |
| GET | `/api/v1/health` | no |
| POST | `/api/v1/auth/register` | no |
| POST | `/api/v1/auth/login` | no |
| POST | `/api/v1/auth/google` | no |
| POST | `/api/v1/auth/refresh` | no |
| POST | `/api/v1/auth/logout` | yes |
| GET, PATCH | `/api/v1/me` | yes |
| GET | `/api/v1/genres` | no |
| GET | `/api/v1/books` | no |
| GET | `/api/v1/books/{book_id}` | no |
| GET | `/api/v1/books/{book_id}/related` | no |
| GET, POST | `/api/v1/books/{book_id}/reviews` | GET no, POST yes |
| POST, DELETE | `/api/v1/books/{book_id}/save` | yes |
| GET | `/api/v1/collections` | no |
| GET | `/api/v1/collections/{slug}` | no |
| GET, POST | `/api/v1/shelves` | yes |
| GET, PATCH, DELETE | `/api/v1/shelves/{shelf_id}` | yes |
| POST | `/api/v1/shelves/{shelf_id}/books` | yes |
| DELETE | `/api/v1/shelves/{shelf_id}/books/{book_id}` | yes |
| GET | `/api/v1/cart` | yes |
| POST | `/api/v1/cart/items` | yes |
| PATCH, DELETE | `/api/v1/cart/items/{item_id}` | yes |
| POST, DELETE | `/api/v1/cart/voucher` | yes |
| GET | `/api/v1/shipping-methods` | no |
| POST | `/api/v1/checkout` | yes |
| POST | `/api/v1/checkout/one-click` | yes |
| GET | `/api/v1/orders` | yes |
| GET, PATCH | `/api/v1/orders/{order_id}` | yes |
| GET | `/api/v1/orders/{order_id}/tracking` | yes |
| GET | `/api/v1/orders/{order_id}/invoice` | yes |
| POST | `/api/v1/orders/{order_id}/buy-again` | yes |
| GET, POST | `/api/v1/addresses` | yes |
| PATCH, DELETE | `/api/v1/addresses/{address_id}` | yes |
| GET, POST | `/api/v1/payment-methods` | yes |
| DELETE | `/api/v1/payment-methods/{payment_method_id}` | yes |
| POST | `/api/v1/newsletter/subscriptions` | no |
| GET | `/api/v1/support/faqs` | no |
| POST | `/api/v1/support/messages` | no |

### Catalog query

`GET /api/v1/books?q=&genre=&price=&format=&in_stock=&sort=&page=&page_size=`

- `price`: `any` (default), `under_16`, `from_16_to_18`, `over_18` — compared to the default edition price
- `format`: `paperback`, `hardcover`, `ebook`, `signed`
- `sort`: `featured` (default), `title`, `price_asc`, `price_desc`, `newest`, `rating`
- `genre`: slug such as `fiction`, `memoir`, `nonfiction`, `thriller`

### Orders query

`GET /api/v1/orders?status=all|active|past&q=`

`active` means not delivered and not cancelled. `past` means delivered or cancelled. `q` matches the order number or a title in the parcel.

## Main flows

### Register

```http
POST /api/v1/auth/register
Content-Type: application/json

{
  "name": "Elena Rostova",
  "email": "elena@example.com",
  "password": "a-long-secret"
}
```

```json
{
  "access": "<jwt>",
  "refresh": "<jwt>",
  "user": {
    "id": "7c9e6679-7425-40de-944b-e07fc1f90ae7",
    "name": "Elena Rostova",
    "email": "elena@example.com",
    "phone": null,
    "member_since": "2026-10-03",
    "patron_number": "4802",
    "loyalty_points": 0,
    "voucher": null,
    "marketing_opt_in": false,
    "active_order_count": 0,
    "shelf_count": 0,
    "saved_book_count": 0
  }
}
```

### Catalog card

`GET /api/v1/books?genre=nonfiction&price=from_16_to_18&sort=featured&page=1&page_size=4`

Each result includes `id`, `title`, `author_name`, `genre`, `rating`, `review_count`, `price`, `compare_at_price`, `format`, `cover_url`, `badges`, `in_stock`, and `saved`.

Book detail (`GET /api/v1/books/{book_id}`) adds `about`, `author`, `sku`, `pages`, `publisher`, `language`, `isbn13`, `dimensions`, `published_on`, `formats[]`, `gallery[]`, `table_of_contents[]`, and `curator_note`. Cards also include `format_label` (for example `Paperback`).

Edition `formats[].code` is `paperback`, `hardcover`, `ebook`, or `signed`.

### Save and add to cart

```http
POST /api/v1/books/{book_id}/save
Authorization: Bearer <access_token>
```

```http
POST /api/v1/cart/items
Authorization: Bearer <access_token>
Content-Type: application/json

{ "book_id": "3c52c712-092d-46c1-8c71-1bcc451f1f7c", "format": "paperback", "quantity": 1 }
```

The cart response includes `items`, `item_count`, `subtotal`, `discount`, `shipping`, `tax`, `total`, `voucher`, and `amount_until_free_shipping`. Sending the same book and format again increases quantity. `PATCH` with `"quantity": 0` removes the line.

Apply the seeded voucher:

```http
POST /api/v1/cart/voucher
Authorization: Bearer <access_token>
Content-Type: application/json

{ "code": "GUILD24" }
```

### Checkout

```http
POST /api/v1/checkout
Authorization: Bearer <access_token>
Content-Type: application/json

{
  "email": "elena.rostova@reader.example",
  "marketing_opt_in": true,
  "shipping_method": "standard",
  "address": {
    "full_name": "Elena Rostova",
    "street": "18 Clement Street",
    "line2": null,
    "city": "San Francisco",
    "state": "CA",
    "postal_code": "94118",
    "phone": "+14155550198",
    "save": true
  },
  "payment": {
    "method": "card",
    "brand": "visa",
    "last4": "4242",
    "exp_month": 12,
    "exp_year": 2028,
    "save": true
  }
}
```

`201` returns the order: `id`, `number` (for example `RD-89410`), `status` (`confirmed`), totals, snapshotted `items`, `address`, `payment`, and tracking fields.

One-click buy uses the saved default address and payment method and does not change the cart:

```http
POST /api/v1/checkout/one-click
Authorization: Bearer <access_token>
Content-Type: application/json

{ "book_id": "3c52c712-092d-46c1-8c71-1bcc451f1f7c", "format": "paperback", "quantity": 1 }
```

`409` with code `checkout_not_ready` when no default address or payment method exists.

### Orders

`GET /api/v1/orders?status=active` and `GET /api/v1/orders?status=past`.

`GET /api/v1/orders/{order_id}/tracking` returns `carrier`, `tracking_number`, `estimated_delivery`, and `events[]` with `state` of `completed`, `current`, or `upcoming`.

`GET /api/v1/orders/{order_id}/invoice` is the receipt JSON.

`PATCH /api/v1/orders/{order_id}` accepts `{ "delivery_instructions": "Leave with the doorman." }` until the order is delivered or cancelled.

`POST /api/v1/orders/{order_id}/buy-again` copies lines into the cart and returns the cart.

### Review

```http
POST /api/v1/books/{book_id}/reviews
Authorization: Bearer <access_token>
Content-Type: application/json

{ "rating": 5, "body": "The two-minute rule stuck.", "edition": "Paperback" }
```

A second review by the same reader returns `409`.

## Seeded reader

After `python manage.py seed_reader`:

| | |
| --- | --- |
| Email | `elena.rostova@reader.example` |
| Password | `shelf-reader-4802` |
| Voucher | `GUILD24` (`24.00` off, once) |
| Admin email | `admin@reader.example` |
| Admin password | `shelf-admin-4802` |

Catalog includes Atomic Habits (`3c52c712-092d-46c1-8c71-1bcc451f1f7c`), Educated, Klara and the Sun, and Project Hail Mary, plus four more titles so page 2 of the shop is populated.
