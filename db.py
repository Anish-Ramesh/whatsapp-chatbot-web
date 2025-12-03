# --- FILE: db.py ---
import hashlib
import mysql.connector
import json as _json
import os
from dotenv import load_dotenv
import logging
import datetime 
from dateutil.relativedelta import relativedelta  

load_dotenv()

def get_connection():
	return mysql.connector.connect(
		host="bhlkdzzuictcpwf1inf0-mysql.services.clever-cloud.com",
		user="uaexqxjgpmm15ma7",
		password="SfXKRZzv2cIa2fJzm3IJ",
		database="bhlkdzzuictcpwf1inf0",
		port=3306,
		ssl_disabled=True,
		connect_timeout=10
	)

def ensure_user_exists(phone):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("INSERT IGNORE INTO users (phone_number) VALUES (%s)", (phone,))
    conn.commit()
    cur.close()
    conn.close()

def get_user_id(phone):
    try:
        conn = get_connection()
        cur = conn.cursor()
        cur.execute("SELECT id FROM users WHERE phone_number = %s", (phone,))
        result = cur.fetchone()
        return result[0] if result else None
    except Exception as e:
        print("DB Error in get_user_id:", e)
        return None
    finally:
        try:
            cur.close()
            conn.close()
        except:
            pass

def update_user_language(phone, lang_code):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("UPDATE users SET language = %s WHERE phone_number = %s", (lang_code, phone))
    conn.commit()
    cur.close()
    conn.close()

def get_user_language(phone):
    conn = get_connection()
    cur = conn.cursor()
    phone = phone[1:]
    cur.execute("SELECT language FROM users WHERE phone_number = %s", (phone,))
    result = cur.fetchone()
    cur.close()
    conn.close()
    if result and result[0]:
        return result[0]
    return None

def update_user_address(phone, address):
    conn = get_connection()
    cur = conn.cursor()
    # Ensure user exists
    cur.execute("SELECT id FROM users WHERE phone_number = %s", (phone,))
    if not cur.fetchone():
        cur.execute("INSERT INTO users (phone_number) VALUES (%s)", (phone,))

    # Update address
    cur.execute("UPDATE users SET address = %s WHERE phone_number = %s", (address, phone))

    conn.commit()
    cur.close()
    conn.close()


# --- Persistent user_context ---
def get_user_context(phone):
    try:
        conn = get_connection()
        cur = conn.cursor()
        cur.execute("SELECT context_json FROM user_context WHERE phone = %s", (phone,))
        row = cur.fetchone()
        cur.close()
        conn.close()
        if row and row[0]:
            return _json.loads(row[0])
        return None
    except Exception as e:
        print("DB Error in get_user_context:", e)
        return None

def set_user_context(phone, context_dict):
    try:
        conn = get_connection()
        cur = conn.cursor()
        context_json = _json.dumps(context_dict)
        cur.execute("REPLACE INTO user_context (phone, context_json) VALUES (%s, %s)", (phone, context_json))
        conn.commit()
        cur.close()
        conn.close()
    except Exception as e:
        print("DB Error in set_user_context:", e)

def clear_user_context(phone):
    try:
        conn = get_connection()
        cur = conn.cursor()
        cur.execute("DELETE FROM user_context WHERE phone = %s", (phone,))
        conn.commit()
        cur.close()
        conn.close()
    except Exception as e:
        print("DB Error in clear_user_context:", e)

def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

# --- Seller Session Management ---
def login_seller_session(phone):
    try:
        conn = get_connection()
        cur = conn.cursor()
        cur.execute("REPLACE INTO seller_sessions (phone_number, login_time) VALUES (%s, NOW())", (phone,))
        conn.commit()
        cur.close()
        conn.close()
    except Exception as e:
        print("DB Error in login_seller_session:", e)

def logout_seller_session(phone):
    try:
        conn = get_connection()
        cur = conn.cursor()
        cur.execute("DELETE FROM seller_sessions WHERE phone_number = %s", (phone,))
        conn.commit()
        cur.close()
        conn.close()
    except Exception as e:
        print("DB Error in logout_seller_session:", e)

