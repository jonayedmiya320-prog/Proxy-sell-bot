import telebot
import requests
import json
import os
from datetime import datetime
import time

# ─────────────────────────────────────────────────────────────
#  CONFIG FILE  (all settings live here – editable at runtime)
# RydenX─────────────────────────────────────────────────────────────
CONFIG_FILE = "config.json"

DEFAULT_CONFIG = {
    "bot_token":          "8609593081:AAEHnIV9qvtZWNRKpK-57zVZHgD7owKQQ4A",
    "admin_id":           7095358778,
    "admin_set":          False,
    "smm_panel_url":      "",
    "smm_api_key":        "",

    # Rates
    "points_per_reaction": 10,
    "points_per_view":     100,
    "points_per_member":   1,
    "points_per_referral": 25,
    "daily_bonus_points":  10,

    # Service IDs
    "service_id_reactions": 476,
    "service_id_views":     500,
    "service_id_members":   470,

    # Logs channel (username without @ or chat_id as string)
    "logs_channel": "",

    # Force-join channels
    "channels": [
        {"name": "🌺 MAIN", "username": "SMM_BD_COM", "url": "https://t.me/SMM_BD_COM"},
        {"name": "🤖 JOIN", "username": "-1003788493595", "url": "https://t.me/SMM_BD_COM"}
    ],

    "qr_code_url": "https://t.me/C_T_A_2",
    "payment_contact": "@C_T_A_2",
    "bot_username": "SMM_BD_COM"
}


def load_config():
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, "r") as f:
            data = json.load(f)
        # Fill any missing keys from defaults
        for k, v in DEFAULT_CONFIG.items():
            if k not in data:
                data[k] = v
        return data
    else:
        save_config(DEFAULT_CONFIG)
        return DEFAULT_CONFIG.copy()


def save_config(cfg):
    with open(CONFIG_FILE, "w") as f:
        json.dump(cfg, f, indent=2)


cfg = load_config()

# ─────────────────────────────────────────────────────────────
#  BOT INIT
# ─────────────────────────────────────────────────────────────
bot = telebot.TeleBot(cfg["bot_token"], parse_mode="HTML")

# ─────────────────────────────────────────────────────────────
#  IN-MEMORY USER DATA
# ─────────────────────────────────────────────────────────────
user_balances        = {}   # {user_id: float}
user_last_bonus      = {}   # {user_id: date}
user_referrals       = {}   # {user_id: {"referrer": int, "rewarded": bool}}
users                = set()
gift_codes           = {}   # {code: points}
banned_users         = set()
user_redeemed_codes  = {}   # {user_id: set of codes}
user_orders          = {}   # {user_id: [order_dict]}
user_state           = {}   # FSM state per user

MAIN_COMMANDS = [
    "👍 Order Reactions", "👀 Order Views", "👥 Order Members",
    "💰 Check Balance", "🎁 Claim Bonus", "➕ Add Funds",
    "📢 Refer & Earn", "🔳 GiftCode", "💬 Feedback",
    "🖲 Track Order", "📜 Order History"
]

# ─────────────────────────────────────────────────────────────
#  HELPERS
# ─────────────────────────────────────────────────────────────
def is_admin(uid):
    return int(uid) == int(cfg["admin_id"])


def send_log(text, disable_preview=True):
    """Send message to logs channel if configured."""
    ch = cfg.get("logs_channel", "").strip()
    if not ch:
        return
    try:
        # Accept @username or numeric chat_id
        target = ch if ch.startswith("-") else ("@" + ch.lstrip("@"))
        bot.send_message(target, text, disable_web_page_preview=disable_preview)
    except Exception as e:
        print(f"[LOG CHANNEL ERROR] {e}")


def reload_cfg():
    global cfg
    cfg = load_config()


# ─────────────────────────────────────────────────────────────
#  SAFE WRAPPERS
# ─────────────────────────────────────────────────────────────
def safe_handler(func):
    def wrapper(message, *args, **kwargs):
        try:
            if not hasattr(message, 'text') and message.content_type != 'photo':
                bot.send_message(message.chat.id, "❌ Please send a text message.")
                return
            return func(message, *args, **kwargs)
        except Exception as e:
            print(f"[HANDLER ERROR] {func.__name__}: {e}")
            try:
                bot.send_message(message.chat.id, "❌ Something went wrong. Please try again.")
            except Exception:
                pass
    return wrapper


def safe_callback(func):
    def wrapper(call, *args, **kwargs):
        try:
            return func(call, *args, **kwargs)
        except Exception as e:
            print(f"[CALLBACK ERROR] {func.__name__}: {e}")
            try:
                bot.answer_callback_query(call.id, "❌ Something went wrong.")
            except Exception:
                pass
    return wrapper


def require_not_banned(func):
    def wrapper(message, *args, **kwargs):
        try:
            if message.chat.id in banned_users:
                bot.send_message(message.chat.id, "🚫 You are banned from using this bot.")
                return
            if message.text in MAIN_COMMANDS:
                user_state.pop(message.chat.id, None)
            return func(message, *args, **kwargs)
        except Exception as e:
            print(f"[BAN WRAPPER ERROR]: {e}")
    return wrapper


# ─────────────────────────────────────────────────────────────
#  KEYBOARDS  – USER RydenX
# ─────────────────────────────────────────────────────────────
def join_menu():
    markup = telebot.types.InlineKeyboardMarkup()
    channels = cfg["channels"]
    # Row 1 – first channel alone
    if channels:
        markup.add(telebot.types.InlineKeyboardButton(channels[0]["name"], url=channels[0]["url"]))
    # Pair remaining channels 2-per-row
    for i in range(1, len(channels), 2):
        row_btns = [telebot.types.InlineKeyboardButton(channels[i]["name"], url=channels[i]["url"])]
        if i + 1 < len(channels):
            row_btns.append(telebot.types.InlineKeyboardButton(channels[i+1]["name"], url=channels[i+1]["url"]))
        markup.row(*row_btns)
    markup.add(telebot.types.InlineKeyboardButton("✅ Joined", callback_data="joined"))
    return markup


def main_menu():
    markup = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.row("👍 Order Reactions", "👀 Order Views", "👥 Order Members")
    markup.row("💰 Check Balance", "🎁 Claim Bonus")
    markup.row("➕ Add Funds", "📢 Refer & Earn")
    markup.row("🔳 GiftCode", "💬 Feedback")
    markup.row("🖲 Track Order", "📜 Order History")
    return markup


