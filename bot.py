#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Infaz Bot - Temiz Kayıt Sistemi
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

def register_user(username, password, telegram_id, telegram_username, phone, full_name):
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
        return False, "❌ Bu kullanıcı adı veya Telegram hesabı zaten kayıtlı!"
    except Exception as e:
        return False, f"❌ Hata: {str(e)}"

# ===================== LOG =====================
def send_log(text):
    try:
        bot.send_message(LOG_CHANNEL_ID, text, parse_mode='HTML')
    except:
        pass

# ===================== BOT =====================
bot = telebot.TeleBot(TOKEN, parse_mode='HTML')

user_registration = {}   # Sadece kayıt için

# ===================== KLAVYELER =====================
def main_menu():
    markup = ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    markup.add(KeyboardButton("📞 Call Bomber"))
    markup.add(KeyboardButton("🔑 Giriş Yap"), KeyboardButton("📝 Kayıt Ol"))
    markup.add(KeyboardButton("❓ Yardım"), KeyboardButton("🚪 Çıkış Yap"))
    return markup

# ===================== KAYIT SİSTEMİ =====================
@bot.message_handler(func=lambda m: m.text == "📝 Kayıt Ol")
def kayit_ol(message):
    chat_id = message.chat.id
    user_registration[chat_id] = {'step': 'username'}
    
    bot.reply_to(message, "👤 **Kayıt Ol**\n\nKullanıcı adınızı girin:", 
                 reply_markup=ReplyKeyboardMarkup([["❌ İptal"]], resize_keyboard=True))

@bot.message_handler(func=lambda m: user_registration.get(m.chat.id, {}).get('step') == 'username')
def reg_username(message):
    chat_id = message.chat.id
    if message.text == "❌ İptal":
        user_registration.pop(chat_id, None)
        bot.reply_to(message, "❌ Kayıt iptal edildi.", reply_markup=main_menu())
        return

    username = message.text.strip().lower()
    if len(username) < 3 or not re.match(r'^[a-z0-9_]+$', username):
        bot.reply_to(message, "❌ Geçersiz kullanıcı adı! (küçük harf, rakam, _)")
        return
    if check_username_exists(username):
        bot.reply_to(message, "❌ Bu kullanıcı adı zaten alınmış!")
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
    user_registration[chat_id]['step'] = 'contact'

    markup = ReplyKeyboardMarkup([[KeyboardButton("📱 Numara Gönder", request_contact=True)]], resize_keyboard=True)
    bot.reply_to(message, "📱 Kayıt için numaranızı gönderin:", reply_markup=markup)

@bot.message_handler(content_types=['contact'])
def contact_handler(message):
    chat_id = message.chat.id
    
    if chat_id not in user_registration or user_registration[chat_id].get('step') != 'contact':
        bot.reply_to(message, "❌ Geçersiz işlem!", reply_markup=main_menu())
        return

    contact = message.contact
    data = user_registration[chat_id]

    success, msg = register_user(
        username=data['username'],
        password=data['password'],
        telegram_id=message.from_user.id,
        telegram_username=message.from_user.username,
        phone=contact.phone_number,
        full_name=contact.first_name
    )

    if success:
        send_log(
            f"🔔 <b>YENİ KAYIT</b>\n\n"
            f"👤 Kullanıcı: <code>{data['username']}</code>\n"
            f"📱 Numara: <code>{contact.phone_number}</code>\n"
            f"👨 İsim: {contact.first_name}\n"
            f"🆔 ID: <code>{chat_id}</code>\n"
            f"⏰ {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        )
        bot.reply_to(message, "✅ **Kayıt Başarılı!**\nArtık giriş yapabilirsin.", reply_markup=main_menu())
    else:
        bot.reply_to(message, msg, reply_markup=main_menu())

    user_registration.pop(chat_id, None)

# Diğer butonlar (geçici)
@bot.message_handler(func=lambda m: True)
def other_buttons(message):
    text = message.text
    if text == "❌ İptal":
        bot.reply_to(message, "İşlem iptal edildi.", reply_markup=main_menu())
    elif text in ["🔑 Giriş Yap", "📞 Call Bomber", "❓ Yardım", "🚪 Çıkış Yap"]:
        bot.reply_to(message, "Bu özellik yakında aktif edilecek.")
    else:
        bot.reply_to(message, "Lütfen menüden seçim yapın.", reply_markup=main_menu())

# ===================== BAŞLAT =====================
if __name__ == "__main__":
    init_db()
    print("🚀 Infaz Bot Başladı...")
    bot.infinity_polling()
