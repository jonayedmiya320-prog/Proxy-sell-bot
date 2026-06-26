# ============================================================
# ЁЯдЦ SpyX Sell Proxy Bot - Single File Version
# Author: @sadhin8miya
# Deploy: Railway / Render
# ============================================================

import logging
import json
import os
import io
from datetime import datetime, timedelta
from telegram import (
    Update, ReplyKeyboardMarkup, InlineKeyboardMarkup, InlineKeyboardButton
)
from telegram.ext import (
    Application, CommandHandler, MessageHandler,
    CallbackQueryHandler, filters, ContextTypes
)
from telegram.constants import ParseMode

# ============================================================
# тЪЩя╕П CONFIGURATION тАФ ржПржЦрж╛ржирзЗ ржЖржкржирж╛рж░ рждржерзНржп ржжрж┐ржи
# ============================================================

BOT_TOKEN   = os.environ.get("BOT_TOKEN", "8777803602:AAGT2aXEtxjQ6op9LyvGrs6gboJuB8xzfxE")
ADMIN_ID    = int(os.environ.get("ADMIN_ID", "7095358778"))  # ржЖржкржирж╛рж░ Telegram ID
SUPPORT_USERNAME = "@sadhin8miya"
BOT_NAME    = "SpyX Proxy Bot"
CURRENCY    = "BDT"
PAGE_SIZE   = 10
DATA_DIR    = "data"

# JSON file paths
USERS_FILE    = "data/users.json"
PRODUCTS_FILE = "data/products.json"
STOCK_FILE    = "data/stock.json"
ORDERS_FILE   = "data/orders.json"
DEPOSITS_FILE = "data/deposits.json"
SETTINGS_FILE = "data/settings.json"

# ============================================================
# ЁЯТ╛ DATABASE тАФ JSON Functions
# ============================================================

def init_db():
    os.makedirs(DATA_DIR, exist_ok=True)
    defaults = {
        USERS_FILE: {},
        PRODUCTS_FILE: {},
        STOCK_FILE: {},
        ORDERS_FILE: {},
        DEPOSITS_FILE: {},
        SETTINGS_FILE: {
            "bkash": "",
            "nagad": "",
            "referral_commission": 10,
            "welcome_message": (
                f"Welcome to {BOT_NAME}! ЁЯЪА\n\n"
                "We provide premium VPN accounts & proxies at the best prices.\n\n"
                "тЪб High Speed\nЁЯФТ Secure & Stable\nтЬЕ Instant Delivery\nЁЯТм 24/7 Support"
            )
        }
    }
    for filepath, default in defaults.items():
        if not os.path.exists(filepath):
            save_json(filepath, default)


def load_json(filepath):
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def save_json(filepath, data):
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


# ---------- USERS ----------

def get_user(user_id):
    return load_json(USERS_FILE).get(str(user_id))


def save_user(user_id, data):
    users = load_json(USERS_FILE)
    users[str(user_id)] = data
    save_json(USERS_FILE, users)


def get_all_users():
    return load_json(USERS_FILE)


def create_user(user_id, username, full_name, referred_by=None):
    existing = get_user(user_id)
    if existing:
        return existing
    user = {
        "id": user_id,
        "username": username or "",
        "full_name": full_name or "",
        "balance": 0,
        "referred_by": referred_by,
        "referral_count": 0,
        "total_earned": 0,
        "total_orders": 0,
        "is_banned": False,
        "joined_at": datetime.now().isoformat()
    }
    save_user(user_id, user)
    if referred_by:
        referrer = get_user(referred_by)
        if referrer:
            referrer["referral_count"] = referrer.get("referral_count", 0) + 1
            save_user(referred_by, referrer)
    return user


def update_user_balance(user_id, amount):
    user = get_user(user_id)
    if user:
        user["balance"] = round(user.get("balance", 0) + amount, 2)
        save_user(user_id, user)
        return user["balance"]
    return None


def ban_user(user_id, banned=True):
    user = get_user(user_id)
    if user:
        user["is_banned"] = banned
        save_user(user_id, user)
        return True
    return False


def search_user_by_username(username):
    users = load_json(USERS_FILE)
    username = username.lstrip("@").lower()
    for uid, user in users.items():
        if user.get("username", "").lower() == username:
            return user
    return None