# ─────────────────────────────────────────────────────────────
#  KEYBOARDS  – ADMIN PANEL
# ─────────────────────────────────────────────────────────────
def admin_panel_markup():
    mk = telebot.types.InlineKeyboardMarkup(row_width=2)
    mk.add(
        telebot.types.InlineKeyboardButton("📊 Stats",            callback_data="ap_stats"),
        telebot.types.InlineKeyboardButton("📢 Broadcast",        callback_data="ap_broadcast"),
    )
    mk.add(
        telebot.types.InlineKeyboardButton("🎁 Create GiftCode",  callback_data="ap_giftcode_create"),
        telebot.types.InlineKeyboardButton("🗑 Delete GiftCode",  callback_data="ap_giftcode_delete"),
    )
    mk.add(
        telebot.types.InlineKeyboardButton("➕ Add Balance",       callback_data="ap_add_balance"),
        telebot.types.InlineKeyboardButton("➖ Remove Balance",    callback_data="ap_remove_balance"),
    )
    mk.add(
        telebot.types.InlineKeyboardButton("💰 Check User Bal",   callback_data="ap_check_balance"),
        telebot.types.InlineKeyboardButton("🚫 Ban User",         callback_data="ap_ban"),
    )
    mk.add(
        telebot.types.InlineKeyboardButton("✅ Unban User",       callback_data="ap_unban"),
        telebot.types.InlineKeyboardButton("📋 List Banned",      callback_data="ap_list_banned"),
    )
    mk.add(
        telebot.types.InlineKeyboardButton("⚙️ Edit Rates",       callback_data="ap_rates"),
        telebot.types.InlineKeyboardButton("🔧 Edit Service IDs", callback_data="ap_service_ids"),
    )
    mk.add(
        telebot.types.InlineKeyboardButton("🔑 Edit API Key",     callback_data="ap_edit_apikey"),
        telebot.types.InlineKeyboardButton("📡 Set Logs Channel", callback_data="ap_set_logs"),
    )
    mk.add(
        telebot.types.InlineKeyboardButton("🌐 Edit SMM URL",     callback_data="ap_edit_smmurl"),
        telebot.types.InlineKeyboardButton("🖼 Edit QR URL",      callback_data="ap_edit_qr"),
    )
    mk.add(
        telebot.types.InlineKeyboardButton("👑 Transfer Admin",   callback_data="ap_transfer_admin"),
    )
    return mk


def rates_markup():
    mk = telebot.types.InlineKeyboardMarkup(row_width=2)
    mk.add(
        telebot.types.InlineKeyboardButton("👍 Reactions Rate",   callback_data="rate_reaction"),
        telebot.types.InlineKeyboardButton("👀 Views Rate",       callback_data="rate_view"),
    )
    mk.add(
        telebot.types.InlineKeyboardButton("👥 Members Rate",     callback_data="rate_member"),
        telebot.types.InlineKeyboardButton("🤝 Referral Points",  callback_data="rate_referral"),
    )
    mk.add(
        telebot.types.InlineKeyboardButton("🎁 Daily Bonus Pts",  callback_data="rate_bonus"),
    )
    mk.add(telebot.types.InlineKeyboardButton("🔙 Back",          callback_data="ap_back"))
    return mk


def service_ids_markup():
    mk = telebot.types.InlineKeyboardMarkup(row_width=1)
    mk.add(
        telebot.types.InlineKeyboardButton(
            f"👍 Reactions ID  (current: {cfg['service_id_reactions']})",
            callback_data="sid_reactions"
        ),
        telebot.types.InlineKeyboardButton(
            f"👀 Views ID  (current: {cfg['service_id_views']})",
            callback_data="sid_views"
        ),
        telebot.types.InlineKeyboardButton(
            f"👥 Members ID  (current: {cfg['service_id_members']})",
            callback_data="sid_members"
        ),
    )
    mk.add(telebot.types.InlineKeyboardButton("🔙 Back", callback_data="ap_back"))
    return mk


# ─────────────────────────────────────────────────────────────
#  /setadmin  – first-run admin claim RydenX
# ─────────────────────────────────────────────────────────────
@bot.message_handler(commands=['setadmin'])
@safe_handler
def set_admin_cmd(message):
    reload_cfg()
    uid = message.chat.id
    if cfg.get("admin_set") and int(cfg["admin_id"]) != 0:
        if is_admin(uid):
            bot.send_message(uid, "👑 You are already the admin!")
        else:
            bot.send_message(uid, "❌ Admin is already set. Contact current admin.")
        return
    # First person to call /setadmin becomes admin
    cfg["admin_id"] = uid
    cfg["admin_set"] = True
    save_config(cfg)
    bot.send_message(uid,
        "👑 <b>You are now the PERMANENT ADMIN!</b>\n\nUse /admin to open your control panel.",
        reply_markup=main_menu()
    )


# ─────────────────────────────────────────────────────────────
#  /admin  – open admin panel
# ─────────────────────────────────────────────────────────────
@bot.message_handler(commands=['admin'])
@safe_handler
def admin_panel(message):
    reload_cfg()
    if not is_admin(message.chat.id):
        return
    bot.send_message(
        message.chat.id,
        "👑 <b>ADMIN CONTROL PANEL</b>\n\nSelect an action below:",
        reply_markup=admin_panel_markup()
    )


