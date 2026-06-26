# ============================================================
# SpyX Sell Proxy Bot - Single File Version
# python-telegram-bot==21.3 | Python 3.11/3.12/3.13
# ============================================================

import logging, json, os, io
from datetime import datetime, timedelta
from telegram import Update, ReplyKeyboardMarkup, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes
from telegram.constants import ParseMode

# ── CONFIG ────────────────────────────────────────────────────
BOT_TOKEN        = os.environ.get("BOT_TOKEN", "8777803602:AAGT2aXEtxjQ6op9LyvGrs6gboJuB8xzfxE")
ADMIN_ID         = int(os.environ.get("ADMIN_ID", "7095358778"))
SUPPORT_USERNAME = "sadhin8miya"
BOT_NAME         = "SpyX Proxy Bot"
CURRENCY         = "BDT"
PAGE_SIZE        = 10
DATA_DIR         = "data"
USERS_FILE       = "data/users.json"
PRODUCTS_FILE    = "data/products.json"
STOCK_FILE       = "data/stock.json"
ORDERS_FILE      = "data/orders.json"
DEPOSITS_FILE    = "data/deposits.json"
PROVIDERS_FILE   = "data/providers.json"
SETTINGS_FILE    = "data/settings.json"

logging.basicConfig(format="%(asctime)s - %(levelname)s - %(message)s", level=logging.INFO)
logger = logging.getLogger(__name__)

# ── DATABASE ──────────────────────────────────────────────────

def init_db():
    os.makedirs(DATA_DIR, exist_ok=True)
    defaults = {
        USERS_FILE: {}, PRODUCTS_FILE: {}, STOCK_FILE: {},
        ORDERS_FILE: {}, DEPOSITS_FILE: {},
        SETTINGS_FILE: {
            "bkash": "", "nagad": "", "referral_commission": 10,
            "welcome_message": f"Welcome to {BOT_NAME}! 🚀\n\nPremium VPN & Proxy at best prices.\n\n⚡ High Speed  🔒 Secure  ✅ Instant Delivery"
        }
    }
    for f, d in defaults.items():
        if not os.path.exists(f):
            _save(f, d)

def _load(f):
    try:
        with open(f, "r", encoding="utf-8") as fp: return json.load(fp)
    except: return {}

def _save(f, d):
    os.makedirs(os.path.dirname(f), exist_ok=True)
    with open(f, "w", encoding="utf-8") as fp: json.dump(d, fp, ensure_ascii=False, indent=2)

# Users
def get_user(uid): return _load(USERS_FILE).get(str(uid))
def save_user(uid, d): u=_load(USERS_FILE); u[str(uid)]=d; _save(USERS_FILE,u)
def get_all_users(): return _load(USERS_FILE)

def create_user(uid, username, full_name, referred_by=None):
    e = get_user(uid)
    if e: return e
    u = {"id":uid,"username":username or "","full_name":full_name or "","balance":0,
         "referred_by":referred_by,"referral_count":0,"total_earned":0,
         "total_orders":0,"is_banned":False,"joined_at":datetime.now().isoformat()}
    save_user(uid, u)
    if referred_by:
        r = get_user(referred_by)
        if r: r["referral_count"]=r.get("referral_count",0)+1; save_user(referred_by,r)
    return u

def update_balance(uid, amount):
    u = get_user(uid)
    if u: u["balance"]=round(u.get("balance",0)+amount,2); save_user(uid,u); return u["balance"]
    return None

def ban_user(uid, val=True):
    u = get_user(uid)
    if u: u["is_banned"]=val; save_user(uid,u); return True
    return False

def search_by_username(username):
    username = username.lstrip("@").lower()
    for uid, u in _load(USERS_FILE).items():
        if u.get("username","").lower()==username: return u
    return None

