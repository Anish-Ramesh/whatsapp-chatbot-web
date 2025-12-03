import logging
from db import *
from utils import send_text, send_text_with_buttons

logger = logging.getLogger(__name__)

ALERT_TYPES = [
    "order placed",
    "low stock",
    "payment issue",
    "custom"
]

def create_admin_alert_simple(phone, text=None):
    """
    Prompts user to submit all alert info in one message: type, message, and address (comma-separated).
    Example: order_placed, Payment not received, 123 Main St
    """
    if not text:
        send_text(phone, '''Please enter alert details in this format:
<type>, <message>, <address>

Available ALERT_TYPES:
1. order placed
2. low stock
3. payment issue
4. custom''')
        set_user_context(phone, {
            "next_action": "alert_simple_wait_input",
            "step": "awaiting_alert_details",
            "prompted": True
        })
        return

    # Parse input
    parts = [p.strip() for p in text.split(",")]
    if len(parts) < 3:
        send_text(phone, "❌ Invalid format. Please enter: <type>, <message>, <address>")
        set_user_context(phone, {
            "next_action": "alert_simple_wait_input",
            "step": "awaiting_alert_details",
            "error": "format_invalid"
        })
        return

    alert_type = parts[0].lower()
    message = parts[1]
    address = ", ".join(parts[2:])

    if alert_type not in ALERT_TYPES:
        send_text(phone, f"❌ Invalid alert type. Valid types: {', '.join(ALERT_TYPES)}")
        set_user_context(phone, {
            "next_action": "alert_simple_wait_input",
            "step": "awaiting_alert_details",
            "error": "invalid_type",
            "received_type": alert_type
        })
        return

    # Store alert
    full_message = f"{message}\nAddress: {address}"
    store_admin_alert(alert_type, full_message, phone)

    send_text_with_buttons(phone, f"✅ Alert created!\nType: *{alert_type.replace('_', ' ').title()}*", [
        {"type": "reply", "reply": {"id": "view_alerts", "title": "View My Alerts"}},
        {"type": "reply", "reply": {"id": "main_menu", "title": "🏠 Main Menu"}}
    ])

    notify_admins_new_alert(alert_type, full_message, phone)

    # Clear context after success
    clear_user_context(phone)

def notify_admins_new_alert(alert_type, message, user_phone):
    seller_phones = get_all_seller_phones()
    for seller_phone in seller_phones:
        if is_seller_session(seller_phone):
            send_text(seller_phone, f"*ADMIN ALERT*\nType: {alert_type.replace('_', ' ').title()}\nFrom: {user_phone}\n\nAlert:\n{message}")

def handle_admin_alert_action(phone, payload):
    if payload.startswith("resolve_alert_"):
        try:
            alert_id = int(payload.replace("resolve_alert_", ""))
            # Check if the user is a seller or the original creator of the alert
            alert = get_alert_by_id(alert_id)
            if is_seller(phone) or (alert and alert['user_phone'] == phone):
                resolve_admin_alert(alert_id)
                send_text(phone, f"Alert #{alert_id} marked as resolved.")
            else:
                send_text(phone, "You do not have permission to resolve this alert.")
        except (ValueError, IndexError):
            send_text(phone, "Invalid alert ID.")
        except Exception as e:
            logger.error(f"Error resolving alert: {e}")
            send_text(phone, "An error occurred while resolving the alert.")
    else:
        send_text(phone, "Unknown admin action.")

def send_admin_alerts(phone):
    # Ask for seller password or confirmation not a seller
    send_text(phone, "Are you a seller?\nPlease enter your current seller password.\n\nIf not a seller, type: *notseller*")
    set_user_context(phone, {"next_action": "verify_seller_for_alerts"})

def show_user_alerts(phone1, phone):
    
    try:
        alerts = get_admin_alerts(phone,resolved=False)
        if not alerts:
            send_text(phone1, "No Unresolved Alerts")
            return

        send_text(phone1, "*Unresolved Alerts:*")
        for alert in alerts:
            msg = f"*ID: {alert['id']}* | *Type: {alert['alert_type'].replace('_', ' ').title()}*\nFrom: {alert['user_phone']}\nMessage: {alert['message']}"
            buttons = [
                {"type": "reply", "reply": {"id": f"resolve_alert_{alert['id']}", "title": f"Resolve #{alert['id']}"}}
            ]
            send_text_with_buttons(phone1, msg, buttons)
    except Exception as e:
        logger.error(f"Error in send_admin_alerts: {e}")
        send_text(phone, "❌ An error occurred while processing your request.")

def show_all_alerts_for_admin(phone):
    try:
        all_users = get_all_user_phones()
        send_text(phone, "Alerts for all users:")
        send_text(phone, all_users)
        for user_phone in all_users:
            show_user_alerts(phone,user_phone)
        
    except Exception as e:
        logger.error(f"Error in show_all_alerts_for_admin: {e}")
        send_text(phone, "❌ Error retrieving alerts.")