# ─────────────────────────────────────────────────────────────
#  ADMIN PANEL CALLBACKS
# ─────────────────────────────────────────────────────────────
@bot.callback_query_handler(func=lambda c: c.data.startswith("ap_") or c.data.startswith("rate_") or c.data.startswith("sid_"))
@safe_callback
def admin_callback(call):
    reload_cfg()
    uid = call.message.chat.id
    if not is_admin(uid):
        bot.answer_callback_query(call.id, "❌ Not authorized.")
        return

    data = call.data

    # ── Back to main panel ──
    if data == "ap_back":
        bot.edit_message_text(
            "👑 <b>ADMIN CONTROL PANEL</b>\n\nSelect an action below:",
            uid, call.message.message_id,
            reply_markup=admin_panel_markup()
        )
        return

    # ── Stats ──
    if data == "ap_stats":
        total_users   = len(users)
        banned_count  = len(banned_users)
        gift_count    = len(gift_codes)
        total_orders  = sum(len(v) for v in user_orders.values())
        total_balance = sum(user_balances.values())
        text = (
            f"📊 <b>BOT STATISTICS</b>\n\n"
            f"👥 Total Users: <b>{total_users}</b>\n"
            f"🚫 Banned Users: <b>{banned_count}</b>\n"
            f"🎁 Active Gift Codes: <b>{gift_count}</b>\n"
            f"🛒 Total Orders: <b>{total_orders}</b>\n"
            f"💰 Total Points Held: <b>{total_balance:.0f}</b>\n\n"
            f"⚙️ <b>Current Settings</b>\n"
            f"👍 Reactions Rate: {cfg['points_per_reaction']} units/pt\n"
            f"👀 Views Rate: {cfg['points_per_view']} units/pt\n"
            f"👥 Members Rate: {cfg['points_per_member']} units/pt\n"
            f"🤝 Referral Points: {cfg['points_per_referral']}\n"
            f"🎁 Daily Bonus: {cfg['daily_bonus_points']}\n"
            f"📡 Logs Channel: {cfg.get('logs_channel') or 'Not Set'}"
        )
        mk = telebot.types.InlineKeyboardMarkup()
        mk.add(telebot.types.InlineKeyboardButton("🔙 Back", callback_data="ap_back"))
        bot.edit_message_text(text, uid, call.message.message_id, reply_markup=mk)
        return

    # ── Broadcast ──
    if data == "ap_broadcast":
        user_state[uid] = {"action": "admin_broadcast"}
        mk = telebot.types.InlineKeyboardMarkup()
        mk.add(telebot.types.InlineKeyboardButton("❌ Cancel", callback_data="ap_back"))
        bot.edit_message_text(
            "📢 <b>Broadcast</b>\n\nSend your message now.\nSupports text, photos, videos, stickers.\n\n<i>Reply or just send your next message.</i>",
            uid, call.message.message_id, reply_markup=mk
        )
        bot.register_next_step_handler(call.message, process_admin_broadcast)
        return

    # ── Gift code – create ──
    if data == "ap_giftcode_create":
        user_state[uid] = {"action": "admin_gc_create", "step": "code"}
        mk = telebot.types.InlineKeyboardMarkup()
        mk.add(telebot.types.InlineKeyboardButton("❌ Cancel", callback_data="ap_back"))
        bot.edit_message_text(
            "🎁 <b>Create Gift Code</b>\n\nStep 1/2 – Enter the gift code text:",
            uid, call.message.message_id, reply_markup=mk
        )
        bot.register_next_step_handler(call.message, process_gc_create_step)
        return

    # ── Gift code – delete ──
    if data == "ap_giftcode_delete":
        if not gift_codes:
            bot.answer_callback_query(call.id, "No active gift codes.")
            return
        user_state[uid] = {"action": "admin_gc_delete"}
        codes_list = "\n".join([f"<code>{c}</code> → {p} pts" for c, p in gift_codes.items()])
        mk = telebot.types.InlineKeyboardMarkup()
        mk.add(telebot.types.InlineKeyboardButton("❌ Cancel", callback_data="ap_back"))
        bot.edit_message_text(
            f"🗑 <b>Delete Gift Code</b>\n\nActive codes:\n{codes_list}\n\nSend the code to delete:",
            uid, call.message.message_id, reply_markup=mk
        )
        bot.register_next_step_handler(call.message, process_gc_delete)
        return

    # ── Add balance ──
    if data == "ap_add_balance":
        user_state[uid] = {"action": "admin_add_bal"}
        mk = telebot.types.InlineKeyboardMarkup()
        mk.add(telebot.types.InlineKeyboardButton("❌ Cancel", callback_data="ap_back"))
        bot.edit_message_text(
            "➕ <b>Add Balance</b>\n\nSend in format:\n<code>USER_ID POINTS</code>\n\nExample: <code>123456789 500</code>",
            uid, call.message.message_id, reply_markup=mk
        )
        bot.register_next_step_handler(call.message, process_admin_add_bal)
        return

    # ── Remove balance ──
    if data == "ap_remove_balance":
        user_state[uid] = {"action": "admin_rem_bal"}
        mk = telebot.types.InlineKeyboardMarkup()
        mk.add(telebot.types.InlineKeyboardButton("❌ Cancel", callback_data="ap_back"))
        bot.edit_message_text(
            "➖ <b>Remove Balance</b>\n\nSend in format:\n<code>USER_ID POINTS</code>\n\nExample: <code>123456789 100</code>",
            uid, call.message.message_id, reply_markup=mk
        )
        bot.register_next_step_handler(call.message, process_admin_rem_bal)
        return

    # ── Check balance ──
    if data == "ap_check_balance":
        user_state[uid] = {"action": "admin_check_bal"}
        mk = telebot.types.InlineKeyboardMarkup()
        mk.add(telebot.types.InlineKeyboardButton("❌ Cancel", callback_data="ap_back"))
        bot.edit_message_text(
            "💰 <b>Check User Balance</b>\n\nSend the User ID:",
            uid, call.message.message_id, reply_markup=mk
        )
        bot.register_next_step_handler(call.message, process_admin_check_bal)
        return

    # ── Ban ──
    if data == "ap_ban":
        user_state[uid] = {"action": "admin_ban"}
        mk = telebot.types.InlineKeyboardMarkup()
        mk.add(telebot.types.InlineKeyboardButton("❌ Cancel", callback_data="ap_back"))
        bot.edit_message_text(
            "🚫 <b>Ban User</b>\n\nSend the User ID to ban:",
            uid, call.message.message_id, reply_markup=mk
        )
        bot.register_next_step_handler(call.message, process_admin_ban)
        return

    # ── Unban ──
    if data == "ap_unban":
        user_state[uid] = {"action": "admin_unban"}
        mk = telebot.types.InlineKeyboardMarkup()
        mk.add(telebot.types.InlineKeyboardButton("❌ Cancel", callback_data="ap_back"))
        bot.edit_message_text(
            "✅ <b>Unban User</b>\n\nSend the User ID to unban:",
            uid, call.message.message_id, reply_markup=mk
        )
        bot.register_next_step_handler(call.message, process_admin_unban)
        return

    # ── List banned ──
    if data == "ap_list_banned":
        if not banned_users:
            bot.answer_callback_query(call.id, "No banned users.")
            return
        text = "📋 <b>Banned Users:</b>\n" + "\n".join(str(u) for u in banned_users)
        mk = telebot.types.InlineKeyboardMarkup()
        mk.add(telebot.types.InlineKeyboardButton("🔙 Back", callback_data="ap_back"))
        bot.edit_message_text(text, uid, call.message.message_id, reply_markup=mk)
        return

    # ── Rates menu ──
    if data == "ap_rates":
        text = (
            f"⚙️ <b>Edit Rates</b>\n\n"
            f"👍 Reactions: 1pt = {cfg['points_per_reaction']} reactions\n"
            f"👀 Views: 1pt = {cfg['points_per_view']} views\n"
            f"👥 Members: 1pt = {cfg['points_per_member']} members\n"
            f"🤝 Referral reward: {cfg['points_per_referral']} pts\n"
            f"🎁 Daily bonus: {cfg['daily_bonus_points']} pts\n\n"
            f"Select which rate to edit:"
        )
        bot.edit_message_text(text, uid, call.message.message_id, reply_markup=rates_markup())
        return

    # ── Individual rate edits ──
    rate_map = {
        "rate_reaction":  ("points_per_reaction",  "👍 Reactions (units per 1 point)"),
        "rate_view":      ("points_per_view",       "👀 Views (units per 1 point)"),
        "rate_member":    ("points_per_member",     "👥 Members (units per 1 point)"),
        "rate_referral":  ("points_per_referral",   "🤝 Referral reward (points)"),
        "rate_bonus":     ("daily_bonus_points",    "🎁 Daily bonus (points)"),
    }
    if data in rate_map:
        cfg_key, label = rate_map[data]
        user_state[uid] = {"action": "admin_edit_rate", "cfg_key": cfg_key, "label": label}
        mk = telebot.types.InlineKeyboardMarkup()
        mk.add(telebot.types.InlineKeyboardButton("❌ Cancel", callback_data="ap_rates"))
        bot.edit_message_text(
            f"⚙️ <b>Edit {label}</b>\n\nCurrent value: <b>{cfg[cfg_key]}</b>\n\nSend the new value (numbers only):",
            uid, call.message.message_id, reply_markup=mk
        )
        bot.register_next_step_handler(call.message, process_admin_edit_rate)
        return

    # ── Service IDs menu ──
    if data == "ap_service_ids":
        bot.edit_message_text(
            "🔧 <b>Edit Service IDs</b>\n\nSelect which service to update:",
            uid, call.message.message_id,
            reply_markup=service_ids_markup()
        )
        return

    # ── Individual service ID edits ──
    sid_map = {
        "sid_reactions": ("service_id_reactions", "👍 Reactions"),
        "sid_views":     ("service_id_views",     "👀 Views"),
        "sid_members":   ("service_id_members",   "👥 Members"),
    }
    if data in sid_map:
        cfg_key, label = sid_map[data]
        user_state[uid] = {"action": "admin_edit_sid", "cfg_key": cfg_key, "label": label}
        mk = telebot.types.InlineKeyboardMarkup()
        mk.add(telebot.types.InlineKeyboardButton("❌ Cancel", callback_data="ap_service_ids"))
        bot.edit_message_text(
            f"🔧 <b>Set {label} Service ID</b>\n\nCurrent ID: <b>{cfg[cfg_key]}</b>\n\nSend the new Service ID (integer only):",
            uid, call.message.message_id, reply_markup=mk
        )
        bot.register_next_step_handler(call.message, process_admin_edit_sid)
        return

    # ── Edit API Key ──
    if data == "ap_edit_apikey":
        user_state[uid] = {"action": "admin_edit_apikey"}
        mk = telebot.types.InlineKeyboardMarkup()
        mk.add(telebot.types.InlineKeyboardButton("❌ Cancel", callback_data="ap_back"))
        bot.edit_message_text(
            f"🔑 <b>Edit SMM API Key</b>\n\nCurrent: <code>{cfg['smm_api_key']}</code>\n\nSend the new API key:",
            uid, call.message.message_id, reply_markup=mk
        )
        bot.register_next_step_handler(call.message, process_admin_edit_apikey)
        return

    # ── Set logs channel ──
    if data == "ap_set_logs":
        user_state[uid] = {"action": "admin_set_logs"}
        current = cfg.get("logs_channel") or "Not set"
        mk = telebot.types.InlineKeyboardMarkup()
        mk.add(telebot.types.InlineKeyboardButton("❌ Cancel", callback_data="ap_back"))
        bot.edit_message_text(
            f"📡 <b>Set Logs Channel</b>\n\nCurrent: <b>{current}</b>\n\n"
            "Send the channel <b>username</b> (without @) or <b>chat ID</b>.\n\n"
            "⚠️ Make sure to add the bot as <b>Admin</b> in that channel first!",
            uid, call.message.message_id, reply_markup=mk
        )
        bot.register_next_step_handler(call.message, process_admin_set_logs)
        return

    # ── Edit SMM URL ── RydenX
    if data == "ap_edit_smmurl":
        user_state[uid] = {"action": "admin_edit_smmurl"}
        mk = telebot.types.InlineKeyboardMarkup()
        mk.add(telebot.types.InlineKeyboardButton("❌ Cancel", callback_data="ap_back"))
        bot.edit_message_text(
            f"🌐 <b>Edit SMM Panel URL</b>\n\nCurrent: <code>{cfg['smm_panel_url']}</code>\n\nSend the new URL:",
            uid, call.message.message_id, reply_markup=mk
        )
        bot.register_next_step_handler(call.message, process_admin_edit_smmurl)
        return

    # ── Edit QR URL ──
    if data == "ap_edit_qr":
        user_state[uid] = {"action": "admin_edit_qr"}
        mk = telebot.types.InlineKeyboardMarkup()
        mk.add(telebot.types.InlineKeyboardButton("❌ Cancel", callback_data="ap_back"))
        bot.edit_message_text(
            f"🖼 <b>Edit QR Code Image URL</b>\n\nCurrent: <code>{cfg['qr_code_url']}</code>\n\nSend the new image URL:",
            uid, call.message.message_id, reply_markup=mk
        )
        bot.register_next_step_handler(call.message, process_admin_edit_qr)
        return

    # ── Transfer admin ──
    if data == "ap_transfer_admin":
        user_state[uid] = {"action": "admin_transfer"}
        mk = telebot.types.InlineKeyboardMarkup()
        mk.add(telebot.types.InlineKeyboardButton("❌ Cancel", callback_data="ap_back"))
        bot.edit_message_text(
            "👑 <b>Transfer Admin Rights</b>\n\n⚠️ This will remove YOUR admin rights!\n\nSend the User ID of the new admin:",
            uid, call.message.message_id, reply_markup=mk
        )
        bot.register_next_step_handler(call.message, process_admin_transfer)
        return


