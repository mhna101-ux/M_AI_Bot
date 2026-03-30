# ==============================================================================
# 🐋 CYBER WHALE BOT V15 ULTIMATE - THE COLOSSUS ENGINE (STABLE CONSOLE)
# ==============================================================================

import sys
import io

# ==============================================================================
# --- 1. WINDOWS CMD SHIELD (ANTI-FREEZE PROTOCOL) ---
# ==============================================================================
try:
    if hasattr(sys.stdout, 'buffer'):
        sys.stdout = io.TextIOWrapper(
            sys.stdout.buffer, 
            encoding='utf-8', 
            line_buffering=True
        )
        sys.stderr = io.TextIOWrapper(
            sys.stderr.buffer, 
            encoding='utf-8', 
            line_buffering=True
        )
except Exception:
    pass

# ==============================================================================
# --- 2. STANDARD IMPORTS ---
# ==============================================================================
import time
import threading
import os
import subprocess

# ==============================================================================
# --- COCKPIT DASHBOARD: ANSI COLOR ENABLER (Windows 10+) ---
# ==============================================================================
os.system('')  # تفعيل ألوان ANSI في Windows CMD/PowerShell

# رموز الألوان
_G  = '\033[32m'    # أخضر داكن (للإطار)
_GB = '\033[92m'    # أخضر فاقع (للأرقام المهمة والأرباح)
_GD = '\033[2;32m'  # أخضر خافت (للبيانات الثانوية)
_R  = '\033[91m'    # أحمر (للتحذيرات)
_Y  = '\033[93m'    # أصفر (للحالة المتوسطة)
_B  = '\033[1m'     # غامق Bold
_DIM= '\033[2m'     # خافت
_RST= '\033[0m'     # إعادة ضبط
import requests
import json
import re
import logging
import sqlite3
import queue
import concurrent.futures
from concurrent.futures import as_completed
import psutil
import traceback
import getpass
import random
from datetime import datetime, timedelta
from typing import Optional, Tuple, Dict, Any, List

import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
import websocket
from web3 import Web3
from groq import Groq
from dotenv import load_dotenv

# ==============================================================================
# --- 3. CONFIGURATION & ENVIRONMENT VARIABLES ---
# ==============================================================================
load_dotenv()

PRIVATE_KEY = os.getenv("PRIVATEKEY")
if not PRIVATE_KEY:
    print("\n⚠️ لم يتم العثور على Private Key في المتغيرات.")
    PRIVATE_KEY = getpass.getpass("🔑 أدخل الـ Private Key الخاص بمحفظتك للبدء (لن يظهر على الشاشة): ")

WALLET_ADDRESS_ENV = os.getenv("WALLET_ADDRESS")
TELEGRAM_TOKEN = os.getenv("TELEGRAMTOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAMCHATID")
GROQ_API_KEY = os.getenv("GROQAPIKEY")

# Logging Setup
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

TRADE_DB_FILE = os.getenv("TRADE_DB_FILE", "trades.db")
PROFITS_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "total_profits.json")

MIN_BUY_USD = float(os.getenv("MIN_BUY_USD", "5.0"))           
PRICE_CACHE_SECONDS = int(os.getenv("PRICE_CACHE_SECONDS", "3"))
MAX_APPROVE_USDT = float(os.getenv("MAX_APPROVE_USDT", "10000"))
BUY_LADDER_STR = os.getenv("BUY_LADDER", "0.02:0.10,0.05:0.20,0.10:0.40")
SELL_LADDER_STR = os.getenv("SELL_LADDER", "0.05:0.50,0.08:1.00")
COOLDOWN_SECONDS = int(os.getenv("COOLDOWN_SECONDS", "900"))
MIN_BNB_TO_KEEP = float(os.getenv("MIN_BNB_TO_KEEP", "0.005"))
MAX_GAS_RATIO = float(os.getenv("MAX_GAS_RATIO", "0.20"))
MIN_LIQUIDITY_USD = float(os.getenv("MIN_LIQUIDITY_USD", "50000"))
MAX_ARB_SIZE_USD = float(os.getenv("MAX_ARB_SIZE_USD", "1000"))
TRAILING_STOP_PERCENT = float(os.getenv("TRAILING_STOP_PERCENT", "1.5"))

# ==============================================================================
# --- 🏗️ تحويل النصوص إلى قواموس (Parse Ladders to Dicts) ---
# ==============================================================================
def parse_ladder_string(ladder_str: str) -> dict:
    """تحويل نص السلم إلى قاموس {نسبة_الهبوط: نسبة_المبلغ}"""
    try:
        ladder = {}
        for pair in ladder_str.split(','):
            drop, amount = pair.split(':')
            ladder[float(drop)] = float(amount)
        return ladder
    except Exception as e:
        print(f"⚠️ خطأ في تحليل السلم: {e}")
        return {}

# تحويل النصوص إلى قواموس
BUY_LADDER = parse_ladder_string(BUY_LADDER_STR)
SELL_LADDER = parse_ladder_string(SELL_LADDER_STR)

# تأكد من أن السلالم ليست فارغة (قيم افتراضية كحماية)
if not BUY_LADDER:
    print("⚠️ تم استخدام قيم افتراضية للـ BUY_LADDER")
    BUY_LADDER = {0.02: 0.10, 0.05: 0.20, 0.10: 0.40}

if not SELL_LADDER:
    print("⚠️ تم استخدام قيم افتراضية للـ SELL_LADDER")
    SELL_LADDER = {0.05: 0.50, 0.08: 1.00}

# ==============================================================================
# --- 💰 إعدادات الأرباح والخسائر (PROFIT & LOSS SETTINGS) ---
# ==============================================================================
TARGET_PROFIT = float(os.getenv("TARGET_PROFIT", "2.0"))  # 2% gain target
STOP_LOSS = float(os.getenv("STOP_LOSS", "1.0"))  # 1% loss limit


# ==============================================================================
# --- 3. ⚙️ [SYSTEM CONSTANTS & BLOCKCHAIN ADDRESSES] ---
# ==============================================================================
ROUTER_ADDR = os.getenv("ROUTER_ADDR", "0x10ED43C718714eb63d5aA57B78B54704E256024E")
USDT_ADDR   = os.getenv("USDT_ADDR",   "0x55d398326f99059fF775485246999027B3197955")
WBNB_ADDR   = os.getenv("WBNB_ADDR",   "0xbb4CdB9CBd36B01bD1cBaEBF2De08d9173bc095c")
ETH_ADDR    = os.getenv("ETH_ADDR",    "0x2170Ed0880ac9A755fd29B2688956BD959F933F8")  # Binance-Peg ETH
SOL_ADDR    = os.getenv("SOL_ADDR",    "0x570A5D26f7765Ecb712C0924E4De545B89fD43dF")  # Binance-Peg SOL
PAIR_ADDRESS = "0x16b9a82891338f9bA80E2D6970FddA79D1eb0daE"  # PancakeSwap WBNB/USDT Pool
PANCAKESWAP_FACTORY = "0xcA143Ce32Fe78f1f7019d7d551a6402fC5350c73"
ARBITRAGE_AMOUNT_IN_1 = 1000000000000000000   # 1 WBNB
MAX_LOAN_BNB = float(os.getenv("MAX_LOAN_BNB", "20.0"))

# ABIs
ROUTER_ABI = json.loads('[{"inputs":[{"internalType":"uint256","name":"amountIn","type":"uint256"},{"internalType":"address[]","name":"path","type":"address[]"}],"name":"getAmountsOut","outputs":[{"internalType":"uint256[]","name":"amounts","type":"uint256[]"}],"stateMutability":"view","type":"function"},{"inputs":[{"internalType":"uint256","name":"amountOutMin","type":"uint256"},{"internalType":"address[]","name":"path","type":"address[]"},{"internalType":"address","name":"to","type":"address"},{"internalType":"uint256","name":"deadline","type":"uint256"}],"name":"swapExactETHForTokens","outputs":[{"internalType":"uint256[]","name":"amounts","type":"uint256[]"}],"stateMutability":"payable","type":"function"},{"inputs":[{"internalType":"uint256","name":"amountIn","type":"uint256"},{"internalType":"uint256","name":"amountOutMin","type":"uint256"},{"internalType":"address[]","name":"path","type":"address[]"},{"internalType":"address","name":"to","type":"address"},{"internalType":"uint256","name":"deadline","type":"uint256"}],"name":"swapExactTokensForETH","outputs":[{"internalType":"uint256[]","name":"amounts","type":"uint256[]"}],"stateMutability":"nonpayable","type":"function"},{"inputs":[{"internalType":"uint256","name":"amountIn","type":"uint256"},{"internalType":"uint256","name":"amountOutMin","type":"uint256"},{"internalType":"address[]","name":"path","type":"address[]"},{"internalType":"address","name":"to","type":"address"},{"internalType":"uint256","name":"deadline","type":"uint256"}],"name":"swapExactTokensForTokens","outputs":[{"internalType":"uint256[]","name":"amounts","type":"uint256[]"}],"stateMutability":"nonpayable","type":"function"}]')
ERC20_ABI = json.loads('[{"constant":true,"inputs":[{"name":"owner","type":"address"}],"name":"balanceOf","outputs":[{"name":"balance","type":"uint256"}],"type":"function"},{"constant":false,"inputs":[{"name":"spender","type":"address"},{"name":"value","type":"uint256"}],"name":"approve","outputs":[{"name":"","type":"bool"}],"type":"function"},{"constant":true,"inputs":[{"name":"owner","type":"address"},{"name":"spender","type":"address"}],"name":"allowance","outputs":[{"name":"","type":"uint256"}],"type":"function"},{"constant":true,"inputs":[],"name":"decimals","outputs":[{"name":"","type":"uint8"}],"type":"function"},{"constant":true,"inputs":[],"name":"symbol","outputs":[{"name":"","type":"string"}],"type":"function"}]')
FACTORY_ABI = json.loads('[{"constant":true,"inputs":[{"internalType":"address","name":"","type":"address"},{"internalType":"address","name":"","type":"address"}],"name":"getPair","outputs":[{"internalType":"address","name":"","type":"address"}],"payable":false,"stateMutability":"view","type":"function"}]')

XRP_ADDR   = "0x1D2F0da169ceB9fC7B3144628dB156f3F6c60dBE"
BTCB_ADDR  = "0x7130d2A12B9BCbFAe4f2634d864A1Ee1Ce3Ead9c"
LINK_ADDR  = "0xF8A0BF9cF54Bb92F17374d9e9A321E6a111a51bD"
MATIC_ADDR = "0xCC42724C6683B7E57334c4E856f4c9965ED682bD"
UNI_ADDR   = "0xBf5140A22578168FD562DCcF235E5D43A02ce9B1"
AVAX_ADDR  = "0x1CE0c2827e2eF14D5C4f29a091d735A204794041"
DOT_ADDR   = "0x7083609fCE4d1d8Dc0C979AAb8c869Ea2C873402"
ADA_ADDR   = "0x3EE2200Efb3400fAbB9AacF31297cBdD1d435D47"
DOGE_ADDR  = "0xbA2aE424d960c26247Dd6c32edC70B295c744C43"
CAKE_ADDR  = "0x0E09FaBB73Bd3Ade0a17ECC321fD13a19e81cE82"
LTC_ADDR   = "0x4338665CBB7B2485A8855A139b75D5e34AB0DB94"
BCH_ADDR   = "0x8fF795a6F4D97E7887C79beA79aba5cc76444aDf"
ATOM_ADDR  = "0x0Eb3a705fc54725037CC9e008bDede697f62F335"
AXS_ADDR   = "0x715D400F88C167884bbCc41C5FeA407ed4D2f8A0"
FIL_ADDR   = "0x0D8Ce2A99Bb6e3B7Db580eD848240e4a0F9aE153"
NEAR_ADDR  = "0x1Fa4a73a3F0133f0025378af00236f3aBEeE954B"
TRX_ADDR   = "0x85EAC5Ac2F758618Dfa09bDbe0cf174e7d574D5B"
GMT_ADDR   = "0x3019BF2a2eF8040C242C9a4c5D2CF68Be70cc83a"

DEX_ROUTERS = {
    "PancakeSwap V2": "0x10ED43C718714eb63d5aA57B78B54704E256024E",
    "Biswap":         "0x3a6d8cA21D1CF76F653A67577FA0D27453350dD8",
    "ApeSwap":        "0xcF0feBd3f17CEf5b47b0cD257aCf6025c5BFf3b7",
    "DODO V2":        "0xBe9Aa485F4D76533081e831206cAbf1981Fbe9aC"
}

FLASH_ARBITRAGE_ADDRESS = "0x077125c612F3703bBaF7135F1A177E9C44b0Ba7F"
FLASH_ARBITRAGE_ABI = [{"inputs":[{"internalType":"address","name":"_pairAddress","type":"address"},{"internalType":"uint256","name":"_amountToBorrow","type":"uint256"},{"internalType":"address","name":"_wbnb","type":"address"},{"internalType":"address","name":"_usdt","type":"address"},{"internalType":"address","name":"_router1","type":"address"},{"internalType":"address","name":"_router2","type":"address"}],"name":"startArbitrage","outputs":[],"stateMutability":"nonpayable","type":"function"},{"inputs":[{"internalType":"address","name":"_token","type":"address"}],"name":"withdrawProfits","outputs":[],"stateMutability":"nonpayable","type":"function"}]

# ☢️ NUCLEAR PROTOCOL: ADVANCED LIQUIDITY NODES
DODO_V2_POOL = "0xFeA7a9D113003790b40fd3ac8f236eba01FD60ba" # DODO V2 Pool for USDT/WBNB
VENUS_COMPTROLLER = "0xfD36E2c2a6789Db23113685031d7F16329158384" # Venus Protocol (BSC)

# ==============================================================================
# --- 🌐 المودم المصفح (HARDENED RPC & SESSION MANAGEMENT) ---
# ==============================================================================
RPC_LIST = [
    "https://bsc-dataseed.binance.org/",
    "https://bsc-dataseed1.defibit.io/",
    "https://1rpc.io/bnb",
    "https://rpc.ankr.com/bsc"
]

session = requests.Session()
adapter = requests.adapters.HTTPAdapter(pool_connections=20, pool_maxsize=20, max_retries=1)
session.mount('https://', adapter)
session.mount('http://', adapter)


def get_stable_w3():
    global router, usdt_token, flash_contract, dex_contracts
    for url in RPC_LIST:
        try:
            _w3 = Web3(Web3.HTTPProvider(url, session=session, request_kwargs={'timeout': 5}))
            if _w3.is_connected():
                router = _w3.eth.contract(address=ROUTER_ADDR, abi=ROUTER_ABI)
                usdt_token = _w3.eth.contract(address=USDT_ADDR, abi=ERC20_ABI)
                flash_contract = _w3.eth.contract(address=Web3.to_checksum_address(FLASH_ARBITRAGE_ADDRESS), abi=FLASH_ARBITRAGE_ABI)
                dex_contracts = {}
                for name, addr in DEX_ROUTERS.items():
                    dex_contracts[name] = _w3.eth.contract(address=Web3.to_checksum_address(addr), abi=ROUTER_ABI)
                return _w3, url
        except: continue
    return None, None

w3, ACTIVE_RPC = get_stable_w3()
if not w3:
    print("\u274c CRITICAL: All RPC nodes are down. Check your internet.")
    sys.exit(1)

wallet_address = w3.to_checksum_address(
    WALLET_ADDRESS_ENV if WALLET_ADDRESS_ENV
    else "0xEe3A81CA82047d18463944eC87A93e203343de5e"
)

ws_ready = True
# ☢️ NUCLEAR ACTIVATION: TRADE_MODE FORCED TO REAL
TRADE_MODE = "REAL"  # تم تفعيل الوضع الحقيقي نهائياً
PAPER_TRADING = False
PAPER_BALANCE_USDT = 0.0
USE_TRAILING_STOP = True

# --- 🪂 إضافات V16 ---
TRAILING_BUY_REBOUND_PCT = float(os.getenv("TRAILING_BUY_REBOUND_PCT", "0.5"))

MAX_GAS_FEE_USD = float(os.getenv("MAX_GAS_FEE_USD", "1.50"))
GAS_MULTIPLIER = float(os.getenv("GAS_MULTIPLIER", "1.1"))
RSI_OVERSOLD = int(os.getenv("RSI_OVERSOLD", "35"))
MACD_BEARISH = float(os.getenv("MACD_BEARISH", "0.0"))

# ==============================================================================
# --- 5. ASYNC DATABASE & THREAD POOL ---
# ==============================================================================
trade_executor = concurrent.futures.ThreadPoolExecutor(max_workers=2, thread_name_prefix="TradeEngine")
db_queue = queue.Queue()
loop_alive_time = time.time()
BOT_START_TIME = time.time()

# ==============================================================================
# --- 💰 PROFIT PERSISTENCE ENGINE (إجمالي الأرباح الدائمة) ---
# ==============================================================================
_profits_lock = threading.Lock()

def load_total_profits() -> float:
    """يقرأ إجمالي الأرباح من الملف عند كل إعادة تشغيل (حماية من التصفير)"""
    try:
        if os.path.exists(PROFITS_FILE):
            with open(PROFITS_FILE, 'r') as f:
                data = json.load(f)
                return float(data.get("total_profit_usd", 0.0))
    except Exception:
        pass
    return 0.0

def save_total_profits(amount: float):
    """يحفظ إجمالي الأرباح للملف بشكل آمن (Thread-Safe)"""
    try:
        with _profits_lock:
            with open(PROFITS_FILE, 'w') as f:
                json.dump({
                    "total_profit_usd": round(amount, 4),
                    "last_updated": datetime.now().isoformat()
                }, f, indent=2)
    except Exception as e:
        logger.error(f"[PROFITS] Failed to save: {e}")

def add_profit(net_profit_usd: float):
    """يُضيف ربحاً صافياً لإجمالي الأرباح ويحفظه فوراً"""
    global _total_profit_usd
    with _profits_lock:
        _total_profit_usd += net_profit_usd
    save_total_profits(_total_profit_usd)

# تحميل الأرباح عند بدء التشغيل (الحماية من التصفير)
_total_profit_usd: float = load_total_profits()

# ==============================================================================
# --- 🖥️ ACTION LOG + COCKPIT RENDERER ---
# ==============================================================================
_action_log: list = []   # سجل الأحداث الحقيقية (أقصى 8 سطور)
_dashboard_lock = threading.Lock()

def log_action(icon: str, action_type: str, details: str, net_profit: float = 0.0):
    """
    يُضيف حدثاً حقيقياً للسجل (صفقة / مراجحة / خطأ جسيم فقط).
    يُضيف الربح الصافي لإجمالي الأرباح إذا كان موجوداً.
    """
    global _action_log
    ts = datetime.now().strftime("%H:%M:%S")
    entry = f"  [{ts}] {icon} {action_type:<13} | {details}"
    if net_profit != 0.0:
        profit_color = _GB if net_profit > 0 else _R
        entry += f" | PnL: {profit_color}{net_profit:+.2f}${_RST}"
        if net_profit > 0:
            add_profit(net_profit)
    with _dashboard_lock:
        _action_log.append(entry)
        if len(_action_log) > 8:   # نحافظ على آخر 8 أحداث
            _action_log.pop(0)

