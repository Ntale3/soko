import logging
import httpx
from app.core.config import settings

logger = logging.getLogger(__name__)

DISTRICTS = [
    "Kampala", "Wakiso", "Mukono", "Mbarara",
    "Gulu", "Lira", "Jinja", "Mbale"
]

CATEGORIES = [
    "Grains", "Vegetables", "Fruits",
    "Livestock", "Dairy", "Other"
]


async def handle_prices(
    state:        str,
    user_input:   str,
    session_data: dict,
) -> tuple[str, str, dict]:
    """Returns (response_text, next_state, updated_session_data)."""

    if state == "prices_district":
        lines = "\n".join(f"{i+1}. {d}" for i, d in enumerate(DISTRICTS))
        return f"CON Select district:\n{lines}\n0. Back", "prices_category", session_data

    if state == "prices_category":
        if user_input == "0":
            return "CON Main Menu:\n1. Prices\n2. Orders\n3. Register\n0. Exit", "main_menu", {}

        if not user_input.isdigit() or int(user_input) < 1 or int(user_input) > len(DISTRICTS):
            return "CON Invalid choice.\n0. Back", "prices_district", session_data

        session_data["district"] = DISTRICTS[int(user_input) - 1]
        lines = "\n".join(f"{i+1}. {c}" for i, c in enumerate(CATEGORIES))
        return f"CON Select category:\n{lines}\n0. Back", "prices_result", session_data

    if state == "prices_result":
        if user_input == "0":
            return "CON Select district:\n" + "\n".join(
                f"{i+1}. {d}" for i, d in enumerate(DISTRICTS)
            ) + "\n0. Back", "prices_category", {}

        if not user_input.isdigit() or int(user_input) < 1 or int(user_input) > len(CATEGORIES):
            return "CON Invalid choice.\n0. Back", "prices_category", session_data

        district = session_data.get("district", "")
        category = CATEGORIES[int(user_input) - 1]

        try:
            async with httpx.AsyncClient() as client:
                res = await client.get(
                    f"{settings.PRODUCE_SERVICE_URL}/listings/price-suggestion",
                    params={"category": category, "unit": "kg", "district": district},
                    headers={"x-internal-secret": settings.INTERNAL_SECRET},
                    timeout=5.0
                )
                data = res.json()

            if data.get("suggested", 0) == 0:
                return (
                    f"END {category} in {district}\n"
                    f"No listings yet.\n"
                    f"Dial *384*1# to check again.",
                    "main_menu", {}
                )

            return (
                f"END {category} ({district})\n"
                f"Min: {int(data['min']):,} UGX/kg\n"
                f"Max: {int(data['max']):,} UGX/kg\n"
                f"Avg: {int(data['suggested']):,} UGX/kg\n"
                f"{data['basis']}\n"
                f"Dial *384*1# for more.",
                "main_menu", {}
            )

        except Exception as e:
            logger.error(f"Price fetch failed: {e}")
            return (
                "END Could not fetch prices.\nPlease try again.\nDial *384*1#",
                "main_menu", {}
            )

    return "END Something went wrong.\nDial *384*1#", "main_menu", {}