# ─────────────────────────────────────────────────────────────
#  ADMIN STEP PROCESSORS RydenX
# ─────────────────────────────────────────────────────────────
@safe_handler
def process_admin_broadcast(message):
    uid = message.chat.id
    state = user_state.pop(uid, {})
    if state.get("action") != "admin_broadcast":
        return
    if not is_admin(uid):
        return
    success = fail = 0
    for user in users:
        try:
            bot.copy_message(user, uid, message.message_id)
            success += 1
        except Exception:
            fail += 1
    bot.send_message(uid,
        f"✅ <b>Broadcast Done!</b>\n✅ Sent: {success}\n❌ Failed: {fail}",
        reply_markup=admin_panel_markup()
    )


@safe_handler
def process_gc_create_step(message):
    uid = message.chat.id
    state = user_state.get(uid, {})
    if state.get("action") != "admin_gc_create":
        return
    if not is_admin(uid):
        return
    if state["step"] == "code":
        code = message.text.strip()
        if not code:
            bot.send_message(uid, "❌ Invalid code. Try again:")
            bot.register_next_step_handler(message, process_gc_create_step)
            return
        user_state[uid]["gift_code"] = code
        user_state[uid]["step"] = "points"
        bot.send_message(uid, f"Step 2/2 – Code: <code>{code}</code>\n\nNow enter the points value (number):")
        bot.register_next_step_handler(message, process_gc_create_step)
    elif state["step"] == "points":
        try:
            points = float(message.text.strip())
        except ValueError:
            bot.send_message(uid, "❌ Enter a valid number:")
            bot.register_next_step_handler(message, process_gc_create_step)
            return
        code = user_state.pop(uid)["gift_code"]
        gift_codes[code] = points
        bot.send_message(uid,
            f"✅ Gift code <code>{code}</code> created with <b>{points:.0f} points</b>!",
            reply_markup=admin_panel_markup()
        )


@safe_handler
def process_gc_delete(message):
    uid = message.chat.id
    state = user_state.pop(uid, {})
    if state.get("action") != "admin_gc_delete":
        return
    if not is_admin(uid):
        return
    code = message.text.strip()
    if code in gift_codes:
        del gift_codes[code]
        bot.send_message(uid, f"✅ Gift code <code>{code}</code> deleted.", reply_markup=admin_panel_markup())
    else:
        bot.send_message(uid, f"❌ Code <code>{code}</code> not found.", reply_markup=admin_panel_markup())


@safe_handler
def process_admin_add_bal(message):
    uid = message.chat.id
    state = user_state.pop(uid, {})
    if state.get("action") != "admin_add_bal" or not is_admin(uid):
        return
    try:
        parts = message.text.strip().split()
        target_id = int(parts[0])
        points = float(parts[1])
        user_balances[target_id] = user_balances.get(target_id, 0) + points
        bot.send_message(uid, f"✅ Added <b>{points:.0f} pts</b> to user <code>{target_id}</code>.\nNew balance: {user_balances[target_id]:.0f}", reply_markup=admin_panel_markup())
        try:
            bot.send_message(target_id, f"🎉 Admin credited <b>{points:.0f} points</b> to your account!")
        except Exception:
            pass
    except (ValueError, IndexError):
        bot.send_message(uid, "❌ Invalid format. Use: <code>USER_ID POINTS</code>", reply_markup=admin_panel_markup())


@safe_handler
def process_admin_rem_bal(message):
    uid = message.chat.id
    state = user_state.pop(uid, {})
    if state.get("action") != "admin_rem_bal" or not is_admin(uid):
        return
    try:
        parts = message.text.strip().split()
        target_id = int(parts[0])
        points = float(parts[1])
        user_balances[target_id] = user_balances.get(target_id, 0) - points
        bot.send_message(uid, f"✅ Removed <b>{points:.0f} pts</b> from user <code>{target_id}</code>.\nNew balance: {user_balances[target_id]:.0f}", reply_markup=admin_panel_markup())
        try:
            bot.send_message(target_id, f"⚠️ Admin deducted <b>{points:.0f} points</b> from your account.")
        except Exception:
            pass
    except (ValueError, IndexError):
        bot.send_message(uid, "❌ Invalid format. Use: <code>USER_ID POINTS</code>", reply_markup=admin_panel_markup())