def get_users_page(page=1, ftype="all"):
    ul = list(_load(USERS_FILE).values())
    if ftype=="banned": ul=[u for u in ul if u.get("is_banned")]
    ul.sort(key=lambda x: x.get("joined_at",""), reverse=True)
    total=len(ul); pages=max(1,(total+PAGE_SIZE-1)//PAGE_SIZE)
    page=max(1,min(page,pages))
    s=(page-1)*PAGE_SIZE
    return ul[s:s+PAGE_SIZE], total, pages

# Products
def get_product(pid): return _load(PRODUCTS_FILE).get(str(pid))
def save_product(pid, d): p=_load(PRODUCTS_FILE); p[str(pid)]=d; _save(PRODUCTS_FILE,p)
def get_all_products(): return _load(PRODUCTS_FILE)
def delete_product(pid): p=_load(PRODUCTS_FILE); p.pop(str(pid),None); _save(PRODUCTS_FILE,p)

def create_product(name, price, category, days, description="", provider_id=None, provider_name=None, usdt_price=None):
    p=_load(PRODUCTS_FILE); pid=str(int(datetime.now().timestamp()*1000))
    p[pid]={"id":pid,"name":name,"price":price,"usdt_price":usdt_price,"category":category,"duration_days":days,
            "description":description,"provider_id":provider_id,"provider_name":provider_name,
            "is_active":True,"created_at":datetime.now().isoformat()}
    _save(PRODUCTS_FILE,p); return pid

def get_products_by_cat(cat):
    return {k:v for k,v in _load(PRODUCTS_FILE).items() if v.get("category")==cat and v.get("is_active",True)}

# Providers
def get_all_providers():
    return _load(PROVIDERS_FILE)

def get_provider(pid):
    return _load(PROVIDERS_FILE).get(str(pid))

def save_provider(pid, data):
    p=_load(PROVIDERS_FILE); p[str(pid)]=data; _save(PROVIDERS_FILE,p)

def create_provider(name, description=""):
    p=_load(PROVIDERS_FILE); pid=str(int(datetime.now().timestamp()*1000))
    p[pid]={"id":pid,"name":name,"description":description,"is_active":True,"created_at":datetime.now().isoformat()}
    _save(PROVIDERS_FILE,p); return pid

def delete_provider(pid):
    p=_load(PROVIDERS_FILE); p.pop(str(pid),None); _save(PROVIDERS_FILE,p)

def get_proxy_products_by_provider(provider_id):
    return {k:v for k,v in _load(PRODUCTS_FILE).items()
            if v.get("category")=="proxy" and v.get("provider_id")==str(provider_id) and v.get("is_active",True)}

# Stock
def get_stock_count(pid): return sum(1 for i in _load(STOCK_FILE).get(str(pid),[]) if not i.get("used"))

def add_stock(pid, cred):
    s=_load(STOCK_FILE); pid=str(pid)
    if pid not in s: s[pid]=[]
    s[pid].append({"data":cred,"used":False}); _save(STOCK_FILE,s)

def pop_stock(pid):
    s=_load(STOCK_FILE); pid=str(pid)
    for item in s.get(pid,[]):
        if not item.get("used"): item["used"]=True; _save(STOCK_FILE,s); return item["data"]
    return None

# Orders
def create_order(uid, pid, pname, cat, cred, price, days, expiry):
    o=_load(ORDERS_FILE); oid=f"SPX-{int(datetime.now().timestamp()*1000)}"
    o[oid]={"order_id":oid,"user_id":uid,"product_id":pid,"product_name":pname,"category":cat,
            "credential":cred,"price":price,"duration_days":days,"expiry_date":expiry,
            "status":"active","created_at":datetime.now().isoformat()}
    _save(ORDERS_FILE,o)
    u=get_user(uid)
    if u: u["total_orders"]=u.get("total_orders",0)+1; save_user(uid,u)
    return oid

def get_user_orders(uid, page=1):
    ol=[o for o in _load(ORDERS_FILE).values() if o.get("user_id")==uid]
    ol.sort(key=lambda x:x.get("created_at",""),reverse=True)
    now=datetime.now().isoformat()
    for o in ol:
        if o.get("expiry_date") and o["expiry_date"]<now: o["status"]="expired"
    total=len(ol); pages=max(1,(total+PAGE_SIZE-1)//PAGE_SIZE); s=(page-1)*PAGE_SIZE
    return ol[s:s+PAGE_SIZE], total, pages

# Deposits
def create_deposit(uid, username, amount, trxid, phone, method=""):
    d=_load(DEPOSITS_FILE); did=f"DEP-{int(datetime.now().timestamp()*1000)}"
    d[did]={"dep_id":did,"user_id":uid,"username":username or "","amount":amount,
            "trx_id":trxid,"phone":phone,"method":method,"status":"pending","created_at":datetime.now().isoformat()}
    _save(DEPOSITS_FILE,d); return did

def get_deposit(did): return _load(DEPOSITS_FILE).get(did)

def update_deposit(did, status):
    d=_load(DEPOSITS_FILE)
    if did in d: d[did]["status"]=status; d[did]["updated_at"]=datetime.now().isoformat(); _save(DEPOSITS_FILE,d); return True
    return False

def get_pending_deps(page=1):
    dl=[d for d in _load(DEPOSITS_FILE).values() if d.get("status")=="pending"]
    dl.sort(key=lambda x:x.get("created_at",""),reverse=True)
    total=len(dl); pages=max(1,(total+PAGE_SIZE-1)//PAGE_SIZE); s=(page-1)*PAGE_SIZE
    return dl[s:s+PAGE_SIZE], total, pages

# Settings
def get_settings(): return _load(SETTINGS_FILE)
def update_setting(k, v): s=_load(SETTINGS_FILE); s[k]=v; _save(SETTINGS_FILE,s)

# Stats
def trxid_exists(trxid):
    for d in _load(DEPOSITS_FILE).values():
        if d.get("trx_id","").strip().lower() == trxid.strip().lower():
            return True
    return False

def user_has_pending(uid):
    for d in _load(DEPOSITS_FILE).values():
        if d.get("user_id")==uid and d.get("status")=="pending":
            return True
    return False

def get_deps_by_status(status, page=1):
    dl=[d for d in _load(DEPOSITS_FILE).values() if d.get("status")==status]
    dl.sort(key=lambda x:x.get("created_at",""),reverse=True)
    total=len(dl); pages=max(1,(total+PAGE_SIZE-1)//PAGE_SIZE); s=(page-1)*PAGE_SIZE
    return dl[s:s+PAGE_SIZE], total, pages

def get_stats():
    u=_load(USERS_FILE); o=_load(ORDERS_FILE); d=_load(DEPOSITS_FILE)
    return {
        "total_users":len(u), "banned":sum(1 for x in u.values() if x.get("is_banned")),
        "total_orders":len(o), "vpn":sum(1 for x in o.values() if x.get("category")=="vpn"),
        "proxy":sum(1 for x in o.values() if x.get("category")=="proxy"),
        "total_dep":sum(x.get("amount",0) for x in d.values() if x.get("status")=="approved"),
        "pending_dep":sum(1 for x in d.values() if x.get("status")=="pending"),
    }

# ── HELPERS ───────────────────────────────────────────────────

def fmt_date(iso):
    try: return datetime.fromisoformat(iso).strftime("%d %b %Y")
    except: return iso or "N/A"

def expiry_from_days(days):
    return (datetime.now()+timedelta(days=int(days))).isoformat()

def is_expired(expiry):
    try: return datetime.fromisoformat(expiry)<datetime.now()
    except: return False

def fmt_order(o):
    status = "⚠️ Expired" if is_expired(o.get("expiry_date","")) else "✅ Active"
    emoji  = "🔒" if o.get("category")=="vpn" else "🌐"
    cred   = o.get("credential","")
    parts  = cred.split(":")
    if len(parts)==2: ct=f"👤 `{parts[0]}`\n🔑 `{parts[1]}`"
    elif len(parts)>=3: ct=f"🌐 `{cred}`"
    else: ct=f"`{cred}`"
    return (f"{emoji} *{o.get('product_name','N/A')}*\n"
            f"🆔 `{o.get('order_id')}`\n"
            f"📅 Expires: {fmt_date(o.get('expiry_date',''))}\n"
            f"⚡ {status}\n{ct}")

def fmt_user(u):
    uname = f"@{u['username']}" if u.get("username") else "No username"
    status= "🚫 Banned" if u.get("is_banned") else "✅ Active"
    return (f"👤 *User Info*\n━━━━━━━━━━━━━━━\n"
            f"🆔 `{u['id']}`\n👤 {u.get('full_name','N/A')}\n📱 {uname}\n"
            f"💰 {u.get('balance',0)} {CURRENCY}\n🛒 Orders: {u.get('total_orders',0)}\n"
            f"👥 Referrals: {u.get('referral_count',0)}\n💸 Earned: {u.get('total_earned',0)} {CURRENCY}\n"
            f"📅 {fmt_date(u.get('joined_at',''))}\n⚡ {status}")

def fmt_deposit(d):
    method=d.get("method","")
    return (f"💳 *Deposit Request*\n━━━━━━━━━━━━━━━\n"
            f"🆔 `{d.get('dep_id')}`\n👤 @{d.get('username','N/A')} (`{d.get('user_id')}`)\n"
            f"{method+chr(10) if method else ''}"
            f"💰 *{d.get('amount')} {CURRENCY}*\n🧾 TrxID: `{d.get('trx_id')}`\n"
            f"📱 `{d.get('phone')}`\n📅 {fmt_date(d.get('created_at',''))}\n"
            f"⚡ {d.get('status','').upper()}")

def users_txt(ftype="all"):
    ul=list(_load(USERS_FILE).values())
    if ftype=="banned": ul=[u for u in ul if u.get("is_banned")]
    lines=[f"SpyX Bot - {'Banned' if ftype=='banned' else 'All'} Users","="*50,""]
    for u in ul:
        lines+=[f"ID: {u['id']}",f"Name: {u.get('full_name','N/A')}",
                f"Username: @{u.get('username','N/A')}",f"Balance: {u.get('balance',0)} {CURRENCY}",
                f"Orders: {u.get('total_orders',0)}",f"Status: {'BANNED' if u.get('is_banned') else 'ACTIVE'}","-"*30]
    return "\n".join(lines)

def deposits_txt():
    lines=["SpyX Bot - Deposits","="*50,""]
    for d in _load(DEPOSITS_FILE).values():
        lines+=[f"ID: {d.get('dep_id')}",f"User: @{d.get('username','N/A')} ({d.get('user_id')})",
                f"Amount: {d.get('amount')} {CURRENCY}",f"TrxID: {d.get('trx_id')}",
                f"Phone: {d.get('phone')}",f"Status: {d.get('status','').upper()}","-"*30]
    return "\n".join(lines)

def make_file(content, name):
    b=io.BytesIO(); b.write(content.encode("utf-8")); b.seek(0); b.name=name; return b

def is_admin(uid): return uid==ADMIN_ID

# ── KEYBOARDS ─────────────────────────────────────────────────

def main_kb():
    return ReplyKeyboardMarkup([
        ["👤 My Account","💰 Check Balance"],
        ["🔒 Buy VPN","🌐 Buy Proxy"],
        ["📋 My Orders","💳 Deposit Money"],
        ["🎁 Referral","🎧 Support"]
    ], resize_keyboard=True)

def admin_kb():
    return ReplyKeyboardMarkup([
        ["📦 Products","📁 Stock"],
        ["📋 Pending Deposits","👥 Users"],
        ["📢 Broadcast","👤 Personal Message"],
        ["💰 Payment Settings","🎁 Referral Settings"],
        ["📊 Statistics","🔙 User Menu"]
    ], resize_keyboard=True)

def cancel_kb(): return ReplyKeyboardMarkup([["❌ Cancel"]], resize_keyboard=True)

def support_kb(): return InlineKeyboardMarkup([[InlineKeyboardButton("🎧 Contact Support",url=f"https://t.me/{SUPPORT_USERNAME}")]])

def providers_kb(providers):
    kb=[]; row=[]; count=0
    for pid,p in providers.items():
        btn=InlineKeyboardButton(p["name"],callback_data=f"prov_{pid}")
        row.append(btn); count+=1
        if count%2==0: kb.append(row); row=[]
    if row: kb.append(row)
    return InlineKeyboardMarkup(kb)

def admin_providers_kb(providers):
    kb=[]
    for pid,p in providers.items():
        st="🟢" if p.get("is_active") else "🔴"
        kb.append([InlineKeyboardButton(f"{st} {p['name']}",callback_data=f"vprov_{pid}")])
    kb.append([InlineKeyboardButton("➕ Add Provider",callback_data="add_provider")])
    return InlineKeyboardMarkup(kb)

def admin_provider_actions_kb(pid):
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("✏️ Edit Name",callback_data=f"eprovname_{pid}"),
         InlineKeyboardButton("📝 Edit Price List",callback_data=f"eprovdesc_{pid}")],
        [InlineKeyboardButton("📦 View Products",callback_data=f"prov_prods_{pid}"),
         InlineKeyboardButton("➕ Add Product",callback_data=f"addprod_prov_{pid}")],
        [InlineKeyboardButton("🗑️ Delete Provider",callback_data=f"delprov_{pid}")]
    ])

def products_kb(products, cat):
    kb=[]; row=[]; count=0
    for pid,p in products.items():
        btn=InlineKeyboardButton(f"{p['name']} — {p['price']}৳",callback_data=f"buy_{pid}")
        row.append(btn); count+=1
        if count%3==0:
            kb.append(row); row=[]
    if row: kb.append(row)
    return InlineKeyboardMarkup(kb)

def confirm_kb(pid): return InlineKeyboardMarkup([[InlineKeyboardButton("✅ Confirm",callback_data=f"cbuy_{pid}")],[InlineKeyboardButton("❌ Cancel",callback_data="noop")]])

def orders_nav_kb(page, pages):
    nav=[]
    if page>1: nav.append(InlineKeyboardButton("⬅️",callback_data=f"op_{page-1}"))
    nav.append(InlineKeyboardButton(f"{page}/{pages}",callback_data="noop"))
    if page<pages: nav.append(InlineKeyboardButton("➡️",callback_data=f"op_{page+1}"))
    return InlineKeyboardMarkup([nav]) if nav else None

def dep_kb(did): return InlineKeyboardMarkup([[InlineKeyboardButton("✅ Approve",callback_data=f"adep_{did}"),InlineKeyboardButton("❌ Reject",callback_data=f"rdep_{did}")]])

def deps_nav_kb(page, pages):
    nav=[]
    if page>1: nav.append(InlineKeyboardButton("⬅️",callback_data=f"dp_{page-1}"))
    nav.append(InlineKeyboardButton(f"{page}/{pages}",callback_data="noop"))
    if page<pages: nav.append(InlineKeyboardButton("➡️",callback_data=f"dp_{page+1}"))
    kb=[nav] if nav else []
    kb.append([InlineKeyboardButton("📥 Download .txt",callback_data="dl_deps")])
    return InlineKeyboardMarkup(kb)

def users_nav_kb(page, pages, ft):
    kb=[]
    nav=[]
    if page>1: nav.append(InlineKeyboardButton("⬅️ Prev",callback_data=f"ul_{ft}_{page-1}"))
    nav.append(InlineKeyboardButton(f"📄 {page}/{pages}",callback_data="noop"))
    if page<pages: nav.append(InlineKeyboardButton("Next ➡️",callback_data=f"ul_{ft}_{page+1}"))
    kb.append(nav)
    kb.append([InlineKeyboardButton("📥 Download .txt",callback_data=f"dl_users_{ft}")])
    return InlineKeyboardMarkup(kb)

def user_actions_kb(uid, banned):
    bt="✅ Unban" if banned else "🚫 Ban"; bc=f"unban_{uid}" if banned else f"ban_{uid}"
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(bt,callback_data=bc)],
        [InlineKeyboardButton("💰 Add Balance",callback_data=f"addbal_{uid}"),InlineKeyboardButton("💸 Deduct",callback_data=f"dedbal_{uid}")],
        [InlineKeyboardButton("📋 Orders",callback_data=f"uorders_{uid}"),InlineKeyboardButton("✉️ Message",callback_data=f"msguser_{uid}")]
    ])

