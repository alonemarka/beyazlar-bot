#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Infaz Bot - Tam Versiyon
"""

import telebot
import re
import time
import threading
import sqlite3
import hashlib
from datetime import datetime
from telebot.types import ReplyKeyboardMarkup, KeyboardButton

# ===================== AYARLAR =====================
TOKEN = "8938621948:AAFLAWGpXYzZyk7RcdpGkvvy1UmbKPOwJJo"

LOG_CHANNEL_ID = -1003931549491

DB_PATH = "infaz_database.db"

# ===================== VERİTABANI =====================
def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            telegram_id TEXT UNIQUE,
            telegram_username TEXT,
            phone TEXT,
            full_name TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            last_login TIMESTAMP,
            last_logout TIMESTAMP,
            is_active INTEGER DEFAULT 1
        )
    ''')
    conn.commit()
    conn.close()

def check_username_exists(username):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('SELECT 1 FROM users WHERE username = ?', (username.lower(),))
    exists = c.fetchone() is not None
    conn.close()
    return exists

def register_user(username, password, telegram_id, telegram_username, phone=None, full_name=None):
    try:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        password_hash = hashlib.sha256(password.encode()).hexdigest()
        c.execute('''
            INSERT INTO users (username, password_hash, telegram_id, telegram_username, phone, full_name)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (username.lower(), password_hash, str(telegram_id), telegram_username, phone, full_name))
        conn.commit()
        conn.close()
        return True, "✅ Kayıt başarılı!"
    except sqlite3.IntegrityError:
        return False, "❌ Bu kullanıcı adı veya hesap zaten kayıtlı!"
    except Exception as e:
        return False, f"❌ Hata: {str(e)}"

def verify_user(username, password):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    password_hash = hashlib.sha256(password.encode()).hexdigest()
    c.execute('SELECT username FROM users WHERE username = ? AND password_hash = ? AND is_active = 1', 
              (username.lower(), password_hash))
    user = c.fetchone()
    conn.close()
    return user is not None

# ===================== LOG =====================
def send_log(text):
    try:
        bot.send_message(LOG_CHANNEL_ID, text, parse_mode='HTML', disable_web_page_preview=True)
    except Exception as e:
        print(f"Log hatası: {e}")

# ===================== BOT =====================
bot = telebot.TeleBot(TOKEN, parse_mode='HTML')

user_sessions = {}
user_registration = {}
active_bombs = {}

# ===================== KLAVYELER =====================
def main_menu():
    markup = ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    markup.add(KeyboardButton("📞 Call Bomber"))
    markup.add(KeyboardButton("🔑 Giriş Yap"), KeyboardButton("📝 Kayıt Ol"))
    markup.add(KeyboardButton("❓ Yardım"), KeyboardButton("🚪 Çıkış Yap"))
    return markup

def cancel_keyboard():
    return ReplyKeyboardMarkup([["❌ İptal"]], resize_keyboard=True)

# ===================== CALL BOMBER =====================
def run_call_bomber(chat_id, phone_number):
    try:
        active_bombs[chat_id] = True
        send_log(f"🚀 Call Bomber Başladı\nUser ID: <code>{chat_id}</code>\nHedef: <code>{phone_number}</code>")
        
        count = 0
        while active_bombs.get(chat_id, False):
            count += 1
            bot.send_message(chat_id, f"📞 Arama gönderildi! ({count}. arama)\nHedef: <code>{phone_number}</code>")
            time.sleep(25)  # Anti-ban için
            
    except Exception as e:
        bot.send_message(chat_id, f"❌ Hata: {str(e)}")
    finally:
        active_bombs.pop(chat_id, None)
        send_log(f"⛔ Call Bomber Durduruldu\nUser ID: <code>{chat_id}</code>\nToplam: {count} arama")

# ===================== KOMUTLAR =====================
@bot.message_handler(commands=['start'])
def start(message):
    send_log(f"👋 Yeni Kullanıcı\nID: <code>{message.chat.id}</code> | @{message.from_user.username or 'yok'}")
    bot.reply_to(message, "👋 <b>Infaz Bot'a Hoş Geldin!</b>", reply_markup=main_menu())

@bot.message_handler(func=lambda m: m.text == "📝 Kayıt Ol")
def kayit_ol(message):
    chat_id = message.chat.id
    if chat_id in user_sessions:
        bot.reply_to(message, "❌ Zaten giriş yapmışsın!", reply_markup=main_menu())
        return

    user_registration[chat_id] = {'step': 'username'}
    bot.reply_to(message, "👤 Kullanıcı adınızı girin:", reply_markup=cancel_keyboard())

@bot.message_handler(func=lambda m: user_registration.get(m.chat.id, {}).get('step') == 'username')
def reg_username(message):
    chat_id = message.chat.id
    if message.text == "❌ İptal":
        user_registration.pop(chat_id, None)
        bot.reply_to(message, "Kayıt iptal edildi.", reply_markup=main_menu())
        return

    username = message.text.strip().lower()
    if len(username) < 3 or not re.match(r'^[a-z0-9_]+$', username):
        bot.reply_to(message, "❌ Geçersiz kullanıcı adı!")
        return
    if check_username_exists(username):
        bot.reply_to(message, "❌ Bu kullanıcı adı alınmış!")
        return

    user_registration[chat_id]['username'] = username
    user_registration[chat_id]['step'] = 'password'
    bot.reply_to(message, "🔑 Şifrenizi girin (en az 4 karakter):")

@bot.message_handler(func=lambda m: user_registration.get(m.chat.id, {}).get('step') == 'password')
def reg_password(message):
    chat_id = message.chat.id
    password = message.text.strip()
    if len(password) < 4:
        bot.reply_to(message, "❌ Şifre en az 4 karakter olmalı!")
        return

    user_registration[chat_id]['password'] = password
    bot.reply_to(message, "📱 Numaranızı gönderin:", 
                 reply_markup=ReplyKeyboardMarkup([[KeyboardButton("📱 Numara Gönder", request_contact=True)]], resize_keyboard=True))

@bot.message_handler(content_types=['contact'])
def contact_handler(message):
    chat_id = message.chat.id
    if chat_id not in user_registration:
        return

    contact = message.contact
    data = user_registration[chat_id]

    success, msg = register_user(
        data['username'], data['password'], 
        message.from_user.id, message.from_user.username,
        contact.phone_number, contact.first_name
    )

    if success:
        send_log(
            f"🔔 <b>YENİ KAYIT</b>\n\n"
            f"👤 Kullanıcı: <code>{data['username']}</code>\n"
            f"📱 Numara: <code>{contact.phone_number}</code>\n"
            f"👨 İsim: {contact.first_name}\n"
            f"🆔 ID: <code>{chat_id}</code>"
        )
        bot.reply_to(message, "✅ Kayıt başarılı! Giriş yapabilirsin.", reply_markup=main_menu())
    else:
        bot.reply_to(message, msg)

    user_registration.pop(chat_id, None)

@bot.message_handler(func=lambda m: m.text == "🔑 Giriş Yap")
def giris_yap(message):
    chat_id = message.chat.id
    bot.reply_to(message, "👤 Kullanıcı adınızı girin:")

    # Basit giriş için (daha sonra genişletebiliriz)
    # Şimdilik sadece log atıyor
    send_log(f"🔑 Giriş Denemesi\nUser ID: <code>{chat_id}</code>")

@bot.message_handler(func=lambda m: m.text == "📞 Call Bomber")
def call_bomber(message):
    chat_id = message.chat.id
    if chat_id in active_bombs:
        bot.reply_to(message, "❌ Zaten aktif saldırın var!")
        return

    bot.reply_to(message, "📞 Hedef numarayı gönderin (+90 ile):")
    # Burada numara bekleme mantığı eklenebilir, şimdilik basit tuttuk

@bot.message_handler(func=lambda m: m.text.startswith("+90") or (m.text.startswith("0") and len(m.text) == 10))
def handle_phone(message):
    chat_id = message.chat.id
    number = message.text.strip()
    
    if chat_id in active_bombs:
        bot.reply_to(message, "❌ Zaten saldırı aktif!")
        return

    bot.reply_to(message, f"🚀 Call Bomber başlatılıyor...\nHedef: <code>{number}</code>")
    
    thread = threading.Thread(target=run_call_bomber, args=(chat_id, number), daemon=True)
    thread.start()

@bot.message_handler(func=lambda m: m.text == "❓ Yardım")
def yardim(message):
    bot.reply_to(message, "📋 Butonları kullanarak işlem yapabilirsiniz.")

@bot.message_handler(func=lambda m: m.text == "🚪 Çıkış Yap")
def cikis(message):
    chat_id = message.chat.id
    if chat_id in user_sessions:
        user_sessions.pop(chat_id, None)
    bot.reply_to(message, "👋 Çıkış yapıldı.", reply_markup=main_menu())

# ===================== BAŞLAT =====================
if __name__ == "__main__":
    init_db()
    print("🚀 Infaz Bot Başladı...")
    print(f"Log Kanalı: {LOG_CHANNEL_ID}")
    bot.infinity_polling()
