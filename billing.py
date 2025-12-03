import logging
from db import get_connection, get_user_id, get_pending_bill, carry_over_bill, clear_user_context
from utils import send_text, send_text_with_buttons
import datetime

logger = logging.getLogger(__name__)

def generate_monthly_bill(user_id):
    # This function should be run by a scheduler at the beginning of each month
    # It calculates the total pending amount from the previous month and creates a new bill
    pass

def send_billing_reminders():
    # This function should be run by a scheduler daily
    # It checks for pending bills and sends reminders to users only from 25th to last day of the month
    today = datetime.date.today()
    last_day = (today.replace(day=28) + datetime.timedelta(days=4)).replace(day=1) - datetime.timedelta(days=1)
    if today.day < 25 or today.day > last_day.day:
        return  # Only alert from 25th to last day

    conn = get_connection()
    cur = conn.cursor(dictionary=True)
    cur.execute("SELECT * FROM monthly_bills WHERE status = 'pending'")
    bills = cur.fetchall()
    cur.close()
    conn.close()

    for bill in bills:
        user_id = bill['user_id']
        conn = get_connection()
        cur = conn.cursor()
        cur.execute("SELECT phone_number FROM users WHERE id = %s", (user_id,))
        phone = cur.fetchone()[0]
        cur.close()
        conn.close()

        message = f"Hi! This is a reminder that your bill of ₹{bill['pending_amount']:.2f} is due on {bill['due_date'].strftime('%d-%m-%Y')}."
        buttons = [
            {"type": "reply", "reply": {"id": f"move_to_next_month_{bill['id']}", "title": "Move to Next Month"}},
            {"type": "reply", "reply": {"id": "contact_support", "title": "Contact Support"}}
        ]
        send_text_with_buttons(phone, message, buttons)

def move_pending_to_next_month(phone: str, bill_id: int) -> None:
    try:
        uid = get_user_id(phone)
        if not uid:
            send_text(phone, "User not found.")
            return

        bill = get_pending_bill(uid)
        if not bill or bill['id'] != bill_id:
            send_text(phone, "No pending bill found to move.")
            return

        carry_over_bill(bill_id)
        clear_user_context(phone)
        send_text(phone, "Your pending amount has been moved to next month's bill.")
    except Exception as e:
        logger.error(f"Error in move_pending_to_next_month: {e}")
        send_text(phone, "An error occurred while moving your pending amount.")
