# --- FILE: app.py ---
from flask import Flask, request, render_template, jsonify, redirect, url_for, session
from handlers import handle_message, place_order_from_catalog
import os
from dotenv import load_dotenv
from utils import WEB_MESSAGES, format_phone_number
from db import check_seller_password, get_products, update_cart_item, get_cart, clear_cart, get_connection, register_seller, is_seller
import openpyxl

load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv("FLASK_SECRET_KEY", "dev-secret-key")
VERIFY_TOKEN = os.getenv("VERIFY_TOKEN")  

@app.route('/', methods=['GET'])
def index():
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    error = None
    if request.method == 'POST':
        role = request.form.get('role') or 'user'
        phone = (request.form.get('phone') or '').strip()
        name = (request.form.get('name') or '').strip()
        admin_password = (request.form.get('admin_password') or '').strip()
        if not phone:
            error = 'Phone is required'
        elif role == 'admin':
            if admin_password != 'pass123':
                error = 'Invalid admin password'
            else:
                session['role'] = 'admin'
                session['phone'] = phone
                session['name'] = name
                session['admin_phone'] = phone
                try:
                    # Only create a seller with the default password if this phone
                    # is not already a seller, so that password changes are preserved.
                    if not is_seller(phone):
                        register_seller(phone, 'pass123')
                except Exception as e:
                    print(f"[WARN] register_seller failed in login: {e}")
                return redirect(url_for('admin'))
        else:
            session['role'] = 'user'
            session['phone'] = phone
            session['name'] = name
            return redirect(url_for('chat_page'))

    else:
        if session.get('role') == 'admin':
            return redirect(url_for('admin'))
        if session.get('role') == 'user' and session.get('phone'):
            return redirect(url_for('chat_page'))
    return render_template('login.html', error=error)

@app.route('/chat', methods=['GET'])
def chat_page():
    phone = session.get('phone')
    name = session.get('name') or ''
    if not phone:
        return redirect(url_for('login'))
    return render_template('chat.html', initial_phone=phone, initial_name=name, role=session.get('role', 'user'))

@app.route('/logout', methods=['GET'])
def logout():
    session.clear()
    return redirect(url_for('login'))