def is_seller_session(phone):
    try:
        conn = get_connection()
        cur = conn.cursor()
        cur.execute("SELECT phone_number FROM seller_sessions WHERE phone_number = %s", (phone,))
        result = cur.fetchone()
        cur.close()
        conn.close()
        return bool(result)
    except Exception as e:
        print("DB Error in is_seller_session:", e)
        return False

# --- Seller Management ---
def register_seller(phone, password="SELLERPASS123"):
    try:
        conn = get_connection()
        cur = conn.cursor()
        password_hash = hash_password(password)
        cur.execute("INSERT INTO sellers (phone_number, password_hash, created_at) VALUES (%s, %s, NOW()) ON DUPLICATE KEY UPDATE password_hash=%s", (phone, password_hash, password_hash))
        conn.commit()
        cur.close()
        conn.close()
    except Exception as e:
        print("DB Error in register_seller:", e)

def get_all_user_phones():
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT DISTINCT user_phone FROM admin_alerts")
    result = cur.fetchall()
    return [row[0] for row in result] if result else []

def check_seller_password(phone, password):
    try:
        conn = get_connection()
        cur = conn.cursor()
        cur.execute("SELECT password_hash FROM sellers WHERE phone_number = %s", (phone,))
        row = cur.fetchone()
        cur.close()
        conn.close()
        if not row:
            return False
        return row[0] == hash_password(password)
    except Exception as e:
        print("DB Error in check_seller_password:", e)
        return False

def update_seller_password(phone, new_password):
    try:
        conn = get_connection()
        cur = conn.cursor()
        password_hash = hash_password(new_password)
        cur.execute("UPDATE sellers SET password_hash = %s WHERE phone_number = %s", (password_hash, phone))
        conn.commit()
        cur.close()
        conn.close()
    except Exception as e:
        print("DB Error in update_seller_password:", e)

def is_seller(phone):
    try:
        conn = get_connection()
        cur = conn.cursor()
        cur.execute("SELECT id FROM sellers WHERE phone_number = %s", (phone,))
        result = cur.fetchone()
        cur.close()
        conn.close()
        return bool(result)
    except Exception as e:
        print("DB Error in is_seller:", e)
        return False

def get_all_seller_phones():
    try:
        conn = get_connection()
        cur = conn.cursor()
        cur.execute("SELECT phone_number FROM sellers")
        rows = cur.fetchall()
        cur.close()
        conn.close()
        return [row[0] for row in rows]
    except Exception as e:
        print("DB Error in get_all_seller_phones:", e)
        return []

# --- Admin Alerts ---
def store_admin_alert(alert_type, message, user_phone):
    try:
        conn = get_connection()
        cur = conn.cursor()
        cur.execute("INSERT INTO admin_alerts (alert_type, message, user_phone) VALUES (%s, %s, %s)", (alert_type, message, user_phone))
        conn.commit()
        cur.close()
        conn.close()
    except Exception as e:
        print("DB Error in store_admin_alert:", e)
        
def get_admin_alerts(phone, resolved=False):
    try:
        conn = get_connection()
        cur = conn.cursor(dictionary=True)
        r = 0
        cur.execute(
                    "SELECT * FROM admin_alerts WHERE resolved = %s AND user_phone = %s ORDER BY timestamp DESC",
                    (r, phone)
                )
        rows = cur.fetchall()
        cur.close()
        conn.close()
        return rows
    except Exception as e:
        print("DB Error in get_admin_alerts:", e)
        return []
    
def resolve_admin_alert(alert_id):
    try:
        conn = get_connection()
        cur = conn.cursor()
        cur.execute("UPDATE admin_alerts SET resolved = 1 WHERE id = %s", (alert_id,))
        conn.commit()
        cur.close()
        conn.close()
    except Exception as e:
        print("DB Error in resolve_admin_alert:", e)

def get_alert_by_id(alert_id):
    try:
        conn = get_connection()
        cur = conn.cursor(dictionary=True)
        cur.execute("SELECT * FROM admin_alerts WHERE id = %s", (alert_id,))
        row = cur.fetchone()
        cur.close()
        conn.close()
        return row
    except Exception as e:
        print("DB Error in get_alert_by_id:", e)
        return None

