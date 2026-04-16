```py
async with httpx.AsyncClient() as client:
    await client.post(
        f"{settings.NOTIFICATION_SERVICE_URL}/internal/notify",
        json={
            "event":      "order_placed",
            "order_id":   str(order.id),
            "buyer_id":   str(order.buyer_id),
            "farmer_id":  str(farmer_id),
            "meta": {
                "product": first_item_name,
            }
        },
        headers={"x-internal-secret": settings.INTERNAL_SECRET},
        timeout=5.0
    )


```