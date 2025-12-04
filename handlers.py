from utils import *
from db import *
import uuid
from fuzzywuzzy import fuzz
from nltk.stem import WordNetLemmatizer
import logging
from typing import Any, Dict, Optional
import time
from admin_alerts import *
import decimal
from features import *
from billing import move_pending_to_next_month
from utils import language_map

lemmatizer = WordNetLemmatizer()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# --- Rate Limiting ---
user_last_message_time = {}
def is_rate_limited(phone, min_interval=2):
    now = time.time()
    last = user_last_message_time.get(phone, 0)
    if now - last < min_interval:
        return True
    user_last_message_time[phone] = now
    return False

BUTTONS_MAIN_MENU = [
    {"type": "reply", "reply": {"id": "catalog", "title": "🛍️ Browse Products"}},
    {"type": "reply", "reply": {"id": "order", "title": "✅ My Orders"}},
    {"type": "reply", "reply": {"id": "help", "title": "💬 Support"}}
]
BUTTONS_AFTER_ORDER = [
    {"type": "reply", "reply": {"id": "track", "title": "📦 Track Order"}},
    {"type": "reply", "reply": {"id": "credit", "title": "💳 Check Credit"}},
    {"type": "reply", "reply": {"id": "catalog", "title": "🛍️ Browse More"}}
]
BUTTONS_AFTER_CANCEL = [
    {"type": "reply", "reply": {"id": "catalog", "title": "🛍️ Browse Products"}},
    {"type": "reply", "reply": {"id": "place_new_order", "title": "✅ Place New Order"}},
    {"type": "reply", "reply": {"id": "help", "title": "💬 Help"}}
]
BUTTONS_AFTER_CREDIT = [
    {"type": "reply", "reply": {"id": "catalog", "title": "🛍️ Browse Products"}},
    {"type": "reply", "reply": {"id": "order", "title": "✅ My Orders"}},
    {"type": "reply", "reply": {"id": "help", "title": "💬 Support"}}
]
BUTTONS_AFTER_HISTORY = [
    {"type": "reply", "reply": {"id": "track", "title": "📦 Track Current Order"}},
    {"type": "reply", "reply": {"id": "credit", "title": "💳 Check Credit"}},
    {"type": "reply", "reply": {"id": "help", "title": "❓ Get Help"}}
]
BUTTONS_AFTER_LANGUAGE = [
    {"type": "reply", "reply": {"id": "catalog", "title": "View Catalog"}},
    {"type": "reply", "reply": {"id": "help", "title": "💬 Help"}}
]

# --- INTENT DETECTION ---
def detect_intent(text: Optional[str], button_payload: Optional[str] = None) -> str:
    if button_payload:
        return button_payload
    text = (text or "").lower().strip()
    # Use simple lowercase tokens instead of lemmatization to avoid requiring NLTK corpora
    text_words = text.split()
    synonyms = {
        "greeting": ["hi", "hello", "hey", "namaste", "hola", "greetings"],
        "thanks": ["thanks", "thank you", "thx", "dhanyavad", "shukriya"],
        "bye": ["bye", "goodbye", "see you", "tata", "alvida"],
        "yes": ["yes", "yeah", "yup", "haan", "ok", "sure"],
        "no": ["no", "nope", "nah", "nahi", "not now", "exit"],
        "catalog": ["catalog", "browse", "show products", "see items"],
        "history": ["order", "history", "past orders", "previous orders"],
        "credit": ["credit", "wallet", "balance","Credit"],
        "cancel": ["cancel", "abort", "remove order"],
        "track": ["track", "status", "order status"],
        "language": ["language", "set language"],
        "address": ["address", "set address", "change address", "update address"],
        "help": ["help", "support", "fix", "issue"],
        "seller_login": ["seller login", "become seller", "admin login", "owner login"],
        "seller_logout": ["seller logout", "logout"],
        "add_seller": ["add seller", "new seller", "register seller"],
        "change_password": ["change password", "update password", "reset password"],
        "create_alert": ["create alert", "report issue", "raise alert", "send alert"],
        "view_alerts": ["alerts", "view alerts", "alert", "show alerts", "see alerts"],
        "view_monthly_bill": ["Monthly bill", "view bill", "show bill"]
    }
    best_score = 0
    best_intent = "unknown"
    for intent, keys in synonyms.items():
        for key in keys:
            key_words = key.split()
            joined_key = " ".join(key_words)
            score = fuzz.partial_ratio(" ".join(text_words), joined_key)
            if score > best_score:
                best_score = score
                best_intent = intent
    if best_score >= 70:
        return best_intent
    return "unknown"