def get_user_credit_history(user_id):
    conn = get_connection()
    cur = conn.cursor(dictionary=True)
    cur.execute("SELECT * FROM credit_history WHERE user_id = %s", (user_id,))
    rows = cur.fetchall()
    cur.close()
    conn.close()
    return rows

# --- DB Connection Checker ---
def check_db_connection():
    try:
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT 1")
                cur.fetchone()  # fetch the result to clear the result set
        print("Database connection: SUCCESS")
        return True
    except Exception as e:
        print(f"Database connection: FAILED ({e})")
        return False

def get_user_orders(user_id):
    conn = get_connection()
    cur = conn.cursor(dictionary=True)
    cur.execute("SELECT * FROM orders WHERE user_id = %s ORDER BY timestamp DESC", (user_id,))
    rows = cur.fetchall()
    cur.close()
    conn.close()
    return rows

def get_pending_bill(user_id):
    conn = get_connection()
    cur = conn.cursor(dictionary=True)
    cur.execute("SELECT * FROM monthly_bills WHERE user_id = %s AND status = 'pending' ORDER BY bill_month DESC LIMIT 1", (user_id,))
    bill = cur.fetchone()
    cur.close()
    conn.close()
    return bill

def get_pending_bills_for_display(user_id):
    conn = get_connection()
    cur = conn.cursor(dictionary=True)
    cur.execute("SELECT * FROM monthly_bills WHERE user_id = %s AND status = 'pending' ORDER BY bill_month ASC", (user_id,))
    bills = cur.fetchall()
    cur.close()
    conn.close()
    return bills

def carry_over_bill(bill_id):
    conn = get_connection()
    cur = conn.cursor()

    # Get current due_date
    cur.execute("SELECT due_date FROM monthly_bills WHERE id = %s", (bill_id,))
    result = cur.fetchone()
    if not result:
        cur.close()
        conn.close()
        raise ValueError("Bill ID not found.")

    current_due_date = result[0]
    new_due_date = current_due_date + relativedelta(months=1)

    # Update status and due_date
    cur.execute("""
        UPDATE monthly_bills 
        SET status = 'carried_over', due_date = %s 
        WHERE id = %s
    """, (new_due_date, bill_id))

    conn.commit()
    cur.close()
    conn.close()


def create_bill_for_order(user_id, order_id, total_amount,delivery_status):
    conn = get_connection()
    cur = conn.cursor()
    today = datetime.date.today()
    bill_month = today.replace(day=1)
    next_month = bill_month.replace(day=28) + datetime.timedelta(days=4)
    due_date = next_month - datetime.timedelta(days=next_month.day)
    cur.execute("INSERT INTO monthly_bills (user_id, order_id, bill_month, total_amount, pending_amount, status, due_date) VALUES (%s, %s, %s, %s, %s, %s, %s)", (user_id, order_id, bill_month, total_amount, total_amount, delivery_status, due_date))
    conn.commit()
    cur.close()
    conn.close()

