import logging
import httpx
from app.core.config import settings

logger = logging.getLogger(__name__)


async def handle_orders(
    state:         str,
    user_input:    str,
    session_data:  dict,
    platform_id:   str,
) -> tuple[str, str, dict]:
    """Returns (response_text, next_state, updated_session_data)."""

    if state == "orders_list":
        try:
            async with httpx.AsyncClient() as client:
                res = await client.get(
                    f"{settings.ORDER_SERVICE_URL}/orders/me",
                    headers={
                        "x-internal-secret": settings.INTERNAL_SECRET,
                        "x-user-id":         platform_id,
                        "x-user-role":       "buyer",
                    },
                    params={"limit": 5},
                    timeout=5.0
                )
                orders = res.json()

            if not orders:
                return (
                    "END No orders found.\nDial *384*1# for menu.",
                    "main_menu", {}
                )

            lines = "\n".join(
                f"{i+1}. #{o['id'][:6].upper()} - {o['status'].capitalize()}"
                for i, o in enumerate(orders[:5])
            )
            session_data["orders"] = [
                {"id": o["id"], "status": o["status"],
                 "total": o["total"], "itemCount": o["itemCount"],
                 "createdAt": o["createdAt"]}
                for o in orders[:5]
            ]
            return (
                f"CON Your orders:\n{lines}\n0. Back",
                "orders_detail", session_data
            )

        except Exception as e:
            logger.error(f"Orders fetch failed: {e}")
            return (
                "END Could not fetch orders.\nTry again later.\nDial *384*1#",
                "main_menu", {}
            )

    if state == "orders_detail":
        if user_input == "0":
            return (
                "CON Welcome to Soko!\n1. Crop Prices\n2. My Orders\n3. Register\n0. Exit",
                "main_menu", {}
            )

        orders = session_data.get("orders", [])
        if not user_input.isdigit() or int(user_input) < 1 or int(user_input) > len(orders):
            return "CON Invalid choice.\n0. Back", "orders_list", session_data

        o = orders[int(user_input) - 1]
        return (
            f"END Order #{o['id'][:6].upper()}\n"
            f"Status: {o['status'].capitalize()}\n"
            f"Total: {int(o['total']):,} UGX\n"
            f"Items: {o['itemCount']}\n"
            f"Date: {o['createdAt'][:10]}\n"
            f"Dial *384*1# for more.",
            "main_menu", {}
        )

    return "END Invalid state.\nDial *384*1#", "main_menu", {}