def prods_kb(products):
    kb=[]
    for pid,p in products.items():
        st="🟢" if p.get("is_active") else "🔴"; cat="🔒" if p.get("category")=="vpn" else "🌐"
        kb.append([InlineKeyboardButton(f"{st} {cat} {p['name']} — {p['price']} {CURRENCY}",callback_data=f"vp_{pid}")])
    kb.append([InlineKeyboardButton("➕ Add New",callback_data="addprod")])
    return InlineKeyboardMarkup(kb)

def prod_actions_kb(pid, active):
    st="🔴 Disable" if active else "🟢 Enable"; sc=f"dprod_{pid}" if active else f"eprod_{pid}"
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("✏️ Name",callback_data=f"ename_{pid}"),InlineKeyboardButton("💲 BDT Price",callback_data=f"eprice_{pid}")],
        [InlineKeyboardButton("💵 USDT Price",callback_data=f"eusdt_{pid}"),InlineKeyboardButton("📅 Duration",callback_data=f"edur_{pid}")],
        [InlineKeyboardButton("📝 Description",callback_data=f"edesc_{pid}"),InlineKeyboardButton(st,callback_data=sc)],
        [InlineKeyboardButton("🗑️ Delete",callback_data=f"delprod_{pid}")]
    ])

def cat_kb(): return InlineKeyboardMarkup([[InlineKeyboardButton("🔒 VPN",callback_data="pc_vpn"),InlineKeyboardButton("🌐 Proxy",callback_data="pc_proxy")],[InlineKeyboardButton("❌ Cancel",callback_data="noop")]])

# ── HANDLERS ──────────────────────────────────────────────────

async def cmd_start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    u=update.effective_user; args=ctx.args; ref=None
    if args and args[0].startswith("ref"):
        try:
            r=int(args[0][3:])
            if r!=u.id: ref=r
        except: pass
    db=create_user(u.id,u.username,u.full_name,ref)
    if db.get("is_banned"):
        await update.message.reply_text("🚫 You are banned."); return
    s=get_settings()
    await update.message.reply_text(f"👋 *{s.get('welcome_message',f'Welcome to {BOT_NAME}!')}*",parse_mode=ParseMode.MARKDOWN,reply_markup=main_kb())

async def cmd_admin(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id): return
    s=get_stats()
    await update.message.reply_text(
        f"⚙️ *Admin Panel*\n━━━━━━━━━━━━━━━\n👥 Users: {s['total_users']}\n⏳ Pending: {s['pending_dep']}\n🛒 Orders: {s['total_orders']}",
        parse_mode=ParseMode.MARKDOWN,reply_markup=admin_kb())