@safe_handler
def process_admin_check_bal(message):
    uid = message.chat.id
    state = user_state.pop(uid, {})
    if state.get("action") != "admin_check_bal" or not is_admin(uid):
        return
    try:
        target_id = int(message.text.strip())
        bal = user_balances.get(target_id, 0)
        bot.send_message(uid, f"💰 User <code>{target_id}</code> balance: <b>{bal:.2f} points</b>", reply_markup=admin_panel_markup())
    except ValueError:
        bot.send_message(uid, "❌ Invalid user ID.", reply_markup=admin_panel_markup())


@safe_handler
def process_admin_ban(message):
    uid = message.chat.id
    state = user_state.pop(uid, {})
    if state.get("action") != "admin_ban" or not is_admin(uid):
        return
    try:
        target_id = int(message.text.strip())
        banned_users.add(target_id)
        bot.send_message(uid, f"🚫 User <code>{target_id}</code> has been banned.", reply_markup=admin_panel_markup())
        try:
            bot.send_message(target_id, "🚫 You have been banned from this bot.")
        except Exception:
            pass
    except ValueError:
        bot.send_message(uid, "❌ Invalid user ID.", reply_markup=admin_panel_markup())


@safe_handler
def process_admin_unban(message):
    uid = message.chat.id
    state = user_state.pop(uid, {})
    if state.get("action") != "admin_unban" or not is_admin(uid):
        return
    try:
        target_id = int(message.text.strip())
        banned_users.discard(target_id)
        bot.send_message(uid, f"✅ User <code>{target_id}</code> has been unbanned.", reply_markup=admin_panel_markup())
        try:
            bot.send_message(target_id, "✅ You have been unbanned. Use /start to continue.")
        except Exception:
            pass
    except ValueError:
        bot.send_message(uid, "❌ Invalid user ID.", reply_markup=admin_panel_markup())


@safe_handler
def process_admin_edit_rate(message):
    uid = message.chat.id
    state = user_state.pop(uid, {})
    if state.get("action") != "admin_edit_rate" or not is_admin(uid):
        return
    try:
        val = float(message.text.strip())
        if val <= 0:
            raise ValueError
        cfg[state["cfg_key"]] = val
        save_config(cfg)
        bot.send_message(uid,
            f"✅ <b>{state['label']}</b> updated to <b>{val}</b>",
            reply_markup=admin_panel_markup()
        )
    except ValueError:
        bot.send_message(uid, "❌ Invalid value. Must be a positive number.", reply_markup=admin_panel_markup())


@safe_handler
def process_admin_edit_sid(message):
    uid = message.chat.id
    state = user_state.pop(uid, {})
    if state.get("action") != "admin_edit_sid" or not is_admin(uid):
        return
    val_str = message.text.strip()
    if not val_str.isdigit():
        bot.send_message(uid, "❌ Service ID must be a whole number (integer).", reply_markup=admin_panel_markup())
        return
    val = int(val_str)
    cfg[state["cfg_key"]] = val
    save_config(cfg)
    bot.send_message(uid,
        f"✅ <b>{state['label']} Service ID</b> updated to <b>{val}</b>",
        reply_markup=admin_panel_markup()
    )


@safe_handler
def process_admin_edit_apikey(message):
    uid = message.chat.id
    state = user_state.pop(uid, {})
    if state.get("action") != "admin_edit_apikey" or not is_admin(uid):
        return
    new_key = message.text.strip()
    if len(new_key) < 5:
        bot.send_message(uid, "❌ API key seems too short.", reply_markup=admin_panel_markup())
        return
    cfg["smm_api_key"] = new_key
    save_config(cfg)
    bot.send_message(uid, f"✅ API key updated to <code>{new_key}</code>", reply_markup=admin_panel_markup())


@safe_handler
def process_admin_set_logs(message):
    uid = message.chat.id
    state = user_state.pop(uid, {})
    if state.get("action") != "admin_set_logs" or not is_admin(uid):
        return
    channel = message.text.strip().lstrip("@")
    cfg["logs_channel"] = channel
    save_config(cfg)
    # Test send
    try:
        target = channel if channel.startswith("-") else "@" + channel
        bot.send_message(target, "✅ Logs channel connected to SMM bot! Powerd By @Ethical_Hackers_BD (ETHBD) ")
        bot.send_message(uid, f"✅ Logs channel set to <b>{channel}</b> and test message sent!", reply_markup=admin_panel_markup())
    except Exception as e:
        bot.send_message(uid,
            f"⚠️ Channel saved as <b>{channel}</b> but test message failed.\nError: {e}\n\n"
            "Make sure bot is admin in the channel.",
            reply_markup=admin_panel_markup()
        )


@safe_handler
def process_admin_edit_smmurl(message):
    uid = message.chat.id
    state = user_state.pop(uid, {})
    if state.get("action") != "admin_edit_smmurl" or not is_admin(uid):
        return
    url = message.text.strip()
    if not url.startswith("http"):
        bot.send_message(uid, "❌ Invalid URL.", reply_markup=admin_panel_markup())
        return
    cfg["smm_panel_url"] = url
    save_config(cfg)
    bot.send_message(uid, f"✅ SMM Panel URL updated to <code>{url}</code>", reply_markup=admin_panel_markup())


@safe_handler
def process_admin_edit_qr(message):
    uid = message.chat.id
    state = user_state.pop(uid, {})
    if state.get("action") != "admin_edit_qr" or not is_admin(uid):
        return
    url = message.text.strip()
    if not url.startswith("http"):
        bot.send_message(uid, "❌ Invalid URL.", reply_markup=admin_panel_markup())
        return
    cfg["qr_code_url"] = url
    save_config(cfg)
    bot.send_message(uid, f"✅ QR code URL updated!", reply_markup=admin_panel_markup())


@safe_handler
def process_admin_transfer(message):
    uid = message.chat.id
    state = user_state.pop(uid, {})
    if state.get("action") != "admin_transfer" or not is_admin(uid):
        return
    try:
        new_admin = int(message.text.strip())
        old_admin = uid
        cfg["admin_id"] = new_admin
        save_config(cfg)
        bot.send_message(uid, f"✅ Admin rights transferred to <code>{new_admin}</code>. You are no longer admin.")
        try:
            bot.send_message(new_admin,
                "👑 <b>You are now the ADMIN!</b>\n\nUse /admin to open your control panel."
            )
        except Exception:
            pass
        send_log(f"👑 Admin transferred from {old_admin} to {new_admin}")
    except ValueError:
        bot.send_message(uid, "❌ Invalid user ID.", reply_markup=admin_panel_markup())


