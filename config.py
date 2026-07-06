import logging
import threading
from logging.handlers import RotatingFileHandler

# ---- Logging ----
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        RotatingFileHandler("sai_app.log", maxBytes=5*1024*1024, backupCount=2),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# ---- Bot global config ----
BOT_CONFIG = {
    "alert_errors": False,
    "lock": threading.Lock()
}

# ---- Session state defaults ----
defaults = {
    "bot_thread": None, "bot_running": False,
    "rates": {}, "prev_rates": {},
    "bot_queue": None, "stop_event": None,
    "auto_refresh": False, "refresh_interval": 3,
    "trading_account": {"balance": 10000.0, "equity": 10000.0, "open_positions": [], "order_history": []},
    "auto_trade": False, "last_history_update": None, "risk_level": 5,
    "use_auto_arima": False,
    "live_rates_lock": threading.Lock(), "live_rates_data": {"rates": {}, "prev_rates": {}, "timestamp": None},
    "live_stream_thread": None, "live_stream_stop_event": None,
    "alert_signals": False, "alert_errors": False,
    "alert_threshold": 0.02,
    "db_initialised": False
}

# ---- Constants ----
HISTORY_MAX_ROWS = 2000
ALL_CURRENCIES = ["UGX", "KES", "TZS", "RWF", "BIF", "SSP", "ETB", "USD", "EUR", "GBP", "JPY"]
EAST_AFRICAN_CURRENCIES = ["UGX", "KES", "TZS", "RWF", "BIF", "SSP", "ETB"]
OTHER_CURRENCIES = ["USD", "EUR", "GBP", "JPY"]
DB_PATH = "sai_trading.db"

# ---- Custom CSS ----
CUSTOM_CSS = """
<style>
    .main {
        background: linear-gradient(135deg, #0a0a1a 0%, #111122 100%);
    }
    .stApp {
        background: transparent;
    }
    div[data-testid="stMetricValue"] {
        font-size: 2rem;
        font-weight: 700;
        background: linear-gradient(90deg, #00F2FE, #4FACFE);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        background-clip: text;
    }
    div[data-testid="stMetricLabel"] {
        font-size: 0.9rem;
        color: #BBBBBB;
        letter-spacing: 0.5px;
    }
    .forex-card {
        background: rgba(20, 20, 45, 0.6);
        backdrop-filter: blur(12px);
        border-radius: 20px;
        padding: 20px;
        margin: 8px 0;
        border: 1px solid rgba(255,255,255,0.15);
        box-shadow: 0 8px 32px rgba(0,0,0,0.3);
        transition: all 0.3s ease;
    }
    .forex-card:hover {
        border-color: #00F2FE;
        box-shadow: 0 8px 32px rgba(0,242,254,0.3);
        transform: translateY(-2px);
    }
    .currency-pair {
        font-size: 1.2rem;
        font-weight: 600;
        color: #E0E0E0;
        margin-bottom: 10px;
    }
    .rate-value {
        font-size: 2.5rem;
        font-weight: 700;
        color: #FFFFFF;
        text-shadow: 0 0 10px rgba(0,242,254,0.5);
    }
    .change-positive {
        color: #00C853;
        font-weight: 600;
    }
    .change-negative {
        color: #FF1744;
        font-weight: 600;
    }
    .section-title {
        font-size: 1.6rem;
        font-weight: 700;
        background: linear-gradient(90deg, #00F2FE, #4FACFE);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        background-clip: text;
        margin: 20px 0 10px 0;
        border-bottom: 2px solid rgba(0,242,254,0.3);
        padding-bottom: 5px;
        display: inline-block;
        letter-spacing: 0.5px;
    }
    .stButton > button {
        background: linear-gradient(90deg, #00F2FE 0%, #4FACFE 100%);
        color: #0a0a1a;
        font-weight: 700;
        border: none;
        border-radius: 12px;
        padding: 12px 24px;
        font-size: 1rem;
        letter-spacing: 0.5px;
        box-shadow: 0 4px 15px rgba(0,242,254,0.4);
        transition: all 0.3s ease;
    }
    .stButton > button:hover {
        transform: translateY(-3px);
        box-shadow: 0 8px 25px rgba(0,242,254,0.7);
    }
    [data-testid="stSidebar"] {
        background: rgba(10, 10, 26, 0.95);
        backdrop-filter: blur(10px);
    }
    .stTabs [data-baseweb="tab-list"] {
        gap: 10px;
        background: rgba(20,20,45,0.4);
        border-radius: 12px;
        padding: 5px;
    }
    .stTabs [data-baseweb="tab"] {
        border-radius: 8px;
        padding: 8px 16px;
        color: #CCCCCC;
        font-weight: 500;
    }
    .stTabs [aria-selected="true"] {
        background: linear-gradient(90deg, #00F2FE, #4FACFE) !important;
        color: black !important;
    }
    .streamlit-expanderHeader {
        background: rgba(20,20,45,0.6);
        border-radius: 12px;
        color: #00F2FE;
        font-weight: 600;
    }
    .stDataFrame {
        border-radius: 12px;
        overflow: hidden;
        border: 1px solid rgba(255,255,255,0.1);
    }
    ::-webkit-scrollbar { width: 6px; }
    ::-webkit-scrollbar-track { background: #0a0a1a; }
    ::-webkit-scrollbar-thumb { background: #00F2FE; border-radius: 3px; }
    @keyframes pulse {
        0% { box-shadow: 0 0 0 0 rgba(0,200,83,0.7); }
        70% { box-shadow: 0 0 0 10px rgba(0,200,83,0); }
        100% { box-shadow: 0 0 0 0 rgba(0,200,83,0); }
    }
    @media (max-width: 768px) {
        .forex-card { padding: 12px; margin: 4px 0; }
        .rate-value { font-size: 1.8rem; }
        .currency-pair { font-size: 1rem; }
        .section-title { font-size: 1.3rem; }
        .stButton > button { padding: 10px 20px; font-size: 0.9rem; }
    }
</style>
"""