async def handle_text(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    text=update.message.text.strip(); uid=update.effective_user.id
    u=update.effective_user
    step=ctx.user_data.get("step",""); dep=ctx.user_data.get("dep_step","")
    db=get_user(uid)
    if not db:
        db=create_user(uid, u.username, u.full_name)
    if db and db.get("is_banned"):
        await update.message.reply_text("🚫 You are banned."); return
    if text in ["❌ Cancel","🔙 User Menu"]:
        ctx.user_data.clear()
        await update.message.reply_text("🏠 Main Menu",reply_markup=main_kb()); return

    menu_buttons = ["👤 My Account","💰 Check Balance","🔒 Buy VPN","🌐 Buy Proxy",
                    "📋 My Orders","💳 Deposit Money","🎁 Referral","🎧 Support",
                    "📦 Products","📁 Stock","📋 Pending Deposits","👥 Users",
                    "📢 Broadcast","👤 Personal Message","💰 Payment Settings",
                    "🎁 Referral Settings","📊 Statistics"]
    if dep and text in menu_buttons:
        ctx.user_data.clear()

    # ── DEPOSIT FLOW ──
    dep = ctx.user_data.get("dep_step","")
    if dep=="amount":
        try:
            a=float(text)
            if a<=0: raise ValueError
            ctx.user_data["dep_amount"]=a; ctx.user_data["dep_step"]="trxid"
            await update.message.reply_text("🧾 *Enter Transaction ID:*",parse_mode=ParseMode.MARKDOWN)
        except: await update.message.reply_text("❌ Invalid amount.")
        return
    if dep=="trxid":
        if trxid_exists(text):
            await update.message.reply_text(
                "❌ *This Transaction ID has already been used!*\n\nPlease check your TrxID and try again.\nIf you think this is a mistake, contact support.",
                parse_mode=ParseMode.MARKDOWN,reply_markup=support_kb())
            ctx.user_data.clear()
            return
        ctx.user_data["dep_trxid"]=text; ctx.user_data["dep_step"]="phone"
        await update.message.reply_text("📱 *Enter phone number used for payment:*",parse_mode=ParseMode.MARKDOWN); return
    if dep=="phone":
        u=update.effective_user
        a=ctx.user_data.get("dep_amount"); tx=ctx.user_data.get("dep_trxid")
        method=ctx.user_data.get("dep_method","Unknown"); ph=text
        did=create_deposit(u.id,u.username,a,tx,ph,method); ctx.user_data.clear()
        await update.message.reply_text(
            f"✅ *Deposit Submitted!*\n━━━━━━━━━━━━━━━\n{method}\n💰 {a} {CURRENCY}\n🧾 `{tx}`\n📱 `{ph}`\n🆔 `{did}`\n\n⏳ Waiting for approval...",
            parse_mode=ParseMode.MARKDOWN,reply_markup=main_kb())
        try:
            await ctx.bot.send_message(ADMIN_ID,
                f"💳 *New Deposit!*\n━━━━━━━━━━━━━━━\n👤 @{u.username or 'N/A'} (`{u.id}`)\n{method}\n💰 *{a} {CURRENCY}*\n🧾 `{tx}`\n📱 `{ph}`\n🆔 `{did}`",
                parse_mode=ParseMode.MARKDOWN,reply_markup=dep_kb(did))
        except: pass
        return

    # ── ADMIN STEPS ──
    if is_admin(uid) and step:
        if step=="apn":
            ctx.user_data["np_name"]=text; ctx.user_data["step"]="app"
            await update.message.reply_text("💲 Price (BDT):",reply_markup=cancel_kb()); return
        if step=="app":
            try: ctx.user_data["np_price"]=float(text); ctx.user_data["step"]="apd"; await update.message.reply_text("📅 Duration (days):",reply_markup=cancel_kb())
            except: await update.message.reply_text("❌ Invalid price.")
            return
        if step=="apd":
            try:
                ctx.user_data["np_days"]=int(text); ctx.user_data["step"]="apusdt"
                await update.message.reply_text(
                    "💵 *Enter USDT price:*\nExample: `0.32`\n\nOr send /skip if no USDT price",
                    parse_mode=ParseMode.MARKDOWN,reply_markup=cancel_kb())
            except: await update.message.reply_text("❌ Invalid days.")
            return

        if step=="apusdt":
            if text=="/skip":
                ctx.user_data["np_usdt"]=None
            else:
                try: ctx.user_data["np_usdt"]=float(text)
                except: await update.message.reply_text("❌ Invalid. Enter like `0.32` or send /skip",parse_mode=ParseMode.MARKDOWN); return
            ctx.user_data["step"]="apdesc"
            await update.message.reply_text(
                "📝 *Enter description:*\n(Extra info shown to user)\n\nOr send /skip",
                parse_mode=ParseMode.MARKDOWN,reply_markup=cancel_kb())
            return

        if step=="apdesc":
            ctx.user_data["np_desc"]="" if text=="/skip" else text
            days=ctx.user_data["np_days"]; desc=ctx.user_data.get("np_desc","")
            usdt=ctx.user_data.get("np_usdt")
            # ── FIX: provider already set (addprod_prov_ flow) ──
            if ctx.user_data.get("np_prov_id"):
                prov_id=ctx.user_data["np_prov_id"]
                prov_name=ctx.user_data.get("np_prov_name","")
                pid=create_product(ctx.user_data["np_name"],ctx.user_data["np_price"],"proxy",days,desc,provider_id=prov_id,provider_name=prov_name,usdt_price=usdt)
                nm=ctx.user_data["np_name"]; pr=ctx.user_data["np_price"]; ctx.user_data.clear()
                usdt_txt=f" / ${usdt}" if usdt else ""
                await update.message.reply_text(f"✅ *Product Added!*\n📌 {nm}\n💰 {pr} {CURRENCY}{usdt_txt}\n📅 {days} days\n🌐 Provider: {prov_name}",parse_mode=ParseMode.MARKDOWN,reply_markup=admin_kb())
                return
            # ── FIX: proxy category → ask provider ──
            if ctx.user_data.get("np_cat")=="proxy":
                provs=get_all_providers()
                if provs:
                    ctx.user_data["step"]="ap_provider"
                    kb=[[InlineKeyboardButton(p["name"],callback_data=f"selp_{pid2}")] for pid2,p in provs.items()]
                    kb.append([InlineKeyboardButton("⏭️ No Provider",callback_data="selp_none")])
                    await update.message.reply_text("🌐 Select provider for this product:",reply_markup=InlineKeyboardMarkup(kb))
                    return
            # ── FIX: VPN or proxy with no providers ──
            pid=create_product(ctx.user_data["np_name"],ctx.user_data["np_price"],ctx.user_data.get("np_cat","vpn"),days,desc,usdt_price=usdt)
            nm=ctx.user_data["np_name"]; pr=ctx.user_data["np_price"]; ctx.user_data.clear()
            usdt_txt=f" / ${usdt}" if usdt else ""
            await update.message.reply_text(f"✅ *Product Added!*\n📌 {nm}\n💰 {pr} {CURRENCY}{usdt_txt}\n📅 {days} days",parse_mode=ParseMode.MARKDOWN,reply_markup=admin_kb())
            return

        if step=="add_prov_name":
            ctx.user_data["prov_name"]=text; ctx.user_data["step"]="add_prov_desc"
            await update.message.reply_text(
                "📝 Enter price list for this provider:\nExample:\n`Nodemaven Price List\n120MB - 42 BDT\n240MB - 83 BDT`\n\nOr send /skip",
                parse_mode=ParseMode.MARKDOWN); return

        if step=="add_prov_desc":
            desc="" if text=="/skip" else text
            name=ctx.user_data.get("prov_name","")
            pid=create_provider(name,desc); ctx.user_data.clear()
            await update.message.reply_text(f"✅ *Provider Added!*\n🌐 {name}",parse_mode=ParseMode.MARKDOWN,reply_markup=admin_kb()); return

        if step=="edit_prov_name":
            pid=ctx.user_data.get("edit_prov_id"); p=get_provider(pid)
            if p: p["name"]=text; save_provider(pid,p); ctx.user_data.clear()
            await update.message.reply_text(f"✅ Provider name → *{text}*",parse_mode=ParseMode.MARKDOWN,reply_markup=admin_kb()); return

        if step=="edit_prov_desc":
            pid=ctx.user_data.get("edit_prov_id"); p=get_provider(pid)
            if p: p["description"]=text; save_provider(pid,p); ctx.user_data.clear()
            await update.message.reply_text("✅ Price list updated!",reply_markup=admin_kb()); return

        if step=="edesc":
            pid=ctx.user_data.get("epid"); p=get_product(pid)
            if p:
                p["description"]="" if text=="/skip" else text
                save_product(pid,p); ctx.user_data.clear()
                await update.message.reply_text("✅ Description updated!",reply_markup=admin_kb())
            return

        if step=="ename":
            pid=ctx.user_data.get("epid"); p=get_product(pid)
            if p: p["name"]=text; save_product(pid,p); ctx.user_data.clear(); await update.message.reply_text(f"✅ Name → *{text}*",parse_mode=ParseMode.MARKDOWN,reply_markup=admin_kb())
            return
        if step=="eprice":
            pid=ctx.user_data.get("epid"); p=get_product(pid)
            try: p["price"]=float(text); save_product(pid,p); ctx.user_data.clear(); await update.message.reply_text(f"✅ Price → *{text} {CURRENCY}*",parse_mode=ParseMode.MARKDOWN,reply_markup=admin_kb())
            except: await update.message.reply_text("❌ Invalid.")
            return
        if step=="eusdt":
            pid=ctx.user_data.get("epid"); p=get_product(pid)
            if text=="/skip":
                if p: p["usdt_price"]=None; save_product(pid,p); ctx.user_data.clear(); await update.message.reply_text("✅ USDT price removed.",reply_markup=admin_kb())
            else:
                try:
                    if p: p["usdt_price"]=float(text); save_product(pid,p); ctx.user_data.clear(); await update.message.reply_text(f"✅ USDT Price → *${text}*",parse_mode=ParseMode.MARKDOWN,reply_markup=admin_kb())
                except: await update.message.reply_text("❌ Invalid.")
            return
        if step=="edur":
            pid=ctx.user_data.get("epid"); p=get_product(pid)
            try: p["duration_days"]=int(text); save_product(pid,p); ctx.user_data.clear(); await update.message.reply_text(f"✅ Duration → *{text} days*",parse_mode=ParseMode.MARKDOWN,reply_markup=admin_kb())
            except: await update.message.reply_text("❌ Invalid.")
            return
        if step=="stock":
            if text=="/done":
                pid=ctx.user_data.get("spid"); c=get_stock_count(pid); ctx.user_data.clear()
                await update.message.reply_text(f"✅ Done! Stock: *{c}*",parse_mode=ParseMode.MARKDOWN,reply_markup=admin_kb())
            else:
                pid=ctx.user_data.get("spid"); add_stock(pid,text)
                await update.message.reply_text(f"✅ Added! Total: *{get_stock_count(pid)}*  |  Add more or /done",parse_mode=ParseMode.MARKDOWN)
            return
        if step=="suser":
            found=None
            if text.startswith("@"): found=search_by_username(text)
            else:
                found=search_by_username(text)
                if not found:
                    try: found=get_user(int(text))
                    except: pass
            ctx.user_data.clear()
            if found: await update.message.reply_text(fmt_user(found),parse_mode=ParseMode.MARKDOWN,reply_markup=user_actions_kb(found["id"],found.get("is_banned",False)))
            else: await update.message.reply_text("❌ User not found.")
            return
        if step=="manual_bal_uid":
            found=None
            if text.startswith("@"): found=search_by_username(text)
            else:
                found=search_by_username(text)
                if not found:
                    try: found=get_user(int(text))
                    except: pass
            if found:
                act=ctx.user_data.get("bal_manual_act","add")
                ctx.user_data["bal_uid"]=found["id"]; ctx.user_data["bal_act"]=act; ctx.user_data["step"]="manual_bal_amt"
                name=found.get("full_name","N/A"); uname=found.get("username","N/A"); bal=found.get("balance",0)
                verb="add to" if act=="add" else "deduct from"
                await update.message.reply_text(
                    f"✅ User: {name} (@{uname})\nBalance: *{bal} {CURRENCY}*\n\nEnter amount to {verb}:",
                    parse_mode=ParseMode.MARKDOWN)
            else: await update.message.reply_text("❌ User not found.")
            return

        if step=="manual_bal_amt":
            try:
                amt=float(text)
                if amt<=0: raise ValueError
                tid=ctx.user_data.get("bal_uid"); act=ctx.user_data.get("bal_act","add")
                final=amt if act=="add" else -amt
                u_check=get_user(tid)
                if final<0 and u_check and u_check.get("balance",0)+final<0:
                    await update.message.reply_text(f"❌ Cannot deduct! User only has *{u_check.get('balance',0)} {CURRENCY}*",parse_mode=ParseMode.MARKDOWN)
                    return
                nb=update_balance(tid,final); ctx.user_data.clear()
                verb="Added +" if final>0 else "Deducted -"
                emoji="💰" if final>0 else "💸"
                await update.message.reply_text(
                    f"{emoji} *Balance Updated!*\n👤 `{tid}`\n{verb}{abs(amt)} {CURRENCY}\nNew Balance: *{nb} {CURRENCY}*",
                    parse_mode=ParseMode.MARKDOWN,reply_markup=admin_kb())
                try:
                    msg=f"💰 *{amt} {CURRENCY}* added to your balance by admin.\nNew Balance: *{nb} {CURRENCY}*" if final>0 else f"💸 *{amt} {CURRENCY}* deducted from your balance by admin.\nNew Balance: *{nb} {CURRENCY}*"
                    await ctx.bot.send_message(tid,msg,parse_mode=ParseMode.MARKDOWN)
                except: pass
            except: await update.message.reply_text("❌ Invalid amount.")
            return

        if step=="balamt":
            try:
                amt=float(text); tid=ctx.user_data.get("bal_uid"); act=ctx.user_data.get("bal_act")
                fa=amt if act=="add" else -amt; nb=update_balance(tid,fa); ctx.user_data.clear()
                vb="added to" if fa>0 else "deducted from"
                await update.message.reply_text(f"✅ *{abs(fa)} {CURRENCY}* {vb} `{tid}`\nNew: *{nb} {CURRENCY}*",parse_mode=ParseMode.MARKDOWN,reply_markup=admin_kb())
                try:
                    msg=f"💰 *{amt} {CURRENCY}* {'added to' if fa>0 else 'deducted from'} your balance.\nNew Balance: *{nb} {CURRENCY}*"
                    await ctx.bot.send_message(tid,msg,parse_mode=ParseMode.MARKDOWN)
                except: pass
            except: await update.message.reply_text("❌ Invalid amount.")
            return
        if step=="setbk": update_setting("bkash",text); ctx.user_data.clear(); await update.message.reply_text(f"✅ bKash → `{text}`",parse_mode=ParseMode.MARKDOWN,reply_markup=admin_kb()); return
        if step=="setng": update_setting("nagad",text); ctx.user_data.clear(); await update.message.reply_text(f"✅ Nagad → `{text}`",parse_mode=ParseMode.MARKDOWN,reply_markup=admin_kb()); return
        if step=="setcom":
            try:
                r=float(text)
                if 0<=r<=100: update_setting("referral_commission",r); ctx.user_data.clear(); await update.message.reply_text(f"✅ Commission → *{r}%*",parse_mode=ParseMode.MARKDOWN,reply_markup=admin_kb())
                else: await update.message.reply_text("❌ 0–100 only.")
            except: await update.message.reply_text("❌ Invalid.")
            return
        if step=="bcast":
            users=get_all_users(); sent=fail=0
            for i in users:
                try: await ctx.bot.send_message(int(i),text,parse_mode=ParseMode.MARKDOWN); sent+=1
                except: fail+=1
            ctx.user_data.clear()
            await update.message.reply_text(f"📢 Done! ✅ {sent}  ❌ {fail}",reply_markup=admin_kb()); return
        if step=="pmid":
            t=None
            if text.startswith("@"): f=search_by_username(text); t=f["id"] if f else None
            else:
                try: ti=int(text); t=ti if get_user(ti) else None
                except: pass
            if t: ctx.user_data["pm_uid"]=t; ctx.user_data["step"]="pmtxt"; await update.message.reply_text(f"✅ User `{t}` found.\n\nEnter message:",parse_mode=ParseMode.MARKDOWN)
            else: await update.message.reply_text("❌ Not found.")
            return
        if step=="pmtxt":
            t=ctx.user_data.get("pm_uid")
            try: await ctx.bot.send_message(t,text,parse_mode=ParseMode.MARKDOWN); ctx.user_data.clear(); await update.message.reply_text("✅ Sent!",reply_markup=admin_kb())
            except: await update.message.reply_text("❌ Failed.")
            return

    # ── MENU ──
    if text=="👤 My Account":
        u=get_user(uid)
        if not u: await update.message.reply_text("❌ Not found. /start again."); return
        uname=f"@{u['username']}" if u.get("username") else "No username"
        rl=f"https://t.me/{(await ctx.bot.get_me()).username}?start=ref{uid}"
        await update.message.reply_text(
            f"👤 *My Account*\n━━━━━━━━━━━━━━━\n🆔 `{u['id']}`\n📱 {uname}\n"
            f"💰 *{u.get('balance',0)} {CURRENCY}*\n🛒 Orders: {u.get('total_orders',0)}\n"
            f"👥 Referrals: {u.get('referral_count',0)}\n📅 {fmt_date(u.get('joined_at',''))}\n\n"
            f"🔗 *Referral Link:*\n`{rl}`",parse_mode=ParseMode.MARKDOWN)
    elif text=="💰 Check Balance":
        u=get_user(uid)
        await update.message.reply_text(f"💰 *Balance: {u.get('balance',0) if u else 0} {CURRENCY}*",parse_mode=ParseMode.MARKDOWN)
    elif text=="🔒 Buy VPN":
        u=get_user(uid)
        if u and u.get("is_banned"): await update.message.reply_text("🚫 Banned."); return
        p=get_products_by_cat("vpn")
        if not p: await update.message.reply_text("❌ No VPN products available."); return
        bal=u.get("balance",0) if u else 0
        price_lines=""
        for pid2,prod in p.items():
            desc=prod.get("description","")
            if desc: price_lines+=desc+"\n"
        if price_lines:
            msg=price_lines+"\nSelect your plan:"
        else:
            msg="🔒 *VPN Accounts*\n\n"
            for pid2,prod in p.items():
                msg+=f"📦 {prod['name']} — {prod['price']} {CURRENCY} | {prod['duration_days']} days\n"
            msg+=f"\n💳 Balance: *{bal} {CURRENCY}*\n\nSelect your plan:"
        await update.message.reply_text(msg,parse_mode=ParseMode.MARKDOWN,reply_markup=products_kb(p,"vpn"))
    elif text=="🌐 Buy Proxy":
        u=get_user(uid)
        if u and u.get("is_banned"): await update.message.reply_text("🚫 Banned."); return
        providers={k:v for k,v in get_all_providers().items() if v.get("is_active",True)}
        if not providers:
            p=get_products_by_cat("proxy")
            if not p: await update.message.reply_text("❌ No Proxy products available."); return
            msg="🌐 *Proxy Plans*\n\nSelect your plan:"
            await update.message.reply_text(msg,parse_mode=ParseMode.MARKDOWN,reply_markup=products_kb(p,"proxy"))
        else:
            await update.message.reply_text(
                "🌐 *Buy Proxy*\n\nSelect your provider:",
                parse_mode=ParseMode.MARKDOWN,reply_markup=providers_kb(providers))
    elif text=="📋 My Orders":
        orders,total,pages=get_user_orders(uid,1)
        if not orders: await update.message.reply_text("📋 *My Orders*\n\nYou have no orders yet.",parse_mode=ParseMode.MARKDOWN); return
        t=f"📋 *My Orders* — 1/{pages}\n━━━━━━━━━━━━━━━\n\n"+"\n\n".join(fmt_order(o) for o in orders)
        await update.message.reply_text(t,parse_mode=ParseMode.MARKDOWN,reply_markup=orders_nav_kb(1,pages) if pages>1 else None)
    elif text=="💳 Deposit Money":
        s=get_settings(); bk=s.get("bkash") or "Not set"; ng=s.get("nagad") or "Not set"
        await update.message.reply_text(
            f"💳 *Deposit Money*\n━━━━━━━━━━━━━━━\n\n"
            f"📌 *Step 1:* Send money to any number below\n\n"
            f"💚 *bKash:* `{bk}`\n"
            f"🟠 *Nagad:* `{ng}`\n\n"
            f"📌 *Step 2:* Tap below & submit payment info\n\n"
            f"⚠️ Send money FIRST, then submit!",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("📤 Submit Payment",callback_data="subdep")]]))
    elif text=="🎁 Referral":
        u=get_user(uid); s=get_settings(); com=s.get("referral_commission",10)
        rl=f"https://t.me/{(await ctx.bot.get_me()).username}?start=ref{uid}"
        await update.message.reply_text(
            f"🎁 *Referral System*\n━━━━━━━━━━━━━━━\n💸 Commission: *{com}%*\n"
            f"👥 Referred: *{u.get('referral_count',0) if u else 0}*\n💰 Earned: *{u.get('total_earned',0) if u else 0} {CURRENCY}*\n\n"
            f"1️⃣ Share your link\n2️⃣ Friend deposits\n3️⃣ You earn {com}%!\n\n🔗 `{rl}`",parse_mode=ParseMode.MARKDOWN)
    elif text=="🎧 Support":
        await update.message.reply_text("🎧 *Support*\n\nContact us below!",parse_mode=ParseMode.MARKDOWN,reply_markup=support_kb())
    # Admin menu
    elif is_admin(uid):
        if text=="📦 Products":
            p=get_all_products(); provs=get_all_providers()
            vpn_c=sum(1 for x in p.values() if x.get("category")=="vpn")
            prx_c=sum(1 for x in p.values() if x.get("category")=="proxy")
            await update.message.reply_text(
                f"📦 *Products*\n━━━━━━━━━━━━━━━\n🔒 VPN: {vpn_c}\n🌐 Proxy: {prx_c}\n🌐 Providers: {len(provs)}\n\nSelect:",
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton(f"🔒 VPN ({vpn_c})",callback_data="show_vpn_prods"),InlineKeyboardButton(f"🌐 Proxy ({prx_c})",callback_data="show_proxy_prods")],
                    [InlineKeyboardButton(f"🌐 Providers ({len(provs)})",callback_data="show_providers")],
                    [InlineKeyboardButton("➕ Add VPN",callback_data="add_vpn_prod"),InlineKeyboardButton("➕ Add Proxy",callback_data="add_proxy_prod")]
                ]))
        elif text=="📁 Stock":
            p=get_all_products()
            if not p: await update.message.reply_text("❌ No products."); return
            kb=[[InlineKeyboardButton(f"{'🔒' if v.get('category')=='vpn' else '🌐'} {v['name']} — {get_stock_count(k)} stock",callback_data=f"mstock_{k}")] for k,v in p.items()]
            await update.message.reply_text("📁 *Stock Management*\nSelect product:",parse_mode=ParseMode.MARKDOWN,reply_markup=InlineKeyboardMarkup(kb))
        elif text=="📋 Pending Deposits":
            await update.message.reply_text("📋 *Deposits*\nSelect:",parse_mode=ParseMode.MARKDOWN,
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("⏳ Pending",callback_data="deps_pending_1")],
                    [InlineKeyboardButton("✅ Approved",callback_data="deps_approved_1")],
                    [InlineKeyboardButton("❌ Rejected",callback_data="deps_rejected_1")],
                    [InlineKeyboardButton("📥 Download All",callback_data="dl_deps")]
                ]))
        elif text=="👥 Users":
            await update.message.reply_text("👥 *Users Management*\nSelect:",parse_mode=ParseMode.MARKDOWN,
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("👥 All Users",callback_data="ul_all_1")],
                    [InlineKeyboardButton("🚫 Banned Users",callback_data="ul_banned_1")],
                    [InlineKeyboardButton("🔍 Search by Username",callback_data="susearch")],
                    [InlineKeyboardButton("🔢 Search by User ID",callback_data="suid")],
                    [InlineKeyboardButton("💰 Add Balance",callback_data="addbal_manual"),
                     InlineKeyboardButton("💸 Deduct Balance",callback_data="dedbal_manual")]
                ]))
        elif text=="📢 Broadcast": ctx.user_data["step"]="bcast"; await update.message.reply_text("📢 Enter broadcast message:",reply_markup=cancel_kb())
        elif text=="👤 Personal Message": ctx.user_data["step"]="pmid"; await update.message.reply_text("👤 Enter User ID or @username:",reply_markup=cancel_kb())
        elif text=="💰 Payment Settings":
            s=get_settings()
            await update.message.reply_text("💰 *Payment Settings*",parse_mode=ParseMode.MARKDOWN,
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton(f"💚 bKash: {s.get('bkash') or 'Not set'}",callback_data="sbk")],[InlineKeyboardButton(f"🟠 Nagad: {s.get('nagad') or 'Not set'}",callback_data="sng")]]))
        elif text=="🎁 Referral Settings":
            com=get_settings().get("referral_commission",10)
            await update.message.reply_text(f"🎁 Commission: *{com}%*",parse_mode=ParseMode.MARKDOWN,
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton(f"✏️ Change ({com}%)",callback_data="scom")]]))
        elif text=="📊 Statistics":
            s=get_stats()
            await update.message.reply_text(
                f"📊 *Statistics*\n━━━━━━━━━━━━━━━\n👥 Users: *{s['total_users']}*\n🚫 Banned: *{s['banned']}*\n"
                f"⏳ Pending Deps: *{s['pending_dep']}*\n💰 Total Deposited: *{s['total_dep']} {CURRENCY}*\n"
                f"🛒 Orders: *{s['total_orders']}*\n🔒 VPN: *{s['vpn']}*\n🌐 Proxy: *{s['proxy']}*",parse_mode=ParseMode.MARKDOWN)