# --- HANDLERS ---
def handle_payload_action(phone: str, payload: str) -> None:
    try:
        uid = get_user_id(phone)
        if payload == "catalog":
            if is_feature_enabled("catalog"):
                send_product_list(phone)
        elif payload == "help":
            send_help(phone)
        elif payload == "main_menu":
            send_text_with_buttons(phone, "Welcome! Choose an option:", BUTTONS_MAIN_MENU)
        elif payload == "credit":
            if is_feature_enabled("credit"):
                send_credit(phone)
        elif payload == "history" or payload == "order":
            if is_feature_enabled("order_history"):
                send_order_history(phone)
        elif payload in ["alerts", "view_alerts", "alert"]:
            if is_feature_enabled("alerts"):
                send_admin_alerts(phone)
        elif payload == "create_alert":
            if is_feature_enabled("alerts"):
                create_admin_alert_simple(phone)
        elif payload == "place_new_order":
            if is_feature_enabled("place_order"):
                send_text(phone, "Please type 'catalog' to browse and add products to your cart.")
        elif payload == "track":
            if is_feature_enabled("track_order"):
                track_order(phone)
        elif payload == "view_monthly_bill":
            if is_feature_enabled("monthly_billing"):
                send_monthly_bill(phone)
        elif payload.startswith("cancel_order_"):
            if is_feature_enabled("cancel_order"):
                order_id = payload.replace("cancel_order_", "")
                cancel_order(phone, order_id)
        elif payload.startswith("resolve_alert_"):
            if is_feature_enabled("resolve_alert"):
                alert_id = int(payload.replace("resolve_alert_", ""))
                resolve_admin_alert(alert_id)
                send_text(phone, f"✅ Alert {alert_id} marked as resolved.")
        elif payload.startswith("mark_delivered_"):
            if is_feature_enabled("mark_delivered"):
                order_id = payload.replace("mark_delivered_", "")
                if order_id:
                    mark_order_delivered_and_paid(phone, order_id)
                else:
                    send_text(phone, "Invalid order ID for marking as delivered.")
        elif payload.startswith("move_to_next_month_"):
            if is_feature_enabled("enhanced_credit"):
                bill_id = int(payload.replace("move_to_next_month_", ""))
                move_pending_to_next_month(phone, bill_id)
            else:
                send_text(phone, "An error occurred while processing your request.")

    except Exception as e:
        logger.error(f"Error in handle_payload_action: {e}")
        send_text(phone, "An error occurred while processing your request.")