def render_cockpit_dashboard(
    coin_market_data: dict,
    usdt_bal: float,
    cpu_usage: float,
    btc_crashed: bool,
    mode_str: str
):
    """يمسح الشاشة ويرسم لوحة تحكم مقصورة الطائرة الحربية دفعةً واحدة."""

    # ─── بيانات العملات القيادية الثلاث ───────────────────────────────────────
    cmd_coins = ["BNB", "ETH", "SOL"]
    cmd_data  = {}
    for sym in cmd_coins:
        d = latest_market_data["coins"].get(sym, {})
        c = state.coins.get(sym, None)
        price      = d.get("price", 0.0)
        tgt_buy    = d.get("target_buy",  0.0)
        tgt_sell   = d.get("target_sell", 0.0)
        if c and c.trailing_active and c.highest_price > 0:
            stop_p   = c.highest_price * (1 - c.trailing_deviation)
            tgt_sell = stop_p  # نعرض سعر الوقف المتحرك
        cmd_data[sym] = (price, tgt_buy, tgt_sell)

    def coin_col(sym: str) -> str:
        price, buy_t, sell_t = cmd_data[sym]
        p_str  = f"{_GB}{price:>10.2f}${_RST}" if price > 0  else f"{'---':>11}"
        b_str  = f"{_G}{buy_t:>10.2f}${_RST}"  if buy_t > 0 else f"{'---':>11}"
        s_str  = f"{_GB}{sell_t:>10.2f}${_RST}" if sell_t > 0 else f"{'---':>11}"
        name   = f"{_B}{_GB}{sym}/USDT{_RST}"
        return (
            f"  {name:<22}\n"
            f"  Price  : {p_str}\n"
            f"  Buy @  : {b_str}\n"
            f"  Sell @ : {s_str}"
        )

    bnb_col = coin_col("BNB").splitlines()
    eth_col = coin_col("ETH").splitlines()
    sol_col = coin_col("SOL").splitlines()

    # ─── حالة النظام ───────────────────────────────────────────────────────────
    # تحسين: نعتبر البوت متصلاً إذا كان هناك استجابة من عقدة الـ RPC ولدينا رصيد
    is_online = (w3 is not None and w3.is_connected()) or (usdt_bal > 0)
    net_status    = f"{_GB}✅ ONLINE{_RST}" if is_online else f"{_R}❌ OFFLINE{_RST}"
    btc_status    = f"{_R}🔴 BTC CRASH{_RST}" if btc_crashed else f"{_GB}🟢 Safe{_RST}"
    active_coins  = len(coin_market_data)
    radar_status  = f"{_GB}✅ {active_coins}/4 Targets Locked{_RST}"
    mode_col      = f"{_R}{mode_str}{_RST}" if mode_str == "REAL" else f"{_Y}{mode_str}{_RST}"
    # نسبة استخدام CPU مع لون تحذيري
    cpu_col = _R if cpu_usage >= 80 else (_Y if cpu_usage >= 60 else _GB)
    temp_str = f"{cpu_col}{cpu_usage:.0f}%{_RST}"

    # uptime
    up_sec  = int(time.time() - BOT_START_TIME)
    days    = up_sec // 86400
    hours   = (up_sec % 86400) // 3600
    mins    = (up_sec % 3600) // 60
    uptime  = f"{days}d {hours:02d}h {mins:02d}m" if days > 0 else f"{hours:02d}h {mins:02d}m"

    # ─── إجمالي الأرباح (العلامة الخضراء) ────────────────────────────────────
    profit_str = f"{_GB}{_B}$ {_total_profit_usd:+.4f}{_RST}"

    # ─── Action Log ───────────────────────────────────────────────────────────
    with _dashboard_lock:
        log_lines = list(_action_log)
    # نملأ لأسفل لو السجل أقل من 8 سطور
    while len(log_lines) < 8:
        log_lines.append("")

    W = 84   # عرض اللوحة الإجمالي (أحرف)

    def bar(char="═", width=W) -> str:
        return _G + char * width + _RST

    def row(content: str, width=W) -> str:
        """يُحاط المحتوى بإطار البوابة ║ ويُكمل العرض بمسافات."""
        # نحسب الطول المرئي (بدون رموز ANSI)
        visible = re.sub(r'\033\[[0-9;]*m', '', content)
        pad     = width - 2 - len(visible)
        pad     = max(pad, 0)
        return f"{_G}║{_RST}{content}{' ' * pad}{_G}║{_RST}"

    # ─── بناء اللوحة ───────────────────────────────────────────────────────────
    lines = []
    # Header
    lines.append(f"{_G}╔{bar('═', W-2)}╗{_RST}")
    header_txt = f"  {_GB}{_B}⚡ CYBER WHALE AI  ——  COCKPIT DASHBOARD  ——  v17 COLOSSUS  |  {mode_col}  MODE{_RST}"
    lines.append(row(header_txt))
    lines.append(f"{_G}╠{bar('═', W-2)}╣{_RST}")

    # Command Coins section
    lines.append(row(f"  {_B}{_G}⚡ COMMAND COINS{_RST}"))
    lines.append(row(""))

    col_w = 26   # عرض كل خانة عملة
    for i in range(4):
        b = bnb_col[i] if i < len(bnb_col) else ""
        e = eth_col[i] if i < len(eth_col) else ""
        s = sol_col[i] if i < len(sol_col) else ""
        b_vis = re.sub(r'\033\[[0-9;]*m', '', b)
        e_vis = re.sub(r'\033\[[0-9;]*m', '', e)
        s_vis = re.sub(r'\033\[[0-9;]*m', '', s)
        b_pad = " " * max(0, col_w - len(b_vis))
        e_pad = " " * max(0, col_w - len(e_vis))
        combined = b + b_pad + "  " + e + e_pad + "  " + s
        lines.append(row(combined))

    lines.append(row(""))
    lines.append(f"{_G}╠{bar('═', W-2)}╣{_RST}")

    # System Status section
    lines.append(row(f"  {_B}{_G}🛡️  SYSTEM STATUS{_RST}"))
    lines.append(row(
        f"  CPU      : {temp_str}    "
        f"Net : {net_status}    "
        f"Radar : {radar_status}"
    ))
    lines.append(row(
        f"  Uptime   : {_GD}{uptime}{_RST}    "
        f"Mode: {mode_col}    "
        f"BTC   : {btc_status}"
    ))
    lines.append(row(
        f"  {_B}💰 Total Profit  : {profit_str}   "
        f"{_GD}(USDT • accumulated since first boot){_RST}"
    ))
    lines.append(f"{_G}╠{bar('═', W-2)}╣{_RST}")

    # ─── Triangular Scan section ──────────────────────────────────────────────
    lines.append(row(f"  {_B}{_G}△ TRIANGULAR SCAN{_RST}  {_GD}[ Fast In-DEX Arbitrage — Fee: 0.75% ]{_RST}"))
    with _tri_scan_lock:
        tri_path = _tri_scan_result["path"]
        tri_spread = _tri_scan_result["spread"]
        tri_status = _tri_scan_result["status"]
    
    spread_col = _GB if tri_spread > 0.75 else (_Y if tri_spread > 0 else _GD)
    status_col = _R if tri_status == "TARGET LOCKED" else _GD
    lines.append(row(f"  Best Path  : {_B}{tri_path}{_RST}"))
    lines.append(row(f"  Net Spread : {spread_col}{tri_spread:+.4f}%{_RST}  |  Status: {status_col}{tri_status}{_RST}"))
    lines.append(f"{_G}╠{bar('═', W-2)}╣{_RST}")

    # Action Log section
    lines.append(row(
        f"  {_B}{_G}📡 ACTION LOG{_RST}  "
        f"{_GD}[ Real Events Only — Buy / Sell / Arbitrage / Critical Error ]{_RST}"
    ))
    for ln in log_lines:
        lines.append(row(ln if ln else ""))

    # Footer
    ts_now = datetime.now().strftime("%Y-%m-%d  %H:%M:%S")
    rpc_name = ACTIVE_RPC.split("//")[1].split("/")[0][:15] # تبسيط شكل الرابط
    lines.append(f"{_G}╠{bar('═', W-2)}╣{_RST}")
    lines.append(row(f"  {_GD}Last refresh: {ts_now}   RPC: {rpc_name}...   Bal: {usdt_bal:.2f}${_RST}"))
    lines.append(f"{_G}╚{bar('═', W-2)}╝{_RST}")

    # المسح ثم الطباعة دفعةً واحدة
    os.system('cls')
    print('\n'.join(lines), flush=True)

bot = telebot.TeleBot(TELEGRAM_TOKEN)

def init_db():
    try:
        conn = sqlite3.connect(TRADE_DB_FILE)
        c = conn.cursor()
        c.execute('''
            CREATE TABLE IF NOT EXISTS trades (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                tx_hash TEXT,
                action TEXT,
                amount_usd REAL,
                price REAL,
                gas_usd REAL,
                timestamp INTEGER,
                mode TEXT
            )
        ''')
        c.execute("CREATE INDEX IF NOT EXISTS idx_timestamp ON trades (timestamp)")
        conn.commit()
        conn.close()
    except Exception as e:
        logger.error(f"Database initialization failed: {e}")

init_db()

def db_worker():
    while True:
        task = db_queue.get()
        if task is None: break
        try:
            conn = sqlite3.connect(TRADE_DB_FILE)
            c = conn.cursor()
            c.execute('''INSERT INTO trades (tx_hash, action, amount_usd, price, gas_usd, timestamp, mode) VALUES (?, ?, ?, ?, ?, ?, ?)''', task)
            conn.commit()
            conn.close()
        except Exception as e:
            logger.error(f"Failed to log trade to DB: {e}")
        db_queue.task_done()

threading.Thread(target=db_worker, daemon=True).start()

def log_trade(tx_hash: str, action: str, amount_usd: float, price: float, gas_usd: float, mode: str = "Real"):
    db_queue.put((tx_hash, action, amount_usd, price, gas_usd, int(time.time()), mode))

# ==============================================================================
# --- 6. MULTI-COIN STATE MANAGER V16 ---
# ==============================================================================
MEMORY_FILE = "botmemory_v16.json"
state_lock = threading.RLock()

# ==============================================================================
# --- 🎯 رادار المسح الشامل (MARKET SCAN RADAR) - محسّن للسرعة والتركيز ---
# قائمة موحدة بأقوى 4 عملات من حيث السيولة (The Big 4)
# ==============================================================================
SUPPORTED_COINS = {
    "BNB":   WBNB_ADDR,   
    "ETH":   ETH_ADDR,    
    "SOL":   SOL_ADDR,    
    "XRP":   XRP_ADDR,    
}

# مسارات المراجحة المثلثية (80 مساراً)
TRIANGULAR_PATHS = []
for _sym, _addr in SUPPORTED_COINS.items():
    if _sym == "BNB": continue
    TRIANGULAR_PATHS.append(["USDT", "BNB",  _sym,  "USDT"])
    TRIANGULAR_PATHS.append(["USDT", _sym,   "BNB",  "USDT"])
    TRIANGULAR_PATHS.append(["BNB",  "USDT", _sym,  "BNB"])
    TRIANGULAR_PATHS.append(["BNB",  _sym,   "USDT", "BNB"])

class CoinState:
    def __init__(self):
        self.total_spent_usdt = 0.0
        self.total_held = 0.0
        self.initial_position = 0.0
        self.average_buy_price = 0.0
        self.last_auto_buy_level = 0.0
        self.last_auto_sell_level = 0.0
        self.trailing_active = False
        self.trailing_trigger_level = 0.0
        self.peak_profit_pct = 0.0
        self.trailing_buy_active = False
        self.lowest_drop_pct = 0.0
        self.last_auto_action_time = 0.0
        self.highest_price = 0.0
        self.trailing_deviation = 0.005

class BotState:
    def __init__(self):
        self.bot_active = True
        self.next_market_report = datetime.now() + timedelta(hours=1)
        self.coins = {coin: CoinState() for coin in SUPPORTED_COINS.keys()}
        self.load()

    def load(self):
        if os.path.exists(MEMORY_FILE):
            try:
                with open(MEMORY_FILE, 'r') as f:
                    data = json.load(f)
                    with state_lock:
                        self.bot_active = data.get("bot_active", True)
                        for coin in self.coins.keys():
                            if coin in data:
                                c_data = data[coin]
                                c = self.coins[coin]
                                c.total_spent_usdt = c_data.get("total_spent_usdt", 0.0)
                                c.average_buy_price = c_data.get("average_buy_price", 0.0)
                                c.total_held = c_data.get("total_held", 0.0)
                                c.initial_position = c_data.get("initial_position", c.total_held)
                                c.last_auto_buy_level = c_data.get("last_auto_buy_level", 0.0)
                                c.last_auto_sell_level = c_data.get("last_auto_sell_level", 0.0)
                                c.trailing_active = c_data.get("trailing_active", False)
                                c.trailing_trigger_level = c_data.get("trailing_trigger_level", 0.0)
                                c.peak_profit_pct = c_data.get("peak_profit_pct", 0.0)
                                c.trailing_buy_active = c_data.get("trailing_buy_active", False)
                                c.highest_price = c_data.get("highest_price", 0.0)
                                c.trailing_deviation = c_data.get("trailing_deviation", 0.005)
            except Exception: pass

    def save(self):
        try:
            with state_lock:
                data = {"bot_active": self.bot_active}
                for coin, c in self.coins.items():
                    data[coin] = {
                        "total_spent_usdt": c.total_spent_usdt,
                        "average_buy_price": c.average_buy_price,
                        "total_held": c.total_held,
                        "initial_position": c.initial_position,
                        "last_auto_buy_level": c.last_auto_buy_level,
                        "last_auto_sell_level": c.last_auto_sell_level,
                        "trailing_active": c.trailing_active,
                        "trailing_trigger_level": c.trailing_trigger_level,
                        "peak_profit_pct": c.peak_profit_pct,
                        "trailing_buy_active": c.trailing_buy_active,
                        "lowest_drop_pct": c.lowest_drop_pct,
                        "highest_price": c.highest_price,
                        "trailing_deviation": c.trailing_deviation
                    }
            with open(MEMORY_FILE, 'w') as f:
                json.dump(data, f)
        except Exception: pass

state = BotState()

# ==============================================================================
# --- 7. WATCHDOG ---
# ==============================================================================
def watchdog_worker():
    global loop_alive_time
    alerted = False
    while True:
        time.sleep(30)
        if time.time() - loop_alive_time > 300: # 300s = 5 minutes
            if not alerted and state.bot_active:
                try:
                    bot.send_message(TELEGRAM_CHAT_ID, "🚨 **تنبيه:** محرك التداول الأساسي لا يستجيب منذ 5 دقائق متواصلة! يرجى فحص السيرفر.")
                except Exception:
                    pass
                alerted = True
        else:
            alerted = False

threading.Thread(target=watchdog_worker, daemon=True).start()

# ==============================================================================
# --- ☢️ NUCLEAR: MEMPOOL & LIQUIDATION RADARS ---
# ==============================================================================
_mempool_trigger = threading.Event()

def mempool_watcher():
    """الضربة الاستباقية: مراقبة الـ Mempool بحثاً عن معاملات الحيتان المعلقة"""
    print("[☢️ NUCLEAR] Mempool Watcher active...", flush=True)
    while True:
        try:
            # نراقب المعاملات المعلقة في القائمة (Pending Block)
            pending_block = w3.eth.get_block('pending', full_transactions=True)
            for tx in pending_block.transactions:
                # ☢️ NUCLEAR: مراقبة USDT + WBNB + DODO Pools
                to_addr = tx['to'].lower() if tx['to'] else ""
                is_whale_move = (to_addr in [USDT_ADDR.lower(), WBNB_ADDR.lower(), DODO_V2_POOL.lower()])
                
                if is_whale_move and tx['value'] > w3.to_wei(50000, 'ether'):
                        print(f"🐋 [MEMPOOL] Large movement detected! Triggering rapid scan...", flush=True)
                        _mempool_trigger.set()
                        break
            time.sleep(1) # تفادي ضغط الـ RPC في الوضع العادي
        except Exception:
            time.sleep(5)

threading.Thread(target=mempool_watcher, daemon=True, name="MempoolScanner").start()

# ==============================================================================
# --- 8. MARKET ORACLE ---
# ==============================================================================
_price_cache = {"price": 0.0, "timestamp": 0}
_price_lock = threading.Lock()
ws_ready = False
_ws_lock = threading.Lock()

def on_ws_message(ws, message):
    global ws_ready
    try:
        data = json.loads(message)
        if 'p' in data:
            with _price_lock:
                _price_cache["price"] = float(data['p'])
                _price_cache["timestamp"] = time.time()
            with _ws_lock:
                ws_ready = True
    except Exception:
        pass

def ws_thread():
    global ws_ready
    backoff = 1
    while True:
        try:
            ws = websocket.WebSocketApp("wss://stream.binance.com:9443/ws/bnbusdt@aggTrade", on_message=on_ws_message)
            ws.run_forever(ping_interval=30, ping_timeout=60)
            time.sleep(backoff)
            backoff = min(backoff * 2, 60)
        except Exception:
            time.sleep(backoff)
            backoff = min(backoff * 2, 60)

threading.Thread(target=ws_thread, daemon=True).start()

def get_bnb_price(use_cache: bool = True) -> float:
    with _price_lock:
        cache_age = time.time() - _price_cache["timestamp"]
        if use_cache and cache_age < PRICE_CACHE_SECONDS and _price_cache["price"] > 0:
            return _price_cache["price"]
    try:
        amounts = router.functions.getAmountsOut(w3.to_wei(1, 'ether'), [WBNB_ADDR, USDT_ADDR]).call()
        price = amounts[1] / 10**18
        if price > 0:
            with _price_lock:
                _price_cache["price"] = price
                _price_cache["timestamp"] = time.time()
            return price
        else:
            return _price_cache["price"]
    except Exception:
        return _price_cache["price"]

# ==============================================================================
# --- 💾 GLOBAL CACHE SYSTEM: Centralized Price & Balance Updates ---
# ==============================================================================
_global_prices_lock = threading.Lock()
_global_balances_lock = threading.Lock()
_price_buffer_lock = threading.Lock()

# قواموس التخزين المركزي
global_prices = {}       # {symbol: {'price': float, 'timestamp': float, 'rsi': float}}
global_balances = {}     # {'usdt': float, 'bnb': float, 'timestamp': float}

# 🔥 NEW: مخزن بيانات مؤقت للأسعار (آخر 50 سعر لكل عملة) للمؤشرات التقنية
price_buffer = {}  # {symbol: [price1, price2, ..., price50]}
price_buffer_timestamps = {}  # {symbol: timestamp}
PRICE_BUFFER_SIZE = 50
BUFFER_UPDATE_INTERVAL = 300  # تحديث كل 5 دقائق

def initialize_price_buffers():
    """تهيئة مخازن الأسعار عند البدء"""
    print("[BOOT] Initializing price buffers...", flush=True)
    for symbol in list(SUPPORTED_COINS.keys())[:10]:
        try:
            # جلب آخر 50 سعراً من Binance (فقط مرة واحدة عند البدء)
            url = f"https://api.binance.com/api/v3/klines?symbol={symbol}USDT&interval=1m&limit=50"
            resp = requests.get(url, timeout=5).json()
            prices = [float(c[4]) for c in resp if len(c) > 4]
            
            with _price_buffer_lock:
                price_buffer[symbol] = prices[-PRICE_BUFFER_SIZE:] if len(prices) >= PRICE_BUFFER_SIZE else prices
                price_buffer_timestamps[symbol] = time.time()
            
            print(f"  ✅ {symbol}: {len(price_buffer[symbol])} أسعار محملة", flush=True)
        except Exception as e:
            print(f"  ⚠️ {symbol}: فشل التحميل", flush=True)
            with _price_buffer_lock:
                price_buffer[symbol] = [0.0]
                price_buffer_timestamps[symbol] = time.time()

def update_price_buffers_worker():
    """Thread منفصلة لتحديث مخازن الأسعار كل 5 دقائق"""
    global price_buffer, price_buffer_timestamps
    print("[BUFFERS] Price buffer updater started", flush=True)
    while True:
        try:
            for symbol in list(SUPPORTED_COINS.keys())[:10]:
                try:
                    # تحديث كل 5 دقائق فقط - ليس كل ثانية
                    if time.time() - price_buffer_timestamps.get(symbol, 0) < BUFFER_UPDATE_INTERVAL:
                        continue
                    
                    url = f"https://api.binance.com/api/v3/klines?symbol={symbol}USDT&interval=1m&limit=50"
                    resp = requests.get(url, timeout=5).json()
                    prices = [float(c[4]) for c in resp if len(c) > 4]
                    
                    if prices:
                        with _price_buffer_lock:
                            price_buffer[symbol] = prices[-PRICE_BUFFER_SIZE:]
                            price_buffer_timestamps[symbol] = time.time()
                except Exception:
                    pass
            
            time.sleep(30)  # فحص كل 30 ثانية
        except Exception as e:
            print(f"[BUFFERS] Error: {e}", flush=True)
            time.sleep(60)