async def handle_cb(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    q=update.callback_query; data=q.data; uid=update.effective_user.id
    u=update.effective_user
    await q.answer()
    if not get_user(uid):
        create_user(uid, u.username, u.full_name)
    if data=="noop": return
    if data=="go_back":
        await q.edit_message_text("🏠 Use the menu below.")
        return

    if data=="subdep":
        if user_has_pending(uid):
            await q.edit_message_text(
                "⚠️ *You already have a pending deposit!*\n\nPlease wait for admin to approve your previous deposit before submitting a new one.",
                parse_mode=ParseMode.MARKDOWN)
            return
        s=get_settings(); bk=s.get("bkash") or "Not set"; ng=s.get("nagad") or "Not set"
        await q.edit_message_text(
            f"💳 *Select Payment Method*\n━━━━━━━━━━━━━━━\n💚 bKash: `{bk}`\n🟠 Nagad: `{ng}`",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton(f"💚 bKash — {bk}", callback_data="dep_bkash")],
                [InlineKeyboardButton(f"🟠 Nagad — {ng}", callback_data="dep_nagad")],
                [InlineKeyboardButton("❌ Cancel", callback_data="noop")]
            ])); return

    if data in ["dep_bkash","dep_nagad"]:
        method="💚 bKash" if data=="dep_bkash" else "🟠 Nagad"
        ctx.user_data["dep_method"]=method
        ctx.user_data["dep_step"]="amount"
        await q.edit_message_text(
            f"✅ *{method}* selected.\n\n💰 *Enter deposit amount (BDT):*\nExample: `500`",
            parse_mode=ParseMode.MARKDOWN); return

    # ── FIX: Provider selected by user — check prov_ prefix carefully ──
    if data.startswith("prov_") and not data.startswith("prov_prods_"):
        prov_id=data[5:]; prov=get_provider(prov_id)
        if not prov: await q.edit_message_text("❌ Provider not found."); return
        prods=get_proxy_products_by_provider(prov_id)
        if not prods: await q.edit_message_text(f"❌ No products for {prov['name']} yet."); return
        prov_desc=prov.get("description","")
        if prov_desc:
            msg=prov_desc+"\n\nSelect your plan:"
        else:
            has_usdt=any(p.get("usdt_price") for p in prods.values())
            title=f"*{prov['name']} Price List*"
            if has_usdt: title+=" (BDT & USDT)"
            msg=title+"\n━━━━━━━━━━━━━━━\n"
            for pid2,prod in prods.items():
                usdt=prod.get("usdt_price")
                if usdt:
                    msg+=f"• {prod['name']} — {prod['price']} BDT / ${usdt} USDT\n"
                else:
                    msg+=f"• {prod['name']} — {prod['price']} BDT\n"
            msg+="\nSelect your plan:"
        await q.edit_message_text(msg,parse_mode=ParseMode.MARKDOWN,reply_markup=products_kb(prods,"proxy"))
        return

    # Buy product
    if data.startswith("buy_"):
        pid=data[4:]; p=get_product(pid); u=get_user(uid)
        if not p: await q.edit_message_text("❌ Not found."); return
        sc=get_stock_count(pid); e="🔒" if p.get("category")=="vpn" else "🌐"
        desc=p.get("description","")
        desc_line=f"\n📝 {desc}\n" if desc else "\n"
        t=(f"{e} *{p['name']}*\n━━━━━━━━━━━━━━━\n"
           f"💰 Price: *{p['price']} {CURRENCY}*\n"
           f"📅 Duration: *{p['duration_days']} days*{desc_line}"
           f"💳 Your Balance: *{u.get('balance',0) if u else 0} {CURRENCY}*\n")
        if not u or u.get("balance",0)<p["price"]:
            t+=f"\n❌ *Insufficient balance!*"
            await q.edit_message_text(t,parse_mode=ParseMode.MARKDOWN,
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("💳 Deposit",callback_data="subdep"),InlineKeyboardButton("🔙 Back",callback_data="go_back")]])); return
        if sc==0:
            t+="\n❌ *Out of stock!*"
            await q.edit_message_text(t,parse_mode=ParseMode.MARKDOWN,reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back",callback_data="go_back")]])); return
        t+="\n✅ Ready to purchase!"
        await q.edit_message_text(t,parse_mode=ParseMode.MARKDOWN,reply_markup=confirm_kb(pid)); return

    # Confirm buy
    if data.startswith("cbuy_"):
        pid=data[5:]; p=get_product(pid); u=get_user(uid)
        if not p or not u: await q.edit_message_text("❌ Error."); return
        if u.get("balance",0)<p["price"]: await q.edit_message_text("❌ Insufficient balance."); return
        cred=pop_stock(pid)
        if not cred: await q.edit_message_text("❌ Out of stock!"); return
        exp=expiry_from_days(p["duration_days"]); oid=create_order(uid,pid,p["name"],p["category"],cred,p["price"],p["duration_days"],exp)
        update_balance(uid,-p["price"]); parts=cred.split(":")
        ct=f"👤 `{parts[0]}`\n🔑 `{parts[1]}`" if len(parts)==2 else f"🌐 `{cred}`"
        e="🔒" if p.get("category")=="vpn" else "🌐"; nb=get_user(uid).get("balance",0)
        await q.edit_message_text(
            f"✅ *Purchase Successful!*\n━━━━━━━━━━━━━━━\n{e} *{p['name']}*\n🆔 `{oid}`\n📅 {fmt_date(exp)}\n\n{ct}\n\n💰 Balance: *{nb} {CURRENCY}*\n\nThank you! 🎉",
            parse_mode=ParseMode.MARKDOWN)
        try:
            await ctx.bot.send_message(ADMIN_ID,f"🛒 *New Order!*\n👤 `{uid}`\n📦 {p['name']}\n💰 {p['price']} {CURRENCY}\n🆔 `{oid}`",parse_mode=ParseMode.MARKDOWN)
        except: pass
        if get_stock_count(pid)<=2:
            try: await ctx.bot.send_message(ADMIN_ID,f"⚠️ *Low Stock!*\n{e} {p['name']}\nRemaining: *{get_stock_count(pid)}*",parse_mode=ParseMode.MARKDOWN)
            except: pass
        return

    # Orders pagination
    if data.startswith("op_"):
        pg=int(data[3:]); orders,total,pages=get_user_orders(uid,pg)
        if not orders: await q.edit_message_text("No more orders."); return
        t=f"📋 *My Orders* — {pg}/{pages}\n━━━━━━━━━━━━━━━\n\n"+"\n\n".join(fmt_order(o) for o in orders)
        await q.edit_message_text(t,parse_mode=ParseMode.MARKDOWN,reply_markup=orders_nav_kb(pg,pages) if pages>1 else None); return

    # Approve deposit
    if data.startswith("adep_"):
        if not is_admin(uid): return
        did=data[5:]; d=get_deposit(did)
        if not d: await q.edit_message_text("❌ Not found."); return
        if d.get("status")!="pending": await q.edit_message_text(f"⚠️ Already {d.get('status')}."); return
        amt=float(d.get("amount",0)); duid=int(d.get("user_id"))
        update_deposit(did,"approved")
        nb=update_balance(duid,amt)
        if nb is None:
            await q.edit_message_text(f"❌ User `{duid}` not found in database!",parse_mode=ParseMode.MARKDOWN)
            return
        du=get_user(duid)
        if du and du.get("referred_by"):
            try:
                com=get_settings().get("referral_commission",10)/100
                c=round(amt*com,2)
                rid=int(du["referred_by"])
                r=get_user(rid)
                if r:
                    update_balance(rid,c)
                    r["total_earned"]=round(r.get("total_earned",0)+c,2)
                    save_user(rid,r)
                    await ctx.bot.send_message(rid,f"🎁 *Commission!*\nFriend deposited {amt} {CURRENCY}\nYou earned: *{c} {CURRENCY}*\nBalance: *{get_user(rid).get('balance',0)} {CURRENCY}*",parse_mode=ParseMode.MARKDOWN)
            except: pass
        await q.edit_message_text(f"✅ *Approved!*\n👤 `{duid}`\n💰 *{amt} {CURRENCY}* added\nNew Balance: *{nb} {CURRENCY}*",parse_mode=ParseMode.MARKDOWN)
        try: await ctx.bot.send_message(duid,f"✅ *Deposit Approved!*\n\n💰 *{amt} {CURRENCY}* added to your balance!\nNew Balance: *{nb} {CURRENCY}*\n\nBuy VPN or Proxy now! 🎉",parse_mode=ParseMode.MARKDOWN)
        except: pass
        return

    # Reject deposit
    if data.startswith("rdep_"):
        if not is_admin(uid): return
        did=data[5:]; d=get_deposit(did)
        if not d: await q.edit_message_text("❌ Not found."); return
        update_deposit(did,"rejected"); await q.edit_message_text(f"❌ Rejected `{did}`",parse_mode=ParseMode.MARKDOWN)
        try: await ctx.bot.send_message(d.get("user_id"),f"❌ *Deposit Rejected*\n{d.get('amount')} {CURRENCY}\nTrxID: `{d.get('trx_id')}`\n\nContact support if needed.",parse_mode=ParseMode.MARKDOWN,reply_markup=support_kb())
        except: pass
        return

    # Deposits pagination
    if data.startswith("dp_"):
        if not is_admin(uid): return
        pg=int(data[3:]); deps,total,pages=get_pending_deps(pg)
        await q.edit_message_text(f"📋 Page {pg}/{pages}",reply_markup=deps_nav_kb(pg,pages))
        for d in deps: await q.message.reply_text(fmt_deposit(d),parse_mode=ParseMode.MARKDOWN,reply_markup=dep_kb(d["dep_id"]))
        return

    if data.startswith("deps_"):
        if not is_admin(uid): return
        parts=data.split("_"); status=parts[1]; pg=int(parts[2])
        deps,total,pages=get_deps_by_status(status,pg)
        status_emoji={"pending":"⏳","approved":"✅","rejected":"❌"}.get(status,"📋")
        if not deps:
            await q.edit_message_text(f"{status_emoji} No {status} deposits."); return
        await q.edit_message_text(f"{status_emoji} *{status.title()} Deposits* ({total}) — {pg}/{pages}",parse_mode=ParseMode.MARKDOWN)
        for d in deps:
            kb=dep_kb(d["dep_id"]) if status=="pending" else None
            await q.message.reply_text(fmt_deposit(d),parse_mode=ParseMode.MARKDOWN,reply_markup=kb)
        nav=[]
        if pg>1: nav.append(InlineKeyboardButton("⬅️",callback_data=f"deps_{status}_{pg-1}"))
        nav.append(InlineKeyboardButton(f"{pg}/{pages}",callback_data="noop"))
        if pg<pages: nav.append(InlineKeyboardButton("➡️",callback_data=f"deps_{status}_{pg+1}"))
        if nav: await q.message.reply_text(f"Page {pg}/{pages}",reply_markup=InlineKeyboardMarkup([nav]))
        return

    if data=="dl_deps":
        if not is_admin(uid): return
        await q.message.reply_document(make_file(deposits_txt(),"spyx_deposits.txt"),filename="spyx_deposits.txt"); return
    if data.startswith("dl_users_"):
        if not is_admin(uid): return
        ft=data[9:]; await q.message.reply_document(make_file(users_txt(ft),f"spyx_{ft}_users.txt"),filename=f"spyx_{ft}_users.txt"); return

    # View product
    if data.startswith("vp_"):
        if not is_admin(uid): return
        pid=data[3:]; p=get_product(pid)
        if not p: await q.edit_message_text("❌ Not found."); return
        sc=get_stock_count(pid); cat="🔒 VPN" if p.get("category")=="vpn" else "🌐 Proxy"; st="🟢 Active" if p.get("is_active") else "🔴 Disabled"
        desc=p.get("description",""); desc_line=f"\n📝 {desc}" if desc else ""
        usdt=p.get("usdt_price"); usdt_line=f"\n💵 ${usdt} USDT" if usdt else ""
        await q.edit_message_text(
            f"📦 *{p['name']}*\n━━━━━━━━━━━━━━━\n💰 {p['price']} {CURRENCY}{usdt_line}\n📅 {p['duration_days']} days\n{cat}\n📦 Stock: {sc}\n⚡ {st}{desc_line}",
            parse_mode=ParseMode.MARKDOWN,reply_markup=prod_actions_kb(pid,p.get("is_active",True))); return

    # Add product
    if data in ["addprod","add_vpn_prod","add_proxy_prod"]:
        if not is_admin(uid): return
        if data=="add_vpn_prod":
            ctx.user_data["np_cat"]="vpn"; ctx.user_data["step"]="apn"
            await q.edit_message_text("➕ *Add VPN Product*\n\nEnter product name:",parse_mode=ParseMode.MARKDOWN); return
        elif data=="add_proxy_prod":
            ctx.user_data["np_cat"]="proxy"; ctx.user_data["step"]="apn"
            await q.edit_message_text("➕ *Add Proxy Product*\n\nEnter product name:",parse_mode=ParseMode.MARKDOWN); return
        else:
            await q.edit_message_text("➕ Select category:",reply_markup=cat_kb()); return

    # Provider selection during product creation
    if data.startswith("selp_"):
        if not is_admin(uid): return
        prov_id=data[5:]
        days=ctx.user_data.get("np_days",30); desc=ctx.user_data.get("np_desc","")
        name=ctx.user_data.get("np_name",""); price=ctx.user_data.get("np_price",0)
        cat=ctx.user_data.get("np_cat","proxy"); usdt=ctx.user_data.get("np_usdt")
        prov_name=""
        if prov_id!="none":
            prov=get_provider(prov_id)
            prov_name=prov["name"] if prov else ""
            pid=create_product(name,price,cat,days,desc,provider_id=prov_id,provider_name=prov_name,usdt_price=usdt)
        else:
            pid=create_product(name,price,cat,days,desc,usdt_price=usdt)
        ctx.user_data.clear()
        usdt_txt=f" / ${usdt}" if usdt else ""
        prov_txt=f"\n🌐 Provider: {prov_name}" if prov_name else ""
        await q.edit_message_text(f"✅ *Product Added!*\n📌 {name}\n💰 {price} {CURRENCY}{usdt_txt}\n📅 {days} days{prov_txt}",parse_mode=ParseMode.MARKDOWN)
        return

    if data=="show_providers":
        if not is_admin(uid): return
        provs=get_all_providers()
        if not provs:
            await q.edit_message_text("🌐 *Proxy Providers*\n\nNo providers yet.",parse_mode=ParseMode.MARKDOWN,
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("➕ Add Provider",callback_data="add_provider")]]))
        else:
            await q.edit_message_text(f"🌐 *Proxy Providers* ({len(provs)})",parse_mode=ParseMode.MARKDOWN,
                reply_markup=admin_providers_kb(provs))
        return

    if data=="show_vpn_prods":
        if not is_admin(uid): return
        p={k:v for k,v in get_all_products().items() if v.get("category")=="vpn"}
        txt="🔒 *VPN Products*\n\n"+"".join(f"• {v['name']} — {v['price']} {CURRENCY}\n" for v in p.values()) if p else "🔒 No VPN products."
        await q.edit_message_text(txt,parse_mode=ParseMode.MARKDOWN,reply_markup=prods_kb(p) if p else InlineKeyboardMarkup([[InlineKeyboardButton("➕ Add",callback_data="addprod")]]))
        return

    if data=="show_proxy_prods":
        if not is_admin(uid): return
        p={k:v for k,v in get_all_products().items() if v.get("category")=="proxy"}
        txt="🌐 *Proxy Products*\n\n"+"".join(f"• {v['name']} ({v.get('provider_name','No Provider')}) — {v['price']} {CURRENCY}\n" for v in p.values()) if p else "🌐 No proxy products."
        await q.edit_message_text(txt,parse_mode=ParseMode.MARKDOWN,reply_markup=prods_kb(p) if p else InlineKeyboardMarkup([[InlineKeyboardButton("➕ Add",callback_data="addprod")]]))
        return

    # ── FIX: Add product directly from provider ──
    if data.startswith("addprod_prov_"):
        if not is_admin(uid): return
        prov_id=data[13:]
        prov=get_provider(prov_id)
        if not prov: await q.edit_message_text("❌ Provider not found."); return
        ctx.user_data["np_cat"]="proxy"
        ctx.user_data["np_prov_id"]=prov_id
        ctx.user_data["np_prov_name"]=prov["name"]
        ctx.user_data["step"]="apn"
        await q.edit_message_text(
            f"➕ *Add Product to {prov['name']}*\n\nEnter product name:",
            parse_mode=ParseMode.MARKDOWN); return

    if data=="add_provider":
        if not is_admin(uid): return
        ctx.user_data["step"]="add_prov_name"
        await q.edit_message_text("➕ *Add Proxy Provider*\n\nEnter provider name:\nExample: `Nodemaven`",parse_mode=ParseMode.MARKDOWN); return

    if data.startswith("vprov_"):
        if not is_admin(uid): return
        prov_id=data[6:]; prov=get_provider(prov_id)
        if not prov: await q.edit_message_text("❌ Not found."); return
        desc=prov.get("description","Not set")
        prods=get_proxy_products_by_provider(prov_id)
        await q.edit_message_text(
            f"🌐 *{prov['name']}*\n━━━━━━━━━━━━━━━\n📝 Price List:\n{desc}\n\n📦 Products: {len(prods)}",
            parse_mode=ParseMode.MARKDOWN,reply_markup=admin_provider_actions_kb(prov_id))
        return

    if data.startswith("eprovname_"):
        if not is_admin(uid): return
        ctx.user_data["edit_prov_id"]=data[10:]; ctx.user_data["step"]="edit_prov_name"
        await q.edit_message_text("✏️ Enter new provider name:"); return

    if data.startswith("eprovdesc_"):
        if not is_admin(uid): return
        ctx.user_data["edit_prov_id"]=data[10:]; ctx.user_data["step"]="edit_prov_desc"
        await q.edit_message_text("📝 Enter price list for this provider:\n(This will be shown to users when they select this provider)",parse_mode=ParseMode.MARKDOWN); return

    if data.startswith("delprov_"):
        if not is_admin(uid): return
        prov_id=data[8:]; prov=get_provider(prov_id)
        if prov: delete_provider(prov_id); await q.edit_message_text(f"✅ Provider *{prov['name']}* deleted.",parse_mode=ParseMode.MARKDOWN)
        return

    if data.startswith("prov_prods_"):
        if not is_admin(uid): return
        prov_id=data[11:]; prov=get_provider(prov_id)
        if not prov: await q.edit_message_text("❌ Provider not found."); return
        prods=get_proxy_products_by_provider(prov_id)
        if not prods: await q.edit_message_text(f"📦 No products for {prov['name']} yet.\nAdd products and assign to this provider."); return
        await q.edit_message_text(f"📦 *{prov['name']} Products*",parse_mode=ParseMode.MARKDOWN,reply_markup=prods_kb(prods))
        return

    if data.startswith("pc_"):
        if not is_admin(uid): return
        cat=data[3:]; ctx.user_data["np_cat"]=cat; ctx.user_data["step"]="apn"
        await q.edit_message_text(f"➕ *Add {'VPN' if cat=='vpn' else 'Proxy'}*\n\nEnter product name:",parse_mode=ParseMode.MARKDOWN); return

    # Delete product
    if data.startswith("delprod_"):
        if not is_admin(uid): return
        pid=data[8:]; p=get_product(pid)
        if p: delete_product(pid); await q.edit_message_text(f"✅ *{p['name']}* deleted.",parse_mode=ParseMode.MARKDOWN)
        return

    # Toggle product
    if data.startswith("eprod_") or data.startswith("dprod_"):
        if not is_admin(uid): return
        en=data.startswith("eprod_"); pid=data[6:]; p=get_product(pid)
        if p: p["is_active"]=en; save_product(pid,p); await q.edit_message_text(f"✅ {'Enabled 🟢' if en else 'Disabled 🔴'}",parse_mode=ParseMode.MARKDOWN)
        return

    # Edit product fields
    if data.startswith("ename_"): ctx.user_data["epid"]=data[6:]; ctx.user_data["step"]="ename"; await q.edit_message_text("✏️ New name:"); return
    if data.startswith("edesc_"): ctx.user_data["epid"]=data[6:]; ctx.user_data["step"]="edesc"; await q.edit_message_text("📝 New description:\n(Send /skip to remove description)"); return
    if data.startswith("eprice_"): ctx.user_data["epid"]=data[7:]; ctx.user_data["step"]="eprice"; await q.edit_message_text("💲 New price (BDT):"); return
    if data.startswith("eusdt_"): ctx.user_data["epid"]=data[6:]; ctx.user_data["step"]="eusdt"; await q.edit_message_text("💵 New USDT price:\n(Send /skip to remove)"); return
    if data.startswith("edur_"): ctx.user_data["epid"]=data[5:]; ctx.user_data["step"]="edur"; await q.edit_message_text("📅 New duration (days):"); return

    # Manage stock
    if data.startswith("mstock_"):
        if not is_admin(uid): return
        pid=data[7:]; p=get_product(pid); ctx.user_data["step"]="stock"; ctx.user_data["spid"]=pid
        await q.edit_message_text(
            f"📁 *{p['name']}* — Stock: {get_stock_count(pid)}\n\nVPN: `user:pass`\nProxy: `ip:port:user:pass`\n\nType each credential and send.\nSend /done when finished.",
            parse_mode=ParseMode.MARKDOWN); return

    # Users list
    if data.startswith("ul_"):
        if not is_admin(uid): return
        parts=data.split("_"); ft=parts[1]; pg=int(parts[2])
        ul,total,pages=get_users_page(pg,ft)
        if not ul: await q.edit_message_text("No users."); return
        t=f"{'👥 All' if ft=='all' else '🚫 Banned'} Users ({total}) — {pg}/{pages}\n━━━━━━━━━━━━━━━\n\n"
        for u in ul:
            un=f"@{u['username']}" if u.get("username") else "No username"
            t+=f"{'🚫' if u.get('is_banned') else '✅'} `{u['id']}` — {un} — {u.get('balance',0)} {CURRENCY}\n"
        if len(t)>4000: t=t[:4000]+"..."
        try:
            await q.edit_message_text(t,parse_mode=ParseMode.MARKDOWN,reply_markup=users_nav_kb(pg,pages,ft))
        except Exception as e:
            if "message is not modified" in str(e).lower(): pass
            else: await q.message.reply_text(t,parse_mode=ParseMode.MARKDOWN,reply_markup=users_nav_kb(pg,pages,ft))
        return

    # Search user
    if data=="susearch":
        if not is_admin(uid): return
        ctx.user_data["step"]="suser"; await q.edit_message_text("🔍 Enter @username or User ID:"); return

    if data=="suid":
        if not is_admin(uid): return
        ctx.user_data["step"]="suser"; await q.edit_message_text("🔢 Enter User ID or @username:"); return

    if data=="addbal_manual":
        if not is_admin(uid): return
        ctx.user_data["step"]="manual_bal_uid"
        ctx.user_data["bal_manual_act"]="add"
        await q.edit_message_text("💰 *Add Balance to User*\n\nEnter User ID or @username:",parse_mode=ParseMode.MARKDOWN); return

    if data=="dedbal_manual":
        if not is_admin(uid): return
        ctx.user_data["step"]="manual_bal_uid"
        ctx.user_data["bal_manual_act"]="deduct"
        await q.edit_message_text("💸 *Deduct Balance from User*\n\nEnter User ID or @username:",parse_mode=ParseMode.MARKDOWN); return

    # Ban/Unban
    if data.startswith("ban_") or data.startswith("unban_"):
        if not is_admin(uid): return
        banning=data.startswith("ban_"); tid=int(data[4:] if banning else data[6:])
        ban_user(tid,banning); act="banned 🚫" if banning else "unbanned ✅"
        await q.edit_message_text(f"User `{tid}` {act}.",parse_mode=ParseMode.MARKDOWN)
        try: await ctx.bot.send_message(tid,"🚫 You have been banned." if banning else "✅ You have been unbanned!")
        except: pass
        return

    # Balance from user actions button
    if data.startswith("addbal_") or data.startswith("dedbal_"):
        if not is_admin(uid): return
        adding=data.startswith("addbal_")
        tid_str=data[7:]
        try: tid=int(tid_str)
        except: return
        ctx.user_data["bal_act"]="add" if adding else "ded"; ctx.user_data["bal_uid"]=tid; ctx.user_data["step"]="balamt"
        await q.edit_message_text(f"💰 Amount to {'add to' if adding else 'deduct from'} `{tid}`:"); return

    # User orders
    if data.startswith("uorders_"):
        if not is_admin(uid): return
        tid=int(data[8:]); orders,total,pages=get_user_orders(tid,1)
        if not orders: await q.edit_message_text("No orders."); return
        t=f"📋 *Orders of `{tid}`* — 1/{pages}\n━━━━━━━━━━━━━━━\n\n"+"\n\n".join(fmt_order(o) for o in orders)
        await q.edit_message_text(t,parse_mode=ParseMode.MARKDOWN); return

    # Msg user
    if data.startswith("msguser_"):
        if not is_admin(uid): return
        tid=int(data[8:]); ctx.user_data["pm_uid"]=tid; ctx.user_data["step"]="pmtxt"
        await q.edit_message_text(f"✉️ Message to `{tid}`:",parse_mode=ParseMode.MARKDOWN); return

    # Settings
    if data=="sbk":
        if not is_admin(uid): return
        ctx.user_data["step"]="setbk"; await q.edit_message_text("💚 Enter new bKash number:"); return
    if data=="sng":
        if not is_admin(uid): return
        ctx.user_data["step"]="setng"; await q.edit_message_text("🟠 Enter new Nagad number:"); return
    if data=="scom":
        if not is_admin(uid): return
        ctx.user_data["step"]="setcom"; await q.edit_message_text("🎁 Enter commission % (0–100):"); return