def handle_message(data: Dict[str, Any]) -> None:
    if is_feature_enabled("handle_message"):
        try:
            msg = None
            phone = None
            text = None
            button = None
            try:
                msg = data.get("entry", [{}])[0].get("changes", [{}])[0].get("value", {}).get("messages", [{}])[0]
                phone = msg.get("from")
                text = msg.get("text", {}).get("body")
                button = (
                    msg.get("button", {}).get("payload") or
                    msg.get("button_reply", {}).get("id") or
                    msg.get("interactive", {}).get("button_reply", {}).get("id")
                )
            except Exception:
                import os
                admin_phone = os.getenv("ADMIN_PHONE")
                if phone:
                    send_text(phone, "Malformed message data received.")
                elif admin_phone:
                    send_text(admin_phone, "Malformed message data received.")
                else:
                    print("Malformed message data received.")
                return
            
            if is_rate_limited(phone):
                send_text(phone, "⏳ Please wait a moment before sending another message.")
                return
            
            ensure_user_exists(phone)

            if msg.get("order"):
                place_order_from_catalog(phone, msg.get("order"))
                return

            context = get_user_context(phone)
            if context:
                next_action = context.get("next_action")
                if next_action == "verify_seller_for_alerts":

                    if text.strip().lower() == "notseller":
                        show_user_alerts(phone, phone)

                    else:

                        if check_seller_password(phone, text.strip()):
                            show_all_alerts_for_admin(phone)
                        else:
                            send_text(phone, "Incorrect password. Try again or type *notseller*.")
                            return 
                    clear_user_context(phone)
                    return 

                if detect_intent(text) == "no":
                    clear_user_context(phone)
                    send_text(phone, "Action cancelled.")
                    send_text_with_buttons(phone, "Welcome! Choose an option:", BUTTONS_MAIN_MENU)
                    return
                elif next_action == "place_order":
                    set_address(phone, text, context.get("order"))
                    return
                
                elif next_action == "payment_method":
                    payment_type = text
                    order_data = context.get("order")
                    address = context.get("address")

                    if not payment_type:
                        send_text(phone, "No payment method selected.")
                        return

                    place_order_from_catalog(phone, order_data, payment_type=payment_type, address=address)
                    return
                
                elif next_action == "alert_simple_wait_input":
                    return create_admin_alert_simple(phone, text)

                elif next_action == "seller_login_password":
                    if check_seller_password(phone, text.strip()):
                        login_seller_session(phone)
                        clear_user_context(phone)
                        send_text(phone, "✅ Seller login successful! You will now receive admin alerts.")
                    else:
                        clear_user_context(phone)
                        send_text(phone, "❌ Incorrect password. Seller login failed.")
                    return
                elif next_action == "seller_change_password_old":
                    if check_seller_password(phone, text.strip()):
                        set_user_context(phone, {"next_action": "seller_change_password_new", "old_password": text.strip()})
                        send_text(phone, "Enter your new password:")
                    else:
                        clear_user_context(phone)
                        send_text(phone, "Incorrect current password. Password change cancelled.")
                    return
                elif next_action == "seller_change_password_new":
                    update_seller_password(phone, text.strip())
                    clear_user_context(phone)
                    send_text(phone, "Seller password updated successfully.")
                    return
                elif next_action == "add_seller_phone":
                    new_seller_phone = text.strip()
                    register_seller(new_seller_phone, "LIMAT123")
                    clear_user_context(phone)
                    send_text(phone, f"✅ New seller with phone number {new_seller_phone} has been added with the default password.")
                    return
                elif next_action == "alert_simple_wait_input":
                    create_admin_alert_simple(phone, text=text)
                    return
                elif next_action == "set_language":
                    set_language(phone, text)
                    clear_user_context(phone)
                    return
                elif next_action == "verify_seller_for_alerts":
                    # handled earlier
                    return
                    
            if button:
                handle_payload_action(phone, button)
                return
            
            intent = detect_intent(text, button)
            if intent == "greeting":
                clear_user_context(phone)
                send_text(phone, "👋 Welome to Grocery App! How can I help you today?")
                send_text_with_buttons(phone, "Welcome! Choose an option:", BUTTONS_MAIN_MENU)
            elif intent == "catalog":
                clear_user_context(phone)
                send_product_list(phone)

            elif intent == "no":
                clear_user_context(phone)
                send_text(phone, "Action cancelled.")
                send_text_with_buttons(phone, "Welcome! Choose an option:", BUTTONS_MAIN_MENU)
                return

            elif intent == "history":
                clear_user_context(phone)
                send_order_history(phone)
            elif intent == "credit":
                send_credit(phone)
            elif intent == "cancel":
                clear_user_context(phone)
                send_order_history(phone)
            elif intent == "track":
                clear_user_context(phone)
                track_order(phone)
            elif intent == "language":
                set_language(phone, text)
            elif intent == "address":
                set_address(phone, text)
            elif intent == "help":
                send_help(phone)
            elif intent == "view_alerts":
                send_admin_alerts(phone)
            elif intent == "create_alert":
                create_admin_alert_simple(phone)
            elif intent == "seller_login":
                set_user_context(phone, {"next_action": "seller_login_password"})
                send_text(phone, "Please enter the seller password:")
            elif intent == "seller_logout":
                logout_seller_session(phone)
                send_text(phone, "✅ You have been logged out as a seller.")

            elif intent == "add_seller":
                if is_seller_session(phone): # Assuming only sellers can add other sellers
                    set_user_context(phone, {"next_action": "add_seller_phone"})
                    send_text(phone, "Please enter the phone number of the new seller: \nwith country code like: 911234567890\n")
                else:
                    send_text(phone, "❌ You must be a seller to add a new seller.")
            elif intent == "change_password":
                if is_seller_session(phone):
                    set_user_context(phone, {"next_action": "seller_change_password_old"})
                    send_text(phone, "Please enter your current seller password:")
                else:
                    send_text(phone, "❌ You must be a seller to change your password. Send 'seller login' to become a seller.")
            elif intent == "view_monthly_bill":
                if is_feature_enabled("monthly_billing"):
                    send_monthly_bill(phone)
                else:
                    send_text(phone, "Sorry, I didn't understand that. Try typing 'catalog', 'order', 'cart', or use the menu below.")
                    send_text_with_buttons(phone, "Welcome! Choose an option:", BUTTONS_MAIN_MENU)
        except Exception as e:
            logger.error(f"Error in handle_message: {e}")
            import os
            admin_phone = os.getenv("ADMIN_PHONE")
            if phone:
                send_text(phone, "❌ An error occurred while processing your message.")
            elif admin_phone:
                send_text(admin_phone, "❌ An error occurred while processing your message.")
            else:
                print("❌ An error occurred while processing your message.")