def update_prices_worker():
    """Thread منفصل لتحديث أسعار جميع العملات بشكل دوري (مع retry)"""
    global global_prices
    print("[PRICES] Global price update thread started", flush=True)
    retry_count = {}
    
    while True:
        try:
            with _global_prices_lock:
                for symbol in list(SUPPORTED_COINS.keys())[:10]:  # أول 10 عملات
                    try:
                        price = get_live_price(symbol)
                        if price > 0:
                            global_prices[symbol] = {
                                'price': price,
                                'timestamp': time.time()
                            }
                            retry_count[symbol] = 0  # reset
                        else:
                            retry_count[symbol] = retry_count.get(symbol, 0) + 1
                    except Exception:
                        retry_count[symbol] = retry_count.get(symbol, 0) + 1
            time.sleep(3)  # تحديث كل 3 ثوان
        except Exception as e:
            print(f"[PRICES] Worker error: {e}", flush=True)
            time.sleep(10)

def update_balances_worker():
    """Thread منفصل لتحديث أرصدة المحفظة بشكل دوري"""
    global global_balances
    print("[BALANCES] Global balances update thread started", flush=True)
    while True:
        try:
            with _global_balances_lock:
                try:
                    usdt_balance = usdt_token.functions.balanceOf(wallet_address).call() / 10**18
                    bnb_balance = w3.eth.get_balance(wallet_address) / 10**18
                    global_balances['usdt'] = usdt_balance
                    global_balances['bnb'] = bnb_balance
                    global_balances['timestamp'] = time.time()
                except Exception:
                    pass
            time.sleep(3)  # تحديث كل 3 ثوان
        except Exception as e:
            print(f"[BALANCES] Worker error: {e}", flush=True)
            time.sleep(10)

def get_price_buffer(symbol: str) -> list:
    """جلب آخر N سعر لعملة معينة من المخزن المؤقت"""
    with _price_buffer_lock:
        return price_buffer.get(symbol, [0.0])

# بدء threads التحديث الخلفية
threading.Thread(target=initialize_price_buffers, daemon=True).start()
threading.Thread(target=update_price_buffers_worker, daemon=True).start()
threading.Thread(target=update_prices_worker, daemon=True).start()
threading.Thread(target=update_balances_worker, daemon=True).start()

def get_balances() -> Tuple[float, float]:
    """جلب الأرصدة من الذاكرة العالمية المحدثة أولاً، أو من الـ blockchain مباشرة"""
    with _global_balances_lock:
        if global_balances and (time.time() - global_balances.get('timestamp', 0)) < 10:
            return global_balances.get('usdt', 0.0), global_balances.get('bnb', 0.0)
    
    # Fallback: جلب مباشر من الـ blockchain إذا فشل التحديث
    try:
        usdt_balance = usdt_token.functions.balanceOf(wallet_address).call() / 10**18
        bnb_balance = w3.eth.get_balance(wallet_address) / 10**18
        with _global_balances_lock:
            global_balances['usdt'] = usdt_balance
            global_balances['bnb'] = bnb_balance
            global_balances['timestamp'] = time.time()
        return usdt_balance, bnb_balance
    except Exception as e:
        logger.error(f"[BALANCE] تعذر جلب الرصيد: {e}")
        return global_balances.get('usdt', 0.0), global_balances.get('bnb', 0.0)

def get_rsi(symbol: str = "BNB", interval: str = "15m") -> float:
    """جلب مؤشر القوة النسبية اللحظي لأي عملة بأي فريم زمني"""
    try:
        # لاحظ أننا وضعنا المتغير interval بدلاً من 15m الثابتة
        url = f"https://api.binance.com/api/v3/klines?symbol={symbol}USDT&interval={interval}&limit=15"
        resp = requests.get(url, timeout=5).json()
        
        closes = [float(c[4]) for c in resp]
        gains = [max(0, closes[i] - closes[i-1]) for i in range(1, len(closes))]
        losses = [max(0, closes[i-1] - closes[i]) for i in range(1, len(closes))]
        
        avg_loss = sum(losses) / len(losses)
        if avg_loss == 0: return 100.0
        
        rs = (sum(gains) / len(gains)) / avg_loss
        return 100 - (100 / (1 + rs))
    except Exception:
        return 50.0  # رقم محايد في حال فشل الاتصال
def get_rsi_matrix(symbol: str) -> dict:
    try:
        matrix = {
            "15m": get_rsi(symbol, interval="15m"),
            "1h": get_rsi(symbol, interval="1h"),
            "4h": get_rsi(symbol, interval="4h")
        }
        return matrix
    except Exception:
        return {"15m": 50.0, "1h": 50.0, "4h": 50.0}
    
def get_pair_address(token_a: str, token_b: str) -> str:
    """جلب عنوان الزوج من PancakeSwap Factory"""
    try:
        factory = w3.eth.contract(address=w3.to_checksum_address(PANCAKESWAP_FACTORY), abi=FACTORY_ABI)
        pair = factory.functions.getPair(w3.to_checksum_address(token_a), w3.to_checksum_address(token_b)).call()
        return pair.lower() if pair != "0x0000000000000000000000000000000000000000" else "0x0000000000000000000000000000000000000000"
    except Exception as e:
        logger.error(f"[PAIR ADDRESS] Error: {e}")
        return "0x0000000000000000000000000000000000000000"

# ==============================================================================
# --- 🔧 CORE STRATEGIC INDICATORS (COLOSSUS V17 REBUILD) ---
# ==============================================================================

def get_macd(symbol: str, fast: int = 12, slow: int = 26, signal: int = 9) -> dict:
    """
    💪 حساب MACD (Momentum): يعطي إشارات قوية للشراء/البيع
    في الـ uptrend يكون MACD فوق Signal line → فرصة شراء
    في الـ downtrend يكون MACD تحت Signal line → فرصة بيع
    🔥 يستخدم المخزن المؤقت للأسعار - لا ينتظر API
    """
    try:
        # جلب آخر 50 سعر من المخزن المؤقت (تحديث كل 5 دقائق)
        closes = get_price_buffer(symbol)
        
        if len(closes) < 30:
            url = f"https://api.binance.com/api/v3/klines?symbol={symbol}USDT&interval=1m&limit=50"
            resp = requests.get(url, timeout=5).json()
            closes = [float(c[4]) for c in resp if len(c) > 4]
        
        if len(closes) < 30:
            return {"macd": 0, "signal": 0, "histogram": 0, "trend": "NEUTRAL"}
        
        def ema(data, period):
            if len(data) < period:
                return [0] * len(data)
            k = 2 / (period + 1)
            ema_vals = [sum(data[:period]) / period]
            for price in data[period:]:
                ema_vals.append(price * k + ema_vals[-1] * (1 - k))
            return ema_vals
        
        ema12 = ema(closes, fast)
        ema26 = ema(closes, slow)
        macd_line = [e12 - e26 for e12, e26 in zip(ema12[-len(ema26):], ema26)]
        signal_line = ema(macd_line, signal)
        
        current_macd = macd_line[-1] if macd_line else 0
        current_signal = signal_line[-1] if signal_line and len(signal_line) > 0 else 0
        histogram = current_macd - current_signal
        
        return {
            "macd": round(current_macd, 6),
            "signal": round(current_signal, 6),
            "histogram": round(histogram, 6),
            "trend": "BULLISH" if histogram > 0 else "BEARISH" if histogram < 0 else "NEUTRAL"
        }
    except Exception as e:
        logger.error(f"[MACD] Error for {symbol}: {e}")
        return {"macd": 0, "signal": 0, "histogram": 0, "trend": "NEUTRAL"}

def get_price_elasticity(symbol: str, interval: str = "1h", period: int = 20) -> dict:
    """
    📊 مرونة السعر: قياس انحراف السعر عن المتوسط المتحرك
    إذا كان elasticity < -8% → قاع عنيف (فرصة شراء)
    إذا كان elasticity > +8% → قمة حادة (فرصة بيع)
    """
    try:
        url = f"https://api.binance.com/api/v3/klines?symbol={symbol}USDT&interval={interval}&limit={period}"
        resp = requests.get(url, timeout=5).json()
        
        closes = [float(c[4]) for c in resp]
        current_price = closes[-1]
        sma = sum(closes) / len(closes)
        elasticity = ((current_price - sma) / sma) * 100
        
        # حساب Bollinger Bands deviation
        variance = sum((x - sma) ** 2 for x in closes) / len(closes)
        std_dev = variance ** 0.5
        
        return {
            "elasticity": round(elasticity, 2),
            "sma": round(sma, 4),
            "std_dev": round(std_dev, 4),
            "lower_band": round(sma - (2 * std_dev), 4),
            "upper_band": round(sma + (2 * std_dev), 4),
            "signal": "BUY" if elasticity < -8 else "SELL" if elasticity > 8 else "HOLD"
        }
    except Exception:
        return {"elasticity": 0, "sma": 0, "std_dev": 0, "lower_band": 0, "upper_band": 0, "signal": "HOLD"}

def get_multi_timeframe_trend(symbol: str) -> dict:
    """
    🎯 تحليل الاتجاه على أفق زمني متعدد:
    - 5m: القرار المباشر (short-term momentum)
    - 15m: التأكيد (confirmation)
    - 1h: الاتجاه الأساسي (structural trend)
    """
    try:
        trends = {}
        for interval, name in [("5m", "short"), ("15m", "medium"), ("1h", "long")]:
            resp = requests.get(f"https://api.binance.com/api/v3/klines?symbol={symbol}USDT&interval={interval}&limit=20", timeout=5).json()
            closes = [float(c[4]) for c in resp]
            
            # حساب EMA-9 و EMA-21
            def ema(data, period):
                k = 2 / (period + 1)
                ema_vals = [sum(data[:period]) / period]
                for price in data[period:]:
                    ema_vals.append(price * k + ema_vals[-1] * (1 - k))
                return ema_vals[-1]
            
            ema9 = ema(closes, 9)
            ema21 = ema(closes, 21) if len(closes) >= 21 else ema(closes, 10)
            
            trend = "UP" if ema9 > ema21 else "DOWN" if ema9 < ema21 else "FLAT"
            strength = abs(ema9 - ema21) / ema21 * 100 if ema21 > 0 else 0
            
            trends[name] = {"trend": trend, "strength": round(strength, 2)}
        
        # قرار مركب
        short_signal = trends["short"]["trend"]
        medium_signal = trends["medium"]["trend"]
        long_signal = trends["long"]["trend"]
        
        # للشراء: يجب اتفاق على الأقل اثنين من الثلاثة على UP
        buy_confirmation = sum(1 for s in [short_signal, medium_signal, long_signal] if s == "UP") >= 2
        sell_confirmation = sum(1 for s in [short_signal, medium_signal, long_signal] if s == "DOWN") >= 2
        
        final_signal = "BUY" if buy_confirmation else "SELL" if sell_confirmation else "HOLD"
        
        return {
            "5m": trends["short"],
            "15m": trends["medium"],
            "1h": trends["long"],
            "final_signal": final_signal,
            "confidence": max(trends[k]["strength"] for k in ["short", "medium", "long"])
        }
    except Exception as e:
        logger.error(f"[MTF TREND] Error: {e}")
        return {"5m": {"trend": "FLAT", "strength": 0}, "15m": {"trend": "FLAT", "strength": 0}, "1h": {"trend": "FLAT", "strength": 0}, "final_signal": "HOLD", "confidence": 0}

def calculate_atr_stop_loss(symbol: str, entry_price: float, period: int = 14) -> dict:
    """
    🛡️ ATR-based Stop Loss (ديناميكي):
    لا نستخدم رقماً ثابتاً، الـ stop loss يتحرك مع تقلب السوق
    إذا كان السوق هادئ: SL قريب
    إذا كان السوق متقلب جداً: SL بعيد (حماية من الـ noise)
    🔥 يستخدم المخزن المؤقت للأسعار - أسرع و أذكى
    """
    try:
        # جلب من المخزن المؤقت أولاً
        closes = get_price_buffer(symbol)
        
        # إذا كان المخزن صغيراً: جلب من Binance
        if len(closes) < 20:
            url = f"https://api.binance.com/api/v3/klines?symbol={symbol}USDT&interval=1m&limit={period + 1}"
            resp = requests.get(url, timeout=5).json()
            closes = [float(c[4]) for c in resp if len(c) > 4]
        
        if len(closes) < 10:
            # Fallback: نسبة ثابتة 1%
            return {
                "atr": entry_price * 0.01,
                "atr_pct": 1.0,
                "stop_loss_price": entry_price * 0.99,
                "stop_loss_pct": 1.0,
                "take_profit_price": entry_price * 1.02,
                "take_profit_pct": 2.0
            }
        
        # احسب ATR من آخر N قيمة
        trs = []
        for i in range(1, min(len(closes), period + 1)):
            high = max(closes[i-1], closes[i])
            low = min(closes[i-1], closes[i])
            prev_close = closes[i-1]
            
            tr = max(
                high - low,
                abs(high - prev_close),
                abs(low - prev_close)
            )
            trs.append(tr)
        
        atr = sum(trs) / len(trs) if trs else entry_price * 0.01
        atr_pct = (atr / entry_price) * 100 if entry_price > 0 else 1.0
        
        # نسبة المخاطرة: عادة 1.5x ATR للـ short-term
        stop_loss_price = entry_price - (atr * 1.5)
        stop_loss_pct = ((entry_price - stop_loss_price) / entry_price) * 100 if entry_price > 0 else 1.0
        
        # هدف الربح: عادة 2x ATR
        take_profit_price = entry_price + (atr * 2)
        take_profit_pct = ((take_profit_price - entry_price) / entry_price) * 100 if entry_price > 0 else 2.0
        
        return {
            "atr": round(atr, 6),
            "atr_pct": round(atr_pct, 2),
            "stop_loss_price": round(stop_loss_price, 6),
            "stop_loss_pct": round(stop_loss_pct, 2),
            "take_profit_price": round(take_profit_price, 6),
            "take_profit_pct": round(take_profit_pct, 2)
        }
    except Exception as e:
        logger.error(f"[ATR] Error: {e}")
        # Fallback: نسبة ثابتة 1%
        return {
            "atr": entry_price * 0.01,
            "atr_pct": 1.0,
            "stop_loss_price": entry_price * 0.99,
            "stop_loss_pct": 1.0,
            "take_profit_price": entry_price * 1.02,
            "take_profit_pct": 2.0
        }

def detect_mev_protection(symbol: str, current_price: float) -> dict:
    """
    🛡️ حماية MEV (Maximal Extractable Value):
    الكشف عن بوتات الساندوتش والفرونت-رن
    """
    try:
        # جلب البيانات الأخيرة (آخر 10 شمعات 1 دقيقة)
        url = f"https://api.binance.com/api/v3/klines?symbol={symbol}USDT&interval=1m&limit=10"
        resp = requests.get(url, timeout=5).json()
        
        prices = [float(c[4]) for c in resp]
        volumes = [float(c[7]) for c in resp]  # quote asset volume
        
        # حساب الانحراف السعري المفاجئ (spike detection)
        price_change_pcts = [abs((prices[i] - prices[i-1]) / prices[i-1] * 100) for i in range(1, len(prices))]
        max_spike = max(price_change_pcts) if price_change_pcts else 0
        
        # حساب الحجم الشاذ
        avg_volume = sum(volumes) / len(volumes)
        volume_spikes = [v for v in volumes if v > avg_volume * 2]
        volume_anomaly_count = len(volume_spikes)
        
        # درجة الخطر
        mev_risk_score = 0
        if max_spike > 3: mev_risk_score += 40  # spike > 3% = خطر عالي
        if volume_anomaly_count >= 2: mev_risk_score += 30  # أكثر من spikين = خطر
        if max_spike > 5: mev_risk_score += 30  # spike > 5% = خطر حرج
        
        # التوصيات
        is_safe = mev_risk_score < 50
        recommendations = []
        if max_spike > 3:
            recommendations.append("⚠️ تم اكتشاف spike سعري - احذر من front-running")
        if volume_anomaly_count >= 2:
            recommendations.append("🚨 حجم تداول شاذ - قد يكون هناك ساندويتش بوت")
        if not is_safe:
            recommendations.append("❌ المعاملة غير آمنة - استخدم slippage أعلى")
        
        return {
            "mev_risk_score": mev_risk_score,
            "is_safe": is_safe,
            "max_spike_pct": round(max_spike, 2),
            "volume_anomalies": volume_anomaly_count,
            "recommendations": recommendations,
            "suggested_slippage": 5.0 if not is_safe else 1.5
        }
    except Exception as e:
        logger.error(f"[MEV] Error: {e}")
        return {"mev_risk_score": 0, "is_safe": True, "max_spike_pct": 0, "volume_anomalies": 0, "recommendations": [], "suggested_slippage": 1.5}

def check_venus_liquidations(token_addr: str = None) -> dict:
    """
    🎯 مراقبة فرص التصفية في بروتوكول Venus:
    تصفيات كبيرة = فرصة ذهبية لالتقاط السيولة المنخفضة
    🔥 محمية بـ try-except عميقة - خطأ واحد لا يوقف البوت
    """
    try:
        try:
            # في النسخة الأولى: نراقب مؤشرات غير مباشرة
            # الفحص الحقيقي يحتاج اتصال مباشر بـ Venus Contract
            
            # 1. فحص حجم التداول على VENUS token نفسه
            venus_resp = requests.get("https://api.binance.com/api/v3/ticker/24hr?symbol=VENUSUSDT", timeout=5).json()
            venus_volume_24h = float(venus_resp.get("quoteAssetVolume", 0))
            
            # 2. فحص السعر Liquidation price مؤشر غير مباشر: تقلب عالي = احتمال تصفيات
            venus_price_resp = requests.get("https://api.binance.com/api/v3/klines?symbol=VENUSUSDT&interval=15m&limit=20", timeout=5).json()
            venus_prices = [float(c[4]) for c in venus_price_resp if len(c) > 4]
            
            if not venus_prices or len(venus_prices) < 2:
                return {"venus_24h_volume": 0, "price_volatility": 0, "liquidation_risk_score": 0, "is_liquidation_likely": False, "opportunity": "بيانات غير متاحة"}
            
            price_volatility = (max(venus_prices) - min(venus_prices)) / min(venus_prices) * 100
            
            # درجة الخطر (احتمال تصفيات)
            liquidation_risk = price_volatility * 0.5  # كقاعدة تقريبية
            is_liquidation_likely = price_volatility > 5  # تقلب > 5% قد يشير لتصفيات
            
            return {
                "venus_24h_volume": round(venus_volume_24h, 2),
                "price_volatility": round(price_volatility, 2),
                "liquidation_risk_score": min(100, round(liquidation_risk, 2)),
                "is_liquidation_likely": is_liquidation_likely,
                "opportunity": "🎯 فرصة مراجحة عالية!" if is_liquidation_likely else "عادي"
            }
        except (KeyError, IndexError, TypeError, ValueError) as e:
            # خطأ في معالجة البيانات النصية أو الفهرسة
            return {"venus_24h_volume": 0, "price_volatility": 0, "liquidation_risk_score": 0, "is_liquidation_likely": False, "opportunity": "بيانات غير متاحة"}
    except Exception as e:
        logger.error(f"[VENUS] Unexpected error: {e}")
        return {"venus_24h_volume": 0, "price_volatility": 0, "liquidation_risk_score": 0, "is_liquidation_likely": False, "opportunity": "بيانات غير متاحة"}

def get_crypto_news() -> str:
    try:
        url = "https://min-api.cryptocompare.com/data/v2/news/?lang=EN"
        resp = requests.get(url, timeout=5).json()
        news_data = resp.get("Data", [])
        if isinstance(news_data, list) and len(news_data) > 0:
            headlines = [str(n.get("title", "")) for n in news_data[:3]]
            return " | ".join(headlines)
        return "لا توجد أخبار بارزة حالياً."
    except Exception:
        return "تعذر الاتصال بخادم الأخبار."

def get_dynamic_slippage(rsi: Optional[float] = None) -> float:
    if rsi is None: rsi = get_rsi()
    if rsi < 30 or rsi > 70: return 3.0
    elif rsi < 40 or rsi > 60: return 1.5
    else: return 0.5
