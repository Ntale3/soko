import logging
import httpx
from passlib.context import CryptContext
from app.core.config import settings

logger = logging.getLogger(__name__)
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_pin(pin: str) -> str:
    return pwd_context.hash(pin)


def verify_pin(pin: str, hashed: str) -> bool:
    try:
        return pwd_context.verify(pin, hashed)
    except Exception:
        return False


async def handle_register(
    state:        str,
    user_input:   str,
    session_data: dict,
    phone:        str,
    db,
) -> tuple[str, str, dict, bool]:
    """Returns (response_text, next_state, session_data, authenticated)."""

    from app.models.ussd import USSDUser

    if state == "register_name":
        if not user_input.strip():
            return "CON Name cannot be empty.\nEnter your name:", "register_name", session_data, False
        session_data["name"] = user_input.strip()
        return "CON Enter 4-digit PIN:", "register_pin", session_data, False

    if state == "register_pin":
        if not user_input.isdigit() or len(user_input) != 4:
            return "CON PIN must be 4 digits.\nEnter PIN:", "register_pin", session_data, False
        session_data["pin"] = user_input
        return "CON You are a:\n1. Buyer\n2. Farmer", "register_role", session_data, False

    if state == "register_role":
        role = "farmer" if user_input == "2" else "buyer"
        name = session_data.get("name", "")
        pin  = session_data.get("pin",  "")

        # Check if already registered
        existing = db.query(USSDUser).filter(USSDUser.phone == phone).first()
        if existing and existing.is_registered:
            return (
                "END Already registered.\nDial *384*1# to continue.",
                "main_menu", {}, False
            )

        try:
            async with httpx.AsyncClient() as client:
                res = await client.post(
                    f"{settings.AUTH_SERVICE_URL}/auth/register",
                    json={
                        "email":    f"{phone.replace('+', '')}@ussd.soko.ug",
                        "password": pin + pin + pin,  # 12-char password from PIN
                        "role":     role,
                        "fullName": name,
                        "phone":    phone,
                        "district": "",
                    },
                    timeout=5.0
                )
                if res.status_code != 201:
                    raise Exception(f"Auth service returned {res.status_code}")

                data        = res.json()
                platform_id = data["user"]["id"]

            # Save USSD user record
            ussd_user = USSDUser(
                phone=phone,
                platform_id=platform_id,
                pin_hash=hash_pin(pin),
                role=role,
                is_registered=True,
            )
            db.add(ussd_user)
            db.commit()

            # Welcome SMS via Notification Service
            try:
                async with httpx.AsyncClient() as client:
                    await client.post(
                        f"{settings.NOTIFICATION_SERVICE_URL}/internal/notify",
                        json={
                            "event":    "system",
                            "buyer_id" if role == "buyer" else "farmer_id": platform_id,
                            "meta": {
                                "message": f"Welcome to Soko, {name}! Dial *384*1# to check crop prices anytime."
                            }
                        },
                        headers={"x-internal-secret": settings.INTERNAL_SECRET},
                        timeout=3.0
                    )
            except Exception as e:
                logger.warning(f"Welcome SMS failed: {e}")

            return (
                f"END Welcome to Soko!\n"
                f"Name: {name}\n"
                f"Role: {role.capitalize()}\n"
                f"Dial *384*1# to continue.",
                "main_menu", {}, True
            )

        except Exception as e:
            logger.error(f"Registration failed: {e}")
            return (
                "END Registration failed.\nPlease try again.\nDial *384*1#",
                "main_menu", {}, False
            )

    return "END Invalid state.\nDial *384*1#", "main_menu", {}, False


async def verify_login(
    user_input:   str,
    session_data: dict,
    phone:        str,
    db,
) -> tuple[str, str, dict, bool, str | None]:
    """
    Verifies PIN for login.
    Returns (response_text, next_state, session_data, authenticated, platform_id)
    """
    from app.models.ussd import USSDUser

    user = db.query(USSDUser).filter(USSDUser.phone == phone).first()

    if not user or not user.is_registered:
        return (
            "CON No account found.\n1. Register\n0. Back",
            "main_menu", {}, False, None
        )

    if not verify_pin(user_input, user.pin_hash):
        return (
            "END Incorrect PIN.\nDial *384*1# to try again.",
            "main_menu", {}, False, None
        )

    session_data["platform_id"] = str(user.platform_id)
    session_data["role"]        = user.role
    return "", "", session_data, True, str(user.platform_id)