def init_db_schema():
    try:
        conn = get_connection()
        cur = conn.cursor()
        cur.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INT AUTO_INCREMENT PRIMARY KEY,
                name VARCHAR(100),
                phone_number VARCHAR(20) NOT NULL UNIQUE,
                language VARCHAR(10),
                address VARCHAR(255),
                onboarded TINYINT(1) DEFAULT 0
            )
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS user_context (
                phone VARCHAR(20) PRIMARY KEY,
                context_json TEXT
            )
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS sellers (
                id INT AUTO_INCREMENT PRIMARY KEY,
                phone_number VARCHAR(20) NOT NULL UNIQUE,
                password_hash VARCHAR(255) NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS seller_sessions (
                phone_number VARCHAR(20) PRIMARY KEY,
                login_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS admin_alerts (
                id INT AUTO_INCREMENT PRIMARY KEY,
                alert_type VARCHAR(50) NOT NULL,
                message TEXT,
                user_phone VARCHAR(20),
                resolved TINYINT(1) DEFAULT 0,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                order_id VARCHAR(255)
            )
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS orders (
                id INT AUTO_INCREMENT PRIMARY KEY,
                user_id INT NOT NULL,
                order_id VARCHAR(50) NOT NULL UNIQUE,
                product_summary TEXT,
                address VARCHAR(255),
                delivery_status VARCHAR(50),
                payment_status VARCHAR(50),
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                price DECIMAL(10,2),
                is_billed TINYINT(1) DEFAULT 0
            )
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS monthly_bills (
                id INT AUTO_INCREMENT PRIMARY KEY,
                user_id INT NOT NULL,
                order_id VARCHAR(50),
                bill_month DATE NOT NULL,
                total_amount DECIMAL(10,2) NOT NULL,
                pending_amount DECIMAL(10,2) NOT NULL,
                status VARCHAR(50) NOT NULL,
                due_date DATE NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
            )
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS credit_history (
                id INT AUTO_INCREMENT PRIMARY KEY,
                user_id INT NOT NULL,
                order_id VARCHAR(50),
                amount DECIMAL(10,2) NOT NULL,
                status VARCHAR(50),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS products (
                id INT AUTO_INCREMENT PRIMARY KEY,
                sku VARCHAR(50) UNIQUE,
                name VARCHAR(255) NOT NULL,
                description TEXT,
                price DECIMAL(10,2) NOT NULL,
                image_url VARCHAR(255),
                stock INT DEFAULT 0
            )
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS carts (
                id INT AUTO_INCREMENT PRIMARY KEY,
                user_phone VARCHAR(20) NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS cart_items (
                id INT AUTO_INCREMENT PRIMARY KEY,
                cart_id INT NOT NULL,
                product_id INT NOT NULL,
                quantity INT NOT NULL,
                UNIQUE(cart_id, product_id)
            )
        """)
        conn.commit()
        cur.close()
        conn.close()
    except Exception as e:
        print("DB Error in init_db_schema:", e)

def get_products():
    conn = get_connection()
    cur = conn.cursor(dictionary=True)
    cur.execute("SELECT id, sku, name, description, price, image_url, stock FROM products ORDER BY name")
    rows = cur.fetchall()
    cur.close()
    conn.close()
    return rows

def update_cart_item(phone, product_id, delta):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT id FROM carts WHERE user_phone = %s ORDER BY id DESC LIMIT 1", (phone,))
    row = cur.fetchone()
    if row:
        cart_id = row[0]
    else:
        cur.execute("INSERT INTO carts (user_phone) VALUES (%s)", (phone,))
        conn.commit()
        cart_id = cur.lastrowid

    cur.execute("SELECT id, quantity FROM cart_items WHERE cart_id = %s AND product_id = %s", (cart_id, product_id))
    existing = cur.fetchone()
    if existing:
        item_id, qty = existing
        new_qty = qty + delta
        if new_qty <= 0:
            cur.execute("DELETE FROM cart_items WHERE id = %s", (item_id,))
        else:
            cur.execute("UPDATE cart_items SET quantity = %s WHERE id = %s", (new_qty, item_id))
    else:
        if delta > 0:
            cur.execute("INSERT INTO cart_items (cart_id, product_id, quantity) VALUES (%s, %s, %s)", (cart_id, product_id, delta))

    conn.commit()
    cur.close()
    conn.close()

def get_cart(phone):
    conn = get_connection()
    cur = conn.cursor(dictionary=True)
    cur.execute("""
        SELECT ci.product_id, p.name, p.price, p.image_url, p.description, ci.quantity
        FROM carts c
        JOIN cart_items ci ON ci.cart_id = c.id
        JOIN products p ON p.id = ci.product_id
        WHERE c.user_phone = %s
    """, (phone,))
    rows = cur.fetchall()
    cur.close()
    conn.close()
    return rows

def clear_cart(phone):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT id FROM carts WHERE user_phone = %s", (phone,))
    carts = cur.fetchall()
    for (cart_id,) in carts:
        cur.execute("DELETE FROM cart_items WHERE cart_id = %s", (cart_id,))
        cur.execute("DELETE FROM carts WHERE id = %s", (cart_id,))
    conn.commit()
    cur.close()
    conn.close()

init_db_schema()