def send_help(phone: str) -> None:
    if is_feature_enabled("send_help"):
        try:
            send_text(
                phone,
                """
    *Main Menu & Commands:*

    Type any of these commands:

    - catalog: Browse Products
    - order: View your order history
    - credit: Check your credit history
    - track: Track your most recent order
    - cancel: Cancel an active order
    - help: Show this menu
    - address: Set or update your address - Do by typing address as prefix then your address
    - language: Set your preferred language by typing 'Language' then type the number assigned for the language you want.
    - exit: Cancel the current operation

    *Alerts:*
    - create alert: Start the alert creation process
    - alerts: View your alerts

    *Roles:*
    - User: Can browse products, place orders, and manage their account.
    - Seller: Can manage products, view orders, users, sellers, and system settings.

    *Seller/Admin:*
    - seller login: Log in as a seller
    - logout: Log out as a seller
    - change password: Change your seller password
    """
            )
        except Exception as e:
            logger.error(f"Error in send_help: {e}")

def place_order_from_catalog(phone: str, order_data: dict, payment_type: Optional[str] = None, address: Optional[str] = None) -> None:
    if is_feature_enabled("place_order"):
        try:
            uid = get_user_id(phone)
            if not uid:
                send_text(phone, "User not found.")
                return

            product_items = order_data.get("product_items", [])
            if not product_items:
                send_text(phone, "No products in the order.")
                return

            items_str = ", ".join([f"{item['product_retailer_id']} x{item['quantity']}" for item in product_items])
            total_price = sum([float(item['item_price']) * int(item['quantity']) for item in product_items])
            
            with get_connection() as conn:
                try:
                    with conn.cursor() as cur:
                        if not address:
                            cur.execute("SELECT address FROM users WHERE id = %s", (uid,))
                            result = cur.fetchone()
                            address = result[0] if result else None

                            if not address or not address.strip():
                                set_user_context(phone, {
                                    "next_action": "place_order",
                                    "order": order_data
                                })
                                send_text(phone, " We don't have your address on file. Please provide it.")
                                send_text(phone, "Type your address like this: *address 123 Main Street*")
                                return

                        if not payment_type:
                            send_text(phone, "Please choose a payment method by typing 'cash' or 'card'.")
                            set_user_context(phone, {
                                "next_action": "payment_method",
                                "order": order_data,
                                "address": address
                            })
                            return

                        payment_type_lower = payment_type.lower()
                        if "cash" in payment_type_lower:
                            payment_status = "pending" # Changed from cash to pending
                        elif "card" in payment_type_lower:
                            payment_status = "pending" # Changed from card to pending
                            send_text(phone, "A card machine will be sent with your delivery.")
                        else:
                            send_text(phone, "Invalid payment method selected. Please type 'cash' or 'card'.")
                            return

                        order_id = str(uuid.uuid4())[:8]
                        delivery_status = "pending"
                    
                        cur.execute("""
                            INSERT INTO orders (user_id, order_id, product_summary, delivery_status, address, payment_status, price, is_billed)
                            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                        """, (uid, order_id, items_str, delivery_status, address, payment_status, total_price,0))
                        create_bill_for_order(uid, order_id, total_price, delivery_status)

                        try:
                            cur.execute("""
                                INSERT INTO admin_alerts (alert_type, message, user_phone, resolved, timestamp)
                                VALUES (%s, %s, %s, %s, NOW())
                            """, (
                                "order placed",
                                f"Items: {items_str}",
                                phone,
                                0
                            ))
                        except Exception as alert_exc:
                            logger.error(f"Alert insert failed: {alert_exc}")
                        
                        conn.commit()

                except Exception as db_exc:
                    conn.rollback()
                    logger.error(f"DB error in place_order: {db_exc}")
                    send_text(phone, "❌ Could not place order due to a database error.")
                    return

            clear_user_context(phone)
            send_text(phone, f"""✅ *Order Placed!*
            🧾 Order ID: `{order_id}`
            📦 Items: {items_str}
            📍 Address: {address}
            💵 Payment: *{payment_status.upper()}*""")
            send_text_with_buttons(phone, "What would you like to do next?", BUTTONS_AFTER_ORDER)
            from admin_alerts import notify_admins_new_alert
            notify_admins_new_alert("order_placed", f"Order ID: {order_id}\nItems: {items_str}\nAddress: {address}", phone)

        except Exception as e:
            logger.error(f"Error in place_order_from_catalog: {e}")
            send_text(phone, "❌ An error occurred while placing your order.")