def get_paginated_users(page=1, filter_type="all"):
    users = load_json(USERS_FILE)
    user_list = list(users.values())
    if filter_type == "banned":
        user_list = [u for u in user_list if u.get("is_banned")]
    elif filter_type == "active":
        user_list = [u for u in user_list if not u.get("is_banned")]
    total = len(user_list)
    total_pages = max(1, (total + PAGE_SIZE - 1) // PAGE_SIZE)
    start = (page - 1) * PAGE_SIZE
    return user_list[start:start + PAGE_SIZE], total, total_pages


# ---------- PRODUCTS ----------

def get_all_products():
    return load_json(PRODUCTS_FILE)


def get_product(product_id):
    return load_json(PRODUCTS_FILE).get(str(product_id))


def save_product(product_id, data):
    products = load_json(PRODUCTS_FILE)
    products[str(product_id)] = data
    save_json(PRODUCTS_FILE, products)


def delete_product(product_id):
    products = load_json(PRODUCTS_FILE)
    if str(product_id) in products:
        del products[str(product_id)]
        save_json(PRODUCTS_FILE, products)
        return True
    return False


def create_product(name, price, category, duration_days):
    products = load_json(PRODUCTS_FILE)
    pid = str(int(datetime.now().timestamp() * 1000))
    products[pid] = {
        "id": pid, "name": name, "price": price,
        "category": category, "duration_days": duration_days,
        "is_active": True, "created_at": datetime.now().isoformat()
    }
    save_json(PRODUCTS_FILE, products)
    return pid


def get_products_by_category(category):
    products = load_json(PRODUCTS_FILE)
    return {k: v for k, v in products.items()
            if v.get("category") == category and v.get("is_active", True)}


# ---------- STOCK ----------

def get_stock(product_id):
    return load_json(STOCK_FILE).get(str(product_id), [])


def add_stock(product_id, credential):
    stock = load_json(STOCK_FILE)
    pid = str(product_id)
    if pid not in stock:
        stock[pid] = []
    stock[pid].append({"data": credential, "used": False})
    save_json(STOCK_FILE, stock)


def get_stock_count(product_id):
    return sum(1 for item in get_stock(product_id) if not item.get("used"))


def pop_stock(product_id):
    stock = load_json(STOCK_FILE)
    pid = str(product_id)
    if pid not in stock:
        return None
    for item in stock[pid]:
        if not item.get("used"):
            item["used"] = True
            save_json(STOCK_FILE, stock)
            return item["data"]
    return None


# ---------- ORDERS ----------

def create_order(user_id, product_id, product_name, category, credential, price, duration_days, expiry_date):
    orders = load_json(ORDERS_FILE)
    order_id = f"SPX-{int(datetime.now().timestamp() * 1000)}"
    orders[order_id] = {
        "order_id": order_id, "user_id": user_id,
        "product_id": product_id, "product_name": product_name,
        "category": category, "credential": credential,
        "price": price, "duration_days": duration_days,
        "expiry_date": expiry_date, "status": "active",
        "created_at": datetime.now().isoformat()
    }
    save_json(ORDERS_FILE, orders)
    user = get_user(user_id)
    if user:
        user["total_orders"] = user.get("total_orders", 0) + 1
        save_user(user_id, user)
    return order_id


def get_user_orders(user_id, page=1):
    orders = load_json(ORDERS_FILE)
    user_orders = [o for o in orders.values() if o.get("user_id") == user_id]
    user_orders.sort(key=lambda x: x.get("created_at", ""), reverse=True)
    now = datetime.now().isoformat()
    for order in user_orders:
        if order.get("expiry_date") and order["expiry_date"] < now:
            order["status"] = "expired"
    total = len(user_orders)
    total_pages = max(1, (total + PAGE_SIZE - 1) // PAGE_SIZE)
    start = (page - 1) * PAGE_SIZE
    return user_orders[start:start + PAGE_SIZE], total, total_pages


def get_all_orders():
    return load_json(ORDERS_FILE)


# ---------- DEPOSITS ----------

def create_deposit(user_id, username, amount, trx_id, phone):
    deposits = load_json(DEPOSITS_FILE)
    dep_id = f"DEP-{int(datetime.now().timestamp() * 1000)}"
    deposits[dep_id] = {
        "dep_id": dep_id, "user_id": user_id,
        "username": username or "", "amount": amount,
        "trx_id": trx_id, "phone": phone,
        "status": "pending", "created_at": datetime.now().isoformat()
    }
    save_json(DEPOSITS_FILE, deposits)
    return dep_id


def get_deposit(dep_id):
    return load_json(DEPOSITS_FILE).get(dep_id)


def update_deposit_status(dep_id, status):
    deposits = load_json(DEPOSITS_FILE)
    if dep_id in deposits:
        deposits[dep_id]["status"] = status
        deposits[dep_id]["updated_at"] = datetime.now().isoformat()
        save_json(DEPOSITS_FILE, deposits)
        return True
    return False


def get_pending_deposits(page=1):
    deposits = load_json(DEPOSITS_FILE)
    pending = [d for d in deposits.values() if d.get("status") == "pending"]
    pending.sort(key=lambda x: x.get("created_at", ""), reverse=True)
    total = len(pending)
    total_pages = max(1, (total + PAGE_SIZE - 1) // PAGE_SIZE)
    start = (page - 1) * PAGE_SIZE
    return pending[start:start + PAGE_SIZE], total, total_pages


def get_all_deposits():
    return load_json(DEPOSITS_FILE)


# ---------- SETTINGS ----------

def get_settings():
    return load_json(SETTINGS_FILE)


def update_setting(key, value):
    settings = load_json(SETTINGS_FILE)
    settings[key] = value
    save_json(SETTINGS_FILE, settings)


# ---------- STATS ----------

def get_stats():
    users    = load_json(USERS_FILE)
    orders   = load_json(ORDERS_FILE)
    deposits = load_json(DEPOSITS_FILE)
    return {
        "total_users":     len(users),
        "banned_users":    sum(1 for u in users.values() if u.get("is_banned")),
        "total_orders":    len(orders),
        "vpn_orders":      sum(1 for o in orders.values() if o.get("category") == "vpn"),
        "proxy_orders":    sum(1 for o in orders.values() if o.get("category") == "proxy"),
        "total_deposits":  sum(d.get("amount", 0) for d in deposits.values() if d.get("status") == "approved"),
        "pending_deposits":sum(1 for d in deposits.values() if d.get("status") == "pending"),
    }


# ============================================================
# ЁЯЫая╕П HELPERS
# ============================================================

def format_date(iso_date):
    try:
        return datetime.fromisoformat(iso_date).strftime("%d %b %Y")
    except:
        return iso_date or "N/A"


def get_expiry_date(duration_days):
    return (datetime.now() + timedelta(days=int(duration_days))).isoformat()


def is_expired(expiry_date):
    try:
        return datetime.fromisoformat(expiry_date) < datetime.now()
    except:
        return False


def format_order_status(expiry_date):
    if not expiry_date:
        return "тЬЕ Active"
    return "тЪая╕П Expired" if is_expired(expiry_date) else "тЬЕ Active"


def format_order(order):
    status     = format_order_status(order.get("expiry_date"))
    cat_emoji  = "ЁЯФТ" if order.get("category") == "vpn" else "ЁЯМР"
    expiry     = format_date(order.get("expiry_date", ""))
    credential = order.get("credential", "")
    parts      = credential.split(":")

    if len(parts) == 2:
        cred_text = f"ЁЯСд Username: `{parts[0]}`\nЁЯФС Password: `{parts[1]}`"
    elif len(parts) >= 3:
        cred_text = f"ЁЯМР Proxy: `{credential}`"
    else:
        cred_text = f"ЁЯУЛ Details: `{credential}`"

    return (
        f"{cat_emoji} *{order.get('product_name', 'N/A')}*\n"
        f"ЁЯЖФ Order: `{order.get('order_id')}`\n"
        f"ЁЯУЕ Expired: {expiry}\n"
        f"тЪб Status: {status}\n"
        f"{cred_text}"
    )


def format_user_info(user):
    status   = "ЁЯЪл Banned" if user.get("is_banned") else "тЬЕ Active"
    username = f"@{user['username']}" if user.get("username") else "No username"
    return (
        f"ЁЯСд *User Info*\n"
        f"тФБтФБтФБтФБтФБтФБтФБтФБтФБтФБтФБтФБтФБтФБтФБ\n"
        f"ЁЯЖФ ID: `{user['id']}`\n"
        f"ЁЯСд Name: {user.get('full_name', 'N/A')}\n"
        f"ЁЯУ▒ Username: {username}\n"
        f"ЁЯТ░ Balance: {user.get('balance', 0)} BDT\n"
        f"ЁЯЫТ Total Orders: {user.get('total_orders', 0)}\n"
        f"ЁЯСе Referrals: {user.get('referral_count', 0)}\n"
        f"ЁЯТ╕ Total Earned: {user.get('total_earned', 0)} BDT\n"
        f"ЁЯУЕ Joined: {format_date(user.get('joined_at', ''))}\n"
        f"тЪб Status: {status}"
    )


def format_deposit(deposit):
    return (
        f"ЁЯТ│ *Deposit Request*\n"
        f"тФБтФБтФБтФБтФБтФБтФБтФБтФБтФБтФБтФБтФБтФБтФБ\n"
        f"ЁЯЖФ Dep ID: `{deposit.get('dep_id')}`\n"
        f"ЁЯСд User: @{deposit.get('username', 'N/A')} (`{deposit.get('user_id')}`)\n"
        f"ЁЯТ░ Amount: *{deposit.get('amount')} BDT*\n"
        f"ЁЯз╛ TrxID: `{deposit.get('trx_id')}`\n"
        f"ЁЯУ▒ Phone: `{deposit.get('phone')}`\n"
        f"ЁЯУЕ Time: {format_date(deposit.get('created_at', ''))}\n"
        f"тЪб Status: {deposit.get('status', 'pending').upper()}"
    )


def users_to_txt(users, filter_type="all"):
    if filter_type == "banned":
        title = "SpyX Bot - Banned Users"
        user_list = [u for u in users.values() if u.get("is_banned")]
    else:
        title = "SpyX Bot - All Users"
        user_list = list(users.values())
    lines = [title, "=" * 50, ""]
    for u in user_list:
        username = f"@{u['username']}" if u.get("username") else "No username"
        lines += [
            f"ID: {u['id']}", f"Name: {u.get('full_name','N/A')}",
            f"Username: {username}", f"Balance: {u.get('balance',0)} BDT",
            f"Orders: {u.get('total_orders',0)}",
            f"Status: {'BANNED' if u.get('is_banned') else 'ACTIVE'}",
            f"Joined: {format_date(u.get('joined_at',''))}", "-" * 30
        ]
    return "\n".join(lines)


def deposits_to_txt(deposits):
    lines = ["SpyX Bot - Deposit Requests", "=" * 50, ""]
    for dep in deposits.values():
        lines += [
            f"Dep ID: {dep.get('dep_id')}", f"User: @{dep.get('username','N/A')} ({dep.get('user_id')})",
            f"Amount: {dep.get('amount')} BDT", f"TrxID: {dep.get('trx_id')}",
            f"Phone: {dep.get('phone')}", f"Status: {dep.get('status','').upper()}",
            f"Time: {format_date(dep.get('created_at',''))}", "-" * 30
        ]
    return "\n".join(lines)


def make_txt_file(content, filename):
    buf = io.BytesIO()
    buf.write(content.encode("utf-8"))
    buf.seek(0)
    buf.name = filename
    return buf


def is_admin(user_id):
    return user_id == ADMIN_ID


# ============================================================
# тМия╕П KEYBOARDS
# ============================================================

def main_menu_kb():
    return ReplyKeyboardMarkup([
        ["ЁЯСд My Account",    "ЁЯТ░ Check Balance"],
        ["ЁЯФТ Buy VPN",       "ЁЯМР Buy Proxy"],
        ["ЁЯУЛ My Orders",     "ЁЯТ│ Deposit Money"],
        ["ЁЯОБ Referral",      "ЁЯОз Support"]
    ], resize_keyboard=True)


def admin_menu_kb():
    return ReplyKeyboardMarkup([
        ["ЁЯУж Products",        "ЁЯУБ Stock"],
        ["ЁЯУЛ Pending Deposits","ЁЯСе Users"],
        ["ЁЯУв Broadcast",       "ЁЯСд Personal Message"],
        ["ЁЯТ░ Payment Settings","ЁЯОБ Referral Settings"],
        ["ЁЯУК Statistics",      "ЁЯФЩ User Menu"]
    ], resize_keyboard=True)


def cancel_kb():
    return ReplyKeyboardMarkup([["тЭМ Cancel"]], resize_keyboard=True)


def support_inline():
    return InlineKeyboardMarkup([[
        InlineKeyboardButton("ЁЯОз Contact Support", url=f"https://t.me/{SUPPORT_USERNAME.lstrip('@')}")
    ]])


def products_inline(products, category):
    keyboard = []
    for pid, product in products.items():
        stock = get_stock_count(pid)
        stock_text = f" ({stock} left)" if stock > 0 else " (Out of stock)"
        emoji = "ЁЯФТ" if category == "vpn" else "ЁЯМР"
        keyboard.append([InlineKeyboardButton(
            f"{emoji} {product['name']} тАФ {product['price']} {CURRENCY}{stock_text}",
            callback_data=f"buy_{pid}"
        )])
    keyboard.append([InlineKeyboardButton("ЁЯФЩ Back", callback_data="back_main")])
    return InlineKeyboardMarkup(keyboard)


def confirm_purchase_inline(product_id):
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("тЬЕ Confirm Purchase", callback_data=f"confirm_buy_{product_id}")],
        [InlineKeyboardButton("тЭМ Cancel",           callback_data="back_main")]
    ])