def get_btc_crash_status() -> bool:
    """قاطع دائرة البيتكوين: يتحقق مما إذا كان البيتكوين قد انهار بنسبة أكثر من 3% في آخر 15 دقيقة"""
    try:
        resp = requests.get("https://api.binance.com/api/v3/klines?symbol=BTCUSDT&interval=15m&limit=2", timeout=5).json()
        open_price = float(resp[-2][1])
        current_price = float(resp[-1][4])
        drop_pct = ((open_price - current_price) / open_price) * 100
        return drop_pct >= 3.0
    except Exception:
        return False

def get_macro_trend(symbol: str) -> str:
    """درع الاتجاه العام: يتحقق من مؤشر EMA 200 على الإطار اليومي"""
    try:
        pair = f"{symbol}USDT"
        resp = requests.get(f"https://api.binance.com/api/v3/klines?symbol={pair}&interval=1d&limit=200", timeout=5).json()
        closes = [float(c[4]) for c in resp]
        current_price = closes[-1]
        ema_200 = sum(closes) / len(closes)
        return "BULLISH" if current_price > ema_200 else "BEARISH"
    except Exception:
        return "NEUTRAL"

def get_atr_volatility(symbol: str) -> float:
    """حساب مسافات التبريد المطاطية: يعطي نسبة تمدد السلم بناءً على جنون السوق"""
    try:
        pair = f"{symbol}USDT"
        resp = requests.get(f"https://api.binance.com/api/v3/klines?symbol={pair}&interval=15m&limit=14", timeout=5).json()
        high_low_diffs = [(float(c[2]) - float(c[3])) / float(c[4]) * 100 for c in resp]
        atr_pct = sum(high_low_diffs) / len(high_low_diffs)
        return max(1.0, min(atr_pct, 3.0))
    except Exception:
        return 1.0

def analyze_sentiment_with_ai(symbol: str) -> bool:
    """رادار المشاعر: يسأل Groq AI إذا كان الوقت آمناً للشراء"""
    try:
        news = get_crypto_news()
        prompt = f"أخبار السوق: {news}. هل توجد أخبار كارثية تمنع شراء عملة {symbol} الآن؟ أجب بـ (نعم) أو (لا) فقط."
        res = groq_client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[{"role": "user", "content": prompt}]
        ).choices[0].message.content.strip()
        return "لا" in res.lower()
    except Exception:
        return True

# ==============================================================================
# --- 9. TRADING ENGINE V16 (REAL MULTI-COIN EXECUTOR) ---
# ==============================================================================
def ensure_token_allowance(token_address: str, amount_wei: int, nonce: int) -> int:
    token_contract = w3.eth.contract(address=token_address, abi=ERC20_ABI)
    for attempt in range(3):
        try:
            allowance = token_contract.functions.allowance(wallet_address, ROUTER_ADDR).call()
            if allowance >= amount_wei: return nonce
            max_allowance = w3.to_wei(MAX_APPROVE_USDT, 'ether')
            tx = token_contract.functions.approve(ROUTER_ADDR, max_allowance).build_transaction({
                'from': wallet_address, 'gasPrice': w3.eth.gas_price, 'nonce': nonce, 'chainId': 56
            })
            tx['gas'] = int(w3.eth.estimate_gas(tx) * GAS_MULTIPLIER)
            signed = w3.eth.account.sign_transaction(tx, private_key=PRIVATE_KEY)
            raw_tx = getattr(signed, 'raw_transaction', getattr(signed, 'rawTransaction', getattr(signed, 'raw', None)))
            tx_hash = w3.eth.send_raw_transaction(raw_tx)
            w3.eth.wait_for_transaction_receipt(tx_hash, timeout=60)
            return nonce + 1
        except Exception:
            if attempt == 2: raise
            time.sleep(2)

def build_and_send_tx(chat_id: str, action: str, amount_usd: float, current_price: float,
                      is_auto: bool = False, use_passed_price: bool = True, symbol: str = "BNB"):
    if not state.bot_active: return False

    try:
        c_state = state.coins[symbol]
        price = current_price if (use_passed_price and current_price > 0) else get_live_price(symbol)
        usdt_bal, bnb_bal = get_balances()
        coin_address = SUPPORTED_COINS[symbol]

        if not PAPER_TRADING:
            if action == "شراء" and usdt_bal < amount_usd:
                bot.send_message(chat_id, f"⚠️ رصيد USDT غير كافٍ ({usdt_bal:.2f} < {amount_usd:.2f})")
                return False
            if action == "بيع":
                if symbol == "BNB" and bnb_bal < (amount_usd / price):
                    bot.send_message(chat_id, f"⚠️ رصيد BNB غير كافٍ للبيع!")
                    return False
                elif symbol != "BNB":
                    token_contract = w3.eth.contract(address=coin_address, abi=ERC20_ABI)
                    token_bal = token_contract.functions.balanceOf(wallet_address).call() / 10**18
                    if token_bal < (amount_usd / price) * 0.99:
                        bot.send_message(chat_id, f"⚠️ رصيد {symbol} الفعلي غير كافٍ للبيع!")
                        return False

        if not PAPER_TRADING:
            nonce = w3.eth.get_transaction_count(wallet_address, 'pending')
            deadline = int(time.time()) + 600
            dyn_slippage = get_dynamic_slippage(get_rsi())

            if action == "شراء":
                usdt_wei = w3.to_wei(amount_usd, 'ether')
                nonce = ensure_token_allowance(USDT_ADDR, usdt_wei, nonce)
                min_out = int(router.functions.getAmountsOut(usdt_wei, [USDT_ADDR, coin_address]).call()[1] * (1 - dyn_slippage / 100))
                
                if symbol == "BNB":
                    tx = router.functions.swapExactTokensForETH(usdt_wei, min_out, [USDT_ADDR, WBNB_ADDR], wallet_address, deadline).build_transaction({'from': wallet_address, 'gasPrice': w3.eth.gas_price, 'nonce': nonce, 'chainId': 56})
                else:
                    tx = router.functions.swapExactTokensForTokens(usdt_wei, min_out, [USDT_ADDR, coin_address], wallet_address, deadline).build_transaction({'from': wallet_address, 'gasPrice': w3.eth.gas_price, 'nonce': nonce, 'chainId': 56})
            else:
                if symbol == "BNB":
                    bnb_wei = w3.to_wei(amount_usd / price, 'ether')
                    min_usdt_wei = int(router.functions.getAmountsOut(bnb_wei, [WBNB_ADDR, USDT_ADDR]).call()[1] * (1 - dyn_slippage / 100))
                    tx = router.functions.swapExactETHForTokens(min_usdt_wei, [WBNB_ADDR, USDT_ADDR], wallet_address, deadline).build_transaction({'from': wallet_address, 'value': bnb_wei, 'gasPrice': w3.eth.gas_price, 'nonce': nonce, 'chainId': 56})
                else:
                    token_wei = w3.to_wei(amount_usd / price, 'ether')
                    nonce = ensure_token_allowance(coin_address, token_wei, nonce)
                    min_usdt_wei = int(router.functions.getAmountsOut(token_wei, [coin_address, USDT_ADDR]).call()[1] * (1 - dyn_slippage / 100))
                    tx = router.functions.swapExactTokensForTokens(token_wei, min_usdt_wei, [coin_address, USDT_ADDR], wallet_address, deadline).build_transaction({'from': wallet_address, 'gasPrice': w3.eth.gas_price, 'nonce': nonce, 'chainId': 56})

            gas_limit = None
            for attempt in range(3):
                try:
                    gas_limit = w3.eth.estimate_gas(tx)
                    break
                except Exception as gas_err:
                    if attempt == 2: raise
                    time.sleep(1)
                    if "nonce too low" in str(gas_err):
                        tx['nonce'] = w3.eth.get_transaction_count(wallet_address, 'pending')

            gas_cost_usd = (gas_limit * w3.eth.gas_price / 10**18) * get_live_price("BNB")
            tx['gas'] = int(gas_limit * GAS_MULTIPLIER)

            if gas_cost_usd > MAX_GAS_FEE_USD:
                bot.send_message(chat_id, f"⚠️ حماية الغاز: تم الإلغاء، الرسوم عالية.")
                return False

            signed_tx = w3.eth.account.sign_transaction(tx, private_key=PRIVATE_KEY)
            raw_tx = getattr(signed_tx, 'raw_transaction', getattr(signed_tx, 'rawTransaction', getattr(signed_tx, 'raw', None)))
            tx_hash = w3.eth.send_raw_transaction(raw_tx)
            w3.eth.wait_for_transaction_receipt(tx_hash, timeout=120)

        # الذاكرة (سواء محاكاة أو حقيقي)
        with state_lock:
            if action == "شراء":
                c_state.total_spent_usdt += amount_usd
                bought_coin = amount_usd / price
                c_state.total_held += bought_coin
                c_state.initial_position += bought_coin
            elif action == "بيع":
                sold_coin = amount_usd / price
                fraction_sold = sold_coin / c_state.total_held if c_state.total_held > 0 else 1.0
                c_state.initial_position = max(0, c_state.initial_position - (c_state.initial_position * fraction_sold))
                cost_reduction = sold_coin * (c_state.average_buy_price if c_state.average_buy_price > 0 else price)
                c_state.total_spent_usdt = max(0, c_state.total_spent_usdt - cost_reduction)
                c_state.total_held -= sold_coin
            
            if c_state.total_held > 0.00001 and c_state.total_spent_usdt > 0:
                c_state.average_buy_price = c_state.total_spent_usdt / c_state.total_held
            else:
                c_state.average_buy_price = 0.0
                c_state.total_spent_usdt = 0.0
                c_state.total_held = 0.0
                c_state.initial_position = 0.0
                c_state.trailing_active = False
                c_state.trailing_buy_active = False

        state.save()

        mode_str = "آلياً 🤖" if is_auto else "يدوياً 👤"
        if not PAPER_TRADING:
            log_trade(tx_hash.hex(), action, amount_usd, price, gas_cost_usd, f"Real-{symbol}")
            bot.send_message(chat_id, f"🔥 **نجاح حقيقي ({symbol})!**\nتم {action} {mode_str} بقيمة {amount_usd:.2f}$\nالهاش: https://bscscan.com/tx/{tx_hash.hex()}")
        else:
            log_trade(f"sim_{int(time.time())}", action, amount_usd, price, 0.0, f"Paper-{symbol}")
            bot.send_message(chat_id, f"📄 **(محاكاة V16 - {symbol})** تم {action} {mode_str} بقيمة {amount_usd:.2f}$ بنجاح.")

        return True

    except Exception as e:
        bot.send_message(chat_id, f"❌ فشل التنفيذ لـ {symbol}: {str(e)[:150]}")
        return False

# ==============================================================================
# --- 10. TELEGRAM UI & AI V16 (MULTI-COIN) ---
# ==============================================================================
groq_client = Groq(api_key=GROQ_API_KEY)
chat_history = []
user_clicks = {}

def get_main_keyboard():
    markup = InlineKeyboardMarkup(row_width=2)
    markup.add(
        InlineKeyboardButton("🟢 شراء 5 (BNB)", callback_data="buy_5_BNB"),
        InlineKeyboardButton("🔴 بيع 5 (BNB)", callback_data="sell_5_BNB"),
        InlineKeyboardButton("📊 التقرير الشامل", callback_data="report"),
        InlineKeyboardButton("⏲️ تصفير الوقت", callback_data="reset_trailing"),
        InlineKeyboardButton("⏸️ إيقاف/تشغيل المحرك", callback_data="toggle_bot"),
        InlineKeyboardButton("🗒️ سجل الصفقات", callback_data="last_trades"),
        InlineKeyboardButton("🔄 المزامنة (Sync)", callback_data="sync"),
        InlineKeyboardButton("💰 سحب الأرباح", callback_data="ask_withdraw"),
        InlineKeyboardButton("☢️ الزر النووي الشامل", callback_data="nuke")
    )
    return markup

def get_vault_balances_text() -> str:
    msg = "🏦 **الأرباح القابلة للسحب (الخزنة):**\n"
    try:
        if not (w3 and w3.is_connected()):
            return msg + "⚠️ عذراً، الاتصال بالشبكة مقطوع حالياً.\n"
            
        found = False
        all_tokens = {"USDT": USDT_ADDR, **SUPPORTED_COINS}
        vault_addr = w3.to_checksum_address(FLASH_ARBITRAGE_ADDRESS)
        
        for sym, addr in all_tokens.items():
            try:
                tk_addr = w3.to_checksum_address(addr)
                tk = w3.eth.contract(address=tk_addr, abi=ERC20_ABI)
                # استخدام call() بسيط كما هو مطلوب
                bal = tk.functions.balanceOf(vault_addr).call()
                
                if bal > 100: # تجنب الغبار البرمجي (Dust)
                    found = True
                    # جلب الـ decimals بشكل آمن من الـ ABI المحدث
                    dec = tk.functions.decimals().call()
                    human_bal = bal / (10 ** dec)
                    fmt = f"{human_bal:.4f}" if sym != "USDT" else f"{human_bal:.2f}"
                    msg += f"- {fmt} {sym}\n"
            except Exception:
                continue # استمر في فحص بقية العملات حتى لو فشلت واحدة
                
        if not found:
            # عرض 0.00$ كما هو مطلوب عند البداية
            msg += "- 0.00$\n"
            
    except Exception as e:
        msg += "⚠️ مشكلة تقنية في قراءة بيانات الخزنة.\n"
        
    return msg + "\n"

def perform_vault_withdrawal(chat_id):
    bot.send_message(chat_id, "🏦 جاري فحص جميع العملات في الخزنة وسحبها وتحويلها إلى USDT...")
    
    try:
        messages = []
        found_any = False
        all_tokens = {"USDT": USDT_ADDR, **SUPPORTED_COINS}
        
        for sym, addr in all_tokens.items():
            try:
                tk = w3.eth.contract(address=w3.to_checksum_address(addr), abi=ERC20_ABI)
                bal = tk.functions.balanceOf(w3.to_checksum_address(FLASH_ARBITRAGE_ADDRESS)).call()
                if bal > 1000: # Threshold to avoid dust
                    found_any = True
                    dec = tk.functions.decimals().call()
                    human_bal = bal / (10 ** dec)
                    
                    # 1. سحب الرصيد من العقد الذكي إلى محفظة المستخدم
                    nonce = w3.eth.get_transaction_count(wallet_address)
                    tx = flash_contract.functions.withdrawProfits(w3.to_checksum_address(addr)).build_transaction({
                        'chainId': 56, 'gas': 150000, 'gasPrice': w3.eth.gas_price, 'nonce': nonce, 'from': wallet_address
                    })
                    signed_txn = w3.eth.account.sign_transaction(tx, private_key=PRIVATE_KEY)
                    raw_tx = getattr(signed_txn, 'raw_transaction', getattr(signed_txn, 'rawTransaction', getattr(signed_txn, 'raw', None)))
                    tx_hash = w3.eth.send_raw_transaction(raw_tx)
                    w3.eth.wait_for_transaction_receipt(tx_hash, timeout=120)
                    
                    # 2. إذا كانت العملة المسحوبة ليست USDT، نقوم بتصريفها إلى USDT فوراً
                    if sym != "USDT":
                        try:
                            sell_amount_wei = bal 
                            nonce = w3.eth.get_transaction_count(wallet_address)
                            # Ensure allowance
                            allowance = tk.functions.allowance(wallet_address, ROUTER_ADDR).call()
                            if allowance < sell_amount_wei:
                                approve_tx = tk.functions.approve(ROUTER_ADDR, 2**256-1).build_transaction({
                                    'from': wallet_address, 'gasPrice': w3.eth.gas_price, 'nonce': nonce, 'chainId': 56
                                })
                                signed_app = w3.eth.account.sign_transaction(approve_tx, private_key=PRIVATE_KEY)
                                raw_app = getattr(signed_app, 'raw_transaction', getattr(signed_app, 'rawTransaction', getattr(signed_app, 'raw', None)))
                                w3.eth.send_raw_transaction(raw_app)
                                nonce += 1
                            
                            path = [w3.to_checksum_address(addr), w3.to_checksum_address(USDT_ADDR)]
                            expected_usdt = router.functions.getAmountsOut(sell_amount_wei, path).call()[1]
                            min_out = int(expected_usdt * 0.90) # 10% Slippage
                            
                            swap_tx = router.functions.swapExactTokensForTokens(
                                sell_amount_wei,
                                min_out,
                                path,
                                wallet_address,
                                int(time.time()) + 600
                            ).build_transaction({
                                'from': wallet_address,
                                'gasPrice': w3.eth.gas_price,
                                'nonce': nonce,
                                'chainId': 56
                            })
                            
                            signed_swap = w3.eth.account.sign_transaction(swap_tx, private_key=PRIVATE_KEY)
                            raw_swap = getattr(signed_swap, 'raw_transaction', getattr(signed_swap, 'rawTransaction', getattr(signed_swap, 'raw', None)))
                            swap_tx_hash = w3.eth.send_raw_transaction(raw_swap)
                            w3.eth.wait_for_transaction_receipt(swap_tx_hash, timeout=120)
                            
                            messages.append(f"🔄 تم سحب وتحويل **{human_bal:.4f} {sym}** إلى USDT.")
                        except Exception as e:
                            logger.error(f"Vault Swap Error: {e}")
                            messages.append(f"⚠️ تم سحب **{human_bal:.4f} {sym}** ولكن فشل التحويل التلقائي.")
                    else:
                        messages.append(f"✅ تم سحب **{human_bal:.2f} USDT** أرباح مباشرة.")
                    
                    time.sleep(1)
            except Exception as e:
                logger.error(f"Vault Token Error ({sym}): {e}")

        if not found_any:
            bot.send_message(chat_id, "⚠️ الخزنة الذكية فارغة حالياً لجميع العملات.")
            return
            
        final_msg = "💰 **تقرير دمج الأرباح بالـ (USDT):**\n\n" + "\n\n".join(messages)
        final_msg += "\n\n**لقد تمت معالجة وسحب الأرباح بالكامل لمصلحتك.**"
        bot.send_message(chat_id, final_msg)
        
    except Exception as e:
        bot.send_message(chat_id, f"❌ حدث خطأ جذري أثناء دورة سحب الأرباح: {e}")