# ─────────────────────────────────────────────────────────────
#  /start RydenX
# ─────────────────────────────────────────────────────────────
@bot.message_handler(commands=['start'])
@safe_handler
@require_not_banned
def send_welcome(message):
    reload_cfg()
    user_id = message.chat.id
    text = message.text.split()

    # SAFE NAME HANDLING
    if message.chat.username:
        display_name = "@" + message.chat.username
    else:
        display_name = "Anonymous"

    if user_id in users:
        if len(text) > 1:
            bot.send_message(user_id, "❌ 𝙔𝙊𝙐 𝙃𝘼𝙑𝙀 𝘼𝙇𝙍𝙀𝘼𝘿𝙔 𝙎𝙏𝘼𝙍𝙏𝙀𝘿 𝙏𝙃𝙀 𝘽𝙊𝙏!")
        return

    users.add(user_id)

    if len(text) > 1:
        ref_str = text[1]
        if ref_str.isdigit():
            referrer_id = int(ref_str)
            if referrer_id == user_id:
                bot.send_message(user_id, "❌ 𝘿𝙊𝙎𝙏 𝙆𝙊 𝘽𝙃𝙀𝙅 𝘽𝙃𝘼𝙄. 𝙔𝙊𝙐 𝘾𝘼𝙉𝙉𝙊𝙏 𝙍𝙀𝙁𝙀𝙍 𝙔𝙊𝙐𝙍𝙎𝙀𝙇𝙁!")
                return
            user_referrals[user_id] = {"referrer": referrer_id, "rewarded": False}

    user_link = f"<a href='tg://user?id={user_id}'>{display_name}</a>"

    bot.send_message(
        user_id,
        f"❤️ 𝘿𝙀𝘼𝙍 {user_link},\n\n"
        "𝙒𝙀𝘾𝙊𝙈𝙀 𝙏𝙊 𝙊𝙐𝙍 𝙏Ｇ 𝙎𝙀𝙍𝙑𝙄𝘾𝙀 𝘽𝙊𝗍!\n"
        "𝙁𝙤𝙧 𝙇𝙖𝙩𝙚𝙨𝙩 𝙐𝙥𝙙𝙖𝙩𝙚𝙨 & 𝙍𝙚𝙜𝙪𝙡𝙖𝙩𝙞𝙤𝙣𝙨 𝙔𝙤𝙪 𝙉𝙚𝙚𝙙 𝙏𝙤 𝙅𝙤𝙞𝙣 𝙊𝙪𝙧 𝘾𝙃𝗔𝗡𝗡𝗘𝗟𝗦:",
        reply_markup=join_menu(),
        disable_web_page_preview=True
    )


# ─────────────────────────────────────────────────────────────
#  Joined callback
# ─────────────────────────────────────────────────────────────
@bot.callback_query_handler(func=lambda call: call.data == "joined")
@safe_callback
def joined_button_handler(call):
    reload_cfg()
    user_id = call.message.chat.id

    # Verify membership in all configured channels
    for ch in cfg["channels"]:
        username = ch["username"]
        try:
            target = username if username.startswith("-100") else "@" + username.lstrip("@")
            member = bot.get_chat_member(target, user_id)
            if member.status not in ["member", "administrator", "creator"]:
                bot.answer_callback_query(call.id, "❌ Please join ALL channels first!")
                return
        except Exception as e:
            print(f"[CHANNEL CHECK ERROR] {username}: {e}")
            bot.answer_callback_query(call.id, "❌ Unable to verify. Please try again.")
            return

    try:
        bot.delete_message(user_id, call.message.message_id)
    except Exception:
        pass

    bot.send_message(user_id, "✅ 𝗪𝗘𝗟𝗖𝗢𝗠𝗘 𝗧𝗢 𝗔𝗖𝗖𝗘𝗦𝗦 𝗣𝗔𝗡𝗘𝗟 🌸", reply_markup=main_menu())

    try:
        first_name = call.message.chat.first_name or str(user_id)
        bot.send_message(cfg["admin_id"],
            f"ℹ️ User <a href='tg://user?id={user_id}'>{first_name}</a> joined and confirmed channels.",
            disable_web_page_preview=True
        )
    except Exception:
        pass

    # Reward referrer
    if user_id in user_referrals:
        ref_info = user_referrals[user_id]
        if not ref_info.get("rewarded"):
            referrer_id = ref_info["referrer"]
            reward = cfg["points_per_referral"]
            user_balances[referrer_id] = user_balances.get(referrer_id, 0) + reward
            user_referrals[user_id]["rewarded"] = True
            try:
                bot.send_message(referrer_id, f"✅ You received <b>{reward} points</b> for a referral!")
            except Exception:
                pass


# ─────────────────────────────────────────────────────────────
#  ORDER FLOW RydenX
# ─────────────────────────────────────────────────────────────
def start_order(message, service_type):
    reload_cfg()
    user_id = message.chat.id
    user_state.pop(user_id, None)
    rates = {
        "reactions": cfg["points_per_reaction"],
        "views":     cfg["points_per_view"],
        "members":   cfg["points_per_member"],
    }
    user_state[user_id] = {
        "action": "order",
        "service_type": service_type,
        "points_per_unit": rates[service_type],
        "step": "awaiting_link",
        "url": None
    }
    labels = {
        "reactions": "❤️ REACTIONS",
        "views":     "👀 VIEWS",
        "members":   "👥 MEMBERS",
    }
    units = rates[service_type]
    bot.send_message(user_id,
        f"𝗦𝗘𝗡𝗗 𝗬𝗢𝗨𝗥 𝗧𝗘𝗟𝗘𝗚𝗥𝗔𝗠 𝗟𝗜𝗡𝗞 𝗙𝗢𝗥 {labels[service_type]}:\n(1 point = {units} {service_type})"
    )


@bot.message_handler(func=lambda m: m.text == "👍 Order Reactions")
@safe_handler
@require_not_banned
def order_reactions(message):
    start_order(message, "reactions")


@bot.message_handler(func=lambda m: m.text == "👀 Order Views")
@safe_handler
@require_not_banned
def order_views(message):
    start_order(message, "views")


@bot.message_handler(func=lambda m: m.text == "👥 Order Members")
@safe_handler
@require_not_banned
def order_members(message):
    start_order(message, "members")


@bot.message_handler(func=lambda m: (
    user_state.get(m.chat.id) is not None and
    user_state.get(m.chat.id, {}).get("action") == "order"
))
@safe_handler
def handle_pending_order(message):
    if message.text in MAIN_COMMANDS:
        user_state.pop(message.chat.id, None)
        return
    state = user_state.get(message.chat.id)
    if not state:
        return
    if state.get("step") == "awaiting_link":
        process_order_link(message)
    elif state.get("step") == "awaiting_quantity":
        process_order_quantity(message)
    else:
        user_state.pop(message.chat.id, None)


@safe_handler
def process_order_link(message):
    user_id = message.chat.id
    state   = user_state.get(user_id)
    if not state or state.get("step") != "awaiting_link":
        return
    if message.content_type != 'text':
        bot.send_message(user_id, "❌ Please send the link as text.")
        return
    state["url"]  = message.text.strip()
    state["step"] = "awaiting_quantity"
    units         = state["points_per_unit"]
    stype         = state["service_type"]
    bot.send_message(user_id,
        f"𝗘𝗡𝗧𝗘𝗥 𝗤𝗨𝗔𝗡𝗧𝗜𝗧𝗬 (𝗠𝗜𝗡 10):\n(1 point = {units} {stype})"
    )