def orders_pagination_inline(page, total_pages):
    nav = []
    if page > 1:
        nav.append(InlineKeyboardButton("тмЕя╕П Prev", callback_data=f"orders_page_{page-1}"))
    nav.append(InlineKeyboardButton(f"ЁЯУД {page}/{total_pages}", callback_data="noop"))
    if page < total_pages:
        nav.append(InlineKeyboardButton("Next тЮбя╕П", callback_data=f"orders_page_{page+1}"))
    return InlineKeyboardMarkup([nav]) if nav else None


def admin_deposit_inline(dep_id):
    return InlineKeyboardMarkup([[
        InlineKeyboardButton("тЬЕ Approve", callback_data=f"approve_dep_{dep_id}"),
        InlineKeyboardButton("тЭМ Reject",  callback_data=f"reject_dep_{dep_id}")
    ]])


def admin_deposits_pagination_inline(page, total_pages):
    nav = []
    if page > 1:
        nav.append(InlineKeyboardButton("тмЕя╕П Prev", callback_data=f"deps_page_{page-1}"))
    nav.append(InlineKeyboardButton(f"ЁЯУД {page}/{total_pages}", callback_data="noop"))
    if page < total_pages:
        nav.append(InlineKeyboardButton("Next тЮбя╕П", callback_data=f"deps_page_{page+1}"))
    keyboard = [nav] if nav else []
    keyboard.append([InlineKeyboardButton("ЁЯУе Download .txt", callback_data="download_deposits")])
    return InlineKeyboardMarkup(keyboard)


def admin_users_inline(page, total_pages, filter_type="all"):
    nav = []
    if page > 1:
        nav.append(InlineKeyboardButton("тмЕя╕П Prev", callback_data=f"users_{filter_type}_{page-1}"))
    nav.append(InlineKeyboardButton(f"ЁЯУД {page}/{total_pages}", callback_data="noop"))
    if page < total_pages:
        nav.append(InlineKeyboardButton("Next тЮбя╕П", callback_data=f"users_{filter_type}_{page+1}"))
    keyboard = [nav] if nav else []
    keyboard.append([InlineKeyboardButton("ЁЯУе Download .txt", callback_data=f"download_users_{filter_type}")])
    return InlineKeyboardMarkup(keyboard)


def admin_user_actions_inline(user_id, is_banned):
    ban_text = "тЬЕ Unban" if is_banned else "ЁЯЪл Ban"
    ban_cb   = f"unban_{user_id}" if is_banned else f"ban_{user_id}"
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(ban_text, callback_data=ban_cb)],
        [InlineKeyboardButton("ЁЯТ░ Add Balance",   callback_data=f"add_bal_{user_id}"),
         InlineKeyboardButton("ЁЯТ╕ Deduct Balance", callback_data=f"deduct_bal_{user_id}")],
        [InlineKeyboardButton("ЁЯУЛ View Orders",   callback_data=f"user_orders_{user_id}")],
        [InlineKeyboardButton("тЬЙя╕П Send Message",  callback_data=f"msg_user_{user_id}")]
    ])


def admin_products_list_inline(products):
    keyboard = []
    for pid, p in products.items():
        status = "ЁЯЯв" if p.get("is_active") else "ЁЯФ┤"
        cat    = "ЁЯФТ" if p.get("category") == "vpn" else "ЁЯМР"
        keyboard.append([InlineKeyboardButton(
            f"{status} {cat} {p['name']} тАФ {p['price']} {CURRENCY}",
            callback_data=f"view_prod_{pid}"
        )])
    keyboard.append([InlineKeyboardButton("тЮХ Add New Product", callback_data="add_product")])
    return InlineKeyboardMarkup(keyboard)


def admin_product_actions_inline(product_id, is_active):
    status_text = "ЁЯФ┤ Disable" if is_active else "ЁЯЯв Enable"
    status_cb   = f"disable_prod_{product_id}" if is_active else f"enable_prod_{product_id}"
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("тЬПя╕П Edit Name",     callback_data=f"edit_prod_name_{product_id}"),
         InlineKeyboardButton("ЁЯТ▓ Edit Price",    callback_data=f"edit_prod_price_{product_id}")],
        [InlineKeyboardButton("ЁЯУЕ Edit Duration", callback_data=f"edit_prod_duration_{product_id}"),
         InlineKeyboardButton(status_text,        callback_data=status_cb)],
        [InlineKeyboardButton("ЁЯЧСя╕П Delete",        callback_data=f"delete_prod_{product_id}")]
    ])


def product_category_inline():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("ЁЯФТ VPN",   callback_data="addprod_vpn"),
         InlineKeyboardButton("ЁЯМР Proxy", callback_data="addprod_proxy")],
        [InlineKeyboardButton("тЭМ Cancel", callback_data="back_main")]
    ])


# ============================================================
# ЁЯСд USER HANDLERS
# ============================================================

async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    args = context.args
    referred_by = None
    if args and args[0].startswith("ref"):
        try:
            ref_id = int(args[0][3:])
            if ref_id != user.id:
                referred_by = ref_id
        except:
            pass

    db_user = create_user(user.id, user.username, user.full_name, referred_by)
    if db_user.get("is_banned"):
        await update.message.reply_text("ЁЯЪл You have been banned from using this bot.")
        return

    settings = get_settings()
    welcome  = settings.get("welcome_message", f"Welcome to {BOT_NAME}!")
    await update.message.reply_text(
        f"ЁЯСЛ *{welcome}*",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=main_menu_kb()
    )