@app.route('/chat/send', methods=['POST'])
def chat_send():
    try:
        data = request.get_json(silent=True) or request.form
        phone = (data.get('phone') or '').strip()
        text = (data.get('text') or '').strip()
        button_id = (data.get('button_id') or '').strip()
        if not phone:
            return jsonify({"error": "phone is required"}), 400
        if not text and not button_id:
            return jsonify({"error": "text is required"}), 400
        msg = {"from": phone}
        if text:
            msg["text"] = {"body": text}
        if button_id:
            msg["interactive"] = {"button_reply": {"id": button_id}}

        payload = {
            "entry": [
                {
                    "changes": [
                        {
                            "value": {
                                "messages": [msg]
                            }
                        }
                    ]
                }
            ]
        }
        handle_message(payload)

        phone_fmt = format_phone_number(phone)
        messages = [m for m in WEB_MESSAGES if m.get("phone") == phone_fmt]
        return jsonify({"messages": messages}), 200
    except Exception as e:
        print(f"[ERROR] Exception in chat_send: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/chat/messages', methods=['GET'])
def chat_messages():
    try:
        phone = (request.args.get('phone') or '').strip()
        if not phone:
            return jsonify({"error": "phone is required"}), 400
        phone_fmt = format_phone_number(phone)
        messages = [m for m in WEB_MESSAGES if m.get("phone") == phone_fmt]
        return jsonify({"messages": messages}), 200
    except Exception as e:
        print(f"[ERROR] Exception in chat_messages: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/products', methods=['GET'])
def api_products():
    try:
        products = get_products()
        return jsonify({"products": products}), 200
    except Exception as e:
        print(f"[ERROR] Exception in api_products: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/cart', methods=['GET'])
def api_cart():
    try:
        phone = (request.args.get('phone') or '').strip()
        if not phone:
            return jsonify({"error": "phone is required"}), 400
        items = get_cart(phone)
        total = sum(float(item['price']) * int(item['quantity']) for item in items) if items else 0.0
        return jsonify({"items": items, "total": total}), 200
    except Exception as e:
        print(f"[ERROR] Exception in api_cart: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/cart/update', methods=['POST'])
def api_cart_update():
    try:
        data = request.get_json(silent=True) or {}
        phone = (data.get('phone') or '').strip()
        product_id = data.get('product_id')
        delta = int(data.get('delta') or 0)
        if not phone or not product_id or delta == 0:
            return jsonify({"error": "phone, product_id and non-zero delta are required"}), 400
        update_cart_item(phone, int(product_id), delta)
        items = get_cart(phone)
        total = sum(float(item['price']) * int(item['quantity']) for item in items) if items else 0.0
        return jsonify({"items": items, "total": total}), 200
    except Exception as e:
        print(f"[ERROR] Exception in api_cart_update: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/cart/checkout', methods=['POST'])
def api_cart_checkout():
    try:
        data = request.get_json(silent=True) or {}
        phone = (data.get('phone') or '').strip()
        if not phone:
            return jsonify({"error": "phone is required"}), 400
        items = get_cart(phone)
        if not items:
            return jsonify({"error": "cart is empty"}), 400
        order_data = {
            "product_items": [
                {
                    "product_retailer_id": str(item['product_id']),
                    "item_price": str(item['price']),
                    "quantity": int(item['quantity'])
                } for item in items
            ]
        }
        place_order_from_catalog(phone, order_data)
        clear_cart(phone)
        return jsonify({"status": "ok"}), 200
    except Exception as e:
        print(f"[ERROR] Exception in api_cart_checkout: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/admin', methods=['GET', 'POST'])
def admin():
    if session.get('role') != 'admin' or not session.get('phone'):
        return redirect(url_for('login'))
    error = None
    if request.method == 'POST' and 'file' in request.files:
        file = request.files['file']
        if file and file.filename:
            wb = openpyxl.load_workbook(file)
            sheet = wb.active
            conn = get_connection()
            cur = conn.cursor()
            first = True
            for row in sheet.iter_rows(values_only=True):
                if first:
                    first = False
                    continue
                name, price, image_url, description, stock, sku = (row + (None,)*6)[:6]
                if not name or price is None:
                    continue
                cur.execute("""
                    INSERT INTO products (sku, name, description, price, image_url, stock)
                    VALUES (%s, %s, %s, %s, %s, %s)
                    ON DUPLICATE KEY UPDATE
                        name = VALUES(name),
                        description = VALUES(description),
                        price = VALUES(price),
                        image_url = VALUES(image_url),
                        stock = VALUES(stock)
                """, (sku, name, description, float(price), image_url, int(stock or 0)))
            conn.commit()
            cur.close()
            conn.close()
    return render_template('admin.html', error=error, logged_in=True)

@app.route('/webhook', methods=['GET'])
def verify():
    mode = request.args.get("hub.mode")
    token = request.args.get("hub.verify_token")
    challenge = request.args.get("hub.challenge")

    if mode == "subscribe" and token == VERIFY_TOKEN:
        print("Webhook verified successfully.")
        return challenge, 200
    else:
        return "Verification failed", 403

@app.route('/webhook', methods=['POST'])
def webhook():
    try:
        print("[WEBHOOK] POST received")
        data = request.get_json(force=True, silent=True)
        if not data:
            print("[ERROR] No JSON payload received!")
            return "No JSON payload", 400
        handle_message(data)
        return "OK", 200
    except Exception as e:
        print(f"[ERROR] Exception in webhook: {e}")
        return f"Webhook error: {e}", 500

if __name__ == '__main__':
    app.run(port=8080, use_reloader=False)