# ==============================================================================
# --- ☢️ NUCLEAR: TELEGRAM EMERGENCY COMMANDS (THE RED BUTTON) ---
# ==============================================================================
@bot.message_handler(commands=['nuclear_stop', 'nuke'])
def handle_nuclear_stop(message):
    """الزر النووي الشامل (v16 Colossus): تصفية شاملة وحرق كافة المراكز إلى BNB"""
    if str(message.chat.id) != str(TELEGRAM_CHAT_ID): return
    global state, w3
    chat_id = message.chat.id
    
    try:
        # 1. إيقاف المحرك فوراً
        state.bot_active = False
        state.save()
        
        bot.send_message(chat_id, "☢️ **[NUCLEAR ACTIVATED: TOTAL WIPEOUT]**\nبروتوكول التصفية الشاملة بدأ! سيتم سحب أرباح الخزنة وتصفية كافة العملات إلى BNB فوراً.")
        
        # 2. خطوة اختيارية: محاولة سحب أرباح الخزنة أولاً
        try:
            all_tokens = {"USDT": USDT_ADDR, **SUPPORTED_COINS}
            for sym, addr in all_tokens.items():
                tk = w3.eth.contract(address=w3.to_checksum_address(addr), abi=ERC20_ABI)
                v_bal = tk.functions.balanceOf(w3.to_checksum_address(FLASH_ARBITRAGE_ADDRESS)).call()
                if v_bal > 1000:
                    nonce = w3.eth.get_transaction_count(wallet_address)
                    tx = flash_contract.functions.withdrawProfits(w3.to_checksum_address(addr)).build_transaction({
                        'chainId': 56, 'gas': 150000, 'gasPrice': int(w3.eth.gas_price * 1.5), 'nonce': nonce, 'from': wallet_address
                    })
                    signed_txn = w3.eth.account.sign_transaction(tx, private_key=PRIVATE_KEY)
                    raw_tx = getattr(signed_txn, 'raw_transaction', getattr(signed_txn, 'rawTransaction', getattr(signed_txn, 'raw', None)))
                    w3.eth.send_raw_transaction(raw_tx)
        except Exception: pass

        # 3. تصفية محتويات المحفظة (الضربة القاضية)
        nonce = w3.eth.get_transaction_count(wallet_address)
        gas_price = int(w3.eth.gas_price * 1.3)
        liquidation_targets = list(SUPPORTED_COINS.items())
        if "USDT" not in SUPPORTED_COINS: liquidation_targets.append(("USDT", USDT_ADDR))
        
        liquidated_count = 0
        for sym, addr in liquidation_targets:
            if sym == "BNB": continue
            try:
                tk_addr = w3.to_checksum_address(addr)
                tk = w3.eth.contract(address=tk_addr, abi=ERC20_ABI)
                balance = tk.functions.balanceOf(wallet_address).call()
                
                if balance > 0:
                    # التحقق من الترخيص
                    allowance = tk.functions.allowance(wallet_address, ROUTER_ADDR).call()
                    if allowance < balance:
                        approve_tx = tk.functions.approve(ROUTER_ADDR, 2**256-1).build_transaction({
                            'from': wallet_address, 'gasPrice': gas_price, 'nonce': nonce, 'chainId': 56
                        })
                        signed_app = w3.eth.account.sign_transaction(approve_tx, private_key=PRIVATE_KEY)
                        raw_app = getattr(signed_app, 'raw_transaction', getattr(signed_app, 'rawTransaction', getattr(signed_app, 'raw', None)))
                        w3.eth.send_raw_transaction(raw_app)
                        time.sleep(1)
                        nonce += 1
                    
                    # تنفيذ البيع الصاعق (Token -> BNB)
                    path = [tk_addr, WBNB_ADDR]
                    deadline = int(time.time()) + 300
                    try:
                        amounts = router.functions.getAmountsOut(balance, path).call()
                        min_out = int(amounts[-1] * 0.75) # 25% Slippage
                    except: min_out = 0
                    
                    swap_tx = router.functions.swapExactTokensForETH(
                        balance, min_out, path, wallet_address, deadline
                    ).build_transaction({
                        'from': wallet_address, 'gasPrice': gas_price, 'nonce': nonce, 'chainId': 56
                    })
                    signed_sw = w3.eth.account.sign_transaction(swap_tx, private_key=PRIVATE_KEY)
                    raw_sw = getattr(signed_sw, 'raw_transaction', getattr(signed_sw, 'rawTransaction', getattr(signed_sw, 'raw', None)))
                    w3.eth.send_raw_transaction(raw_sw)
                    liquidated_count += 1
                    nonce += 1
                    time.sleep(0.5)
            except Exception as e:
                logger.error(f"☢️ Failed to liquidate {sym}: {e}")

        # 4. تصفية الذاكرة
        with state_lock:
            for s in state.coins:
                state.coins[s].total_held = 0
                state.coins[s].total_spent_usdt = 0
            state.save()

        bot.send_message(chat_id, f"✅ **[MISSION ACCOMPLISHED]**\nتمت تصفية {liquidated_count} أصول بالكامل وتحويلها إلى BNB.\nالمحرك متوقف تماماً الآن 🔇.")
        
    except Exception as e:
        bot.reply_to(message, f"⚠️ خطأ حرج في البروتوكول النووي: {e}")


@bot.message_handler(func=lambda msg: str(msg.chat.id) == TELEGRAM_CHAT_ID)
def handle_messages(message, force_report=False):
    chat_id = str(message.chat.id)
    text = message.text.strip() if message.text else "تقرير"

    # تحليل الأوامر النصية وتحديد العملة
    if text.startswith("اشتري") or text.startswith("شراء") or text.startswith("بيع"):
        action = "شراء" if "شراء" in text or "اشتري" in text else "بيع"
        nums = re.findall(r'\d+(?:\.\d+)?', text)
        if nums:
            amount = float(nums[0])
            symbol = "BNB" # افتراضي
            if "ايث" in text or "eth" in text.lower(): symbol = "ETH"
            elif "سول" in text or "sol" in text.lower(): symbol = "SOL"
            elif "xrp" in text.lower() or "ريبل" in text: symbol = "XRP"
            elif "link" in text.lower() or "لينك" in text: symbol = "LINK"
            elif "matic" in text.lower() or "ماتيك" in text: symbol = "MATIC"
            elif "uni" in text.lower() or "يوني" in text: symbol = "UNI"
            elif "avax" in text.lower() or "افاكس" in text: symbol = "AVAX"
            
            trade_executor.submit(build_and_send_tx, chat_id, action, amount, get_live_price(symbol), False, True, symbol)
        return
# --- ☢️ تفعيل البروتوكول النووي (Emergency Sell All) ---
    elif text == "/nuke":
        bot.send_message(chat_id, "⚠️ [WARNING] تم تفعيل البروتوكول النووي! جاري تصفية كافة المراكز فوراً...")
        total_reclaimed_usdt = 0
        with state_lock:
            for symbol, c_state in state.coins.items():
                if c_state.total_held > 0:
                    try:
                        current_price = get_live_price(symbol)
                        amount_to_sell = c_state.total_held
                        
                        # إرسال أمر البيع الفوري
                        trade_executor.submit(build_and_send_tx, chat_id, "بيع", amount_to_sell, current_price, True, symbol)
                        
                        # تصفير بيانات العملة في الذاكرة
                        c_state.total_held = 0
                        c_state.average_buy_price = 0
                        c_state.total_spent_usdt = 0
                        c_state.last_auto_buy_level = 0
                        
                        total_reclaimed_usdt += (amount_to_sell * current_price)
                    except Exception as e:
                        bot.send_message(chat_id, f"❌ فشل تصفية {symbol}: {str(e)}")
            state.save()
        bot.send_message(chat_id, f"✅ [MISSION ACCOMPLISHED]\nتم تصفية المحفظة بالكامل.\nالسيولة التقريبية: ${total_reclaimed_usdt:.2f}")
        return # لإنهاء الدالة هنا وعدم الدخول في شروط أخرى
    elif text == "/sync":
        usdt_bal, bnb_bal = get_balances()
        with state_lock:
            # 1. مزامنة BNB
            c_bnb = state.coins["BNB"]
            c_bnb.total_held = max(0, bnb_bal - MIN_BNB_TO_KEEP)
            c_bnb.initial_position = c_bnb.total_held
            c_bnb.average_buy_price = get_live_price("BNB") if c_bnb.total_held > 0 else 0.0
            c_bnb.total_spent_usdt = c_bnb.total_held * c_bnb.average_buy_price
            
            # 2. مزامنة البقية
            for sym, addr in SUPPORTED_COINS.items():
                if sym == "BNB": continue
                c = state.coins[sym]
                try:
                    token_contract = w3.eth.contract(address=w3.to_checksum_address(addr), abi=ERC20_ABI)
                    bal = token_contract.functions.balanceOf(wallet_address).call() / 10**18
                except Exception:
                    bal = 0.0
                c.total_held = bal
                c.initial_position = bal
                c.average_buy_price = get_live_price(sym) if bal > 0 else 0.0
                c.total_spent_usdt = bal * c.average_buy_price

        state.save()
        bot.send_message(chat_id, f"✅ تمت المزامنة الشاملة لجميع العملات البالغ عددها ({len(SUPPORTED_COINS)}) بنجاح.", reply_markup=get_main_keyboard())
        return

    if force_report or text == "/report":
        usdt_bal, bnb_bal_real = get_balances()
        msg = f"📊 **تقرير V16 Colossus الشامل**\nالكاش المتاح: {usdt_bal:.2f} USDT\n\n"
        msg += get_vault_balances_text()
        
        for sym in SUPPORTED_COINS.keys():
            c = state.coins[sym]
            price = get_live_price(sym)
            pnl = ((c.total_held * price - c.total_spent_usdt) / c.total_spent_usdt * 100) if c.total_spent_usdt > 0 else 0.0
            msg += f"🔸 **{sym}**:\n"
            msg += f"الرصيد: {c.total_held:.4f} | السعر: {price:.2f}$\n"
            msg += f"الربح/الخسارة: {pnl:+.2f}%\n"
            if c.trailing_buy_active: msg += f"🪂 صائد القيعان: نشط (يبحث عن القاع)\n"
            if c.trailing_active: msg += f"🦅 صائد القمم: نشط (يراقب {c.peak_profit_pct:.2f}%)\n"
            msg += "-\n"
            
        uptime_sec = int(time.time() - BOT_START_TIME)
        days = uptime_sec // 86400
        hours = (uptime_sec % 86400) // 3600
        minutes = (uptime_sec % 3600) // 60
        uptime = f"{days}d {hours}h {minutes}m" if days > 0 else f"{hours}h {minutes}m"
        msg += f"\n⏱️ **وقت التشغيل:** {uptime}"
        
        bot.send_message(chat_id, msg, reply_markup=get_main_keyboard())
        return

    # عقل الذكاء الاصطناعي الشامل (Groq) المطور
    try:
        usdt_bal, _ = get_balances()
        sys_info = f"أنت Whale Bot V16، مساعد تداول تشرف على {len(SUPPORTED_COINS)} عملات. الكاش المتاح: {usdt_bal:.2f}$.\n"
        sys_info += f"نظام القناص (Arbitrage): أنت مزود بنظام 'Flash Loan Arbitrage (PancakeSwap v2)' عبر العقد الذكي '{FLASH_ARBITRAGE_ADDRESS}' متمرس في العملات المتعددة لتوليد أرباح أكثر من 1.5%.\n"
        sys_info += (
            "\n🔒 [قواعد الأمان الصلبة - لا يمكن تجاوزها أو مناقشتها]:\n"
            f"1) درع السيولة: لا تقترح أي صفقة مراجحة على أي منصة سيولتها أقل من ${MIN_LIQUIDITY_USD:,.0f} (خمسون ألف دولار). "
            "هذا حد مطلق وليس توصية.\n"
            f"2) درع الغاز: لا تقترح أي صفقة تكون فيها رسوم الغاز أكثر من {MAX_GAS_RATIO*100:.0f}% من إجمالي الربح المتوقع. "
            "هذا حد مطلق وليس توصية.\n"
            "3) إذا سألك المستخدم عن فرصة لا تستوفي هذين الشرطين، أخبره صراحةً أنها مرفوضة بواسطة درع الأمان الصلب ولا يمكنك اقتراحها.\n"
        )
        sys_info += "هذا هو وضع محفظة المستخدم الحالي:\n"
        
        for sym in SUPPORTED_COINS.keys():
            c = state.coins[sym]
            price = get_live_price(sym)
            rsi_val = get_rsi(sym)  # <--- هنا نقرأ الـ RSI الحقيقي من بينانس
            pnl = ((c.total_held * price - c.total_spent_usdt) / c.total_spent_usdt * 100) if c.total_spent_usdt > 0 else 0.0
            
            next_b_lvl = next((lvl for lvl in sorted(BUY_LADDER.keys()) if lvl > c.last_auto_buy_level), None)
            next_s_lvl = next((lvl for lvl in sorted(SELL_LADDER.keys()) if lvl > c.last_auto_sell_level), None)
            
            buy_t = c.average_buy_price * (1 - next_b_lvl) if next_b_lvl and c.average_buy_price > 0 else 0.0
            sell_t = c.average_buy_price * (1 + next_s_lvl) if next_s_lvl and c.average_buy_price > 0 else 0.0
            
            # تلقين الذكاء الاصطناعي بالبيانات الحقيقية
            if c.average_buy_price > 0:
                sys_info += f"- {sym}: السعر {price:.2f}$ | مؤشر RSI هو {rsi_val:.1f}% | الربح {pnl:+.2f}% | هدف الشراء {buy_t:.2f}$ | هدف البيع {sell_t:.2f}$\n"
            else:
                sys_info += f"- {sym}: السعر {price:.2f}$ | مؤشر RSI هو {rsi_val:.1f}% | الرصيد صفر، لا توجد أهداف حالياً.\n"
                
        # رادار الأخبار
        if any(word in text for word in ["اخبار", "أخبار", "جديد", "خبر", "السوق"]):
            live_news = get_crypto_news()
            sys_info += f"\nأخبار الكريبتو اللحظية الآن هي: {live_news}. قم بصياغتها للمستخدم باحترافية واربطها بوضع السوق.\n"
                
        sys_info += "المطلوب منك: أجب المستخدم باختصار، واحترافية، وباللغة العربية، بناءً على هذه الأرقام الدقيقة فقط، ولا تقم بتأليف أرقام من عندك."
        
        chat_history.append({"role": "user", "content": text})
        if len(chat_history) > 6: chat_history.pop(0)
        
        res = groq_client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[{"role": "system", "content": sys_info}] + chat_history
        ).choices[0].message.content
        
        chat_history.append({"role": "assistant", "content": res})
        if len(chat_history) > 6: chat_history.pop(0)
        
        bot.reply_to(message, res, reply_markup=get_main_keyboard())
        
    except Exception as e:
        bot.reply_to(message, f"⚠️ عذراً، محرك الذكاء الاصطناعي واجه صعوبة في الاستجابة. التفاصيل الفنية: {str(e)[:100]}", reply_markup=get_main_keyboard())
        
# ==============================================================================
# --- 11. MAIN AUTO TRADING LOOP V16 ---
# ==============================================================================
# ==============================================================================
# --- 🧭 محرك المشاعر (The Sentiment Engine) ---
# ==============================================================================
_cached_fgi = {"value": 50, "status": "Neutral", "last_update": 0}

def get_fear_and_greed_index() -> dict:
    """جلب مؤشر الخوف والطمع العالمي من alternative.me مع كاش لمدة 5 دقائق"""
    global _cached_fgi
    now = time.time()
    if now - _cached_fgi["last_update"] > 300:
        try:
            resp = requests.get("https://api.alternative.me/fng/", timeout=5).json()
            data = resp.get("data", [{}])[0]
            val = int(data.get("value", 50))
            classification = data.get("value_classification", "Neutral")
            _cached_fgi = {"value": val, "status": classification, "last_update": now}
        except Exception as e:
            pass
    return _cached_fgi

def get_smart_multiplier(rsi_1h, elasticity):
    """عقل التراكم: تحديد قوة الشراء بناءً على شدة القاع المشبوك بالمشاعر"""
    multiplier = 1.0
    fgi = get_fear_and_greed_index()
    sentiment_boost = 1.5 if (fgi["value"] < 20 or "Extreme Fear" in fgi["status"]) else 1.0
    
    if elasticity < -8.0: multiplier = 3.0 * sentiment_boost
    elif elasticity < -5.0: multiplier = 2.0 * sentiment_boost
    if rsi_1h < 25: multiplier += 1.0
    return multiplier




def get_live_price(symbol: str) -> float:
    try:
        # رفع الـ Timeout لـ 15 ثانية لضمان الاستجابة في الشبكات البطيئة
        resp = requests.get(f"https://api.binance.com/api/v3/ticker/price?symbol={symbol}USDT", timeout=15).json()
        return float(resp['price'])
    except Exception:
        return 0.0

def get_liquidity_strength(symbol):
    """
    تحليل عمق السوق لاكتشاف السيولة المخفية
    """
    try:
        # جلب أفضل 100 طلب شراء وبيع عبر واجهة بينانس العامة
        resp = requests.get(f"https://api.binance.com/api/v3/depth?symbol={symbol}USDT&limit=100", timeout=15)
        depth = resp.json()
        
        # حساب إجمالي كميات الشراء (Bids) وإجمالي كميات البيع (Asks)
        total_bids = sum(float(bid[1]) for bid in depth['bids'])
        total_asks = sum(float(ask[1]) for ask in depth['asks'])
        
        # حساب نسبة القوة (Liquidity Ratio)
        ratio = total_bids / total_asks if total_asks > 0 else 1.0
        return round(ratio, 2)
    except Exception as e:
        return 1.0

def calculate_price_prediction(symbol):
    """
    محرك التنبؤ العميق: حساب الانحدار الخطي البسيط لآخر 10 شمعات دقيقة لمعرفة سرعة السعر
    """
    try:
        url = f"https://api.binance.com/api/v3/klines?symbol={symbol}USDT&interval=1m&limit=10"
        resp = requests.get(url, timeout=15)
        if resp.status_code != 200:
            return 0.0
            
        data = resp.json()
        closes = [float(c[4]) for c in data]
        
        n = len(closes)
        if n < 10:
            return 0.0
            
        sum_y = sum(closes)
        sum_x = 45 # 0+1+2+3+4+5+6+7+8+9
        sum_xy = sum(i * closes[i] for i in range(n))
        sum_xx = 285 # 0^2 + ... + 9^2
        
        slope = (n * sum_xy - sum_x * sum_y) / (n * sum_xx - sum_x**2)
        return slope
    except Exception as e:
        return 0.0

latest_market_data = {
    "coins": {coin: {} for coin in SUPPORTED_COINS.keys()}  # ديناميكي - يدعم العملات الـ 10 (رادار محسّن)
}

def refresh_market_data_immediately():
    """تحديث فوري لبيانات السوق (استخدمها قبل أول تقرير مباشرة)"""
    global latest_market_data
    print("[REFRESH] 🔄 Triggering immediate market data refresh...", flush=True)
    try:
        # جلب نتائج تحديث المؤشرات الفور
        scan_results = []
        for symbol in SUPPORTED_COINS.keys():
            try:
                res = fetch_coin_market_data(symbol)
                if not res.get("error", True):
                    scan_results.append(res)
                    # تحديث فوري!!
                    latest_market_data["coins"][symbol] = {
                        "price": res.get("price", 0),
                        "target_buy": res.get("price", 0) * 0.98 if res.get("price") else 0,
                        "target_sell": res.get("price", 0) * 1.02 if res.get("price") else 0,
                        "liq_strength": res.get("liq_strength", 1.0),
                        "prediction_forecast": res.get("final_decision", "🔮 ⚖️ HOLD"),
                        "hunter_status": "🛡️ Safe",
                        "macd": res.get("macd", {}),
                        "multi_tf_trend": res.get("multi_tf_trend", {}),
                        "mtf_trend": res.get("multi_tf_trend", {}),  # تكرار للتوافق
                        "atr": res.get("atr", {}),
                        "mev": res.get("mev", {}),
                        "buy_signals": res.get("buy_signals", 0),
                        "sell_signals": res.get("sell_signals", 0)
                    }
            except Exception as e:
                print(f"    ⚠️ {symbol}: {e}", flush=True)
        
        print(f"[REFRESH] ✅ Updated {len(scan_results)} coins", flush=True)
    except Exception as e:
        print(f"[REFRESH] ❌ Error: {e}", flush=True)