async def show_my_account(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user    = get_user(user_id)
    if not user:
        await update.message.reply_text("тЭМ Account not found. Please /start again.")
        return
    username = f"@{user['username']}" if user.get("username") else "No username"
    ref_link = f"https://t.me/{context.bot.username}?start=ref{user_id}"
    await update.message.reply_text(
        f"ЁЯСд *My Account*\n"
        f"тФБтФБтФБтФБтФБтФБтФБтФБтФБтФБтФБтФБтФБтФБтФБ\n"
        f"ЁЯЖФ ID: `{user['id']}`\n"
        f"ЁЯСд Username: {username}\n"
        f"ЁЯТ░ Balance: *{user.get('balance', 0)} {CURRENCY}*\n"
        f"ЁЯЫТ Total Orders: {user.get('total_orders', 0)}\n"
        f"ЁЯСе Referrals: {user.get('referral_count', 0)}\n"
        f"ЁЯУЕ Joined: {format_date(user.get('joined_at', ''))}\n\n"
        f"ЁЯФЧ Your Referral Link:\n`{ref_link}`",
        parse_mode=ParseMode.MARKDOWN
    )


async def show_check_balance(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = get_user(update.effective_user.id)
    if not user:
        await update.message.reply_text("тЭМ Account not found.")
        return
    await update.message.reply_text(
        f"ЁЯТ░ *Your Balance*\n\nAvailable: *{user.get('balance', 0)} {CURRENCY}*",
        parse_mode=ParseMode.MARKDOWN
    )


async def show_my_orders(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await show_orders_page(update, context, update.effective_user.id, page=1, edit=False)


async def show_orders_page(update, context, user_id, page=1, edit=False):
    orders, total, total_pages = get_user_orders(user_id, page)
    if not orders:
        text = "ЁЯУЛ *My Orders*\n\nYou have no orders yet."
        if edit and update.callback_query:
            await update.callback_query.edit_message_text(text, parse_mode=ParseMode.MARKDOWN)
        else:
            msg = update.callback_query.message if update.callback_query else update.message
            await msg.reply_text(text, parse_mode=ParseMode.MARKDOWN)
        return

    text   = f"ЁЯУЛ *My Orders* тАФ Page {page}/{total_pages}\nтФБтФБтФБтФБтФБтФБтФБтФБтФБтФБтФБтФБтФБтФБтФБ\n\n"
    text  += "\n\n".join(format_order(o) for o in orders)
    markup = orders_pagination_inline(page, total_pages) if total_pages > 1 else None

    if edit and update.callback_query:
        await update.callback_query.edit_message_text(text, parse_mode=ParseMode.MARKDOWN, reply_markup=markup)
    else:
        msg = update.callback_query.message if update.callback_query else update.message
        await msg.reply_text(text, parse_mode=ParseMode.MARKDOWN, reply_markup=markup)


async def show_referral(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id  = update.effective_user.id
    user     = get_user(user_id)
    settings = get_settings()
    commission = settings.get("referral_commission", 10)
    ref_link   = f"https://t.me/{context.bot.username}?start=ref{user_id}"
    await update.message.reply_text(
        f"ЁЯОБ *Referral System*\n"
        f"тФБтФБтФБтФБтФБтФБтФБтФБтФБтФБтФБтФБтФБтФБтФБ\n"
        f"ЁЯТ╕ Commission Rate: *{commission}%*\n\n"
        f"ЁЯСе Total Referred: *{user.get('referral_count', 0)} users*\n"
        f"ЁЯТ░ Total Earned: *{user.get('total_earned', 0)} {CURRENCY}*\n\n"
        f"ЁЯУМ *How it works:*\n"
        f"1я╕ПтГг Share your referral link\n"
        f"2я╕ПтГг Friend joins & deposits\n"
        f"3я╕ПтГг You earn {commission}% commission!\n"
        f"4я╕ПтГг Use balance to buy VPN/Proxy\n\n"
        f"ЁЯФЧ *Your Referral Link:*\n`{ref_link}`",
        parse_mode=ParseMode.MARKDOWN
    )


async def show_support(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        f"ЁЯОз *Support*\n\nNeed help? Contact our support team!\n\nЁЯСЙ Tap the button below.",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=support_inline()
    )


async def show_buy_vpn(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = get_user(update.effective_user.id)
    if user and user.get("is_banned"):
        await update.message.reply_text("ЁЯЪл You are banned.")
        return
    products = get_products_by_category("vpn")
    if not products:
        await update.message.reply_text("тЭМ No VPN products available right now.")
        return
    await update.message.reply_text(
        f"ЁЯФТ *Buy VPN*\n\nЁЯТ░ Your Balance: *{user.get('balance', 0)} {CURRENCY}*\n\nSelect a package:",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=products_inline(products, "vpn")
    )


async def show_buy_proxy(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = get_user(update.effective_user.id)
    if user and user.get("is_banned"):
        await update.message.reply_text("ЁЯЪл You are banned.")
        return
    products = get_products_by_category("proxy")
    if not products:
        await update.message.reply_text("тЭМ No Proxy products available right now.")
        return
    await update.message.reply_text(
        f"ЁЯМР *Buy Proxy*\n\nЁЯТ░ Your Balance: *{user.get('balance', 0)} {CURRENCY}*\n\nSelect a package:",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=products_inline(products, "proxy")
    )


async def show_deposit_money(update: Update, context: ContextTypes.DEFAULT_TYPE):
    settings = get_settings()
    bkash    = settings.get("bkash") or "Not set"
    nagad    = settings.get("nagad") or "Not set"
    await update.message.reply_text(
        f"ЁЯТ│ *Deposit Money*\n"
        f"тФБтФБтФБтФБтФБтФБтФБтФБтФБтФБтФБтФБтФБтФБтФБ\n"
        f"Send money to any of these numbers:\n\n"
        f"ЁЯТЪ *bKash:* `{bkash}`\n"
        f"ЁЯЯа *Nagad:* `{nagad}`\n\n"
        f"After payment, tap below to submit:",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=InlineKeyboardMarkup([[
            InlineKeyboardButton("ЁЯУд Submit Payment", callback_data="submit_deposit")
        ]])
    )


# ============================================================
# тЪЩя╕П ADMIN HANDLERS
# ============================================================

async def show_admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        return
    s = get_stats()
    await update.message.reply_text(
        f"тЪЩя╕П *Admin Panel*\n"
        f"тФБтФБтФБтФБтФБтФБтФБтФБтФБтФБтФБтФБтФБтФБтФБ\n"
        f"ЁЯСе Total Users: {s['total_users']}\n"
        f"тП│ Pending Deposits: {s['pending_deposits']}\n"
        f"ЁЯЫТ Total Orders: {s['total_orders']}\n\n"
        f"Select an option:",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=admin_menu_kb()
    )


async def show_admin_products(update: Update, context: ContextTypes.DEFAULT_TYPE):
    products = get_all_products()
    text = f"ЁЯУж *Products* ({len(products)} total)\n\nSelect to manage:" if products else "ЁЯУж *Products*\n\nNo products yet."
    await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN,
                                    reply_markup=admin_products_list_inline(products))


async def show_admin_stock(update: Update, context: ContextTypes.DEFAULT_TYPE):
    products = get_all_products()
    if not products:
        await update.message.reply_text("тЭМ No products found. Add products first.")
        return
    keyboard = []
    for pid, p in products.items():
        stock = get_stock_count(pid)
        emoji = "ЁЯФТ" if p.get("category") == "vpn" else "ЁЯМР"
        keyboard.append([InlineKeyboardButton(
            f"{emoji} {p['name']} тАФ {stock} in stock",
            callback_data=f"manage_stock_{pid}"
        )])
    await update.message.reply_text(
        "ЁЯУБ *Stock Management*\n\nSelect product to add stock:",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=InlineKeyboardMarkup(keyboard)
    )


async def show_pending_deposits(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await _send_deposits_page(update.message, context, page=1)


async def _send_deposits_page(msg_or_query, context, page=1):
    deposits, total, total_pages = get_pending_deposits(page)
    is_query = hasattr(msg_or_query, 'edit_message_text')

    if not deposits:
        text = "ЁЯУЛ *Pending Deposits*\n\nNo pending requests."
        if is_query:
            await msg_or_query.edit_message_text(text, parse_mode=ParseMode.MARKDOWN)
        else:
            await msg_or_query.reply_text(text, parse_mode=ParseMode.MARKDOWN)
        return

    header = f"ЁЯУЛ *Pending Deposits* ({total} total) тАФ Page {page}/{total_pages}\nтФБтФБтФБтФБтФБтФБтФБтФБтФБтФБтФБтФБтФБтФБтФБ"
    if is_query:
        await msg_or_query.edit_message_text(header, parse_mode=ParseMode.MARKDOWN)
        send_fn = msg_or_query.message.reply_text
    else:
        await msg_or_query.reply_text(header, parse_mode=ParseMode.MARKDOWN)
        send_fn = msg_or_query.reply_text

    for dep in deposits:
        await send_fn(format_deposit(dep), parse_mode=ParseMode.MARKDOWN,
                      reply_markup=admin_deposit_inline(dep["dep_id"]))

    await send_fn(f"ЁЯУД Page {page}/{total_pages}",
                  reply_markup=admin_deposits_pagination_inline(page, total_pages))


async def show_admin_users(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "ЁЯСе *Users Management*\n\nSelect option:",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("ЁЯСе All Users",          callback_data="users_all_1")],
            [InlineKeyboardButton("ЁЯЪл Banned Users",       callback_data="users_banned_1")],
            [InlineKeyboardButton("ЁЯФН Search by Username", callback_data="search_user")]
        ])
    )


async def show_broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["admin_step"] = "broadcast"
    await update.message.reply_text(
        "ЁЯУв *Broadcast Message*\n\nSend the message to broadcast to all users:",
        parse_mode=ParseMode.MARKDOWN, reply_markup=cancel_kb()
    )


async def show_personal_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["admin_step"] = "personal_msg_id"
    await update.message.reply_text(
        "ЁЯСд *Personal Message*\n\nEnter User ID or @username:",
        parse_mode=ParseMode.MARKDOWN, reply_markup=cancel_kb()
    )


async def show_payment_settings(update: Update, context: ContextTypes.DEFAULT_TYPE):
    settings = get_settings()
    await update.message.reply_text(
        "ЁЯТ░ *Payment Settings*\n\nSelect to update:",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton(f"ЁЯТЪ bKash: {settings.get('bkash') or 'Not set'}", callback_data="set_bkash")],
            [InlineKeyboardButton(f"ЁЯЯа Nagad: {settings.get('nagad') or 'Not set'}", callback_data="set_nagad")]
        ])
    )


