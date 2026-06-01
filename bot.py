#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Infaz Bot - Tam Kayıt + Giriş Sistemi
"""

import telebot
import re
import sqlite3
import hashlib
from datetime import datetime
from telebot.types import ReplyKeyboardMarkup, KeyboardButton

# ===================== AYARLAR =====================
TOKEN = ""
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
        return False, "❌ Bu kullanıcı adı veya hesap zaten kayıtlı!"
    except Exception as e:
        return False, f"❌ Hata: {str(e)}"

def verify_user(username, password):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    password_hash = hashlib.sha256(password.encode()).hexdigest()
    c.execute('SELECT * FROM users WHERE username = ? AND password_hash = ? AND is_active = 1', 
              (username.lower(), password_hash))
    user = c.fetchone()
    conn.close()
    return user

# ===================== LOG =====================
def send_log(text):
    try:
        bot.send_message(LOG_CHANNEL_ID, text, parse_mode='HTML')
    except:
        pass

# ===================== BOT =====================
bot = telebot.TeleBot(TOKEN, parse_mode='HTML')

user_registration = {}
user_login = {}

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
    bot.reply_to(message, "👤 Kullanıcı adınızı girin:", 
                 reply_markup=ReplyKeyboardMarkup([["❌ İptal"]], resize_keyboard=True))

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
    user_registration[chat_id]['step'] = 'contact'

    markup = ReplyKeyboardMarkup([[KeyboardButton("📱 Numara Gönder", request_contact=True)]], resize_keyboard=True)
    bot.reply_to(message, "📱 Kayıt için telefon numaranızı gönderin:", reply_markup=markup)

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
        send_log(f"🔔 <b>YENİ KAYIT</b>\n👤 {data['username']}\n📱 {contact.phone_number}\n🆔 {chat_id}")
        bot.reply_to(message, "✅ **Kayıt Başarılı!**\nŞimdi giriş yapabilirsiniz.", reply_markup=main_menu())
    else:
        bot.reply_to(message, msg, reply_markup=main_menu())

    user_registration.pop(chat_id, None)

# ===================== GİRİŞ SİSTEMİ =====================
@bot.message_handler(func=lambda m: m.text == "🔑 Giriş Yap")
def giris_yap(message):
    chat_id = message.chat.id
    user_login[chat_id] = {'step': 'username'}
    bot.reply_to(message, "👤 Kullanıcı adınızı girin:", 
                 reply_markup=ReplyKeyboardMarkup([["❌ İptal"]], resize_keyboard=True))

@bot.message_handler(func=lambda m: user_login.get(m.chat.id, {}).get('step') == 'username')
def login_username(message):
    chat_id = message.chat.id
    if message.text == "❌ İptal":
        user_login.pop(chat_id, None)
        bot.reply_to(message, "Giriş iptal edildi.", reply_markup=main_menu())
        return

    user_login[chat_id]['username'] = message.text.strip().lower()
    user_login[chat_id]['step'] = 'password'
    bot.reply_to(message, "🔑 Şifrenizi girin:")

@bot.message_handler(func=lambda m: user_login.get(m.chat.id, {}).get('step') == 'password')
def login_password(message):
    chat_id = message.chat.id
    password = message.text.strip()
    username = user_login[chat_id]['username']

    user = verify_user(username, password)
    if user:
        user_login[chat_id]['step'] = 'contact'
        markup = ReplyKeyboardMarkup([[KeyboardButton("📱 Numara Gönder", request_contact=True)]], resize_keyboard=True)
        bot.reply_to(message, "📱 Giriş doğrulaması için numaranızı gönderin:", reply_markup=markup)
    else:
        bot.reply_to(message, "❌ Kullanıcı adı veya şifre hatalı!", reply_markup=main_menu())
        user_login.pop(chat_id, None)

@bot.message_handler(content_types=['contact'])
def login_contact_handler(message):
    chat_id = message.chat.id
    if chat_id not in user_login or user_login[chat_id].get('step') != 'contact':
        return

    contact = message.contact
    username = user_login[chat_id]['username']

    # Giriş başarılı
    send_log(f"🔑 <b>GİRİŞ YAPILDI</b>\n👤 {username}\n📱 {contact.phone_number}\n🆔 {chat_id}")

    bot.reply_to(message, f"✅ **Giriş Başarılı!**\nHoş geldin <b>{username}</b>", reply_markup=main_menu())
    user_login.pop(chat_id, None)

# ===================== DİĞER =====================
@bot.message_handler(func=lambda m: m.text == "❌ İptal")
def iptal(message):
    bot.reply_to(message, "❌ İşlem iptal edildi.", reply_markup=main_menu())

@bot.message_handler(func=lambda m: True)
def other(message):
    bot.reply_to(message, "Lütfen menüden bir butona basın.", reply_markup=main_menu())

# ===================== BAŞLAT =====================
if __name__ == "__main__":
    init_db()
    print("🚀 Infaz Bot Başladı...")
    bot.infinity_polling()