def send_hourly_report(to_terminal=False):
    try:
        # 🔄 تأكد من وجود بيانات حديثة (إذا كانت فارغة أو قديمة جداً: حدّث فوراً)
        if not latest_market_data["coins"].get("BNB", {}).get("price"):
            print("[REPORT] 🟡 Data is missing, refreshing immediately...", flush=True)
            refresh_market_data_immediately()
        
        usdt_bal, _ = get_balances()
        active_usdt_bal = usdt_bal if not PAPER_TRADING else PAPER_BALANCE_USDT
        
        msg = f"🤖 [تقرير الحوت - V17 COLOSSUS REBUILD]\n"
        msg += f"💰 الرصيد المتاح: {active_usdt_bal:.2f}$\n"
        msg += get_vault_balances_text()
            
        msg += f"🦅 رادار السوق اللحظي (مع المؤشرات المتقدمة):\n\n"
        
        for symbol in list(SUPPORTED_COINS.keys())[:5]:  # العرض الأول 5 عملات فقط للوضوح
            # 🔥 اقرأ السعر من price_buffer - مصدر الحقيقة
            with _price_buffer_lock:
                buffer_prices = price_buffer.get(symbol, [])
            
            if not buffer_prices or buffer_prices[-1] <= 0:
                # لا توجد بيانات في المخزن المؤقت
                msg += f"{'='*50}\n"
                msg += f"🔸 {symbol}: Loading Data...\n\n"
                continue
            
            # السعر الفعلي من آخر قيمة في المخزن المؤقت
            current_price = buffer_prices[-1]
            
            # اقرأ باقي البيانات من latest_market_data للمؤشرات والأهداف
            coin_data = latest_market_data["coins"].get(symbol, {})
            target_buy = coin_data.get("target_buy", current_price * 0.98)
            target_sell = coin_data.get("target_sell", current_price * 1.02)
            liq_strength = coin_data.get("liq_strength", 1.0)
            
            # المؤشرات الجديدة
            macd_data = coin_data.get("macd", {})
            mtf_trend = coin_data.get("multi_tf_trend", {}) or coin_data.get("mtf_trend", {})
            atr_data = coin_data.get("atr", {})
            mev_data = coin_data.get("mev", {})
            buy_signals = coin_data.get("buy_signals", 0)
            
            # التنسيق
            prediction_forecast = coin_data.get("prediction_forecast", "HOLD")
            if "🔮" in str(prediction_forecast):
                prediction_forecast = str(prediction_forecast).replace("🔮 ", "")
                
            hunter_status = coin_data.get("hunter_status", "Safe")
            if "🛡️" in str(hunter_status):
                hunter_status = str(hunter_status).replace("🛡️ ", "")
            elif "🩸" in str(hunter_status):
                hunter_status = str(hunter_status).replace("🩸 ", "")
                
            c_state = state.coins[symbol]
            sell_val = "Trail" if c_state.trailing_active else f"{target_sell:.4f}"
            
            # الرسالة الرئيسية - مع السعر الحقيقي من price_buffer
            msg += f"{'='*50}\n"
            msg += f"🔸 {symbol}: السعر **${current_price:.4f}**\n"
            msg += f"🎯 شراء: ${target_buy:.4f} | 🎯 بيع: {sell_val}$\n"
            
            # المؤشرات المتقدمة - مع fallback إذا كانت فارغة
            msg += f"\n📊 **المؤشرات:**\n"
            macd_trend = macd_data.get('trend', 'تحميل...') if macd_data else 'تحميل...'
            macd_hist = macd_data.get('histogram', 0) if macd_data else 0
            msg += f"  💪 MACD: {macd_trend} (Hist: {macd_hist:.6f})\n"
            
            mtf_signal = mtf_trend.get('final_signal', 'HOLD') if mtf_trend else 'HOLD'
            mtf_5m = mtf_trend.get('5m', {}).get('trend', 'N/A') if mtf_trend else 'N/A'
            msg += f"  🌍 Multi-TF: {mtf_signal} | 5m: {mtf_5m}\n"
            
            atr_sl = atr_data.get('stop_loss_pct', 0) if atr_data else 0
            atr_tp = atr_data.get('take_profit_pct', 0) if atr_data else 0
            msg += f"  🛡️ ATR/SL: {atr_sl:.2f}% | TP: {atr_tp:.2f}%\n"
            
            mev_risk = mev_data.get('mev_risk_score', 0) if mev_data else 0
            mev_safe = '✅ آمن' if (mev_data and mev_data.get('is_safe')) else '⚠️ خطر'
            msg += f"  🔐 MEV Risk: {mev_risk}/100 {mev_safe}\n"
            
            msg += f"\n⚡ سيولة: {liq_strength} | 📈 تنبؤ: {prediction_forecast} | 🛡️ درع: {hunter_status}\n"
            msg += f"🎲 إشارات شراء: {buy_signals}/4\n"
            
            if symbol != list(SUPPORTED_COINS.keys())[min(4, len(SUPPORTED_COINS)-1)]:
                msg += "\n"
                
        msg += f"\n{'='*50}\n"
        msg += f"✨ تم التحديث باستخدام **Colossus V17 Rebuild** مع:\n"
        msg += f"  ✅ MACD Momentum Analysis\n"
        msg += f"  ✅ Multi-Timeframe Trend\n"
        msg += f"  ✅ ATR-based Dynamic Stop Loss\n"
        msg += f"  ✅ MEV Protection Shield\n"
        msg += f"  ✅ Venus Liquidation Detection\n"
        
        if to_terminal:
            print(msg)
        else:
            bot.send_message(TELEGRAM_CHAT_ID, msg, reply_markup=get_main_keyboard())
    except Exception as e:
        print(f"❌ [ERROR] build report failed: {e}")
        bot.send_message(TELEGRAM_CHAT_ID, f"❌ خطأ في التقرير: {str(e)[:100]}")

# ==============================================================================
# 🔒 HARD CONSTRAINTS - درع الأمان الصلب (قفل برمجي لا يمكن تجاوزه)
# ==============================================================================
MIN_LIQUIDITY_USD = 50_000.0   # الحد الأدنى الصلب للسيولة بالدولار
MAX_GAS_RATIO = 0.20           # الحد الأقصى الصلب لنسبة الغاز من إجمالي الربح

def check_arbitrage_opportunity(token_addr, current_token_price_usd):
    """
    المسبار السريع (Probe) مع درع الأمان الصلب:
    🔒 قفل برمجي #1: يرفض فوراً أي منصة لا تتحمل $50,000 بانزلاق < 15%
    أي منصة تفشل هذا الاختبار يتم تجاهلها نهائياً بغض النظر عن أي شرط آخر.
    """
    path = [w3.to_checksum_address(token_addr), w3.to_checksum_address(USDT_ADDR)]
    valid_prices = {}
    
    if current_token_price_usd <= 0: return 0.0, None, None, 0.0, 0.0
    
    # مسبار 500 دولار للتقييم الأولي
    probe_tokens = 500.0 / current_token_price_usd
    # 🔒 اختبار السيولة الصلب: 50,000 دولار بالضبط (لا يتغير)
    liq_tokens = MIN_LIQUIDITY_USD / current_token_price_usd
    
    PROBE_WEI = w3.to_wei(probe_tokens, 'ether')
    LIQ_WEI = w3.to_wei(liq_tokens, 'ether')
    
    for name, contract in dex_contracts.items():
        try:
            usdt_amount_probe = contract.functions.getAmountsOut(PROBE_WEI, path).call()[1] / (10 ** 18)
            usdt_amount_liq = contract.functions.getAmountsOut(LIQ_WEI, path).call()[1] / (10 ** 18)
            
            price_from_probe = usdt_amount_probe / probe_tokens
            expected_liq_val = price_from_probe * liq_tokens
            actual_slippage_pct = ((expected_liq_val - usdt_amount_liq) / expected_liq_val) * 100 if expected_liq_val > 0 else 100

            # ============================================================
            # 🔒 القفل الصلب: رفض فوري إذا فشل اختبار السيولة ($50,000)
            # ============================================================
            if usdt_amount_liq < (expected_liq_val * 0.85):
                logger.warning(
                    f"🛡️ تم تجاهل فرصة بسبب عدم استيفاء درع الأمان (السيولة/الغاز) | "
                    f"المنصة: {name} | السيولة المطلوبة: ${MIN_LIQUIDITY_USD:,.0f} | "
                    f"الانزلاق الفعلي: {actual_slippage_pct:.1f}% (الحد: 15%)"
                )
                continue  # ← Return False المعادل: رفض فوري لهذه المنصة
                
            valid_prices[name] = price_from_probe
        except Exception: pass

    if len(valid_prices) >= 2:
        cheapest_dex = min(valid_prices, key=valid_prices.get)
        most_expensive_dex = max(valid_prices, key=valid_prices.get)
        spread = ((valid_prices[most_expensive_dex] - valid_prices[cheapest_dex]) / valid_prices[cheapest_dex]) * 100
        return spread, cheapest_dex, most_expensive_dex, valid_prices[cheapest_dex], valid_prices[most_expensive_dex]
        
    return 0.0, None, None, 0.0, 0.0

# ==============================================================================
# --- 📐محرك المراجحة المثلثية (Triangular Engine Core) ---
# ==============================================================================
_tri_scan_result = {"path": "Scanning...", "spread": 0.0, "status": "Ready"}
_tri_scan_lock = threading.Lock()

def get_pool_liquidity_usd(token_a: str, token_b: str) -> float:
    """درع السيولة ($50k): حساب القيمة المقدرة للحوض بالدولار"""
    try:
        pair = get_pair_address(token_a, token_b)
        if pair == "0x0000000000000000000000000000000000000000": return 0.0
        
        # نستخدم USDT أو BNB كمعيار لتقدير قيمة الحوض
        if token_a == USDT_ADDR or token_b == USDT_ADDR:
            usdt_bal = usdt_token.functions.balanceOf(pair).call() / 10**18
            return usdt_bal * 2 # القيمة الإجمالية للحوض المتوازن تقريباً
        elif token_a == WBNB_ADDR or token_b == WBNB_ADDR:
            bnb_bal = w3.eth.get_balance(pair) / 10**18 if token_a == WBNB_ADDR else 0 # تبسيط
            # نستخدم balanceOf لـ WBNB
            wbnb_tk = w3.eth.contract(address=WBNB_ADDR, abi=ERC20_ABI)
            wbnb_bal = wbnb_tk.functions.balanceOf(pair).call() / 10**18
            return wbnb_bal * get_live_price("BNB") * 2
        return 50001.0 # افتراض أمان في حال لم نتمكن من الحساب
    except: return 0.0

def check_triangular_arbitrage(path_symbols: list, amount_in_usd: float = 100.0) -> Tuple[float, list, float]:
    """
    تحليل المسار الثلاثي:
    - حساب المخرجات مطروحاً منها عمولة 0.75% (0.25% لكل تحويل)
    - فحص درع السيولة الـ 50,000$ لكل حوض
    """
    global w3, ACTIVE_RPC
    time.sleep(0.1)  # simple throttle for triangular scan
    try:
        path_addrs = []
        for sym in path_symbols:
            if sym == "USDT": path_addrs.append(USDT_ADDR)
            elif sym == "BNB": path_addrs.append(WBNB_ADDR)
            else: path_addrs.append(SUPPORTED_COINS[sym])

        # 1. درع السيولة الثلاثي (Triple Shield)
        for i in range(len(path_addrs)-1):
            liq = get_pool_liquidity_usd(path_addrs[i], path_addrs[i+1])
            if liq < MIN_LIQUIDITY_USD: return 0.0, [], 0.0
            
        # 2. حساب المخرجات مع الرسوم (PancakeSwap Router يحسب الرسوم داخلياً)
        base_sym = path_symbols[0]
        start_price = get_live_price(base_sym)
        if start_price <= 0: return 0.0, [], 0.0
        
        amount_in_wei = w3.to_wei(amount_in_usd / start_price, 'ether')
        amounts_out = router.functions.getAmountsOut(amount_in_wei, path_addrs).call()
        
        final_amount_human = amounts_out[-1] / 10**18
        final_value_usd = final_amount_human * start_price
        
        spread = ((final_value_usd - amount_in_usd) / amount_in_usd) * 100
        return spread, path_addrs, final_value_usd
    except Exception as e:
        if "429" in str(e) or "Timeout" in str(e):
            new_w3, new_url = get_stable_w3()
            if new_w3:
                w3 = new_w3
                ACTIVE_RPC = new_url
        return 0.0, [], 0.0

def execute_triangular_arbitrage(path_addrs: list, amount_in_usd: float, spread: float, net_profit: float):
    # NUCLEAR: Simulation block removed for LIVE execution
    try:
        nonce = w3.eth.get_transaction_count(wallet_address)
        base_token = path_addrs[0]
        base_price = get_live_price("BNB" if base_token == WBNB_ADDR else "USDT")
        amount_in_wei = w3.to_wei(amount_in_usd / base_price, 'ether')
        min_out = int(amount_in_wei * 1.005)
        deadline = int(time.time()) + 300
        tx = router.functions.swapExactTokensForTokens(
            amount_in_wei, min_out, path_addrs, wallet_address, deadline
        ).build_transaction({'from': wallet_address, 'gasPrice': w3.eth.gas_price, 'nonce': nonce, 'chainId': 56})
        tx['gas'] = int(w3.eth.estimate_gas(tx) * 1.1)
        signed = w3.eth.account.sign_transaction(tx, private_key=PRIVATE_KEY)
        raw_tx = getattr(signed, 'raw_transaction', getattr(signed, 'rawTransaction', getattr(signed, 'raw', None)))
        tx_hash = w3.eth.send_raw_transaction(raw_tx)
        log_action("🚀", "TRI-ARBIT", f"Hash: {w3.to_hex(tx_hash)[:20]}")
        receipt = w3.eth.wait_for_transaction_receipt(tx_hash, timeout=120)
        if receipt.status == 1:
            log_action("🎉", "TRI-SUCCESS", f"Spread: {spread:.2f}%", net_profit=net_profit)
        else:
            log_action("❌", "TRI-FAILED", "Transaction Reverted.")
    except Exception as e:
        log_action("⚠️", "TRI-ERROR", f"{str(e)[:50]}")

def optimize_arbitrage_size(cheap_dex, exp_dex, token_addr, current_token_price_usd, bnb_live_price, wallet_address, nonce_base):
    """محسن الأرباح الديناميكي (Profit Optimizer): يختبر أحجام قروض مبنية على الدولار لاستيعاب العملات الرخيصة"""
    best_size = 0.0
    best_net_profit = 0.0
    best_tx = None
    best_spread = 0.0
    
    # نختبر القروض من 1000$ إلى أقصى حد يحدده المستخدم (بحسب قيمة MAX BNB دولاريّاً)
    max_usd = MAX_LOAN_BNB * bnb_live_price
    usd_sizes = [1000.0, 2500.0, 5000.0, 7500.0, max_usd]
    usd_sizes = sorted(list(set([s for s in usd_sizes if s <= max_usd])))
    if max_usd not in usd_sizes and max_usd > 0: usd_sizes.append(max_usd)
    
    r1 = w3.to_checksum_address(DEX_ROUTERS[cheap_dex])
    r2 = w3.to_checksum_address(DEX_ROUTERS[exp_dex])
    path = [w3.to_checksum_address(token_addr), w3.to_checksum_address(USDT_ADDR)]
    
    # حل مسألة مسبح السيولة للقرض (Factory Call) لمعرفة عنوان الزوج على PancakeSwap حصراً
    try:
        pair_address = get_pair_address(token_addr, USDT_ADDR)
        if pair_address == "0x0000000000000000000000000000000000000000": return 0.0, 0.0, None, 0.0
    except Exception: return 0.0, 0.0, None, 0.0
    
    for usd_size in usd_sizes:
        if current_token_price_usd <= 0: continue
        size = usd_size / current_token_price_usd
        amount_wei = w3.to_wei(size, 'ether')
        
        try:
            # 1. الاستكشاف الأولي للانزلاق
            cheap_out = dex_contracts[cheap_dex].functions.getAmountsOut(amount_wei, path).call()[1] / 10**18
            exp_out = dex_contracts[exp_dex].functions.getAmountsOut(amount_wei, path).call()[1] / 10**18
            gross_profit_usdt = exp_out - cheap_out
            
            if gross_profit_usdt <= 0: continue
                
            # 2. بناء معاملة العقد
            tx = flash_contract.functions.startArbitrage(
                w3.to_checksum_address(pair_address),
                amount_wei,
                w3.to_checksum_address(token_addr),
                w3.to_checksum_address(USDT_ADDR),
                r1, r2
            ).build_transaction({
                'chainId': 56,
                'gasPrice': w3.eth.gas_price,
                'nonce': nonce_base,
                'from': wallet_address
            })
            
            # 3. محاكاة الغاز الفعلية
            estimated_gas = w3.eth.estimate_gas(tx)
            tx['gas'] = min(int(estimated_gas * 1.1), 500000)
            
            gas_fee_usdt = ((tx['gas'] * tx['gasPrice']) / (10**18)) * bnb_live_price
            
            # ============================================================
            # 🔒 القفل الصلب: رفض فوري إذا تجاوز الغاز 20% من الربح
            # ============================================================
            gas_ratio = gas_fee_usdt / gross_profit_usdt if gross_profit_usdt > 0 else 1.0
            if gas_ratio > MAX_GAS_RATIO:
                logger.warning(
                    f"🛡️ تم تجاهل فرصة بسبب عدم استيفاء درع الأمان (السيولة/الغاز) | "
                    f"الغاز: {gas_fee_usdt:.4f}$ = {gas_ratio*100:.1f}% من الربح | "
                    f"الحد الأقصى المسموح: {MAX_GAS_RATIO*100:.0f}%"
                )
                continue  # ← Return False المعادل: رفض فوري لهذا الحجم
                
            # 5. اختيار الحجم الأفضل
            net_profit_usdt = gross_profit_usdt - gas_fee_usdt
            if net_profit_usdt > best_net_profit:
                best_net_profit = net_profit_usdt
                best_size = size
                best_tx = tx
                best_spread = (gross_profit_usdt / cheap_out) * 100
                
        except Exception: continue
            
    return best_size, best_net_profit, best_tx, best_spread

# ==============================================================================
# --- 🚀 V17: محرك المسح المتوازي (Parallel Coin Scanner Engine) ---
# ==============================================================================
_SCAN_WORKERS = 2
_scan_executor = concurrent.futures.ThreadPoolExecutor(
    max_workers=_SCAN_WORKERS,
    thread_name_prefix="CoinScanner"
)

def fetch_coin_market_data(symbol: str) -> dict:
    """
    🚀 محرك جلب البيانات المحسّن (COLOSSUS V17)
    يجلب جميع المؤشرات الاستراتيجية:
    - MACD (الزخم)
    - Multi-TF Trend (الاتجاه على أفق زمني متعدد)
    - ATR Stop Loss (الحماية الديناميكية)
    - MEV Protection (الحماية من الساندويتش)
    - Venus Liquidations (فرص المراجحة)
    """
    time.sleep(0.1)  # throttle لتجنب 429
    try:
        price = get_live_price(symbol)
        if price <= 0:
            return {"symbol": symbol, "error": True}
        
        # جلب المؤشرات الأساسية
        rsi_matrix = get_rsi_matrix(symbol)
        
        # استدعاء الدوال الاستراتيجية الجديدة
        macd_data = get_macd(symbol)
        elasticity_data = get_price_elasticity(symbol, interval="1h")
        mtf_trend = get_multi_timeframe_trend(symbol)
        
        # حساب Stop Loss و Take Profit ديناميكياً
        atr_data = calculate_atr_stop_loss(symbol, price)
        
        # فحص MEV
        mev_data = detect_mev_protection(symbol, price)
        
        # فرص Venus
        venus_data = check_venus_liquidations()
        
        # بيانات إضافية
        liq_strength = get_liquidity_strength(symbol)
        price_slope = calculate_price_prediction(symbol)
        
        # قرار مركب: هل نشتري أم نبيع؟
        buy_signals = 0
        sell_signals = 0
        
        # Signal 1: MACD
        if macd_data["trend"] == "BULLISH":
            buy_signals += 1
        elif macd_data["trend"] == "BEARISH":
            sell_signals += 1
        
        # Signal 2: Multi-TF Trend
        if mtf_trend["final_signal"] == "BUY":
            buy_signals += 1
        elif mtf_trend["final_signal"] == "SELL":
            sell_signals += 1
        
        # Signal 3: Elasticity
        if elasticity_data["signal"] == "BUY":
            buy_signals += 1
        elif elasticity_data["signal"] == "SELL":
            sell_signals += 1
        
        # Signal 4: Price Slope
        if price_slope > 0:
            buy_signals += 1
        elif price_slope < -0.5:
            sell_signals += 1
        
        # قرار نهائي
        if buy_signals >= 2 and mev_data["is_safe"]:
            final_decision = "🟢 BUY"
        elif sell_signals >= 2:
            final_decision = "🔴 SELL"
        else:
            final_decision = "⚫ HOLD"
        
        return {
            "symbol": symbol,
            "price": price,
            "rsi_matrix": rsi_matrix,
            "macd": macd_data,
            "elasticity": elasticity_data,
            "multi_tf_trend": mtf_trend,
            "atr": atr_data,
            "mev": mev_data,
            "venus": venus_data,
            "liq_strength": liq_strength,
            "price_slope": price_slope,
            "buy_signals": buy_signals,
            "sell_signals": sell_signals,
            "final_decision": final_decision,
            "error": False
        }
    except Exception as e:
        logger.warning(f"⚠️ [CoinScanner] فشل جلب بيانات {symbol}: {e}")
        return {"symbol": symbol, "error": True}