async def show_referral_settings(update: Update, context: ContextTypes.DEFAULT_TYPE):
    commission = get_settings().get("referral_commission", 10)
    await update.message.reply_text(
        f"ЁЯОБ *Referral Settings*\n\nCurrent Commission: *{commission}%*",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=InlineKeyboardMarkup([[
            InlineKeyboardButton(f"тЬПя╕П Change ({commission}%)", callback_data="set_commission")
        ]])
    )


async def show_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    s = get_stats()
    await update.message.reply_text(
        f"ЁЯУК *Bot Statistics*\n"
        f"тФБтФБтФБтФБтФБтФБтФБтФБтФБтФБтФБтФБтФБтФБтФБ\n"
        f"ЁЯСе Total Users: *{s['total_users']}*\n"
        f"ЁЯЪл Banned Users: *{s['banned_users']}*\n"
        f"тП│ Pending Deposits: *{s['pending_deposits']}*\n"
        f"ЁЯТ░ Total Deposited: *{s['total_deposits']} {CURRENCY}*\n"
        f"ЁЯЫТ Total Orders: *{s['total_orders']}*\n"
        f"ЁЯФТ VPN Orders: *{s['vpn_orders']}*\n"
        f"ЁЯМР Proxy Orders: *{s['proxy_orders']}*",
        parse_mode=ParseMode.MARKDOWN
    )