@safe_handler
def process_order_quantity(message):
    reload_cfg()
    user_id = message.chat.id
    state   = user_state.get(user_id)
    if not state or state.get("step") != "awaiting_quantity":
        return
    if message.content_type != 'text' or not message.text.strip().isdigit():
        bot.send_message(user_id, "❌ Please enter numbers only.")
        return
    quantity = int(message.text.strip())
    if quantity < 10:
        bot.send_message(user_id, "❌ Minimum order quantity is 10.")
        return

    service_type   = state["service_type"]
    points_per_unit = state["points_per_unit"]
    url            = state["url"]
    required_pts   = quantity / points_per_unit

    if user_balances.get(user_id, 0) < required_pts:
        bot.send_message(user_id, f"❌ Insufficient points. You need <b>{required_pts:.2f}</b> pts but have <b>{user_balances.get(user_id, 0):.2f}</b>.")
        user_state.pop(user_id, None)
        return

    user_balances[user_id] = user_balances.get(user_id, 0) - required_pts

    svc_map = {
        "reactions": cfg["service_id_reactions"],
        "views":     cfg["service_id_views"],
        "members":   cfg["service_id_members"],
    }
    order_data = {
        "key":      cfg["smm_api_key"],
        "action":   "add",
        "service":  svc_map[service_type],
        "link":     url,
        "quantity": quantity
    }
    try:
        response = requests.post(cfg["smm_panel_url"], data=order_data, timeout=15).json()
    except Exception as e:
        user_balances[user_id] += required_pts  # refund
        bot.send_message(user_id, f"❌ Error contacting SMM panel. Points refunded.\n{e}")
        user_state.pop(user_id, None)
        return

    user_state.pop(user_id, None)

    if "order" in response:
        order_id = response["order"]
        ts       = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        order_details = {
            "order_id":    order_id,
            "service_type": service_type,
            "link":        url,
            "quantity":    quantity,
            "timestamp":   ts
        }
        user_orders.setdefault(user_id, []).append(order_details)

        bot.send_message(user_id,
            f"✅ 𝗢𝗥𝗗𝗘𝗥 𝗣𝗟𝗔𝗖𝗘𝗗 🦋\n"
            f"Service: {service_type.capitalize()}\n"
            f"Quantity: {quantity}\n"
            f"Order ID: <code>{order_id}</code>\n"
            f"Estimated time: 2-3 hours"
        )

        # Admin notification
        admin_text = (
            f"🛒 <b>NEW ORDER</b>\n"
            f"👤 User: <a href='tg://user?id={user_id}'>{user_id}</a>\n"
            f"🔧 Service: {service_type.capitalize()}\n"
            f"🔗 Link: {url}\n"
            f"📦 Qty: {quantity}\n"
            f"🆔 Order ID: {order_id}\n"
            f"🕐 Time: {ts}"
        )
        try:
            bot.send_message(cfg["admin_id"], admin_text, disable_web_page_preview=True)
        except Exception:
            pass

        # Logs channel
        send_log(admin_text)
    else:
        # Refund on API error
        user_balances[user_id] += required_pts
        error_msg = response.get("error", str(response))
        bot.send_message(user_id, f"❌ Order failed. Points refunded.\nError: {error_msg}")


# ─────────────────────────────────────────────────────────────
#  USER FEATURES RydenX
# ─────────────────────────────────────────────────────────────
@bot.message_handler(func=lambda m: m.text == "💰 Check Balance")
@safe_handler
@require_not_banned
def check_balance(message):
    user_state.pop(message.chat.id, None)
    reload_cfg()
    uid = message.chat.id
    bal = user_balances.get(uid, 0)
    bot.send_message(uid,
        f"💰 <b>Your Balance</b>\n\n"
        f"Points: <b>{bal:.2f}</b>\n\n"
        f"📊 Conversion rates:\n"
        f"👍 1 pt = {cfg['points_per_reaction']} Reactions\n"
        f"👀 1 pt = {cfg['points_per_view']} Views\n"
        f"👥 1 pt = {cfg['points_per_member']} Members"
    )


@bot.message_handler(func=lambda m: m.text == "🎁 Claim Bonus")
@safe_handler
@require_not_banned
def claim_bonus(message):
    user_state.pop(message.chat.id, None)
    reload_cfg()
    user_id = message.chat.id
    today   = datetime.now().date()
    if user_id in user_last_bonus and user_last_bonus[user_id] == today:
        bot.send_message(user_id, " YOU CAN CLAIM BONUS ONCE A DAY.")
        return
    bonus = cfg["daily_bonus_points"]
    user_balances[user_id] = user_balances.get(user_id, 0) + bonus
    user_last_bonus[user_id] = today
    bot.send_message(user_id, f"✅ <b>{bonus} BONUS POINTS</b> credited to your account! ☺")


@bot.message_handler(func=lambda m: m.text == "➕ Add Funds")
@safe_handler
@require_not_banned
def add_funds(message):
    user_state.pop(message.chat.id, None)
    reload_cfg()
    user_id = message.chat.id
    bot.send_photo(
        user_id,
        cfg["qr_code_url"],
        caption=f"📌 SCAN QR OR SEND MONEY 0127556382\n\nFor help DM {cfg['payment_contact']}"
    )


@bot.message_handler(content_types=['photo'])
@safe_handler
@require_not_banned
def handle_payment_screenshot(message):
    user_id = message.chat.id
    user_state.pop(user_id, None)
    bot.forward_message(cfg["admin_id"], user_id, message.message_id)
    bot.send_message(cfg["admin_id"],
        f"💳 Payment screenshot from user <a href='tg://user?id={user_id}'>{user_id}</a>. Verify and add points.",
        disable_web_page_preview=True
    )
    bot.send_message(user_id, "✅ 𝗣𝗔𝗬𝗠𝗘𝗡𝗧 𝗦𝗖𝗥𝗘𝗘𝗡𝗦𝗛𝗢𝗧 𝗦𝗘𝗡𝗧 𝗧𝗢 𝗔𝗗𝗠𝗜𝗡. Please wait for verification.")


@bot.message_handler(func=lambda m: m.text == "📢 Refer & Earn")
@safe_handler
@require_not_banned
def refer_earn(message):
    user_state.pop(message.chat.id, None)
    reload_cfg()
    user_id = message.chat.id
    bot_username = cfg.get("bot_username", "your_bot")
    link = f"https://t.me/{bot_username}?start={user_id}"
    referred = [r for r, info in user_referrals.items() if info["referrer"] == user_id]
    rewarded  = [r for r, info in user_referrals.items() if info["referrer"] == user_id and info["rewarded"]]
    bot.send_message(user_id,
        f"📢 <b>Refer & Earn</b>\n\n"
        f"Earn <b>{cfg['points_per_referral']} points</b> per referral!\n\n"
        f"🔗 Your link:\n<code>{link}</code>\n\n"
        f"👥 Total referred: {len(referred)}\n"
        f"✅ Rewarded: {len(rewarded)}\n\n"
        f"Send /referrals to see your list."
    )


@bot.message_handler(commands=['referrals', 'refferals'])
@safe_handler
@require_not_banned
def show_referrals(message):
    user_id = message.chat.id
    ref_list = [str(r) for r, info in user_referrals.items() if info["referrer"] == user_id]
    if ref_list:
        bot.send_message(user_id, "📢 <b>Your Referrals:</b>\n" + "\n".join(ref_list))
    else:
        bot.send_message(user_id, "❌ You have 0 referrals yet.")


@bot.message_handler(func=lambda m: m.text == "🔳 GiftCode")
@safe_handler
@require_not_banned
def giftcode_handler(message):
    user_id = message.chat.id
    user_state.pop(user_id, None)
    user_state[user_id] = {"action": "giftcode"}
    bot.send_message(user_id, "𝗣𝗟𝗘𝗔𝗦𝗘 𝗘𝗡𝗧𝗘𝗥 𝗬𝗢𝗨𝗥 𝗚𝗜𝗙𝗧 𝗖𝗢𝗗𝗘:")
    bot.register_next_step_handler(message, process_giftcode)