# ==============================================================================
# --- معالج الأزرار المدمجة (INLINE BUTTONS CALLBACK HANDLER) ---
# ==============================================================================
@bot.callback_query_handler(func=lambda call: True)
def handle_callback_query(call):
    try:
        # إنهاء حالة التحميل (Loading State) للزر
        bot.answer_callback_query(call.id)
        
        chat_id = call.message.chat.id
        
        # ========== الأزرار الأساسية ==========
        
        if call.data == "buy_5_BNB":
            # شراء 5 USDT من BNB
            price = get_live_price("BNB")
            bot.send_message(chat_id, "⏳ جاري معالجة أمر الشراء...")
            trade_executor.submit(build_and_send_tx, chat_id, "شراء", 5.0, price, True, True, "BNB")
        
        elif call.data == "sell_5_BNB":
            # بيع 5 USDT من BNB
            price = get_live_price("BNB")
            bot.send_message(chat_id, "⏳ جاري معالجة أمر البيع...")
            trade_executor.submit(build_and_send_tx, chat_id, "بيع", 5.0, price, True, True, "BNB")
        
        elif call.data == "report":
            # التقرير الشامل
            bot.send_message(chat_id, "📊 جاري إعداد التقرير...")
            try:
                send_hourly_report()
            except Exception as e:
                bot.send_message(chat_id, f"❌ خطأ في التقرير: {str(e)[:100]}")
        
        elif call.data == "reset_trailing":
            # تصفير جميع الـ Trailing Stops
            with state_lock:
                for coin in state.coins.values():
                    coin.trailing_active = False
                    coin.trailing_buy_active = False
                    coin.highest_price = 0.0
                    coin.lowest_drop_pct = 0.0
                state.save()
            bot.send_message(chat_id, "✅ تم تصفير جميع مستويات الـ Trailing Stops")
        
        elif call.data == "toggle_bot":
            # إيقاف/تشغيل البوت
            with state_lock:
                state.bot_active = not state.bot_active
                state.save()
            status = "🟢 نشط" if state.bot_active else "🔴 موقوف"
            bot.send_message(chat_id, f"⚙️ حالة البوت: {status}")
        
        elif call.data == "last_trades":
            # عرض آخر الصفقات
            try:
                conn = sqlite3.connect(TRADE_DB_FILE)
                c = conn.cursor()
                c.execute("SELECT action, amount_usd, price, timestamp FROM trades ORDER BY timestamp DESC LIMIT 5")
                trades = c.fetchall()
                conn.close()
                
                msg = "🗒️ **آخر 5 صفقات:**\n\n"
                if trades:
                    for action, amount, price, ts in trades:
                        dt = datetime.fromtimestamp(ts).strftime("%H:%M:%S")
                        msg += f"• {action} | {amount:.2f}$ @ {price:.2f}$ | {dt}\n"
                else:
                    msg = "لا توجد صفقات مسجلة بعد"
                bot.send_message(chat_id, msg)
            except Exception as e:
                bot.send_message(chat_id, f"❌ خطأ: {str(e)[:100]}")
        
        elif call.data == "sync":
            # مزامنة حالة البوت
            try:
                state.save()
                bot.send_message(chat_id, "✅ تمت مزامنة الحالة بنجاح")
            except Exception as e:
                bot.send_message(chat_id, f"❌ خطأ في المزامنة: {str(e)[:100]}")
        
        elif call.data == "ask_withdraw":
            # سحب الأرباح من العقد الذكي
            bot.send_message(chat_id, "⏳ جاري معالجة طلب السحب...")
            try:
                perform_vault_withdrawal(chat_id)
            except Exception as e:
                bot.send_message(chat_id, f"❌ خطأ في السحب: {str(e)[:100]}")
        
        elif call.data == "nuke":
            # الزر النووي الشامل
            bot.send_message(chat_id, "⚠️ تفعيل البروتوكول النووي...")
            try:
                handle_nuclear_stop(call.message)
            except Exception as e:
                bot.send_message(chat_id, f"❌ خطأ: {str(e)[:100]}")
    
    except Exception as e:
        print(f"❌ خطأ في معالجة الزر: {e}")
        try:
            bot.send_message(call.message.chat.id, f"⚠️ حدث خطأ أثناء معالجة الطلب: {str(e)[:80]}")
        except Exception:
            pass


# ==============================================================================
# --============================================================================
# --- معالج الرسائل الذكية (SMART CHAT V17 - ANTI-HALLUCINATION MODE) ---
# ==============================================================================
@bot.message_handler(func=lambda message: True)
def handle_smart_chat(message):
    try:
        # ========== التحقق من الجروب والمنشن/الرد ==========
        if message.chat.type in ['group', 'supergroup']:
            try:
                bot_username = bot.get_me().username
            except Exception as e:
                print(f"⚠️ خطأ في جلب يوزرنيم البوت: {e}")
                return
            
            bot_mention = f"@{bot_username}"
            is_mention = bot_mention in message.text
            
            is_reply_to_bot = False
            if message.reply_to_message:
                try:
                    is_reply_to_bot = message.reply_to_message.from_user.id == bot.get_me().id
                except Exception:
                    is_reply_to_bot = False
            
            if not (is_mention or is_reply_to_bot):
                return
        
        # ========== جمع البيانات الحقيقية من الكود ==========
        real_data = {
            "timestamp": datetime.now().isoformat(),
            "blockchain_status": "متصل ✓" if (w3 and w3.is_connected()) else "مقطوع ✗",
            "websocket_status": "متصل ✓" if ws_ready else "مقطوع ✗",
        }
        
        # البيانات المالية الحقيقية
        try:
            usdt_bal, bnb_bal = get_balances()
            real_data["balances"] = {
                "usdt": round(usdt_bal, 4),
                "bnb": round(bnb_bal, 6)
            }
        except Exception as e:
            print(f"⚠️ خطأ جلب الأرصدة: {e}")
            real_data["balances"] = {"usdt": 0, "bnb": 0}
        
        # الأسعار الحقيقية من خزن الذاكرة
        collected_prices = {}
        try:
            for sym in list(SUPPORTED_COINS.keys())[:5]:
                try:
                    price = get_live_price(sym)
                    if price > 0:
                        collected_prices[sym] = round(price, 4)
                        rsi_val = get_rsi(sym, "15m")
                        collected_prices[f"{sym}_RSI"] = round(rsi_val, 1)
                except Exception:
                    pass
            real_data["prices"] = collected_prices
        except Exception as e:
            print(f"⚠️ خطأ جلب الأسعار: {e}")
            real_data["prices"] = {}
        
        # بيانات Web3 الحقيقية
        try:
            if w3 and w3.is_connected():
                real_data["web3_info"] = {
                    "chain_id": 56,
                    "gas_price_gwei": round(w3.eth.gas_price / 1e9, 2)
                }
            else:
                real_data["web3_info"] = {"status": "disconnected"}
        except Exception as e:
            real_data["web3_info"] = {"status": "error"}
        
        # تحديات الاتصال
        real_data["network_issues"] = []
        if not ws_ready:
            real_data["network_issues"].append("⚠️ الـ Websocket مقطوع - الأسعار قد تكون قديمة")
        if not (w3 and w3.is_connected()):
            real_data["network_issues"].append("❌ Web3 مقطوع - المعاملات غير ممكنة")
        
        # بناء نص السياق
        context_text = "📊 **البيانات الحقيقية الفعالة:**\n"
        context_text += f"🏦 USDT: ${real_data['balances']['usdt']} | BNB: {real_data['balances']['bnb']}\n"
        context_text += f"🔌 Blockchain: {real_data['blockchain_status']} | Websocket: {real_data['websocket_status']}\n"
        
        if real_data['prices']:
            context_text += "💰 الأسعار:\n"
            for key, val in list(real_data['prices'].items())[:8]:
                if not key.endswith("_RSI"):
                    rsi = real_data['prices'].get(f"{key}_RSI", "N/A")
                    context_text += f"  {key}: ${val} (RSI={rsi})\n"
        
        if real_data['web3_info'].get('status') != 'disconnected':
            context_text += f"⛽ Gas: {real_data['web3_info']['gas_price_gwei']} Gwei\n"
        
        if real_data['network_issues']:
            context_text += "⚠️ **تحديات:**\n"
            for issue in real_data['network_issues']:
                context_text += f"  {issue}\n"
        
        context_text += "\n⚠️ اجب على السؤال بناءً على البيانات الحقيقية أعلاه فقط!\n"
        
        # ========== جلب API Key ==========
        api_key = os.getenv("GROQ_API_KEY")
        if not api_key:
            print("❌ [SMART CHAT] لا يوجد GROQ_API_KEY")
            bot.reply_to(message, "⚠️ API key غير متاح")
            return
        
        # ========== إنشاء عميل Groq ==========
        try:
            client = Groq(api_key=api_key)
        except Exception as e:
            print(f"❌ خطأ Groq: {e}")
            bot.reply_to(message, "❌ خطأ في الاتصال")
            return
        
        # ========== System Prompt منع الـ Hallucination ==========
        system_prompt = """أنت Colossus V17 - محلل تقني ضد الـ Hallucination.

⛔ **قوانين الصرامة:**
1. استخدم البيانات الحقيقية فقط - لا تختر أرقام
2. إذا كان Websocket مقطوع = الأسعار قد تكون قديمة
3. إذا كان Web3 مقطوع = لا يمكن تنفيذ معاملات
4. الجواب يجب أن يستند على المنطق البرمجي الموجود
5. إذا لم تعرف شيء = قل "البيانات لا توفر هذا"

🎯 كن تقنياً دقيقاً، لا كاتب خيال!"""
        
        # ========== استخراج السؤال ==========
        user_text = message.text.strip()
        if message.chat.type in ['group', 'supergroup']:
            try:
                bot_username = bot.get_me().username
                user_text = user_text.replace(f"@{bot_username}", "").strip()
            except Exception:
                pass
        
        if not user_text:
            return
        
        # ========== صياغة البرومبت الدقيقة ==========
        enriched_message = f"{context_text}\n\n👤 **السؤال**: {user_text}"
        
        # ========== استدعاء Groq ==========
        try:
            response = client.chat.completions.create(
                model="mixtral-8x7b-32768",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": enriched_message}
                ],
                max_tokens=1000,
                temperature=0.3  # أقل لمنع الخيال
            )
        except Exception as e:
            try:
                response = client.chat.completions.create(
                    model="llama3-8b-8192",
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": enriched_message}
                    ],
                    max_tokens=1000,
                    temperature=0.3
                )
            except Exception as e2:
                bot.reply_to(message, "❌ خطأ API")
                return
        
        # ========== استخراج الرد ==========
        if not response or not response.choices:
            bot.reply_to(message, "⚠️ لا رد")
            return
        
        ai_response = response.choices[0].message.content.strip()
        if not ai_response:
            bot.reply_to(message, "⚠️ رد فارغ")
            return
        
        # ========== إرسال الرد ==========
        try:
            bot.reply_to(message, ai_response)
        except Exception:
            try:
                bot.send_message(message.chat.id, ai_response)
            except Exception:
                bot.send_message(message.chat.id, "❌ خطأ الإرسال")
    
    except Exception as e:
        print(f"❌ [SMART CHAT] {e}")
        try:
            bot.reply_to(message, "❌ خطأ")
        except Exception:
            pass




# ==============================================================================
# --- ⚡ قناص القروض السريعة الاستراتيجي (FLASH LOAN SNIPER) ---
# ==============================================================================
FLASH_TARGET_COINS_MAP = {
    "WBNB": WBNB_ADDR,
    "ETH": ETH_ADDR,
    "SOL": SOL_ADDR,
    "XRP": XRP_ADDR
}

from web3.exceptions import ContractLogicError

def execute_flash_loan(sym: str, best_tx: dict, best_size: float, best_net_profit: float, final_spread: float, cheap_dex: str, exp_dex: str) -> bool:
    """
    دالة الإطلاق المستقلة والآمنة لهجوم القروض السريعة.
    يتم استدعاؤها مع محاكاة (Dry Run) للحماية من خسارة الغاز قبل التوقيع الحقيقي بدون exit().
    """
    try:
        if sym not in FLASH_TARGET_COINS_MAP:
            return False

        log_action("⚡", "ARB SIMUL", f"{sym} — Optimal size: {best_size:.4f} | Est. net: ~${best_net_profit:.2f} | Simulating...")
        
        # 1. الحماية الصارمة (Dry Run) - محاكاة بدون رسوم غاز عبر node
        try:
            w3.eth.call(best_tx)
        except ContractLogicError as e:
            log_action("⚠️", "ARB REVERT", f"{sym} — المحاكاة فشلت (لا يوجد ربح كاف). {str(e)[:40]}")
            return False
        except Exception as e:
            log_action("⚠️", "ARB SIM ERR", f"{sym} — إحباط: خطأ أثناء المحاكاة. {str(e)[:40]}")
            return False

        # 2. التحديث الدقيق للغاز لضمان التعدين (بناء على web3.py فقط)
        try:
            best_tx['gas'] = int(w3.eth.estimate_gas(best_tx) * 1.15)
            # تحديث النونس الاحتياطي
            best_tx['nonce'] = w3.eth.get_transaction_count(wallet_address)
        except Exception: pass

        # 3. توقيع وإرسال الترانزكشن الفعلية بشكل آمن (لا يتم استخدام requests هنا)
        signed_txn = w3.eth.account.sign_transaction(best_tx, private_key=PRIVATE_KEY)
        raw_tx = getattr(signed_txn, 'raw_transaction', getattr(signed_txn, 'rawTransaction', getattr(signed_txn, 'raw', None)))
        tx_hash = w3.eth.send_raw_transaction(raw_tx)
        tx_hex = w3.to_hex(tx_hash)
        
        log_action("🚀", "ARB LAUNCH", f"{sym} — Tx sent | Hash: {tx_hex[:20]}...")
        
        # 4. تأكيد وصول العملية
        receipt = w3.eth.wait_for_transaction_receipt(tx_hash, timeout=120)
        
        if receipt.status == 1:
            log_action("🎉", "ARB SUCCESS", f"{sym}/USDT | Spread: {final_spread:.2f}% | Loan: {best_size:.4f} {sym}", net_profit=best_net_profit)
            try:
                alert_msg = (
                    f"🚨 [تنبيه: هجوم قناص ناجح!] 🚨\n\n"
                    f"🐋 **السايبر واي:** قنص فرصة مراجحة (Flash Arbitrage)\n"
                    f"🎯 **الهدف المستهدف:** {sym}/USDT\n"
                    f"⚖️ **حجم القرض (Loan Size):** {best_size} {sym}\n"
                    f"💰 **نسبة الربح (Final Spread):** {final_spread:.2f}%\n"
                    f"💵 **الربح الصافي تقريباً:** ~{best_net_profit:.2f}$\n"
                    f"🛡️ **الهجوم:** الشراء السريع من {cheap_dex} والبيع على {exp_dex}\n\n"
                    f"🚀 **رابط الغنيمة (Tx Hash):**\n"
                    f"https://bscscan.com/tx/{tx_hex}"
                )
                bot.send_message(TELEGRAM_CHAT_ID, alert_msg)
            except Exception: pass
            return True
        else:
            log_action("❌", "ARB FAILED", f"{sym} — رسبت الترانزكشن على البلوكشين وضاع الغاز.")
            return False
            
    except Exception as e:
        log_action("⚠️", "ARB FATAL", f"{sym} — خطأ أساسي في الدالة: {str(e)[:40]}")
        return False