# ============================================================
# ЁЯТм UNIFIED TEXT HANDLER
# ============================================================

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text    = update.message.text.strip()
    user_id = update.effective_user.id
    step    = context.user_data.get("admin_step", "")
    dep_step= context.user_data.get("deposit_step", "")

    # Ban check
    db_user = get_user(user_id)
    if db_user and db_user.get("is_banned"):
        await update.message.reply_text("ЁЯЪл You are banned from this bot.")
        return

    # Cancel
    if text in ["тЭМ Cancel", "ЁЯФЩ User Menu"]:
        context.user_data.clear()
        await update.message.reply_text("ЁЯПа Main Menu", reply_markup=main_menu_kb())
        return

    # тФАтФА DEPOSIT FLOW тФАтФАтФАтФАтФАтФАтФАтФАтФАтФАтФАтФАтФАтФАтФАтФАтФАтФАтФАтФАтФАтФАтФАтФАтФАтФАтФАтФАтФАтФАтФАтФАтФАтФАтФАтФАтФАтФА
    if dep_step == "amount":
        try:
            amount = float(text)
            if amount <= 0: raise ValueError
            context.user_data["dep_amount"] = amount
            context.user_data["deposit_step"] = "trxid"
            await update.message.reply_text("ЁЯз╛ *Enter Transaction ID:*", parse_mode=ParseMode.MARKDOWN)
        except ValueError:
            await update.message.reply_text("тЭМ Invalid amount. Enter a valid number.")
        return

    if dep_step == "trxid":
        context.user_data["dep_trxid"] = text
        context.user_data["deposit_step"] = "phone"
        await update.message.reply_text("ЁЯУ▒ *Enter the phone number used for payment:*", parse_mode=ParseMode.MARKDOWN)
        return

    if dep_step == "phone":
        user   = update.effective_user
        amount = context.user_data.get("dep_amount")
        trxid  = context.user_data.get("dep_trxid")
        phone  = text
        dep_id = create_deposit(user.id, user.username, amount, trxid, phone)
        context.user_data.clear()
        await update.message.reply_text(
            f"тЬЕ *Deposit Submitted!*\n"
            f"тФБтФБтФБтФБтФБтФБтФБтФБтФБтФБтФБтФБтФБтФБтФБ\n"
            f"ЁЯТ░ Amount: *{amount} {CURRENCY}*\n"
            f"ЁЯз╛ TrxID: `{trxid}`\n"
            f"ЁЯУ▒ Phone: `{phone}`\n"
            f"ЁЯЖФ Dep ID: `{dep_id}`\n\n"
            f"тП│ Waiting for admin approval...",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=main_menu_kb()
        )
        try:
            await context.bot.send_message(
                ADMIN_ID,
                f"ЁЯТ│ *New Deposit Request!*\n"
                f"тФБтФБтФБтФБтФБтФБтФБтФБтФБтФБтФБтФБтФБтФБтФБ\n"
                f"ЁЯСд @{user.username or 'N/A'} (`{user.id}`)\n"
                f"ЁЯТ░ Amount: *{amount} {CURRENCY}*\n"
                f"ЁЯз╛ TrxID: `{trxid}`\n"
                f"ЁЯУ▒ Phone: `{phone}`\n"
                f"ЁЯЖФ Dep ID: `{dep_id}`",
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=admin_deposit_inline(dep_id)
            )
        except: pass
        return

    # тФАтФА ADMIN STEPS тФАтФАтФАтФАтФАтФАтФАтФАтФАтФАтФАтФАтФАтФАтФАтФАтФАтФАтФАтФАтФАтФАтФАтФАтФАтФАтФАтФАтФАтФАтФАтФАтФАтФАтФАтФАтФАтФАтФА
    if is_admin(user_id) and step:

        if step == "add_prod_name":
            context.user_data["new_prod_name"] = text
            context.user_data["admin_step"] = "add_prod_price"
            await update.message.reply_text("ЁЯТ▓ Enter price (BDT):", reply_markup=cancel_kb())
            return

        if step == "add_prod_price":
            try:
                context.user_data["new_prod_price"] = float(text)
                context.user_data["admin_step"] = "add_prod_duration"
                await update.message.reply_text("ЁЯУЕ Enter duration (days):", reply_markup=cancel_kb())
            except: await update.message.reply_text("тЭМ Invalid price.")
            return

        if step == "add_prod_duration":
            try:
                duration  = int(text)
                pid       = create_product(
                    context.user_data["new_prod_name"],
                    context.user_data["new_prod_price"],
                    context.user_data["new_prod_category"],
                    duration
                )
                name  = context.user_data["new_prod_name"]
                price = context.user_data["new_prod_price"]
                context.user_data.clear()
                await update.message.reply_text(
                    f"тЬЕ *Product Added!*\nЁЯУМ {name}\nЁЯТ░ {price} {CURRENCY}\nЁЯУЕ {duration} days",
                    parse_mode=ParseMode.MARKDOWN, reply_markup=admin_menu_kb()
                )
            except: await update.message.reply_text("тЭМ Invalid duration.")
            return

        if step == "edit_prod_name":
            pid = context.user_data.get("edit_prod_id")
            p   = get_product(pid)
            if p:
                p["name"] = text
                save_product(pid, p)
                context.user_data.clear()
                await update.message.reply_text(f"тЬЕ Name updated to *{text}*", parse_mode=ParseMode.MARKDOWN, reply_markup=admin_menu_kb())
            return

        if step == "edit_prod_price":
            pid = context.user_data.get("edit_prod_id")
            p   = get_product(pid)
            try:
                p["price"] = float(text)
                save_product(pid, p)
                context.user_data.clear()
                await update.message.reply_text(f"тЬЕ Price updated to *{text} {CURRENCY}*", parse_mode=ParseMode.MARKDOWN, reply_markup=admin_menu_kb())
            except: await update.message.reply_text("тЭМ Invalid price.")
            return

        if step == "edit_prod_duration":
            pid = context.user_data.get("edit_prod_id")
            p   = get_product(pid)
            try:
                p["duration_days"] = int(text)
                save_product(pid, p)
                context.user_data.clear()
                await update.message.reply_text(f"тЬЕ Duration updated to *{text} days*", parse_mode=ParseMode.MARKDOWN, reply_markup=admin_menu_kb())
            except: await update.message.reply_text("тЭМ Invalid duration.")
            return

        if step == "add_stock":
            if text == "/done":
                pid   = context.user_data.get("stock_product_id")
                count = get_stock_count(pid)
                context.user_data.clear()
                await update.message.reply_text(
                    f"тЬЕ Done! Total stock: *{count}*",
                    parse_mode=ParseMode.MARKDOWN, reply_markup=admin_menu_kb()
                )
            else:
                pid = context.user_data.get("stock_product_id")
                add_stock(pid, text)
                await update.message.reply_text(
                    f"тЬЕ Added! Stock: *{get_stock_count(pid)}*\nAdd more or /done",
                    parse_mode=ParseMode.MARKDOWN
                )
            return

        if step == "search_user":
            found = search_user_by_username(text)
            context.user_data.clear()
            if found:
                await update.message.reply_text(
                    format_user_info(found), parse_mode=ParseMode.MARKDOWN,
                    reply_markup=admin_user_actions_inline(found["id"], found.get("is_banned", False))
                )
            else:
                await update.message.reply_text(f"тЭМ User @{text.lstrip('@')} not found.")
            return

        if step == "balance_amount":
            try:
                amount    = float(text)
                target_id = context.user_data.get("balance_user_id")
                action    = context.user_data.get("balance_action")
                final_amt = amount if action == "add" else -amount
                new_bal   = update_user_balance(target_id, final_amt)
                context.user_data.clear()
                verb = "added to" if final_amt > 0 else "deducted from"
                await update.message.reply_text(
                    f"тЬЕ *{abs(final_amt)} {CURRENCY}* {verb} user `{target_id}`\nNew balance: *{new_bal} {CURRENCY}*",
                    parse_mode=ParseMode.MARKDOWN, reply_markup=admin_menu_kb()
                )
                try:
                    msg = (f"ЁЯТ░ *{amount} {CURRENCY}* added to your balance by admin.\nNew Balance: *{new_bal} {CURRENCY}*"
                           if final_amt > 0 else
                           f"ЁЯТ╕ *{amount} {CURRENCY}* deducted from your balance by admin.\nNew Balance: *{new_bal} {CURRENCY}*")
                    await context.bot.send_message(target_id, msg, parse_mode=ParseMode.MARKDOWN)
                except: pass
            except: await update.message.reply_text("тЭМ Invalid amount.")
            return

        if step == "set_bkash":
            update_setting("bkash", text)
            context.user_data.clear()
            await update.message.reply_text(f"тЬЕ bKash updated: `{text}`", parse_mode=ParseMode.MARKDOWN, reply_markup=admin_menu_kb())
            return

        if step == "set_nagad":
            update_setting("nagad", text)
            context.user_data.clear()
            await update.message.reply_text(f"тЬЕ Nagad updated: `{text}`", parse_mode=ParseMode.MARKDOWN, reply_markup=admin_menu_kb())
            return

        if step == "set_commission":
            try:
                rate = float(text)
                if 0 <= rate <= 100:
                    update_setting("referral_commission", rate)
                    context.user_data.clear()
                    await update.message.reply_text(f"тЬЕ Commission updated to *{rate}%*", parse_mode=ParseMode.MARKDOWN, reply_markup=admin_menu_kb())
                else:
                    await update.message.reply_text("тЭМ Enter value 0тАУ100.")
            except: await update.message.reply_text("тЭМ Invalid value.")
            return

        if step == "broadcast":
            users = get_all_users()
            sent = failed = 0
            for uid in users:
                try:
                    await context.bot.send_message(int(uid), text, parse_mode=ParseMode.MARKDOWN)
                    sent += 1
                except: failed += 1
            context.user_data.clear()
            await update.message.reply_text(
                f"ЁЯУв *Broadcast Complete!*\nтЬЕ Sent: {sent}\nтЭМ Failed: {failed}",
                parse_mode=ParseMode.MARKDOWN, reply_markup=admin_menu_kb()
            )
            return

        if step == "personal_msg_id":
            target = None
            if text.startswith("@"):
                found = search_user_by_username(text)
                if found: target = found["id"]
            else:
                try:
                    t = int(text)
                    if get_user(t): target = t
                except: pass
            if target:
                context.user_data["personal_msg_target"] = target
                context.user_data["admin_step"] = "personal_msg_text"
                await update.message.reply_text(f"тЬЕ User `{target}` found.\n\nEnter message:", parse_mode=ParseMode.MARKDOWN)
            else:
                await update.message.reply_text("тЭМ User not found.")
            return

        if step == "personal_msg_text":
            target = context.user_data.get("personal_msg_target")
            try:
                await context.bot.send_message(target, text, parse_mode=ParseMode.MARKDOWN)
                context.user_data.clear()
                await update.message.reply_text("тЬЕ Message sent!", reply_markup=admin_menu_kb())
            except: await update.message.reply_text("тЭМ Failed to send.")
            return

    # тФАтФА MENU ROUTING тФАтФАтФАтФАтФАтФАтФАтФАтФАтФАтФАтФАтФАтФАтФАтФАтФАтФАтФАтФАтФАтФАтФАтФАтФАтФАтФАтФАтФАтФАтФАтФАтФАтФАтФАтФАтФАтФА
    routes = {
        "ЁЯСд My Account":   show_my_account,
        "ЁЯТ░ Check Balance":show_check_balance,
        "ЁЯФТ Buy VPN":      show_buy_vpn,
        "ЁЯМР Buy Proxy":    show_buy_proxy,
        "ЁЯУЛ My Orders":    show_my_orders,
        "ЁЯТ│ Deposit Money":show_deposit_money,
        "ЁЯОБ Referral":     show_referral,
        "ЁЯОз Support":      show_support,
    }
    if text in routes:
        await routes[text](update, context)
        return

    if is_admin(user_id):
        admin_routes = {
            "ЁЯУж Products":         show_admin_products,
            "ЁЯУБ Stock":            show_admin_stock,
            "ЁЯУЛ Pending Deposits": show_pending_deposits,
            "ЁЯСе Users":            show_admin_users,
            "ЁЯУв Broadcast":        show_broadcast,
            "ЁЯСд Personal Message": show_personal_message,
            "ЁЯТ░ Payment Settings": show_payment_settings,
            "ЁЯОБ Referral Settings":show_referral_settings,
            "ЁЯУК Statistics":       show_stats,
        }
        if text in admin_routes:
            await admin_routes[text](update, context)


# ============================================================
# ЁЯФШ CALLBACK QUERY HANDLER
# ============================================================

