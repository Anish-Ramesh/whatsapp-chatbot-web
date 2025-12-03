# --- FILE: utils.py ---
import os
import requests
from dotenv import load_dotenv
load_dotenv()

import requests
from db import *

language_map = {
    1: ('English', 'en'), 2: ('French', 'fr'), 3: ('Spanish', 'es'),
    4: ('German', 'de'), 5: ('Italian', 'it'), 6: ('Portuguese', 'pt'),
    7: ('Russian', 'ru'), 8: ('Chinese (Simplified)', 'zh'),
    9: ('Japanese', 'ja'), 10: ('Korean', 'ko'), 11: ('Hindi', 'hi'),
    12: ('Tamil', 'ta'), 13: ('Telugu', 'te'), 14: ('Bengali', 'bn'),
    15: ('Gujarati', 'gu'), 16: ('Kannada', 'kn'), 17: ('Malayalam', 'ml'),
    18: ('Marathi', 'mr'), 19: ('Punjabi', 'pa'), 20: ('Urdu', 'ur'),
    21: ('Arabic', 'ar'), 22: ('Turkish', 'tr'), 23: ('Vietnamese', 'vi'),
    24: ('Thai', 'th'), 25: ('Dutch', 'nl'), 26: ('Greek', 'el'),
    27: ('Hebrew', 'iw'), 28: ('Polish', 'pl'), 29: ('Ukrainian', 'uk'),
    30: ('Romanian', 'ro')
}

def translate_text(text, target_lang):

    if not target_lang or target_lang.lower() in ("en", "eng", "english"):
        return text

    url = "https://google-translate113.p.rapidapi.com/api/v1/translator/json"

    payload = {
        "from": "auto",
        "to": target_lang,
        "protected_paths": ["extra.last_comment.author"],
        "common_protected_paths": ["image"],
        "json": {
            "translate": text
            }
        }
    
    headers = {
        "x-rapidapi-key": "2554ce5c9cmsh0d8e9c3b6c30b14p1869ffjsnfbd011f847ed",
        "x-rapidapi-host": "google-translate113.p.rapidapi.com",
        "Content-Type": "application/json"
    }

    response = requests.post(url, json=payload, headers=headers)

    t = response.json()
    t1 = t['trans']['translate']
    return t1
 
WEB_MESSAGES = []

def format_phone_number(phone):
    phone = str(phone).strip().replace(" ", "").replace("-", "")
    if not phone.startswith("+"):
        phone = "+" + phone
    return phone

def send_text_with_buttons(phone, text, buttons):
    phone = format_phone_number(phone)
    # Fetch user language
    lang = get_user_language(phone)
    translated_text = translate_text(text, lang)
    WEB_MESSAGES.append({
        "phone": phone,
        "type": "buttons",
        "text": translated_text,
        "buttons": buttons
    })
    print("send_text_with_buttons (web):", translated_text)

def send_text(phone, msg):
    phone = format_phone_number(phone)
    # Fetch user language
    lang = get_user_language(phone) 
    translated_msg = translate_text(msg, lang)
    WEB_MESSAGES.append({
        "phone": phone,
        "type": "text",
        "text": translated_msg
    })
    print("send_text (web):", translated_msg)

# --- Catalog: delegate to web UI ---

def send_product_list(phone):
    send_text(phone, "🛍️ To browse products, please use the Catalog button in the web chat above.")