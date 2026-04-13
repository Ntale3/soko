from dataclasses import dataclass
from typing import Optional


@dataclass
class NotificationTemplate:
    title:       str
    body:        str
    entity_type: Optional[str] = None


def get_template(event: str, meta: dict = {}) -> dict:
    """
    Returns { title, body, entity_type } for a given event.
    meta dict carries dynamic values like order_id, name etc.
    """
    order_ref  = meta.get("order_ref",  "your order")
    actor_name = meta.get("actor_name", "Someone")
    product    = meta.get("product",    "your product")

    templates = {

        # ── Buyer notifications
        "order_placed": {
            "buyer": NotificationTemplate(
                title="Order placed!",
                body=f"Your order {order_ref} has been placed. Waiting for payment confirmation.",
                entity_type="order",
            ),
            "farmer": NotificationTemplate(
                title="New order received",
                body=f"You have a new order {order_ref} for {product}.",
                entity_type="order",
            ),
        },

        "payment_confirmed": {
            "buyer": NotificationTemplate(
                title="Payment confirmed",
                body=f"Payment for order {order_ref} was successful. Your farmer will prepare your order.",
                entity_type="order",
            ),
            "farmer": NotificationTemplate(
                title="Payment received",
                body=f"Payment confirmed for order {order_ref}. Please prepare the order.",
                entity_type="order",
            ),
        },

        "payment_failed": {
            "buyer": NotificationTemplate(
                title="Payment failed",
                body=f"Payment for order {order_ref} did not go through. Please try again.",
                entity_type="order",
            ),
        },

        "order_dispatched": {
            "buyer": NotificationTemplate(
                title="Order on the way!",
                body=f"Your order {order_ref} has been dispatched and is on its way to you.",
                entity_type="order",
            ),
        },

        "order_delivered": {
            "buyer": NotificationTemplate(
                title="Order delivered",
                body=f"Your order {order_ref} has been delivered. Enjoy your fresh produce!",
                entity_type="order",
            ),
        },

        "order_cancelled": {
            "buyer": NotificationTemplate(
                title="Order cancelled",
                body=f"Your order {order_ref} has been cancelled.",
                entity_type="order",
            ),
            "farmer": NotificationTemplate(
                title="Order cancelled",
                body=f"Order {order_ref} for {product} was cancelled by the buyer.",
                entity_type="order",
            ),
        },

        "new_message": {
            "recipient": NotificationTemplate(
                title=f"New message from {actor_name}",
                body="You have a new message. Tap to read.",
                entity_type="message",
            ),
        },

        "new_review": {
            "farmer": NotificationTemplate(
                title="New review on your listing",
                body=f"{actor_name} left a review on {product}.",
                entity_type="listing",
            ),
        },

        "new_follower": {
            "farmer": NotificationTemplate(
                title="New follower",
                body=f"{actor_name} started following your farm.",
                entity_type="profile",
            ),
        },
    }

    return templates.get(event, {})