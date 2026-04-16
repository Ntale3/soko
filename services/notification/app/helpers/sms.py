import logging
import africastalking
from app.core.config import settings

logger = logging.getLogger(__name__)

africastalking.initialize(
    username=settings.AT_USERNAME,
    api_key=settings.AT_API_KEY,
)
sms = africastalking.SMS


def send_sms(phone: str, message: str) -> bool:
    if not phone:
        logger.warning("SMS skipped — no phone number")
        return False

    # Normalise Uganda numbers
    if phone.startswith("0"):
        phone = "+256" + phone[1:]
    elif not phone.startswith("+"):
        phone = "+256" + phone

    try:
        response = sms.send(
            message=message,
            recipients=[phone],
            sender_id=settings.AT_SENDER_ID or None,
        )
        status = response["SMSMessageData"]["Recipients"][0]["status"]
        if status == "Success":
            logger.info(f"SMS sent to {phone}")
            return True
        logger.warning(f"SMS failed to {phone}: {status}")
        return False
    except Exception as e:
        logger.error(f"SMS exception for {phone}: {e}")
        return False