async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    data  = query.data
    uid   = update.effective_user.id

    await query.answer()

    # Noop
    if data == "noop":
        return

    # Back to main
    if data == "back_main":
        await query.edit_message_text("ЁЯПа Use the menu below.")
        return

    # Submit deposit
    if data == "submit_deposit":
        context.user_data["deposit_step"] = "amount"
        await query.edit_message_text("ЁЯТ░ *Enter amount (BDT):*\nExample: `500`", parse_mode=ParseMode.MARKDOWN)
        return

    # Go deposit shortcut
    if data == "go_deposit":
        settings = get_settings()
        bkash = settings.get("bkash") or "Not set"
        nagad = settings.get("nagad") or "Not set"
        context.user_data["deposit_step"] = "amount"
        await query.edit_message_text(
            f"ЁЯТ│ bKash: `{bkash}`\nNagad: `{nagad}`\n\nЁЯТ░ Enter amount (BDT):",
            parse_mode=ParseMode.MARKDOWN
        )
        return

    # Buy product
    if data.startswith("buy_") and not data.startswith("buy_vpn") and not data.startswith("buy_proxy"):
        product_id = data.replace("buy_", "")
        product    = get_product(product_id)
        if not product:
            await query.edit_message_text("тЭМ Product not found.")
            return
        user  = get_user(uid)
        stock = get_stock_count(product_id)
        emoji = "ЁЯФТ" if product.get("category") == "vpn" else "ЁЯМР"
        text  = (
            f"{emoji} *{product['name']}*\n"
            f"тФБтФБтФБтФБтФБтФБтФБтФБтФБтФБтФБтФБтФБтФБтФБ\n"
            f"ЁЯТ░ Price: *{product['price']} {CURRENCY}*\n"
            f"ЁЯУЕ Duration: *{product['duration_days']} days*\n"
            f"ЁЯУж Stock: *{stock} available*\n\n"
            f"ЁЯТ│ Your Balance: *{user.get('balance', 0)} {CURRENCY}*\n"
        )
        if user.get("balance", 0) < product["price"]:
            text += f"\nтЭМ *Insufficient balance!*\nNeeded: {product['price']} | Have: {user.get('balance', 0)}"
            await query.edit_message_text(text, parse_mode=ParseMode.MARKDOWN,
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("ЁЯТ│ Deposit", callback_data="go_deposit"),
                     InlineKeyboardButton("ЁЯФЩ Back",    callback_data="back_main")]
                ]))
            return
        if stock == 0:
            text += "\nтЭМ *Out of stock!*"
            await query.edit_message_text(text, parse_mode=ParseMode.MARKDOWN,
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("ЁЯФЩ Back", callback_data="back_main")]]))
            return
        text += "\nтЬЕ Ready to purchase!"
        await query.edit_message_text(text, parse_mode=ParseMode.MARKDOWN,
                                      reply_markup=confirm_purchase_inline(product_id))
        return

    # Confirm buy
    if data.startswith("confirm_buy_"):
        product_id = data.replace("confirm_buy_", "")
        product    = get_product(product_id)
        user       = get_user(uid)
        if not product:
            await query.edit_message_text("тЭМ Product not found.")
            return
        if user.get("balance", 0) < product["price"]:
            await query.edit_message_text("тЭМ Insufficient balance.")
            return
        credential = pop_stock(product_id)
        if not credential:
            await query.edit_message_text("тЭМ Out of stock!")
            return
        expiry_date = get_expiry_date(product["duration_days"])
        order_id    = create_order(uid, product_id, product["name"], product["category"],
                                   credential, product["price"], product["duration_days"], expiry_date)
        update_user_balance(uid, -product["price"])
        parts = credential.split(":")
        if len(parts) == 2:
            cred_text = f"ЁЯСд Username: `{parts[0]}`\nЁЯФС Password: `{parts[1]}`"
        elif len(parts) >= 3:
            cred_text = f"ЁЯМР Proxy: `{credential}`"
        else:
            cred_text = f"ЁЯУЛ Details: `{credential}`"
        emoji = "ЁЯФТ" if product.get("category") == "vpn" else "ЁЯМР"
        new_balance = get_user(uid).get("balance", 0)
        await query.edit_message_text(
            f"тЬЕ *Purchase Successful!*\n"
            f"тФБтФБтФБтФБтФБтФБтФБтФБтФБтФБтФБтФБтФБтФБтФБ\n"
            f"{emoji} *{product['name']}*\n"
            f"ЁЯЖФ Order: `{order_id}`\n"
            f"ЁЯУЕ Expires: {format_date(expiry_date)}\n\n"
            f"ЁЯУЛ *Your Credentials:*\n{cred_text}\n\n"
            f"ЁЯТ░ Remaining Balance: *{new_balance} {CURRENCY}*\n\n"
            f"Thank you! ЁЯОЙ",
            parse_mode=ParseMode.MARKDOWN
        )
        try:
            await context.bot.send_message(
                ADMIN_ID,
                f"ЁЯЫТ *New Order!*\nЁЯСд `{uid}`\nЁЯУж {product['name']}\nЁЯТ░ {product['price']} {CURRENCY}\nЁЯЖФ `{order_id}`",
                parse_mode=ParseMode.MARKDOWN
            )
        except: pass

        # Stock low alert
        remaining = get_stock_count(product_id)
        if remaining <= 2:
            try:
                await context.bot.send_message(
                    ADMIN_ID,
                    f"тЪая╕П *Low Stock Alert!*\n{emoji} {product['name']}\nRemaining: *{remaining}*",
                    parse_mode=ParseMode.MARKDOWN
                )
            except: pass
        return

    # Orders pagination
    if data.startswith("orders_page_"):
        page = int(data.split("_")[-1])
        await show_orders_page(update, context, uid, page, edit=True)
        return

    # Approve deposit
    if data.startswith("approve_dep_"):
        if not is_admin(uid): return
        dep_id = data.replace("approve_dep_", "")
        dep    = get_deposit(dep_id)
        if not dep:
            await query.edit_message_text("тЭМ Not found.")
            return
        if dep.get("status") != "pending":
            await query.edit_message_text(f"тЪая╕П Already {dep.get('status')}.")
            return
        amount  = dep.get("amount", 0)
        user_id = dep.get("user_id")
        update_deposit_status(dep_id, "approved")
        new_bal = update_user_balance(user_id, amount)

        # Referral commission
        dep_user = get_user(user_id)
        if dep_user and dep_user.get("referred_by"):
            commission_rate = get_settings().get("referral_commission", 10) / 100
            commission      = round(amount * commission_rate, 2)
            referrer_id     = dep_user["referred_by"]
            referrer        = get_user(referrer_id)
            if referrer:
                update_user_balance(referrer_id, commission)
                referrer["total_earned"] = round(referrer.get("total_earned", 0) + commission, 2)
                save_user(referrer_id, referrer)
                try:
                    await context.bot.send_message(
                        referrer_id,
                        f"ЁЯОБ *Referral Commission!*\nYour referral deposited {amount} {CURRENCY}\nYou earned: *{commission} {CURRENCY}*\nBalance: *{get_user(referrer_id).get('balance',0)} {CURRENCY}*",
                        parse_mode=ParseMode.MARKDOWN
                    )
                except: pass

        await query.edit_message_text(
            f"тЬЕ Approved! User `{user_id}` | Amount: *{amount} {CURRENCY}* | Balance: *{new_bal} {CURRENCY}*",
            parse_mode=ParseMode.MARKDOWN
        )
        try:
            await context.bot.send_message(
                user_id,
                f"тЬЕ *Deposit Approved!*\nЁЯТ░ *{amount} {CURRENCY}* added.\nNew Balance: *{new_bal} {CURRENCY}*\n\nYou can now buy VPN or Proxy! ЁЯОЙ",
                parse_mode=ParseMode.MARKDOWN
            )
        except: pass
        return

    # Reject deposit
    if data.startswith("reject_dep_"):
        if not is_admin(uid): return
        dep_id = data.replace("reject_dep_", "")
        dep    = get_deposit(dep_id)
        if not dep:
            await query.edit_message_text("тЭМ Not found.")
            return
        update_deposit_status(dep_id, "rejected")
        await query.edit_message_text(f"тЭМ Deposit `{dep_id}` rejected.", parse_mode=ParseMode.MARKDOWN)
        try:
            await context.bot.send_message(
                dep.get("user_id"),
                f"тЭМ *Deposit Rejected*\nAmount: *{dep.get('amount')} {CURRENCY}*\nTrxID: `{dep.get('trx_id')}`\n\nContact support if you think this is a mistake.",
                parse_mode=ParseMode.MARKDOWN, reply_markup=support_inline()
            )
        except: pass
        return

    # Deposits pagination
    if data.startswith("deps_page_"):
        if not is_admin(uid): return
        page = int(data.split("_")[-1])
        await _send_deposits_page(query, context, page)
        return

    # Download deposits
    if data == "download_deposits":
        if not is_admin(uid): return
        content = deposits_to_txt(get_all_deposits())
        await query.message.reply_document(make_txt_file(content, "spyx_deposits.txt"), filename="spyx_deposits.txt")
        return

    # View product
    if data.startswith("view_prod_"):
        if not is_admin(uid): return
        pid     = data.replace("view_prod_", "")
        product = get_product(pid)
        if not product:
            await query.edit_message_text("тЭМ Not found.")
            return
        stock  = get_stock_count(pid)
        cat    = "ЁЯФТ VPN" if product.get("category") == "vpn" else "ЁЯМР Proxy"
        status = "ЁЯЯв Active" if product.get("is_active") else "ЁЯФ┤ Disabled"
        await query.edit_message_text(
            f"ЁЯУж *Product Details*\n"
            f"тФБтФБтФБтФБтФБтФБтФБтФБтФБтФБтФБтФБтФБтФБтФБ\n"
            f"ЁЯУМ {product['name']}\n"
            f"ЁЯТ░ {product['price']} {CURRENCY}\n"
            f"ЁЯУЕ {product['duration_days']} days\n"
            f"ЁЯП╖я╕П {cat}\n"
            f"ЁЯУж Stock: *{stock}*\n"
            f"тЪб {status}",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=admin_product_actions_inline(pid, product.get("is_active", True))
        )
        return

    # Add product
    if data == "add_product":
        if not is_admin(uid): return
        context.user_data["admin_step"] = "add_prod_category"
        await query.edit_message_text("тЮХ *Add New Product*\n\nSelect category:",
                                      parse_mode=ParseMode.MARKDOWN, reply_markup=product_category_inline())
        return

    if data.startswith("addprod_"):
        if not is_admin(uid): return
        category = data.replace("addprod_", "")
        context.user_data["new_prod_category"] = category
        context.user_data["admin_step"]        = "add_prod_name"
        await query.edit_message_text(
            f"тЮХ Add *{'VPN' if category == 'vpn' else 'Proxy'}* Product\n\nEnter product name:",
            parse_mode=ParseMode.MARKDOWN
        )
        return

    # Delete product
    if data.startswith("delete_prod_"):
        if not is_admin(uid): return
        pid = data.replace("delete_prod_", "")
        p   = get_product(pid)
        if p:
            delete_product(pid)
            await query.edit_message_text(f"тЬЕ *{p['name']}* deleted.", parse_mode=ParseMode.MARKDOWN)
        return

    # Toggle product
    if data.startswith("enable_prod_") or data.startswith("disable_prod_"):
        if not is_admin(uid): return
        enabled = data.startswith("enable_prod_")
        pid     = data.replace("enable_prod_" if enabled else "disable_prod_", "")
        p       = get_product(pid)
        if p:
            p["is_active"] = enabled
            save_product(pid, p)
            status = "enabled ЁЯЯв" if enabled else "disabled ЁЯФ┤"
            await query.edit_message_text(f"тЬЕ *{p['name']}* {status}.", parse_mode=ParseMode.MARKDOWN)
        return

    # Edit product
    if data.startswith("edit_prod_name_"):
        if not is_admin(uid): return
        context.user_data["edit_prod_id"] = data.replace("edit_prod_name_", "")
        context.user_data["admin_step"]   = "edit_prod_name"
        await query.edit_message_text("тЬПя╕П Enter new product name:")
        return

    if data.startswith("edit_prod_price_"):
        if not is_admin(uid): return
        context.user_data["edit_prod_id"] = data.replace("edit_prod_price_", "")
        context.user_data["admin_step"]   = "edit_prod_price"
        await query.edit_message_text("ЁЯТ▓ Enter new price (BDT):")
        return

    if data.startswith("edit_prod_duration_"):
        if not is_admin(uid): return
        context.user_data["edit_prod_id"] = data.replace("edit_prod_duration_", "")
        context.user_data["admin_step"]   = "edit_prod_duration"
        await query.edit_message_text("ЁЯУЕ Enter new duration (days):")
        return

    # Manage stock
    if data.startswith("manage_stock_"):
        if not is_admin(uid): return
        pid     = data.replace("manage_stock_", "")
        product = get_product(pid)
        context.user_data["admin_step"]       = "add_stock"
        context.user_data["stock_product_id"] = pid
        await query.edit_message_text(
            f"ЁЯУБ *Add Stock тАФ {product['name']}*\n"
            f"Current: *{get_stock_count(pid)}*\n\n"
            f"For VPN: `username:password`\n"
            f"For Proxy: `ip:port:user:pass`\n\n"
            f"Type /done when finished.",
            parse_mode=ParseMode.MARKDOWN
        )
        return

    # Users list
    if data.startswith("users_all_") or data.startswith("users_banned_"):
        if not is_admin(uid): return
        parts       = data.split("_")
        filter_type = parts[1]
        page        = int(parts[2])
        users, total, total_pages = get_paginated_users(page, filter_type)
        if not users:
            await query.edit_message_text(f"No {filter_type} users.")
            return
        title = "ЁЯСе All Users" if filter_type == "all" else "ЁЯЪл Banned Users"
        text  = f"{title} ({total}) тАФ Page {page}/{total_pages}\nтФБтФБтФБтФБтФБтФБтФБтФБтФБтФБтФБтФБтФБтФБтФБ\n\n"
        for u in users:
            uname  = f"@{u['username']}" if u.get("username") else "No username"
            status = "ЁЯЪл" if u.get("is_banned") else "тЬЕ"
            text  += f"{status} `{u['id']}` тАФ {uname} тАФ {u.get('balance',0)} {CURRENCY}\n"
        await query.edit_message_text(text, parse_mode=ParseMode.MARKDOWN,
                                      reply_markup=admin_users_inline(page, total_pages, filter_type))
        return

    # Search user
    if data == "search_user":
        if not is_admin(uid): return
        context.user_data["admin_step"] = "search_user"
        await query.edit_message_text("ЁЯФН Enter username (with or without @):")
        return

    # View user
    if data.startswith("view_user_"):
        if not is_admin(uid): return
        target_id = int(data.replace("view_user_", ""))
        target    = get_user(target_id)
        if not target:
            await query.edit_message_text("тЭМ User not found.")
            return
        await query.edit_message_text(
            format_user_info(target), parse_mode=ParseMode.MARKDOWN,
            reply_markup=admin_user_actions_inline(target_id, target.get("is_banned", False))
        )
        return

    # Ban/Unban
    if data.startswith("ban_") or data.startswith("unban_"):
        if not is_admin(uid): return
        banning   = data.startswith("ban_")
        target_id = int(data.replace("ban_" if banning else "unban_", ""))
        ban_user(target_id, banning)
        action = "banned ЁЯЪл" if banning else "unbanned тЬЕ"
        await query.edit_message_text(f"User `{target_id}` {action}.", parse_mode=ParseMode.MARKDOWN)
        try:
            msg = "ЁЯЪл You have been banned." if banning else "тЬЕ You have been unbanned. Welcome back!"
            await context.bot.send_message(target_id, msg)
        except: pass
        return

    # Balance actions
    if data.startswith("add_bal_") or data.startswith("deduct_bal_"):
        if not is_admin(uid): return
        adding    = data.startswith("add_bal_")
        target_id = int(data.replace("add_bal_" if adding else "deduct_bal_", ""))
        context.user_data["balance_action"]  = "add" if adding else "deduct"
        context.user_data["balance_user_id"] = target_id
        context.user_data["admin_step"]      = "balance_amount"
        verb = "add to" if adding else "deduct from"
        await query.edit_message_text(f"ЁЯТ░ Enter amount to {verb} `{target_id}`'s balance:", parse_mode=ParseMode.MARKDOWN)
        return

    # User orders
    if data.startswith("user_orders_"):
        if not is_admin(uid): return
        target_id = int(data.replace("user_orders_", ""))
        await show_orders_page(update, context, target_id, page=1, edit=True)
        return

    # Send message to user
    if data.startswith("msg_user_"):
        if not is_admin(uid): return
        target_id = int(data.replace("msg_user_", ""))
        context.user_data["personal_msg_target"] = target_id
        context.user_data["admin_step"]          = "personal_msg_text"
        await query.edit_message_text(f"тЬЙя╕П Enter message to send to `{target_id}`:", parse_mode=ParseMode.MARKDOWN)
        return

    # Download users
    if data.startswith("download_users_"):
        if not is_admin(uid): return
        filter_type = data.replace("download_users_", "")
        content     = users_to_txt(get_all_users(), filter_type)
        filename    = f"spyx_{filter_type}_users.txt"
        await query.message.reply_document(make_txt_file(content, filename), filename=filename)
        return

    # Settings callbacks
    if data == "set_bkash":
        if not is_admin(uid): return
        context.user_data["admin_step"] = "set_bkash"
        await query.edit_message_text("ЁЯТЪ Enter new bKash number:")
        return

    if data == "set_nagad":
        if not is_admin(uid): return
        context.user_data["admin_step"] = "set_nagad"
        await query.edit_message_text("ЁЯЯа Enter new Nagad number:")
        return

    if data == "set_commission":
        if not is_admin(uid): return
        context.user_data["admin_step"] = "set_commission"
        await query.edit_message_text("ЁЯОБ Enter commission percentage (0тАУ100):")
        return


# ============================================================
# ЁЯЪА MAIN
# ============================================================

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)

def main():
    init_db()
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("admin", show_admin_panel))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    app.add_handler(CallbackQueryHandler(handle_callback))
    logging.info("ЁЯЪА SpyX Bot started!")
    app.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()