@safe_handler
def process_giftcode(message):
    user_id = message.chat.id
    state   = user_state.pop(user_id, {})
    if state.get("action") != "giftcode":
        return
    if message.content_type != 'text':
        bot.send_message(user_id, "❌ Please send the gift code as text.")
        return
    code = message.text.strip()
    if code not in gift_codes:
        bot.send_message(user_id, "❌ Wrong code! Ask admin for a valid gift code.")
        return
    redeemed = user_redeemed_codes.setdefault(user_id, set())
    if code in redeemed:
        bot.send_message(user_id, "❌ You have already redeemed this gift code!")
        return
    redeemed.add(code)
    points = gift_codes[code]
    user_balances[user_id] = user_balances.get(user_id, 0) + points
    bot.send_message(user_id, f"✅ Gift code <code>{code}</code> redeemed! You received <b>{points:.0f} points</b> 🎉")


@bot.message_handler(func=lambda m: m.text == "🖲 Track Order")
@safe_handler
@require_not_banned
def track_order(message):
    user_id = message.chat.id
    user_state.pop(user_id, None)
    user_state[user_id] = {"action": "track_order"}
    bot.send_message(user_id, "𝗘𝗡𝗧𝗘𝗥 𝗬𝗢𝗨𝗥 𝗢𝗥𝗗𝗘𝗥 𝗜𝗗:")
    bot.register_next_step_handler(message, process_track_order)


@safe_handler
def process_track_order(message):
    reload_cfg()
    user_id = message.chat.id
    state   = user_state.pop(user_id, {})
    if state.get("action") != "track_order":
        return
    if message.content_type != 'text' or not message.text.strip().isdigit():
        bot.send_message(user_id, "❌ Please send the Order ID as a number.")
        return
    order_id = message.text.strip()
    try:
        response = requests.post(cfg["smm_panel_url"], data={
            "key":    cfg["smm_api_key"],
            "action": "status",
            "order":  order_id
        }, timeout=15).json()
    except Exception as e:
        bot.send_message(user_id, f"❌ Error connecting to SMM panel: {e}")
        return
    if "error" in response:
        bot.send_message(user_id, f"❌ Error: {response['error']}")
    else:
        status = response.get("status", "Unknown")
        info   = "\n".join([f"{k.capitalize()}: {v}" for k, v in response.items() if k != "status"])
        msg    = f"✅ <b>Order {order_id}</b>\nStatus: <b>{status}</b>"
        if info:
            msg += f"\n{info}"
        bot.send_message(user_id, msg)


@bot.message_handler(func=lambda m: m.text == "📜 Order History")
@safe_handler
@require_not_banned
def order_history(message):
    user_id = message.chat.id
    orders  = user_orders.get(user_id, [])
    if not orders:
        bot.send_message(user_id, "❌ You have no orders yet.")
        return
    text = "📜 <b>Your Last 5 Orders:</b>\n\n"
    for o in orders[-5:]:
        text += (
            f"🆔 <code>{o['order_id']}</code> | {o['service_type'].capitalize()} | "
            f"Qty: {o['quantity']} | {o['timestamp']}\n"
        )
    bot.send_message(user_id, text)


@bot.message_handler(func=lambda m: m.text == "💬 Feedback")
@safe_handler
@require_not_banned
def feedback(message):
    user_id = message.chat.id
    user_state.pop(user_id, None)
    user_state[user_id] = {"action": "feedback"}
    bot.send_message(user_id, "𝗘𝗡𝗧𝗘𝗥 𝗬𝗢𝗨𝗥 𝗙𝗘𝗘𝗗𝗕𝗔𝗖𝗞:")
    bot.register_next_step_handler(message, process_feedback)


@safe_handler
def process_feedback(message):
    user_id = message.chat.id
    state   = user_state.pop(user_id, {})
    if state.get("action") != "feedback":
        return
    if message.content_type != 'text':
        bot.send_message(user_id, "❌ Please send feedback as text.")
        return
    text = message.text.strip()
    bot.send_message(cfg["admin_id"],
        f"💬 <b>Feedback</b> from <a href='tg://user?id={user_id}'>{user_id}</a>:\n\n{text}",
        disable_web_page_preview=True
    )
    bot.send_message(user_id, "✅ Feedback submitted! Thank you.")


# ─────────────────────────────────────────────────────────────
#  LEGACY TEXT COMMANDS (still work for admin convenience)
# ─────────────────────────────────────────────────────────────
@bot.message_handler(commands=['addbalance'])
@safe_handler
def cmd_add_balance(message):
    if not is_admin(message.chat.id):
        return
    try:
        _, uid_s, pts_s = message.text.split()
        uid  = int(uid_s)
        pts  = float(pts_s)
        user_balances[uid] = user_balances.get(uid, 0) + pts
        bot.send_message(message.chat.id, f"✅ Added {pts} pts to {uid}")
        try:
            bot.send_message(uid, f"✅ Admin credited {pts:.0f} points to your account!")
        except Exception:
            pass
    except ValueError:
        bot.send_message(message.chat.id, "Usage: /addbalance <user_id> <points>")


@bot.message_handler(commands=['removebalance'])
@safe_handler
def cmd_remove_balance(message):
    if not is_admin(message.chat.id):
        return
    try:
        _, uid_s, pts_s = message.text.split()
        uid  = int(uid_s)
        pts  = float(pts_s)
        user_balances[uid] = user_balances.get(uid, 0) - pts
        bot.send_message(message.chat.id, f"✅ Removed {pts} pts from {uid}. New: {user_balances[uid]:.2f}")
    except ValueError:
        bot.send_message(message.chat.id, "Usage: /removebalance <user_id> <points>")


@bot.message_handler(commands=['checkbalance'])
@safe_handler
def cmd_check_balance(message):
    if not is_admin(message.chat.id):
        return
    try:
        parts = message.text.split()
        uid   = int(parts[1])
        bot.send_message(message.chat.id, f"Balance of {uid}: {user_balances.get(uid, 0):.2f} pts")
    except (ValueError, IndexError):
        bot.send_message(message.chat.id, "Usage: /checkbalance <user_id>")


@bot.message_handler(commands=['giftcode'])
@safe_handler
def cmd_giftcode(message):
    if not is_admin(message.chat.id):
        return
    try:
        _, code, pts_s = message.text.split()
        pts = float(pts_s)
        gift_codes[code] = pts
        bot.send_message(message.chat.id, f"✅ Gift code '{code}' = {pts:.0f} pts")
    except ValueError:
        bot.send_message(message.chat.id, "Usage: /giftcode <code> <points>")


@bot.message_handler(commands=['stats'])
@safe_handler
def cmd_stats(message):
    if not is_admin(message.chat.id):
        return
    bot.send_message(message.chat.id,
        f"📊 Total Users: {len(users)} | Banned: {len(banned_users)} | Gift codes: {len(gift_codes)}"
    )


@bot.message_handler(commands=['broadcast'])
@safe_handler
def cmd_broadcast(message):
    if not is_admin(message.chat.id):
        return
    args = message.text.split(maxsplit=1)
    if len(args) < 2:
        bot.send_message(message.chat.id, "Usage: /broadcast <message>")
        return
    success = fail = 0
    for user in users:
        try:
            bot.send_message(user, args[1])
            success += 1
        except Exception:
            fail += 1
    bot.send_message(message.chat.id, f"✅ Broadcast done. Sent: {success} | Failed: {fail}")


# ─────────────────────────────────────────────────────────────
#  POLLING
# ─────────────────────────────────────────────────────────────
print("🤖 Bot started Powered by CTA")
while True:
    try:
        bot.polling(none_stop=True, timeout=60, long_polling_timeout=60)
    except Exception as e:
        print(f"[POLLING ERROR] {e}")
        time.sleep(15)