def auto_trading_loop():
    global loop_alive_time
    print("[DEBUG] [ENGINE] 1. Entering auto_trading_loop...", flush=True)
    log_action("✅", "BOT ONLINE", f"Whale Bot V17 Colossus booted — scanning {len(SUPPORTED_COINS)} coins + Arbitrage Sniper")
    print(f"{_GB}CORE ENGINE ACTIVE: Whale Bot V17 Colossus is starting...{_RST}", flush=True)
    print("[CORE] High-Speed Radar Active: Top 4 Coins Only (WBNB, ETH, SOL, XRP)", flush=True)

    last_report_time = time.time()
    last_arbitrage_time = 0

    while True:
        try:
            # ☢️ NUCLEAR: استجابة فورية لمحرك الـ Mempool
            if _mempool_trigger.is_set():
                print("🐋 [NUCLEAR] Mempool Trigger caught! Executing Emergency Scan...", flush=True)
                _mempool_trigger.clear()
            
            loop_alive_time = time.time()
            # --- نظام التقرير التلقائي (كل ساعة) ---
            if time.time() - last_report_time >= 3600:
                log_action("⏳", "HOURLY RPT", "Generating & sending hourly Telegram report...")
                try:
                    send_hourly_report()  # استدعاء دالة التقرير
                    last_report_time = time.time()  # تصفير العداد لساعة جديدة
                except Exception as e:
                    print(f"❌ [ERROR] Report failed: {e}")
                    last_report_time = time.time() - 3300  # المحاولة بعد 5 دقائق إذا فشل
            if not state.bot_active:
                time.sleep(10)
                continue

            usdt_bal, _ = get_balances()
            active_usdt_bal = usdt_bal if not PAPER_TRADING else PAPER_BALANCE_USDT
            
            # --- 🚀 أولوية جلب أسعار العملات القيادية (Core Coins) لملء اللوحة فوراً ---
            for core_sym in ["BNB", "ETH", "SOL"]:
                p = get_live_price(core_sym)
                if p > 0:
                    latest_market_data["coins"][core_sym]["price"] = p
                    # ملء أهداف وهمية مبدئية إذا لم تكن موجودة لمنع جفاف اللوحة
                    if "target_buy" not in latest_market_data["coins"][core_sym]:
                        latest_market_data["coins"][core_sym]["target_buy"] = p * 0.98
                        latest_market_data["coins"][core_sym]["target_sell"] = p * 1.02
            
            # ================================================================
            # 🚀 [V17] محرك المسح المتوازي (Parallel Coin Scanner)
            # ================================================================
            coin_market_data = {}
            coin_futures = {
                _scan_executor.submit(fetch_coin_market_data, symbol): symbol 
                for symbol in SUPPORTED_COINS.keys()
            }
            
            print("[DEBUG] [ENGINE] 5. Measuring System Health...", flush=True)
            try:
                cpu_usage = psutil.cpu_percent(interval=None)
            except Exception:
                cpu_usage = 0.0
                
            # 🧭 استدعاء وطباعة مؤشر المشاعر
            fgi = get_fear_and_greed_index()
            print(f"[MARKET SENTIMENT] Index: {fgi['value']} | Status: {fgi['status']}", flush=True)
                
            print("[DEBUG] [ENGINE] 6. Checking Market Crash status...", flush=True)
            btc_crashed = get_btc_crash_status()
            print(f"[DEBUG] [ENGINE] 7. BTC Crash status: {btc_crashed}", flush=True)
            mode_str = TRADE_MODE

            # ================================================================
            # 🚀 [△ TRIANGULAR SCAN] - التحقق من المراجحة المثلثية (الأولوية القصوى)
            # ================================================================
            print(f"[DEBUG] [ENGINE] 6. Starting Triangular Scan ({len(TRIANGULAR_PATHS)} paths)...", flush=True)
            best_tri_spread = 0.0
            best_tri_path = None
            best_tri_addrs = []
            best_tri_final_val = 0.0
            
            # مسح سريع لـ 80 مساراً
            for path_syms in TRIANGULAR_PATHS:
                spread, addrs, f_val = check_triangular_arbitrage(path_syms, amount_in_usd=100.0)
                if spread > best_tri_spread:
                    best_tri_spread = spread
                    best_tri_path = " -> ".join(path_syms)
                    best_tri_addrs = addrs
                    best_tri_final_val = f_val

            # تحديث بيانات اللوحة
            with _tri_scan_lock:
                _tri_scan_result["path"] = best_tri_path if best_tri_path else "Scanning..."
                _tri_scan_result["spread"] = best_tri_spread
                _tri_scan_result["status"] = "TARGET LOCKED" if best_tri_spread > 0.75 else "Ready"

            # ─── جمع نتائج المسح المتوازي ──────────────────────────────────
            print("[DEBUG] [ENGINE] 8. Collecting parallel scan results...", flush=True)
            for future in concurrent.futures.as_completed(coin_futures):
                res = future.result()
                if not res.get("error", True):
                    coin_market_data[res["symbol"]] = res

            # التنفيذ إذا تجاوز الربح الصافي (0.75% رسوم + غاز تقديري)
            if best_tri_spread > 0.85: # عتبة الربح بعد الرسوم والغاز
                net_usd_profit = best_tri_final_val - 100.0
                execute_triangular_arbitrage(best_tri_addrs, 100.0, best_tri_spread, net_usd_profit)
                # نسحب وقت استراحة قليلاً لتجنب التكرار الزائد
                time.sleep(2)
                continue # نعود لبداية الحلقة لإعطاء الأولوية للمثلثات دوماً


            # --- 🔴 [رادار قناص الفلاش] فحص وإطلاق المراجحة اللامركزية ---
            # NUCLEAR: Simulation block removed for LIVE execution
            try:
                nonce = w3.eth.get_transaction_count(wallet_address)
                bnb_live_price = get_live_price("BNB")
                
                for sym, token_addr in FLASH_TARGET_COINS_MAP.items():
                    current_price = get_live_price(sym)
                    probe_spread, cheap_dex, exp_dex, cheap_p, exp_p = check_arbitrage_opportunity(token_addr, current_price)
                    
                    # 🕸️ فلتر المشاعر الثقيل (Sniper Logic)
                    fgi = get_fear_and_greed_index()
                    sniper_threshold = 1.5 * (1.5 if (fgi["value"] > 85 or "Extreme Greed" in fgi["status"]) else 1.0)
                    
                    if probe_spread > sniper_threshold:
                        log_action("🔍", "ARB PROBE", f"{sym}/USDT Spread: {probe_spread:.4f}% | {cheap_dex} → {exp_dex}")
                        
                        best_size, best_net_profit, best_tx, final_spread = optimize_arbitrage_size(
                            cheap_dex, exp_dex, token_addr, current_price, bnb_live_price, wallet_address, nonce
                        )
                        
                        if best_tx is None:
                            log_action("🛑", "ARB CANCEL", f"{sym} — No profitable size passed gas shield")
                            continue
                            
                        # استدعاء دالة الإطلاق المستقلة والآمنة لتفعيل وتأكيد المراجحة (تنفيذ نظام الحماية Dry Run)
                        is_success = execute_flash_loan(
                            sym=sym,
                            best_tx=best_tx,
                            best_size=best_size,
                            best_net_profit=best_net_profit,
                            final_spread=final_spread,
                            cheap_dex=cheap_dex,
                            exp_dex=exp_dex
                        )
                        
                        if is_success:
                            last_arbitrage_time = time.time()
                        
                        break
            except Exception as e:
                print(f"❌ حدث خطأ أثناء فحص/تنفيذ القناص المراجح: {e}")

            # ================================================================
            # 🚀 [V17 Parallel Engine] جلب بيانات كل العملات بالتوازي الكامل
            # ================================================================
            try:
                scan_results = list(_scan_executor.map(
                    fetch_coin_market_data, SUPPORTED_COINS.keys(), timeout=25
                ))
                coin_market_data = {r["symbol"]: r for r in scan_results if not r.get("error")}
            except Exception as _se:
                coin_market_data = {}

            for symbol in SUPPORTED_COINS.keys():
                if symbol not in coin_market_data:
                    continue

                _md        = coin_market_data[symbol]
                c_state    = state.coins[symbol]
                price      = _md["price"]
                rsi_matrix = _md["rsi_matrix"]
                rsi_15m, rsi_1h, rsi_4h = rsi_matrix["15m"], rsi_matrix["1h"], rsi_matrix["4h"]
                
                # 🆕 المؤشرات الاستراتيجية الجديدة
                macd_data = _md.get("macd", {})
                mtf_trend = _md.get("multi_tf_trend", {})
                atr_data = _md.get("atr", {})
                mev_data = _md.get("mev", {})
                elasticity_data = _md.get("elasticity", {})
                buy_signals = _md.get("buy_signals", 0)
                sell_signals = _md.get("sell_signals", 0)
                final_decision = _md.get("final_decision", "⚫ HOLD")
            
                # --- 📈 حساب نسبة الربح والخسارة اللحظية (PnL) ---
                pnl_pct = ((c_state.total_held * price - c_state.total_spent_usdt) / c_state.total_spent_usdt * 100) if c_state.total_spent_usdt > 0 else 0
                current_profit = pnl_pct / 100.0
                current_drop = (c_state.average_buy_price - price) / c_state.average_buy_price if c_state.average_buy_price > 0 else 0.0

                # --- 🎯 [لوحة الأهداف] - حساب ديناميكي باستخدام ATR ---
                avg_p = c_state.average_buy_price
                
                # إذا لم نكن لديها موضع: استخدم ATR للتنبؤ بنقاط الدخول/الخروج
                if avg_p == 0:
                    atr_sl = atr_data.get("stop_loss_price", price * 0.99)
                    atr_tp = atr_data.get("take_profit_price", price * 1.02)
                    target_buy = atr_sl
                    target_sell = atr_tp
                else:
                    # إذا كان لدينا موضع: استخدم ATR المحدث
                    atr_sl = atr_data.get("stop_loss_price", avg_p * 0.99)
                    atr_tp = atr_data.get("take_profit_price", avg_p * 1.02)
                    target_buy = atr_sl
                    target_sell = atr_tp

                display_target_sell = f"{target_sell:.2f}$"
                if c_state.trailing_active:
                    stop_price = c_state.highest_price * (1 - c_state.trailing_deviation)
                    display_target_sell = f"Trail: {stop_price:.2f}$"

                # --- 🕸️ شبكة العناكب (Grid Trading) ---
                grid_step_pct = 0.015
                if avg_p > 0:
                    current_grid_level = int(current_drop / grid_step_pct) if current_drop > 0 else 0
                    grid_buy_target = avg_p * (1 - (current_grid_level + 1) * grid_step_pct)
                    grid_sell_target = avg_p * (1 - (current_grid_level - 1) * grid_step_pct) if current_grid_level > 0 else avg_p * (1 + grid_step_pct)
                else:
                    current_grid_level = 0
                    grid_buy_target = price * (1 - grid_step_pct)
                    grid_sell_target = price * (1 + grid_step_pct)

                # جلب قوة السيولة
                liq_strength = _md.get("liq_strength", 1.0)
                liq_icon = "🟢" if liq_strength > 1.2 else "🔴" if liq_strength < 0.8 else "⚪"

                # --- 🩸 صائد التصفيات الدموية (Liquidation Hunter) ---
                elasticity = elasticity_data.get("elasticity", 0)
                is_dump = (elasticity < -6.0 and rsi_15m < 20)
                hunter_status = "🩸 DUMP!" if is_dump else "🛡️ Safe"

                # --- 🔮 محرك التنبؤ العميق (Deep Prediction) مع MACD و MTF ---
                price_slope = _md.get("price_slope", 0)
                
                # قرار مركب: MACD + Multi-TF + Price Slope
                if final_decision == "🟢 BUY":
                    prediction_forecast = f"🔮 📈 BUY (MACD: {macd_data.get('trend', 'FLAT')}, MTF: {mtf_trend.get('final_signal', 'HOLD')})"
                elif final_decision == "🔴 SELL":
                    prediction_forecast = f"🔮 📉 SELL (MACD: {macd_data.get('trend', 'FLAT')}, MTF: {mtf_trend.get('final_signal', 'HOLD')})"
                else:
                    prediction_forecast = "🔮 ⚖️ HOLD"


                latest_market_data["coins"][symbol] = {
                    "price": price,
                    "target_buy": target_buy,
                    "target_sell": target_sell,
                    "liq_strength": liq_strength,
                    "prediction_forecast": prediction_forecast,
                    "hunter_status": hunter_status,
                    "macd": macd_data,
                    "mtf_trend": mtf_trend,
                    "atr": atr_data,
                    "mev": mev_data,
                    "buy_signals": buy_signals,
                    "sell_signals": sell_signals
                }

                # --- 🚀 [التراكم الذكي v2] شرط الشراء المطور مع MACD و MEV ---
                if avg_p == 0 and not btc_crashed:
                    # شرط الشراء المركب
                    is_smart_buy = (
                        rsi_15m < 30 and 
                        rsi_1h < 45 and 
                        elasticity < -3.0 and
                        macd_data.get("trend") == "BULLISH" and
                        mtf_trend.get("final_signal") == "BUY" and
                        mev_data.get("is_safe", True)  # ✅ حماية MEV
                    )
                    
                    is_preemptive = (
                        liq_strength > 2.5 and 
                        rsi_15m < 45 and
                        buy_signals >= 2
                    )

                    if (is_smart_buy or is_preemptive) and mev_data.get("is_safe", True):
                        multiplier = get_smart_multiplier(rsi_1h, elasticity)
                        if is_dump:
                            multiplier *= 3.0
                        buy_amount = MIN_BUY_USD * multiplier
                        
                        if active_usdt_bal >= buy_amount:
                            buy_tag = "PREEMPTIVE" if is_preemptive else "SMART BUY"
                            macd_signal = macd_data.get("histogram", 0)
                            atr_sl_pct = atr_data.get("stop_loss_pct", 1.0)
                            
                            log_action(
                                "🐋", buy_tag, 
                                f"{symbol} | ${buy_amount:.2f} @ {price:.2f}$ | x{multiplier} | MACD: {macd_data.get('trend', 'N/A')} | SL: {atr_sl_pct:.2f}%"
                            )
                            
                            bot_msg = (
                                f"{'⚡ [PREEMPTIVE STRIKE BUY]' if is_preemptive else '🐋 [SMART BUY V2]'}\n"
                                f"العملة: {symbol}\n"
                                f"السعر: {price:.2f}$\n"
                                f"الشد: {elasticity:.2f}%\n"
                                f"MACD: {macd_data.get('trend', 'FLAT')} (Histogram: {macd_signal:.6f})\n"
                                f"Multi-TF: {mtf_trend.get('final_signal', 'HOLD')}\n"
                                f"ATR/SL: {atr_sl_pct:.2f}% | TP: {atr_data.get('take_profit_pct', 2.0):.2f}%\n"
                                f"القوة: x{multiplier}\n"
                                f"المبلغ: ${buy_amount:.2f}\n"
                                f"Signals: {buy_signals} BUY"
                            )
                            
                            bot.send_message(TELEGRAM_CHAT_ID, bot_msg)
                            
                        with state_lock:
                            c_state.last_auto_buy_level = 0
                            state.save()
                        trade_executor.submit(build_and_send_tx, TELEGRAM_CHAT_ID, "شراء", buy_amount, price, True, symbol)

                        
                        
                # --- 🪂 صائد القيعان (Trailing Buy) - محسّن ---
                if c_state.average_buy_price > 0 and not btc_crashed:
                    trend = get_macro_trend(symbol)
                    atr_mod = get_atr_volatility(symbol)
                    
                    possible_buys = [lvl for lvl in BUY_LADDER.keys() if current_drop >= (lvl * atr_mod) and lvl > c_state.last_auto_buy_level]
                    
                    # أضف شرط MACD والـ MTF Trend
                    macd_bullish = macd_data.get("trend") == "BULLISH"
                    mtf_bullish = mtf_trend.get("final_signal") == "BUY"
                    
                    if possible_buys and trend != "BEARISH" and (macd_bullish or mtf_bullish):
                        if not c_state.trailing_buy_active:
                            with state_lock:
                                c_state.trailing_buy_active = True
                                c_state.lowest_drop_pct = current_drop
                            state.save()
                            bot.send_message(TELEGRAM_CHAT_ID, f"🪂 [{symbol}] رادار القيعان نشط! نلاحق السعر للأسفل...")
                        
                        elif c_state.trailing_buy_active:
                            if current_drop > c_state.lowest_drop_pct:
                                c_state.lowest_drop_pct = current_drop
                            elif current_drop <= (c_state.lowest_drop_pct - (TRAILING_BUY_REBOUND_PCT/100)):
                                if analyze_sentiment_with_ai(symbol):
                                    next_buy_lvl = max(possible_buys)
                                    amount_to_buy = active_usdt_bal * BUY_LADDER[next_buy_lvl]
                                    if amount_to_buy >= MIN_BUY_USD:
                                        with state_lock:
                                            c_state.trailing_buy_active = False
                                            c_state.last_auto_buy_level = next_buy_lvl
                                        state.save()
                                        log_action("💥", "TRAIL BUY", f"{symbol} | Bottom caught! | ${amount_to_buy:.2f} @ {price:.2f}$")
                                        bot.send_message(TELEGRAM_CHAT_ID, f"💥 [{symbol}] تم صيد القاع! ارتداد مؤكد، جاري الشراء...")
                                        if symbol == "BNB":
                                            trade_executor.submit(build_and_send_tx, TELEGRAM_CHAT_ID, "شراء", amount_to_buy, price, True)
                                        else:
                                            bot.send_message(TELEGRAM_CHAT_ID, f"⚠️ جاري تجهيز عقد محاكاة الشراء لعملة {symbol}")

                # --- 📡 جني الأرباح المتحرك (Trailing Take Profit) ---
                if target_sell > 0 and price >= target_sell:
                    if not c_state.trailing_active:
                        with state_lock:
                            c_state.trailing_active = True
                            c_state.highest_price = price
                        state.save()
                        bot.send_message(TELEGRAM_CHAT_ID, f"🦅 [{symbol}] وصلنا للهدف {target_sell:.2f}$. تفعيل الملاحقة المتدرجة لجني أرباح أكبر...")

                if c_state.trailing_active:
                    if price > c_state.highest_price:
                        with state_lock:
                            c_state.highest_price = price
                        state.save()
                    
                    stop_price = c_state.highest_price * (1 - c_state.trailing_deviation)
                    if price <= stop_price:
                        now = time.time()
                        if now - c_state.last_auto_action_time >= COOLDOWN_SECONDS:
                            amount_usd = c_state.total_held * price
                            with state_lock:
                                c_state.last_auto_action_time = now
                                c_state.trailing_active = False
                                c_state.highest_price = 0.0
                            state.save()
                            pnl_at_sell = ((price - c_state.average_buy_price) / c_state.average_buy_price * 100) if c_state.average_buy_price > 0 else 0.0
                            net_usd_profit = amount_usd - (c_state.total_spent_usdt if c_state.total_spent_usdt > 0 else amount_usd)
                            log_action("💸", "TRAIL SELL", f"{symbol} | ${amount_usd:.2f} @ {price:.2f}$ | PnL: {pnl_at_sell:+.2f}%", net_profit=net_usd_profit)
                            bot.send_message(TELEGRAM_CHAT_ID, f"💸 [{symbol}] تم ضرب الوقف المتحرك! جني أرباح عند {price:.2f}$ (ملاحقة القمة). جاري البيع...")
                            trade_executor.submit(build_and_send_tx, TELEGRAM_CHAT_ID, "بيع", amount_usd, price, True, symbol)

                # ✅ [V17] لا انتظار بين العملات - التوازي يُغني عن الـ sleep

            # ─── رسم لوحة التحكم بعد اكتمال مسح كل العملات ──────────────────
            render_cockpit_dashboard(
                coin_market_data=coin_market_data,
                usdt_bal=usdt_bal,
                cpu_usage=cpu_usage,
                btc_crashed=btc_crashed,
                mode_str=mode_str
            )

            # طباعة التقرير الشامل (MACD و RSI) في الشاشة كما طلب المستخدم
            send_hourly_report(to_terminal=True)

        except Exception as e:
            print(f"\n{_R}[CRITICAL ERROR] Loop broken! Details: {e}{_RST}")
            log_action("❌", "LOOP ERROR", str(e)[:80])
            time.sleep(10)

        # فترة راحة المعالج - تخفيف الحمل على المعالج (CPU Relief)
        time.sleep(1)

# ==============================================================================
# ==============================================================================
# --- 12. BOOT SEQUENCE ---
# ==============================================================================
def boot_blockchain_checks():
    """🔥 Thread منفصلة لتفاصيل الـ blockchain (لا تحجب البدء الرئيسي)"""
    print('[DEBUG] [BOOT-BG] Starting blockchain permission checks in background...', flush=True)
    try:
        if not PAPER_TRADING:
            try:
                # مع timeout للحماية من التجمد
                print('[DEBUG] [BOOT-BG] Checking Blockchain Permissions...', flush=True)
                nonce = w3.eth.get_transaction_count(wallet_address)
                print(f'[DEBUG] [BOOT-BG] Nonce retrieved: {nonce}', flush=True)
                ensure_token_allowance(USDT_ADDR, w3.to_wei(MAX_APPROVE_USDT, 'ether'), nonce)
                print('[DEBUG] [BOOT-BG] ✅ Token allowance verified', flush=True)
            except Exception as e:
                print(f'[DEBUG] [BOOT-BG] ⚠️ Permission check failed (non-blocking): {e}')
        
        # تحميل الأرصدة الأولية (يجب أن يكون متاحاً قبل أول report)
        print('[DEBUG] [BOOT-BG] Pre-loading balances...', flush=True)
        try:
            usdt, bnb = get_balances()
            print(f'[DEBUG] [BOOT-BG] ✅ Initial balances loaded: USDT={usdt:.2f}, BNB={bnb:.6f}', flush=True)
        except Exception as e:
            print(f'[DEBUG] [BOOT-BG] ⚠️ Balance pre-load failed: {e}')
    
    except Exception as e:
        print(f'[DEBUG] [BOOT-BG] Unexpected error: {e}', flush=True)

if __name__ == "__main__":
    print('[DEBUG] [BOOT] 1. Starting Boot Sequence...', flush=True)
    
    # 🔥 الخطوة 1: ابدأ بـ initialization الأسعار (سريع جداً - 1-2 ثانية)
    print('[DEBUG] [BOOT] 2. Pre-warming price buffers...', flush=True)
    time.sleep(1)  # اعط وقتاً صغيراً لـ initialize_price_buffers لجلب البيانات
    
    # 🔥 الخطوة 2: ابدأ Telegram أولاً (بدون انتظار blockchain)
    print('[DEBUG] [BOOT] 3. Starting Telegram listener (NON-BLOCKING)...', flush=True)
    telegram_thread = threading.Thread(
        target=lambda: bot.infinity_polling(timeout=20, long_polling_timeout=10),
        daemon=True,
        name="TelegramLoopThread"
    )
    telegram_thread.start()
    
    # 🔥 الخطوة 3: بدء فحوصات الـ blockchain في الخلفية (لا تنتظر النتيجة)
    print('[DEBUG] [BOOT] 4. Starting blockchain checks in background...', flush=True)
    blockchain_thread = threading.Thread(
        target=boot_blockchain_checks,
        daemon=True,
        name="BlockchainBootThread"
    )
    blockchain_thread.start()
    
    # 🔥 الخطوة 4: انتظر قليلاً ثم أرسل بيانات البدء
    time.sleep(2)
    
    print("[DEBUG] [BOOT] 5. Pre-loading market data for first report...", flush=True)
    try:
        refresh_market_data_immediately()
        print("[DEBUG] [BOOT] ✅ Market data pre-loaded", flush=True)
    except Exception as e:
        print(f"[DEBUG] [BOOT] ⚠️ Pre-load failed (non-critical): {e}")

    print("[DEBUG] [BOOT] 6. Sending boot notification to owner...", flush=True)
    try:
        profit_loaded = load_total_profits()
        bot.send_message(
            TELEGRAM_CHAT_ID,
            f"🚀 **Whale Bot V17 Colossus — COCKPIT ONLINE!**\n"
            f"🖥️ لوحة تحكم المقصورة فعّالة\n"
            f"💰 إجمالي الأرباح المحفوظة: **${profit_loaded:+.4f}**\n"
            f"📡 الرادار يراقب {len(SUPPORTED_COINS)} هدفاً\n"
            f"⚡ محرك V17 Colossus جاهز للإقلاع!",
            timeout=10
        )
    except Exception as e:
        print(f"[DEBUG] [BOOT] ⚠️ Telegram notify failed: {e}")

    print("[DEBUG] [BOOT] 7. Entering Main Trading Engine...", flush=True)
    time.sleep(1)  # اعط وقتاً لـ price buffers لتجمع بعض البيانات
    auto_trading_loop()

