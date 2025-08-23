import stripe
from django.conf import settings

stripe.api_key = settings.STRIPE_SECRET_KEY

def create_product(name: str):
    # https://stripe.com/docs/api/products/create
    return stripe.Product.create(name=name)

def create_price(product_id: str, amount_cents: int, currency: str):
    # https://stripe.com/docs/api/prices/create
    return stripe.Price.create(
        product=product_id,
        unit_amount=amount_cents,
        currency=currency,
    )

def create_checkout_session(price_id: str, success_url: str, cancel_url: str, customer_email: str | None = None):
    # https://stripe.com/docs/api/checkout/sessions/create
    return stripe.checkout.Session.create(
        mode="payment",
        payment_method_types=["card"],
        line_items=[{"price": price_id, "quantity": 1}],
        success_url=f"{success_url}?session_id={{CHECKOUT_SESSION_ID}}",
        cancel_url=cancel_url,
        customer_email=customer_email,
    )