# ── MAIN ──────────────────────────────────────────────────────

async def cmd_skip(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    """Handle /skip command"""
    step = ctx.user_data.get("step","")
    dep  = ctx.user_data.get("dep_step","")
    # ── FIX: directly invoke the right step logic ──
    if step=="apusdt":
        ctx.user_data["np_usdt"]=None
        ctx.user_data["step"]="apdesc"
        await update.message.reply_text(
            "📝 *Enter description:*\n(Extra info shown to user)\n\nOr send /skip",
            parse_mode=ParseMode.MARKDOWN,reply_markup=cancel_kb())
    elif step=="apdesc":
        ctx.user_data["np_desc"]=""
        # re-use handle_text logic by faking the text
        update.message.text = "/skip"
        await handle_text(update, ctx)
    elif step=="edesc":
        pid=ctx.user_data.get("epid"); p=get_product(pid)
        if p:
            p["description"]=""; save_product(pid,p); ctx.user_data.clear()
            await update.message.reply_text("✅ Description removed.",reply_markup=admin_kb())
    elif step=="eusdt":
        pid=ctx.user_data.get("epid"); p=get_product(pid)
        if p:
            p["usdt_price"]=None; save_product(pid,p); ctx.user_data.clear()
            await update.message.reply_text("✅ USDT price removed.",reply_markup=admin_kb())
    elif step=="add_prov_desc":
        name=ctx.user_data.get("prov_name","")
        create_provider(name,""); ctx.user_data.clear()
        await update.message.reply_text(f"✅ *Provider Added!*\n🌐 {name}",parse_mode=ParseMode.MARKDOWN,reply_markup=admin_kb())
    else:
        await update.message.reply_text("Nothing to skip.")

async def cmd_done(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    """Handle /done command"""
    step = ctx.user_data.get("step","")
    if step=="stock":
        pid=ctx.user_data.get("spid"); c=get_stock_count(pid); ctx.user_data.clear()
        await update.message.reply_text(f"✅ Done! Stock: *{c}*",parse_mode=ParseMode.MARKDOWN,reply_markup=admin_kb())
    else:
        await update.message.reply_text("Nothing to finish.")

def main():
    init_db()
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("admin", cmd_admin))
    app.add_handler(CommandHandler("skip", cmd_skip))
    app.add_handler(CommandHandler("done", cmd_done))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    app.add_handler(CallbackQueryHandler(handle_cb))
    logger.info("🚀 SpyX Bot started!")
    app.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()