def cancel_order(phone: str, order_id: str) -> None:
    if is_feature_enabled("cancel_order"):
        try:
            uid = get_user_id(phone)
            if not uid:
                send_text(phone, "User not found.")
                return
            with get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute("UPDATE orders SET delivery_status = 'cancelled' WHERE order_id = %s AND user_id = %s", (order_id, uid))
                    conn.commit()
                    send_text(phone, f"❌ Order {order_id} has been cancelled.")
            send_text_with_buttons(phone, "Would you like to do something else?", BUTTONS_AFTER_CANCEL)
        except Exception as e:
            logger.error(f"Error in cancel_order: {e}")
            send_text(phone, "❌ An error occurred while cancelling your order.")

def send_credit(phone: str) -> None:
    if is_feature_enabled("credit"):
        try:
            uid = get_user_id(phone)
            if not uid:
                send_text(phone, "User not found.")
                return

            bills = get_pending_bills_for_display(uid)
            if not bills:
                send_text(phone, "You have no pending bills.")
                return

            for bill in bills:
                lines = [f"*Pending Bill for Order {bill['order_id']}*"]
                lines.append(f"  - Amount: ₹{bill['pending_amount']:.2f}")
                lines.append(f"  - Due Date: {bill['due_date'].strftime('%d-%m-%Y')}")
                
                message = "\n".join(lines)
                buttons = [
                    {"type": "reply", "reply": {"id": f"move_to_next_month_{bill['id']}", "title": "Move to Next Month"}}
                ]
                send_text_with_buttons(phone, message, buttons)

        except Exception as e:
            logger.error(f"Error in send_credit: {e}")
            send_text(phone, "An error occurred while fetching your credit history.")
 
def send_order_history(phone: str) -> None:
    if is_feature_enabled("order_history"):
        try:
            uid = get_user_id(phone)
            if not uid:
                send_text(phone, "User not found.")
                return
            orders = get_user_orders(uid)
            if not orders:
                send_text(phone, "No past orders found.")
                return

            send_text(phone, "*Your Orders:*\n")
            
            for order in orders:
                buttons = []
            
                buttons.append({"type": "reply", "reply": {"id": f"mark_delivered_{order['order_id']}", "title": "Mark as Delivered"}})
                buttons.append({"type": "reply", "reply": {"id": f"cancel_order_{order['order_id']}", "title": "Cancel Order"}})
                
                send_text_with_buttons(
                    phone,
                    f"*Order ID:* {order['order_id']}\n" \
                    f"*Summary:* {order['product_summary']}\n" \
                    f"*Delivery Status:* {order['delivery_status']}\n" \
                    f"*Payment Status:* {order['payment_status']}",
                    buttons
                )

            send_text_with_buttons(phone, "What would you like to do next?", BUTTONS_AFTER_HISTORY)
        except Exception as e:
            logger.error(f"Error in send_order_history: {e}")
            send_text(phone, "An error occurred while fetching your order history.")

def track_order(phone: str) -> None:
    if is_feature_enabled("track_order"):
        try:
            uid = get_user_id(phone)
            if not uid:
                send_text(phone, "User not found.")
                return
            with get_connection() as conn:
                with conn.cursor(dictionary=True) as cur:
                    cur.execute("SELECT * FROM orders WHERE user_id = %s AND delivery_status NOT IN ('delivered', 'cancelled') ORDER BY timestamp DESC", (uid,))
                    orders = cur.fetchall()
            final = ""
            if orders:
                send_text(phone, "*Your Active Orders:*\n")
                for order in orders:
                    status_map = {
                        "pending": "🕒 Pending",
                        "shipped": "📦 Shipped",
                        "out_for_delivery": "🚚 Out for Delivery",
                        "delivered": "✅ Delivered",
                        "cancelled": "❌ Cancelled"
                    }
                    status_icon = status_map.get(order['delivery_status'], order['delivery_status'].capitalize())
                    final = final + f"📝 *Order ID:* {order['order_id']}\n📦 *Items:* {order['product_summary']}\n *Amount:* ₹{order['price']}\n🚚 *Status:* {status_icon}\n\n"
                send_text(phone,final)
            else:
                send_text(phone, "No live orders found.")
            send_text_with_buttons(phone, "What would you like to do next?", BUTTONS_AFTER_HISTORY)
        except Exception as e:
            logger.error(f"Error in track_order: {e}")
            send_text(phone, "An error occurred while tracking your order.")

def mark_order_delivered_and_paid(phone: str, order_id: str) -> None:
    if is_feature_enabled("mark_delivered"):
        try:
            uid = get_user_id(phone)
            if not uid:
                send_text(phone, "User not found.")
                return
            with get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute("UPDATE orders SET delivery_status = 'delivered', payment_status = 'paid' WHERE order_id = %s AND user_id = %s", (order_id, uid))
                    conn.commit()
            send_text(phone, f"Order {order_id} has been marked as delivered and paid.")
        except Exception as e:
            logger.error(f"Error in mark_order_delivered_and_paid: {e}")
            send_text(phone, "An error occurred while updating your order.")

def set_language(phone: str, text: str) -> None:
    if is_feature_enabled("set_language"):
        if text and (text.strip().lower() == 'language' or 'language' in text.lower()):
            message = "Please choose a language:Enter the number beside the language\n\n"
            for key, value in language_map.items():
                message += f"{key}. {value[0]}\n"
            send_text(phone, message)
            set_user_context(phone, {"next_action": "set_language"})
            return

        context = get_user_context(phone)
        if context and context.get("next_action") == "set_language":
            try:
                lang_key = int(text.strip())
                if lang_key in language_map:
                    lang_code = language_map[lang_key][1]
                    update_user_language(phone, lang_code)
                    send_text(phone, f"🌐 Language updated to '{language_map[lang_key][0]}' successfully.")
                    clear_user_context(phone)
                    send_text_with_buttons(phone, "What would you like to do now?", BUTTONS_AFTER_LANGUAGE)
                else:
                    send_text(phone, "Invalid selection. Please choose a number from the list.")
            except (ValueError, TypeError):
                send_text(phone, "Invalid input. Please enter a number.")

def set_address(phone: str, text: str, order_data: Optional[dict] = None) -> None:
    if is_feature_enabled("set_address"):

        addr = text.lower().replace("address", "").strip()

        if len(addr)==0:
            send_text(phone, "Please provide your address as address 123street")
            return
        
        update_user_address(phone, addr)
        send_text(phone,"Address is updated successfully!")

def send_monthly_bill(phone: str) -> None:
    try:
        uid = get_user_id(phone)
        if not uid:
            send_text(phone, "User not found.")
            return

        bills = get_pending_bills_for_display(uid)
        if not bills:
            send_text(phone, "You have no pending bills for this month or the next.")
            return

        for bill in bills:
            message = f"""
            *Monthly Bill*

            Bill for: {bill['bill_month'].strftime('%B %Y')}
            Total Amount: ₹{bill['total_amount']:.2f}
            Pending Amount: ₹{bill['pending_amount']:.2f}
            Due Date: {bill['due_date'].strftime('%d-%m-%Y')}
            """
            buttons = [
                {"type": "reply", "reply": {"id": f"move_to_next_month_{bill['id']}", "title": "Move to Next Month"}},
                {"type": "reply", "reply": {"id": "contact_support", "title": "Contact Support"}}
            ]
            send_text_with_buttons(phone, message, buttons)

    except Exception as e:
        logger.error(f"Error in send_monthly_bill: {e}")
        send_text(phone, "An error occurred while fetching your monthly bill.")
        