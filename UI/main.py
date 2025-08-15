# Modern UI for ValueVault
# This module will contain the main window and navigation logic for the new interface.

import sys
import os

from PyQt5 import QtWidgets, QtGui, QtCore
import sqlite3
import json
import urllib.request


def fetch_currency_rates(symbols=("USD", "EUR", "GBP")):
    """Fetch currency rates and return TL per currency from multiple APIs with fallback."""
    if not symbols:
        return {}

    # Try multiple APIs for better reliability
    apis = [
        # API 1: Fixer.io free tier
        {
            "url": "https://api.fixer.io/latest?base=EUR&symbols=USD,TRY,GBP",
            "parser": lambda data: _parse_fixer_rates(data, symbols)
        },
        # API 2: Exchange rates API
        {
            "url": "https://api.exchangerate-api.com/v4/latest/USD",
            "parser": lambda data: _parse_exchangerate_api_rates(data, symbols)
        },
        # API 3: Free currency API
        {
            "url": "https://api.currencyapi.com/v3/latest?apikey=cur_live_demo&currencies=USD,EUR,GBP,TRY",
            "parser": lambda data: _parse_currencyapi_rates(data, symbols)
        }
    ]
    
    for api in apis:
        try:
            req = urllib.request.Request(api["url"], headers={"User-Agent": "ValueVault/1.0"})
            with urllib.request.urlopen(req, timeout=5) as resp:
                data = json.loads(resp.read().decode("utf-8"))
            result = api["parser"](data)
            if result:  # If we got valid data, return it
                return result
        except Exception:
            continue  # Try next API
    
    # If all APIs fail, return fallback rates (approximate values)
    return {
        "USD": 34.15,
        "EUR": 37.20,
        "GBP": 43.50
    }

def _parse_fixer_rates(data, symbols):
    """Parse Fixer.io API response"""
    if not data.get("success", False):
        return {}
    rates = data.get("rates", {})
    try_rate = rates.get("TRY")
    if not try_rate:
        return {}
    
    result = {}
    for symbol in symbols:
        if symbol == "EUR":
            result[symbol] = try_rate  # EUR is base currency
        elif symbol in rates:
            # Convert: 1 symbol = ? TRY
            symbol_to_eur = 1.0 / rates[symbol]
            result[symbol] = symbol_to_eur * try_rate
    return result


def fetch_stock_quotes(symbols):
    """Fetch stock quotes from multiple APIs with fallback.

    Returns a list of dicts with keys: symbol, name, price, change, changePercent, currency.
    """
    if not symbols:
        return []
    
    # Try multiple APIs for better reliability
    apis = [
        # API 1: Yahoo Finance (primary)
        {
            "name": "Yahoo Finance",
            "fetcher": lambda syms: _fetch_yahoo_quotes(syms)
        },
        # API 2: Alpha Vantage demo (limited)
        {
            "name": "Alpha Vantage",
            "fetcher": lambda syms: _fetch_alphavantage_quotes(syms)
        },
        # API 3: Finnhub free tier
        {
            "name": "Finnhub",
            "fetcher": lambda syms: _fetch_finnhub_quotes(syms)
        }
    ]
    
    for api in apis:
        try:
            result = api["fetcher"](symbols)
            if result:  # If we got valid data, return it
                return result
        except Exception:
            continue  # Try next API
    
    # If all APIs fail, return mock data
    return _get_fallback_quotes(symbols)

def _fetch_yahoo_quotes(symbols, chunk_size=12):
    """Fetch from Yahoo Finance in chunks to avoid truncation and return all rows."""
    if not symbols:
        return []
    rows = []
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
    for i in range(0, len(symbols), chunk_size):
        joined = ",".join(symbols[i:i+chunk_size])
        url = f"https://query1.finance.yahoo.com/v7/finance/quote?symbols={joined}"
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=6) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        results = data.get("quoteResponse", {}).get("result", [])
        for item in results:
            rows.append({
                "symbol": item.get("symbol", "-"),
                "name": item.get("shortName") or item.get("longName") or item.get("symbol", "-"),
                "price": item.get("regularMarketPrice"),
                "change": item.get("regularMarketChange"),
                "changePercent": item.get("regularMarketChangePercent"),
                "currency": item.get("currency", "USD"),
            })
    return rows

def _fetch_alphavantage_quotes(symbols):
    """Fetch from Alpha Vantage (demo key, limited)"""
    rows = []
    for symbol in symbols[:3]:  # Limit to 3 to avoid rate limits
        try:
            url = f"https://www.alphavantage.co/query?function=GLOBAL_QUOTE&symbol={symbol}&apikey=demo"
            req = urllib.request.Request(url, headers={"User-Agent": "ValueVault/1.0"})
            with urllib.request.urlopen(req, timeout=4) as resp:
                data = json.loads(resp.read().decode("utf-8"))
            quote = data.get("Global Quote", {})
            if quote:
                price = float(quote.get("05. price", 0))
                change = float(quote.get("09. change", 0))
                change_pct = float(quote.get("10. change percent", "0%").replace("%", ""))
                rows.append({
                    "symbol": symbol,
                    "name": symbol,
                    "price": price,
                    "change": change,
                    "changePercent": change_pct,
                    "currency": "USD",
                })
        except Exception:
            continue
    return rows

def _fetch_finnhub_quotes(symbols):
    """Fetch from Finnhub free tier"""
    rows = []
    token = os.getenv("FINNHUB_TOKEN", "demo")  # .env/ortamdan al
    for symbol in symbols[:5]:  # Limit requests
        try:
            url = f"https://finnhub.io/api/v1/quote?symbol={symbol}&token={token}"
            req = urllib.request.Request(url, headers={"User-Agent": "ValueVault/1.0"})
            with urllib.request.urlopen(req, timeout=4) as resp:
                data = json.loads(resp.read().decode("utf-8"))
            if data.get("c"):  # current price exists
                current = float(data.get("c", 0))
                prev_close = float(data.get("pc", current))
                change = current - prev_close
                change_pct = (change / prev_close * 100) if prev_close > 0 else 0
                rows.append({
                    "symbol": symbol,
                    "name": symbol,
                    "price": current,
                    "change": change,
                    "changePercent": change_pct,
                    "currency": "USD",
                })
        except Exception:
            continue
    return rows

def _get_fallback_quotes(symbols):
    """Return mock data when all APIs fail"""
    import random
    rows = []
    base_prices = {
        "AAPL": 175.0, "MSFT": 380.0, "GOOGL": 140.0, "AMZN": 155.0,
        "NVDA": 875.0, "TSLA": 250.0, "BABA": 85.0, "META": 485.0,
        "NFLX": 450.0, "AMD": 145.0, "CRM": 220.0, "ORCL": 118.0
    }
    
    for symbol in symbols:
        base = base_prices.get(symbol, 100.0)
        # Add some random variation
        price = base + random.uniform(-5, 5)
        change = random.uniform(-2, 2)
        change_pct = (change / price) * 100
        
        rows.append({
            "symbol": symbol,
            "name": f"{symbol} Inc.",
            "price": round(price, 2),
            "change": round(change, 2),
            "changePercent": round(change_pct, 2),
            "currency": "USD",
        })
    return rows

def _parse_exchangerate_api_rates(data, symbols):
    """Parse exchangerate-api.com response"""
    rates = data.get("rates", {})
    try_rate = rates.get("TRY")
    if not try_rate:
        return {}
    
    result = {}
    for symbol in symbols:
        if symbol == "USD":
            result[symbol] = try_rate  # USD is base currency
        elif symbol in rates:
            # Convert: 1 symbol = ? TRY
            symbol_to_usd = 1.0 / rates[symbol]
            result[symbol] = symbol_to_usd * try_rate
    return result

def _parse_currencyapi_rates(data, symbols):
    """Parse currencyapi.com response"""
    rates_data = data.get("data", {})
    try_value = rates_data.get("TRY", {}).get("value")
    if not try_value:
        return {}
    
    result = {}
    for symbol in symbols:
        symbol_data = rates_data.get(symbol, {})
        symbol_value = symbol_data.get("value")
        if symbol_value:
            result[symbol] = try_value / symbol_value
    return result


def fetch_precious_metals():
    """Fetch precious metals prices from multiple APIs with fallback."""
    
    # Try multiple APIs for better reliability
    apis = [
        # API 1: MetalsAPI (free tier)
        {
            "url": "https://api.metals.live/v1/spot",
            "parser": lambda data: _parse_metals_live(data)
        },
        # API 2: Alternative API
        {
            "url": "https://api.goldapi.io/api/XAU/USD",
            "parser": lambda data: _parse_goldapi(data)
        }
    ]
    
    for api in apis:
        try:
            req = urllib.request.Request(api["url"], headers={"User-Agent": "ValueVault/1.0"})
            with urllib.request.urlopen(req, timeout=5) as resp:
                data = json.loads(resp.read().decode("utf-8"))
            result = api["parser"](data)
            if result:  # If we got valid data, return it
                return result
        except Exception:
            continue  # Try next API
    
    # If all APIs fail, return fallback prices (approximate values in USD)
    return _get_fallback_metals()

def _parse_metals_live(data):
    """Parse metals.live API response"""
    try:
        metals = {}
        if "gold" in data:
            metals["XAU"] = {"name": "Altın", "price": data["gold"], "unit": "ons", "currency": "USD"}
        if "silver" in data:
            metals["XAG"] = {"name": "Gümüş", "price": data["silver"], "unit": "ons", "currency": "USD"}
        if "platinum" in data:
            metals["XPT"] = {"name": "Platin", "price": data["platinum"], "unit": "ons", "currency": "USD"}
        if "palladium" in data:
            metals["XPD"] = {"name": "Paladyum", "price": data["palladium"], "unit": "ons", "currency": "USD"}
        return metals
    except Exception:
        return {}

def _parse_goldapi(data):
    """Parse goldapi.io response"""
    try:
        metals = {}
        if "price" in data:
            metals["XAU"] = {"name": "Altın", "price": data["price"], "unit": "ons", "currency": "USD"}
        return metals
    except Exception:
        return {}

def _get_fallback_metals():
    """Return mock precious metals data when all APIs fail"""
    return {
        "XAU": {"name": "Altın", "price": 2050.50, "unit": "ons", "currency": "USD"},
        "XAG": {"name": "Gümüş", "price": 24.75, "unit": "ons", "currency": "USD"},
        "XPT": {"name": "Platin", "price": 1025.80, "unit": "ons", "currency": "USD"},
        "XPD": {"name": "Paladyum", "price": 1150.30, "unit": "ons", "currency": "USD"}
    }


def fetch_crypto_prices():
    """Fetch cryptocurrency prices from multiple APIs with fallback."""
    
    # Try multiple APIs for better reliability
    apis = [
        # API 1: CoinGecko (free, no API key needed)
        {
            "url": "https://api.coingecko.com/api/v3/simple/price?ids=bitcoin,ethereum,binancecoin,cardano,solana,ripple,dogecoin,polygon,litecoin,chainlink,avalanche-2,uniswap&vs_currencies=usd&include_24hr_change=true",
            "parser": lambda data: _parse_coingecko_prices(data)
        },
        # API 2: CoinCap (backup)
        {
            "url": "https://api.coincap.io/v2/assets?limit=12",
            "parser": lambda data: _parse_coincap_prices(data)
        }
    ]
    
    for api in apis:
        try:
            req = urllib.request.Request(api["url"], headers={"User-Agent": "ValueVault/1.0"})
            with urllib.request.urlopen(req, timeout=5) as resp:
                data = json.loads(resp.read().decode("utf-8"))
            result = api["parser"](data)
            if result:  # If we got valid data, return it
                return result
        except Exception:
            continue  # Try next API
    
    # If all APIs fail, return fallback prices
    return _get_fallback_crypto()

def _parse_coingecko_prices(data):
    """Parse CoinGecko API response"""
    try:
        crypto_mapping = {
            "bitcoin": {"name": "Bitcoin", "symbol": "BTC"},
            "ethereum": {"name": "Ethereum", "symbol": "ETH"},
            "binancecoin": {"name": "BNB", "symbol": "BNB"},
            "cardano": {"name": "Cardano", "symbol": "ADA"},
            "solana": {"name": "Solana", "symbol": "SOL"},
            "ripple": {"name": "XRP", "symbol": "XRP"},
            "dogecoin": {"name": "Dogecoin", "symbol": "DOGE"},
            "polygon": {"name": "Polygon", "symbol": "MATIC"},
            "litecoin": {"name": "Litecoin", "symbol": "LTC"},
            "chainlink": {"name": "Chainlink", "symbol": "LINK"},
            "avalanche-2": {"name": "Avalanche", "symbol": "AVAX"},
            "uniswap": {"name": "Uniswap", "symbol": "UNI"}
        }
        
        cryptos = []
        for coin_id, coin_data in data.items():
            if coin_id in crypto_mapping:
                info = crypto_mapping[coin_id]
                price = coin_data.get("usd", 0)
                change_24h = coin_data.get("usd_24h_change", 0)
                
                cryptos.append({
                    "symbol": info["symbol"],
                    "name": info["name"],
                    "price": price,
                    "change24h": change_24h,
                    "currency": "USD"
                })
        
        return cryptos
    except Exception:
        return []

def _parse_coincap_prices(data):
    """Parse CoinCap API response"""
    try:
        cryptos = []
        assets = data.get("data", [])
        
        for asset in assets[:12]:  # Top 12
            price = float(asset.get("priceUsd", 0))
            change_24h = float(asset.get("changePercent24Hr", 0))
            
            cryptos.append({
                "symbol": asset.get("symbol", ""),
                "name": asset.get("name", ""),
                "price": price,
                "change24h": change_24h,
                "currency": "USD"
            })
        
        return cryptos
    except Exception:
        return []

def _get_fallback_crypto():
    """Return mock crypto data when all APIs fail"""
    return [
        {"symbol": "BTC", "name": "Bitcoin", "price": 65000.0, "change24h": 2.5, "currency": "USD"},
        {"symbol": "ETH", "name": "Ethereum", "price": 3200.0, "change24h": 1.8, "currency": "USD"},
        {"symbol": "BNB", "name": "BNB", "price": 580.0, "change24h": -0.5, "currency": "USD"},
        {"symbol": "ADA", "name": "Cardano", "price": 0.85, "change24h": 3.2, "currency": "USD"},
        {"symbol": "SOL", "name": "Solana", "price": 145.0, "change24h": -1.2, "currency": "USD"},
        {"symbol": "XRP", "name": "XRP", "price": 0.75, "change24h": 1.5, "currency": "USD"},
        {"symbol": "DOGE", "name": "Dogecoin", "price": 0.12, "change24h": 4.8, "currency": "USD"},
        {"symbol": "MATIC", "name": "Polygon", "price": 1.25, "change24h": 2.1, "currency": "USD"},
        {"symbol": "LTC", "name": "Litecoin", "price": 95.0, "change24h": -0.8, "currency": "USD"},
        {"symbol": "LINK", "name": "Chainlink", "price": 18.5, "change24h": 1.9, "currency": "USD"},
        {"symbol": "AVAX", "name": "Avalanche", "price": 42.0, "change24h": -2.1, "currency": "USD"},
        {"symbol": "UNI", "name": "Uniswap", "price": 11.8, "change24h": 0.7, "currency": "USD"}
    ]


class NumpadWidget(QtWidgets.QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.password = ""
        self.max_length = 4  # 4 haneli şifre
        self.parent_dialog = None  # Dialog referansı
        self.setupUI()
    
    def setupUI(self):
        layout = QtWidgets.QVBoxLayout(self)
        layout.setSpacing(12)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # Şifre gösterim alanı
        self.password_display = QtWidgets.QLabel("Şifre Girin")
        self.password_display.setAlignment(QtCore.Qt.AlignCenter)
        self.password_display.setStyleSheet("""
            QLabel {
                background: #f8fafc;
                color: #1f2937;
                border: 2px solid #e5e7eb;
                border-radius: 12px;
                padding: 16px;
                font-size: 18px;
                font-weight: 600;
                letter-spacing: 4px;
                min-height: 20px;
            }
        """)
        layout.addWidget(self.password_display)
        
        # Numpad grid
        numpad_container = QtWidgets.QWidget()
        numpad_layout = QtWidgets.QGridLayout(numpad_container)
        numpad_layout.setSpacing(8)
        numpad_layout.setContentsMargins(0, 0, 0, 0)
        
        # Sayı butonları (1-9)
        for i in range(1, 10):
            btn = self.create_numpad_button(str(i))
            row = (i - 1) // 3
            col = (i - 1) % 3
            numpad_layout.addWidget(btn, row, col)
        
        # Alt sıra: Temizle, 0, Sil
        clear_btn = self.create_numpad_button("C", special=True)
        clear_btn.clicked.connect(self.clear_password)
        numpad_layout.addWidget(clear_btn, 3, 0)
        
        zero_btn = self.create_numpad_button("0")
        numpad_layout.addWidget(zero_btn, 3, 1)
        
        delete_btn = self.create_numpad_button("⌫", special=True)
        delete_btn.clicked.connect(self.delete_last)
        numpad_layout.addWidget(delete_btn, 3, 2)
        
        layout.addWidget(numpad_container)
        
    def create_numpad_button(self, text, special=False):
        btn = QtWidgets.QPushButton(text)
        btn.setFixedSize(70, 70)
        btn.setCursor(QtCore.Qt.PointingHandCursor)
        
        if special:
            btn.setStyleSheet("""
                QPushButton {
                    background: #f3f4f6;
                    color: #6b7280;
                    border: 2px solid #e5e7eb;
                    border-radius: 12px;
                    font-size: 16px;
                    font-weight: 600;
                }
                QPushButton:hover {
                    background: #e5e7eb;
                    border: 2px solid #d1d5db;
                }
                QPushButton:pressed {
                    background: #d1d5db;
                    border: 3px solid #d1d5db;
                }
            """)
        else:
            btn.setStyleSheet("""
                QPushButton {
                    background: white;
                    color: #1f2937;
                    border: 2px solid #e5e7eb;
                    border-radius: 12px;
                    font-size: 20px;
                    font-weight: 700;
                }
                QPushButton:hover {
                    background: #3b82f6;
                    color: white;
                    border: 2px solid #3b82f6;
                }
                QPushButton:pressed {
                    background: #2563eb;
                    border: 3px solid #2563eb;
                }
            """)
            btn.clicked.connect(lambda checked=False, digit=text: self.add_digit(digit))
        
        return btn
    
    def add_digit(self, digit):
        if len(self.password) < self.max_length:
            self.password += digit
            self.update_display()
            
            # 4. rakam girilince otomatik kapat
            if len(self.password) == self.max_length and self.parent_dialog:
                # Kısa bir gecikme ile kapatma (kullanıcı son rakamı görsün)
                QtCore.QTimer.singleShot(300, self.parent_dialog.accept)
    
    def delete_last(self):
        if self.password:
            self.password = self.password[:-1]
            self.update_display()
    
    def clear_password(self):
        self.password = ""
        self.update_display()
    
    def update_display(self):
        if self.password:
            # Şifreyi gizlemek için yıldız kullan
            display_text = "●" * len(self.password)
        else:
            display_text = "Şifre Girin"
        self.password_display.setText(display_text)
    
    def get_password(self):
        return self.password


class PasswordNumpadDialog(QtWidgets.QDialog):
    def __init__(self, parent=None, max_length=4):  # 4 haneli şifre için
        super().__init__(parent)
        self.setModal(True)
        self.setWindowFlags(QtCore.Qt.FramelessWindowHint | QtCore.Qt.Dialog)
        self.setAttribute(QtCore.Qt.WA_TranslucentBackground)

        root = QtWidgets.QVBoxLayout(self)
        root.setContentsMargins(0,0,0,0)
        root.addStretch()
        row = QtWidgets.QHBoxLayout()
        row.addStretch()

        card = QtWidgets.QFrame()
        card.setStyleSheet("QFrame { background: white; border-radius: 16px; }")
        card.setFixedSize(300, 480)
        v = QtWidgets.QVBoxLayout(card)
        v.setContentsMargins(12,12,12,12)
        v.setSpacing(6)

        title = QtWidgets.QLabel("Şifre")
        title.setAlignment(QtCore.Qt.AlignCenter)
        title.setStyleSheet("color:#111827; font-size:18px; font-weight:700;")
        v.addWidget(title)

        self.numpad = NumpadWidget()
        self.numpad.max_length = max_length
        self.numpad.parent_dialog = self  # Dialog referansını ver
        v.addWidget(self.numpad)

        btns = QtWidgets.QHBoxLayout()
        ok = QtWidgets.QPushButton("Tamam")
        cancel = QtWidgets.QPushButton("İptal")
        
        ok.setStyleSheet("""
            QPushButton {
                background: #3b82f6;
                color: white;
                border: none;
                border-radius: 8px;
                padding: 12px;
                font-size: 14px;
                font-weight: 600;
            }
            QPushButton:hover {
                background: #2563eb;
            }
        """)
        
        cancel.setStyleSheet("""
            QPushButton {
                background: #f9fafb;
                color: #6b7280;
                border: 1px solid #e5e7eb;
                border-radius: 8px;
                padding: 12px;
                font-size: 14px;
                font-weight: 500;
            }
            QPushButton:hover {
                background: #f3f4f6;
                color: #374151;
            }
        """)
        
        ok.setCursor(QtCore.Qt.PointingHandCursor)
        cancel.setCursor(QtCore.Qt.PointingHandCursor)
        ok.clicked.connect(self.accept)
        cancel.clicked.connect(self.reject)
        btns.addWidget(ok)
        btns.addWidget(cancel)
        v.addLayout(btns)

        row.addWidget(card)
        row.addStretch()
        root.addLayout(row)
        root.addStretch()
        self.setStyleSheet("QDialog { background: rgba(0,0,0,0.45); }")

    def value(self):
        return self.numpad.get_password()


class AppMessageDialog(QtWidgets.QDialog):
    def __init__(self, parent, title, message, level="info", buttons=None):
        super().__init__(parent)
        self.setModal(True)
        self.setWindowFlags(QtCore.Qt.FramelessWindowHint | QtCore.Qt.Dialog)
        self.setAttribute(QtCore.Qt.WA_TranslucentBackground)
        self.result_value = None

        if buttons is None:
            buttons = ["Tamam"]

        # Make dialog overlay the parent
        if parent is not None:
            self.resize(parent.width(), parent.height())
            self.move(parent.mapToGlobal(QtCore.QPoint(0, 0)))

        overlay_layout = QtWidgets.QVBoxLayout(self)
        overlay_layout.setContentsMargins(0, 0, 0, 0)

        # Spacer to center vertically
        overlay_layout.addStretch()

        # Center horizontally
        center_row = QtWidgets.QHBoxLayout()
        center_row.addStretch()

        # Card
        card = QtWidgets.QFrame()
        card.setFixedWidth(360)
        card.setStyleSheet("""
            QFrame {
                background: white;
                border-radius: 16px;
            }
        """)
        card_layout = QtWidgets.QVBoxLayout(card)
        card_layout.setContentsMargins(20, 20, 20, 20)
        card_layout.setSpacing(14)

        title_lbl = QtWidgets.QLabel(title)
        title_lbl.setAlignment(QtCore.Qt.AlignCenter)
        title_lbl.setStyleSheet("color: #111827; font-size: 18px; font-weight: 700;")
        card_layout.addWidget(title_lbl)

        # Icon and message
        icon_char = {
            "info": "ℹ️",
            "warning": "⚠️",
            "error": "⛔",
            "success": "✅",
            "question": "❓"
        }.get(level, "ℹ️")

        icon_lbl = QtWidgets.QLabel(icon_char)
        icon_lbl.setAlignment(QtCore.Qt.AlignCenter)
        icon_lbl.setStyleSheet("font-size: 28px;")
        card_layout.addWidget(icon_lbl)

        msg_lbl = QtWidgets.QLabel(message)
        msg_lbl.setWordWrap(True)
        msg_lbl.setAlignment(QtCore.Qt.AlignCenter)
        msg_lbl.setStyleSheet("color: #374151; font-size: 14px;")
        card_layout.addWidget(msg_lbl)

        # Buttons
        btn_row = QtWidgets.QHBoxLayout()
        btn_row.addStretch()
        for btext in buttons:
            btn = QtWidgets.QPushButton(btext)
            btn.setCursor(QtCore.Qt.PointingHandCursor)
            btn.setFixedHeight(36)
            btn.setStyleSheet("""
                QPushButton {
                    background: #1e40af;
                    color: white;
                    border: none;
                    border-radius: 8px;
                    padding: 0 16px;
                    font-weight: 600;
                }
                QPushButton:hover { background: #1b3a99; }
            """)
            btn.clicked.connect(lambda checked=False, t=btext: self._on_button(t))
            btn_row.addWidget(btn)
        btn_row.addStretch()
        card_layout.addLayout(btn_row)

        center_row.addWidget(card)
        center_row.addStretch()
        overlay_layout.addLayout(center_row)

        # Spacer bottom
        overlay_layout.addStretch()

        # Dim background via stylesheet
        self.setStyleSheet("QDialog { background: rgba(0,0,0,0.45); }")

    def _on_button(self, text):
        self.result_value = text
        self.accept()

    @staticmethod
    def show_info(parent, title, message):
        dlg = AppMessageDialog(parent, title, message, level="info", buttons=["Tamam"])
        dlg.exec_()
        return True

    @staticmethod
    def show_success(parent, title, message):
        dlg = AppMessageDialog(parent, title, message, level="success", buttons=["Tamam"])
        dlg.exec_()
        return True

    @staticmethod
    def show_warning(parent, title, message):
        dlg = AppMessageDialog(parent, title, message, level="warning", buttons=["Tamam"])
        dlg.exec_()
        return True

    @staticmethod
    def show_error(parent, title, message):
        dlg = AppMessageDialog(parent, title, message, level="error", buttons=["Tamam"])
        dlg.exec_()
        return True

    @staticmethod
    def show_question(parent, title, message):
        dlg = AppMessageDialog(parent, title, message, level="question", buttons=["Evet", "Hayır"])
        dlg.exec_()
        return dlg.result_value == "Evet"


class StockListDialog(QtWidgets.QDialog):
    def __init__(self, parent, quotes):
        super().__init__(parent)
        self.setModal(True)
        self.setWindowFlags(QtCore.Qt.FramelessWindowHint | QtCore.Qt.Dialog)
        self.setAttribute(QtCore.Qt.WA_TranslucentBackground)

        # full overlay sized to parent
        if parent is not None:
            self.resize(parent.width(), parent.height())
            self.move(parent.mapToGlobal(QtCore.QPoint(0, 0)))

        root = QtWidgets.QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.addStretch()

        row = QtWidgets.QHBoxLayout()
        row.addStretch()

        card = QtWidgets.QFrame()
        card.setStyleSheet("QFrame { background: white; border-radius: 16px; }")
        card.setFixedSize(500, 600)  # Daha büyük boyut
        v = QtWidgets.QVBoxLayout(card)
        v.setContentsMargins(16, 16, 16, 16)
        v.setSpacing(10)

        title = QtWidgets.QLabel("Hisse Senetleri")
        title.setAlignment(QtCore.Qt.AlignCenter)
        title.setStyleSheet("color:#111827; font-size:18px; font-weight:700;")
        v.addWidget(title)

        table = QtWidgets.QTableWidget()
        table.setColumnCount(5)
        table.setHorizontalHeaderLabels(["Sembol", "Ad", "Fiyat", "Değişim", "% Değişim"])
        table.horizontalHeader().setStretchLastSection(True)
        table.horizontalHeader().setSectionResizeMode(QtWidgets.QHeaderView.Stretch)
        table.setEditTriggers(QtWidgets.QAbstractItemView.NoEditTriggers)
        table.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)
        table.setAlternatingRowColors(True)
        
        # Kaydırma çubuklarını etkinleştir
        table.setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarAsNeeded)
        table.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAsNeeded)
        table.setMinimumHeight(460)  # ekranda daha çok satır görünsün
        
        table.setStyleSheet("""
            QTableWidget { 
                background: white; 
                color: #111827; 
                gridline-color: #e5e7eb;
                font-size: 12px;
            }
            QHeaderView::section { 
                background: #f3f4f6; 
                padding: 6px; 
                border: none; 
                font-weight: 600; 
                font-size: 12px;
            }
            QTableWidget::item { 
                padding: 6px; 
                border-bottom: 1px solid #f3f4f6;
            }
        """)

        table.setRowCount(len(quotes))
        for r, q in enumerate(quotes):
            symbol_item = QtWidgets.QTableWidgetItem(str(q.get("symbol", "-")))
            name_item = QtWidgets.QTableWidgetItem(str(q.get("name", "-")))
            price_val = q.get("price")
            price_item = QtWidgets.QTableWidgetItem("-" if price_val is None else f"{price_val:.2f} {q.get('currency','')}")
            change_val = q.get("change")
            change_item = QtWidgets.QTableWidgetItem("-" if change_val is None else f"{change_val:+.2f}")
            pct_val = q.get("changePercent")
            pct_item = QtWidgets.QTableWidgetItem("-" if pct_val is None else f"{pct_val:+.2f}%")

            # colorize change
            if isinstance(change_val, (int, float)):
                color = "#10b981" if change_val >= 0 else "#ef4444"
                change_item.setForeground(QtGui.QBrush(QtGui.QColor(color)))
                pct_item.setForeground(QtGui.QBrush(QtGui.QColor(color)))

            table.setItem(r, 0, symbol_item)
            table.setItem(r, 1, name_item)
            table.setItem(r, 2, price_item)
            table.setItem(r, 3, change_item)
            table.setItem(r, 4, pct_item)

        # Tablonun boyutunu içeriğe göre ayarla
        table.resizeRowsToContents()
        table.resizeColumnsToContents()
        
        v.addWidget(table)

        btn_row = QtWidgets.QHBoxLayout()
        btn_row.addStretch()
        close_btn = QtWidgets.QPushButton("Kapat")
        close_btn.setFixedHeight(36)
        close_btn.setCursor(QtCore.Qt.PointingHandCursor)
        close_btn.setStyleSheet("QPushButton { background: #1e40af; color: white; border: none; border-radius: 8px; padding: 0 16px; font-weight: 600; }")
        close_btn.clicked.connect(self.accept)
        btn_row.addWidget(close_btn)
        btn_row.addStretch()
        v.addLayout(btn_row)

        row.addWidget(card)
        row.addStretch()
        root.addLayout(row)
        root.addStretch()
        self.setStyleSheet("QDialog { background: rgba(0,0,0,0.45); }")


class CryptoListDialog(QtWidgets.QDialog):
    def __init__(self, parent, cryptos):
        super().__init__(parent)
        self.setModal(True)
        self.setWindowFlags(QtCore.Qt.FramelessWindowHint | QtCore.Qt.Dialog)
        self.setAttribute(QtCore.Qt.WA_TranslucentBackground)

        # full overlay sized to parent
        if parent is not None:
            self.resize(parent.width(), parent.height())
            self.move(parent.mapToGlobal(QtCore.QPoint(0, 0)))

        root = QtWidgets.QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.addStretch()

        row = QtWidgets.QHBoxLayout()
        row.addStretch()

        card = QtWidgets.QFrame()
        card.setStyleSheet("QFrame { background: white; border-radius: 16px; }")
        card.setFixedSize(540, 650)
        v = QtWidgets.QVBoxLayout(card)
        v.setContentsMargins(16, 16, 16, 16)
        v.setSpacing(10)

        title = QtWidgets.QLabel("💰 Kripto Para Borsası")
        title.setAlignment(QtCore.Qt.AlignCenter)
        title.setStyleSheet("color:#111827; font-size:18px; font-weight:700;")
        v.addWidget(title)

        table = QtWidgets.QTableWidget()
        table.setColumnCount(4)
        table.setHorizontalHeaderLabels(["Sembol", "Ad", "Fiyat", "24h %"])
        table.horizontalHeader().setStretchLastSection(True)
        table.horizontalHeader().setSectionResizeMode(QtWidgets.QHeaderView.Stretch)
        table.setEditTriggers(QtWidgets.QAbstractItemView.NoEditTriggers)
        table.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)
        table.setAlternatingRowColors(True)
        
        table.setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarAsNeeded)
        table.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAsNeeded)
        table.setMinimumHeight(480)
        
        table.setStyleSheet("""
            QTableWidget { 
                background: white; 
                color: #111827; 
                gridline-color: #e5e7eb;
                font-size: 12px;
            }
            QHeaderView::section { 
                background: #f3f4f6; 
                padding: 8px; 
                border: none; 
                font-weight: 600; 
                font-size: 12px;
            }
            QTableWidget::item { 
                padding: 8px; 
                border-bottom: 1px solid #f3f4f6;
            }
        """)

        table.setRowCount(len(cryptos))
        for r, crypto in enumerate(cryptos):
            symbol_item = QtWidgets.QTableWidgetItem(str(crypto.get("symbol", "-")))
            name_item = QtWidgets.QTableWidgetItem(str(crypto.get("name", "-")))
            
            price_val = crypto.get("price")
            if price_val is not None:
                if price_val >= 1:
                    price_text = f"${price_val:,.2f}"
                else:
                    price_text = f"${price_val:.6f}"
            else:
                price_text = "-"
            price_item = QtWidgets.QTableWidgetItem(price_text)
            
            change_val = crypto.get("change24h")
            if change_val is not None:
                change_text = f"{change_val:+.2f}%"
            else:
                change_text = "-"
            change_item = QtWidgets.QTableWidgetItem(change_text)

            # colorize change
            if isinstance(change_val, (int, float)):
                color = "#10b981" if change_val >= 0 else "#ef4444"
                change_item.setForeground(QtGui.QBrush(QtGui.QColor(color)))

            table.setItem(r, 0, symbol_item)
            table.setItem(r, 1, name_item)
            table.setItem(r, 2, price_item)
            table.setItem(r, 3, change_item)

        table.resizeRowsToContents()
        table.resizeColumnsToContents()
        
        v.addWidget(table)

        btn_row = QtWidgets.QHBoxLayout()
        btn_row.addStretch()
        close_btn = QtWidgets.QPushButton("Kapat")
        close_btn.setFixedHeight(36)
        close_btn.setCursor(QtCore.Qt.PointingHandCursor)
        close_btn.setStyleSheet("QPushButton { background: #1e40af; color: white; border: none; border-radius: 8px; padding: 0 16px; font-weight: 600; }")
        close_btn.clicked.connect(self.accept)
        btn_row.addWidget(close_btn)
        btn_row.addStretch()
        v.addLayout(btn_row)

        row.addWidget(card)
        row.addStretch()
        root.addLayout(row)
        root.addStretch()
        self.setStyleSheet("QDialog { background: rgba(0,0,0,0.45); }")


class AppNumberInputDialog(QtWidgets.QDialog):
    def __init__(self, parent, title, label, minimum=0, maximum=10**9, value=None):
        super().__init__(parent)
        self.setModal(True)
        self.setWindowFlags(QtCore.Qt.FramelessWindowHint | QtCore.Qt.Dialog)
        self.setAttribute(QtCore.Qt.WA_TranslucentBackground)
        self.ok = False

        if parent is not None:
            self.resize(parent.width(), parent.height())
            self.move(parent.mapToGlobal(QtCore.QPoint(0, 0)))

        overlay_layout = QtWidgets.QVBoxLayout(self)
        overlay_layout.setContentsMargins(0, 0, 0, 0)
        overlay_layout.addStretch()

        center_row = QtWidgets.QHBoxLayout()
        center_row.addStretch()

        card = QtWidgets.QFrame()
        card.setFixedWidth(360)
        card.setStyleSheet("QFrame { background: white; border-radius: 16px; }")
        v = QtWidgets.QVBoxLayout(card)
        v.setContentsMargins(20, 20, 20, 20)
        v.setSpacing(14)

        title_lbl = QtWidgets.QLabel(title)
        title_lbl.setAlignment(QtCore.Qt.AlignCenter)
        title_lbl.setStyleSheet("color: #111827; font-size: 18px; font-weight: 700;")
        v.addWidget(title_lbl)

        label_lbl = QtWidgets.QLabel(label)
        label_lbl.setAlignment(QtCore.Qt.AlignCenter)
        label_lbl.setStyleSheet("color: #374151; font-size: 14px;")
        v.addWidget(label_lbl)

        self.spin = QtWidgets.QSpinBox()
        self.spin.setRange(minimum, maximum)
        if value is not None:
            self.spin.setValue(value)
        self.spin.setFixedHeight(40)
        self.spin.setStyleSheet("""
            QSpinBox { background: white; color: #111827; border: 1px solid #e5e7eb; border-radius: 8px; padding: 6px 10px; }
            QSpinBox:focus { border: 2px solid #3b82f6; }
        """)
        v.addWidget(self.spin)

        btn_row = QtWidgets.QHBoxLayout()
        btn_row.addStretch()
        ok_btn = QtWidgets.QPushButton("Tamam")
        ok_btn.setCursor(QtCore.Qt.PointingHandCursor)
        ok_btn.setFixedHeight(36)
        ok_btn.setStyleSheet("QPushButton { background: #1e40af; color: white; border: none; border-radius: 8px; padding: 0 16px; font-weight: 600; }")
        ok_btn.clicked.connect(self._accept)
        cancel_btn = QtWidgets.QPushButton("İptal")
        cancel_btn.setCursor(QtCore.Qt.PointingHandCursor)
        cancel_btn.setFixedHeight(36)
        cancel_btn.setStyleSheet("QPushButton { background: #e5e7eb; color: #374151; border: none; border-radius: 8px; padding: 0 16px; font-weight: 600; }")
        cancel_btn.clicked.connect(self.reject)
        btn_row.addWidget(ok_btn)
        btn_row.addWidget(cancel_btn)
        btn_row.addStretch()
        v.addLayout(btn_row)

        center_row.addWidget(card)
        center_row.addStretch()
        overlay_layout.addLayout(center_row)
        overlay_layout.addStretch()
        self.setStyleSheet("QDialog { background: rgba(0,0,0,0.45); }")

    def _accept(self):
        self.ok = True
        self.accept()

    @staticmethod
    def get_int(parent, title, label, minimum=0, maximum=10**9, value=None):
        dlg = AppNumberInputDialog(parent, title, label, minimum, maximum, value)
        dlg.exec_()
        return dlg.spin.value(), dlg.ok


class Customer:
    def __init__(self, id, password, name, balance=0, investment_balance=0):
        self.id = id
        self.password = password
        self.name = name
        self.balance = balance
        self.investment_balance = investment_balance

class ModernMainWindow(QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("ValueVault - Mobile Banking")
        self.setGeometry(100, 100, 420, 760)
        self.setMinimumSize(350, 600)
        self.setStyleSheet("""
            QMainWindow {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, 
                    stop:0 #1e40af, stop:0.7 #3b82f6, stop:1 #60a5fa);
            }
        """)
        # Set application/window icon
        self.icon_path = os.path.normpath(os.path.join(os.path.dirname(__file__), '..', 'Images', 'logo.png'))
        if os.path.exists(self.icon_path):
            self.setWindowIcon(QtGui.QIcon(self.icon_path))
        self.current_customer = None
        self.database_path = os.path.join(os.path.dirname(__file__), '..', 'App', 'database.db')
        self.setup_database()
        self.initUI()

    def setup_database(self):
        """Setup database and create admin account if it doesn't exist"""
        try:
            conn = sqlite3.connect(self.database_path)
            cursor = conn.cursor()
            
            # Create customers table if it doesn't exist
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS customers (
                    id TEXT PRIMARY KEY,
                    password TEXT,
                    name TEXT,
                    balance INTEGER DEFAULT 0,
                    investment_balance INTEGER DEFAULT 0
                )
            ''')
            
            # Ensure investment_balance column exists
            cursor.execute("PRAGMA table_info(customers)")
            cols = [r[1] for r in cursor.fetchall()]
            if "investment_balance" not in cols:
                cursor.execute("ALTER TABLE customers ADD COLUMN investment_balance INTEGER DEFAULT 0")
            
            # Create transactions table if it doesn't exist
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS transactions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    customer_id TEXT,
                    transaction_type TEXT,
                    amount INTEGER,
                    target_customer TEXT,
                    description TEXT,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (customer_id) REFERENCES customers (id)
                )
            ''')
            
            # Check if admin account exists
            cursor.execute('SELECT id FROM customers WHERE id = ?', ('admin',))
            admin_exists = cursor.fetchone()
            
            # Create admin account if it doesn't exist
            if not admin_exists:
                cursor.execute('''
                    INSERT INTO customers (id, password, name, balance, investment_balance) 
                    VALUES (?, ?, ?, ?, ?)
                ''', ('admin', '1234', 'Administrator', 100000, 50000))
                print("Admin hesabı oluşturuldu: admin/1234")
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            print(f"Database setup error: {e}")

    def initUI(self):
        # Set font
        font = QtGui.QFont("Segoe UI", 10)
        self.setFont(font)

        # Central widget and layout
        central = QtWidgets.QWidget()
        self.setCentralWidget(central)
        main_layout = QtWidgets.QVBoxLayout(central)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # Top blue section with welcome and bank icon
        top_section = QtWidgets.QWidget()
        top_section.setStyleSheet("background: transparent;")
        top_section.setFixedHeight(320)
        top_layout = QtWidgets.QVBoxLayout(top_section)
        top_layout.setContentsMargins(40, 60, 40, 40)
        top_layout.setSpacing(30)

        # Welcome text
        welcome_label = QtWidgets.QLabel("ValueVault")
        welcome_label.setStyleSheet("""
            color: white;
            font-size: 28px;
            font-weight: bold;
            letter-spacing: 2px;
        """)
        welcome_label.setAlignment(QtCore.Qt.AlignCenter)
        top_layout.addWidget(welcome_label)

        # Bank icon container
        icon_container = QtWidgets.QFrame()
        icon_container.setFixedSize(96, 96)
        icon_container.setStyleSheet("""
            QFrame {
                background: transparent;  
                border: none;             
                border-radius: 0px;        
            }
        """)
        
        icon_layout = QtWidgets.QVBoxLayout(icon_container)
        icon_layout.setContentsMargins(0, 0, 0, 0)
        
        logo_label = QtWidgets.QLabel()
        logo_pixmap = QtGui.QPixmap(getattr(self, 'icon_path', ''))
        if not logo_pixmap.isNull():
            logo_label.setPixmap(logo_pixmap.scaled(160, 200, QtCore.Qt.KeepAspectRatio, QtCore.Qt.SmoothTransformation))
        else:
            logo_label.setText("🏦")
            logo_label.setStyleSheet("""
                color: #1e40af;
                font-size: 40px;
            """)
        logo_label.setAlignment(QtCore.Qt.AlignCenter)
        icon_layout.addWidget(logo_label)
        
        # Center the icon container
        icon_wrapper = QtWidgets.QHBoxLayout()
        icon_wrapper.addStretch()
        icon_wrapper.addWidget(icon_container)
        icon_wrapper.addStretch()
        top_layout.addLayout(icon_wrapper)
        
        top_layout.addStretch()
        main_layout.addWidget(top_section)

        # White bottom section with form
        bottom_section = QtWidgets.QWidget()
        bottom_section.setStyleSheet("""
            QWidget {
                background: white;
                border-top-left-radius: 30px;
                border-top-right-radius: 30px;
            }
        """)
        bottom_layout = QtWidgets.QVBoxLayout(bottom_section)
        bottom_layout.setContentsMargins(40, 40, 40, 40)
        bottom_layout.setSpacing(20)

        # Username input
        self.username = QtWidgets.QLineEdit()
        self.username.setPlaceholderText("Kullanıcı Adı")
        self.username.setStyleSheet(self.mobile_input_style())
        self.username.setFixedHeight(50)
        bottom_layout.addWidget(self.username)

        # Şifre alanı (tıkla -> numpad aç)
        self.password = QtWidgets.QLineEdit()
        self.password.setPlaceholderText("Şifre (dokun ve numpad açılır)")
        self.password.setEchoMode(QtWidgets.QLineEdit.Password)
        self.password.setReadOnly(True)
        self.password.setStyleSheet(self.mobile_input_style())
        self.password.setFixedHeight(50)
        bottom_layout.addWidget(self.password)

        # Diyalogdan dönen gerçek şifre burada tutulacak
        self._password_value = ""

        # Tıklama ile numpad aç
        def _open_password_numpad(event=None):
            dlg = PasswordNumpadDialog(self, max_length=4)  # 4 haneli şifre
            if dlg.exec_() == QtWidgets.QDialog.Accepted:
                self._password_value = dlg.value() or ""
                # EchoMode=Password olduğu için maskelenmiş görünecek:
                self.password.setText(self._password_value)
            # QLineEdit'in normal davranışı bozulmasın:
            if event is not None:
                QtWidgets.QLineEdit.mousePressEvent(self.password, event)

        # QLineEdit'e tıklama handler'ını bağla
        self.password.mousePressEvent = _open_password_numpad

        # Login button
        self.login_btn = QtWidgets.QPushButton("Giriş Yap")
        self.login_btn.setCursor(QtCore.Qt.PointingHandCursor)
        self.login_btn.setStyleSheet(self.mobile_button_style())
        self.login_btn.setFixedHeight(50)
        self.login_btn.clicked.connect(self.handle_login)
        bottom_layout.addWidget(self.login_btn)

        # Create account link
        self.register_btn = QtWidgets.QPushButton("Müşterimiz Ol")
        self.register_btn.setCursor(QtCore.Qt.PointingHandCursor)
        self.register_btn.setStyleSheet(self.mobile_link_style())
        self.register_btn.clicked.connect(self.show_register_dialog)
        bottom_layout.addWidget(self.register_btn)

        # Status label
        self.status = QtWidgets.QLabel("")
        self.status.setStyleSheet("""
            color: #ef4444; 
            font-size: 14px; 
            font-weight: 500;
            background: rgba(239, 68, 68, 0.1);
            padding: 8px 12px;
            border-radius: 8px;
            margin-top: 10px;
        """)
        self.status.setAlignment(QtCore.Qt.AlignCenter)
        bottom_layout.addWidget(self.status)

        # Demo credentials info
        demo_info = QtWidgets.QLabel("Demo Hesap: admin / 1234")
        demo_info.setStyleSheet("""
            color: #6b7280;
            font-size: 12px;
            font-style: italic;
            background: #f3f4f6;
            padding: 8px 12px;
            border-radius: 6px;
            margin-top: 10px;
        """)
        demo_info.setAlignment(QtCore.Qt.AlignCenter)
        bottom_layout.addWidget(demo_info)

        bottom_layout.addStretch()
        main_layout.addWidget(bottom_section)



    def mobile_input_style(self):
        return """
            QLineEdit {
                background: white;
                color: #333333;
                border: 1px solid #e5e7eb;
                border-radius: 8px;
                padding: 0 16px;
                font-size: 16px;
                font-weight: 400;
            }
            QLineEdit:focus {
                border: 2px solid #3b82f6;
                outline: none;
            }
            QLineEdit::placeholder {
                color: #9ca3af;
            }
        """
    
    def mobile_button_style(self):
        return """
            QPushButton {
                background: #3b82f6;
                color: white;
                border: none;
                border-radius: 8px;
                font-size: 16px;
                font-weight: 600;
                letter-spacing: 1px;
            }
            QPushButton:hover {
                background: #2563eb;
            }
            QPushButton:pressed {
                background: #1d4ed8;
            }
        """
    
    def mobile_link_style(self):
        return """
            QPushButton {
                background: transparent;
                color: #3b82f6;
                border: none;
                font-size: 16px;
                font-weight: 500;
                text-decoration: underline;
            }
            QPushButton:hover {
                color: #2563eb;
            }
        """
    
    def button_style(self, secondary=False):
        if not secondary:
            return (
                "QPushButton {"
                "background: qlineargradient(x1:0, y1:0, x2:1, y2:1, "
                "stop:0 #6366f1, stop:1 #8b5cf6);"
                "color: #ffffff;"
                "border: none;"
                "border-radius: 12px;"
                "padding: 16px 0;"
                "font-size: 16px;"
                "font-weight: 600;"
                "}"
                "QPushButton:hover {"
                "background: qlineargradient(x1:0, y1:0, x2:1, y2:1, "
                "stop:0 #5855eb, stop:1 #7c3aed);"
                "padding: 14px 0;"
                "}"
                "QPushButton:pressed {"
                "padding: 16px 0;"
                "}"
            )
        else:
            return (
                "QPushButton {"
                "background: rgba(255, 255, 255, 0.05);"
                "color: #ffffff;"
                "border: 1px solid rgba(255, 255, 255, 0.2);"
                "border-radius: 12px;"
                "padding: 14px 0;"
                "font-size: 16px;"
                "font-weight: 500;"
                "}"
                "QPushButton:hover {"
                "background: rgba(255, 255, 255, 0.1);"
                "border: 1px solid rgba(99, 102, 241, 0.5);"
                "color: #6366f1;"
                "padding: 12px 0;"
                "}"
            )

    def authenticate_user(self, username, password):
        """Authenticate user with database"""
        try:
            conn = sqlite3.connect(self.database_path)
            cursor = conn.cursor()
            cursor.execute('SELECT id, password, name, balance, investment_balance FROM customers WHERE id = ?', (username,))
            result = cursor.fetchone()
            conn.close()
            
            if result and result[1] == password:
                return Customer(result[0], result[1], result[2], result[3], result[4] if len(result) > 4 else 0)
            return None
        except Exception as e:
            print(f"Database error: {e}")
            return None

    def handle_login(self):
        username = self.username.text().strip()
        password = self._password_value
        
        if not username or not password:
            self.status.setText("Lütfen kullanıcı adı ve şifre girin.")
            return
            
        self.current_customer = self.authenticate_user(username, password)
        if self.current_customer:
            self.status.setText("")
            self.show_main_menu()
        else:
            self.status.setText("Hatalı kullanıcı adı veya şifre.")
            self._password_value = ""  # Şifreyi temizle
            self.password.setText("")  # Alanı da temizle
    
    def show_main_menu(self):
        """Show the main banking menu after successful login"""
        self.main_menu_window = MainMenuWindow(self.current_customer, self.database_path)
        self.main_menu_window.show()
        self.close()
    
    def show_register_dialog(self):
        """Show registration dialog"""
        dialog = RegisterDialog(self.database_path)
        if dialog.exec_() == QtWidgets.QDialog.Accepted:
            AppMessageDialog.show_success(self, "Başarılı", "Hesabınız başarıyla oluşturuldu! Giriş yapabilirsiniz.")


class MainMenuWindow(QtWidgets.QMainWindow):
    def __init__(self, customer, database_path):
        super().__init__()
        self.customer = customer
        self.database_path = database_path
        self.setWindowTitle("ValueVault - Dashboard")
        self.setGeometry(150, 50, 420, 760)
        self.setMinimumSize(350, 600)
        self.setStyleSheet("""
            QMainWindow {
                background: #f8fafc;
            }
        """)
        self.initMainMenuUI()
        
    def initMainMenuUI(self):
        # Set font
        font = QtGui.QFont("Segoe UI", 10)
        self.setFont(font)

        # Central widget
        central = QtWidgets.QWidget()
        self.setCentralWidget(central)
        layout = QtWidgets.QVBoxLayout(central)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Blue header section
        header_section = QtWidgets.QWidget()
        header_section.setStyleSheet("""
            QWidget {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, 
                    stop:0 #1e40af, stop:1 #3b82f6);
            }
        """)
        header_section.setFixedHeight(200)
        header_layout = QtWidgets.QVBoxLayout(header_section)
        header_layout.setContentsMargins(30, 40, 30, 30)
        header_layout.setSpacing(20)

        # Header with greeting and logout
        top_header = QtWidgets.QHBoxLayout()
        greeting = QtWidgets.QLabel(f"Merhaba, {self.customer.name}")
        greeting.setStyleSheet("""
            background: transparent;
            border: none;                  
            color: white; 
            font-size: 20px; 
            font-weight: 600; 
        """)
        
        logout_btn = QtWidgets.QPushButton("Çıkış")
        logout_btn.setStyleSheet(self.mobile_logout_style())
        logout_btn.clicked.connect(self.logout)
        logout_btn.setFixedSize(60, 30)
        
        top_header.addWidget(greeting)
        top_header.addStretch()
        top_header.addWidget(logout_btn)
        header_layout.addLayout(top_header)

        # Balance card
        balance_card = QtWidgets.QFrame()
        balance_card.setStyleSheet("""
            QFrame {
                background: rgba(255, 255, 255, 0.2);
                border-radius: 16px;
                border: 1px solid rgba(255, 255, 255, 0.3);
            }
        """)
        balance_card.setFixedHeight(80)
        balance_layout = QtWidgets.QVBoxLayout(balance_card)
        balance_layout.setContentsMargins(20, 15, 20, 15)
        
        self.balance_title = QtWidgets.QLabel("Toplam Bakiye")
        self.balance_title.setStyleSheet("""
            background: transparent;
            border: none;
            color: rgba(255, 255, 255, 0.8);
            font-size: 14px;
            font-weight: 400;
        """)
        
        self.balance_label = QtWidgets.QLabel(f"{self.customer.balance:,} TL")
        self.balance_label.setStyleSheet("""
            background: transparent;
            border: none;
            color: white; 
            font-size: 24px; 
            font-weight: 700;
        """)
        
        balance_layout.addWidget(self.balance_title)
        balance_layout.addWidget(self.balance_label)
        header_layout.addWidget(balance_card)
        
        layout.addWidget(header_section)

        # White content section
        content_section = QtWidgets.QWidget()
        content_section.setStyleSheet("""
            QWidget {
                background: white;
                border-top-left-radius: 25px;
                border-top-right-radius: 25px;
            }
        """)
        content_layout = QtWidgets.QVBoxLayout(content_section)
        content_layout.setContentsMargins(10, 10, 10, 10)
        content_layout.setSpacing(0)

        # Sayfa yığını
        self.pages = QtWidgets.QStackedWidget()
        content_layout.addWidget(self.pages)

        # --- SAYFA 0: ANA (Hızlı İşlemler) ---
        home_page = QtWidgets.QWidget()
        home_layout = QtWidgets.QVBoxLayout(home_page)
        home_layout.setContentsMargins(10, 10, 10, 10)
        home_layout.setSpacing(20)

        actions_title = QtWidgets.QLabel("Hızlı İşlemler")
        actions_title.setStyleSheet("""
            color: #1f2937;
            font-size: 18px;
            font-weight: 600;
        """)
        home_layout.addWidget(actions_title)

        actions_container = QtWidgets.QWidget()
        actions_grid = QtWidgets.QGridLayout(actions_container)
        actions_grid.setSpacing(10)
        actions_grid.setContentsMargins(0, 0, 0, 0)

        # Ana sayfa hızlı işlemler
        actions = [
            ("💳", "Para Yatır", self.deposit_money),
            ("💸", "Para Çek", self.withdraw_money),
            ("🔄", "Transfer", self.transfer_money),
            ("📈", "Yatırım", self.open_investments_menu),
        ]

        for i, (icon, text, callback) in enumerate(actions):
            action_btn = self.create_action_button(icon, text, callback)
            row = i // 2
            col = i % 2
            actions_grid.addWidget(action_btn, row, col)

        actions_grid.setColumnStretch(0, 1)
        actions_grid.setColumnStretch(1, 1)
        home_layout.addWidget(actions_container)

        account_title = QtWidgets.QLabel("Hesap")
        account_title.setStyleSheet("""
            color: #1f2937;
            font-size: 18px;
            font-weight: 600;
            margin-top: 20px;
        """)
        home_layout.addWidget(account_title)

        accounts_btn = self.create_list_item("🏦", "Hesaplarım", self.open_accounts_dialog)
        account_info_btn = self.create_list_item("👤", "Hesap Bilgileri", self.account_info)
        history_btn = self.create_list_item("📊", "İşlem Geçmişi", self.transaction_history)
        home_layout.addWidget(accounts_btn)
        home_layout.addWidget(account_info_btn)
        home_layout.addWidget(history_btn)
        home_layout.addStretch()

        self.pages.addWidget(home_page)   # index 0

        # --- SAYFA 1: YATIRIM ALT MENÜSÜ ---
        investments_page = self.build_investments_page()
        self.pages.addWidget(investments_page)  # index 1

        layout.addWidget(content_section)
        
        # İlk açılışta doğru başlığı göster
        self.update_header_labels()

    def mobile_logout_style(self):
        return """
            QPushButton {
                background: rgba(255, 255, 255, 0.2);
                color: white;
                border: 1px solid rgba(255, 255, 255, 0.3);
                border-radius: 15px;
                font-size: 12px;
                font-weight: 500;
            }
            QPushButton:hover {
                background: rgba(255, 255, 255, 0.3);
            }
        """

    def create_action_button(self, icon, text, callback):
         """Create mobile-style action button"""
         btn = QtWidgets.QPushButton()
         btn.setMinimumSize(120, 85)
         btn.setMaximumSize(160, 100)
         btn.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Fixed)
         btn.setStyleSheet("""
             QPushButton {
                 background: white;
                 border: 1px solid #e5e7eb;
                 border-radius: 16px;
                 font-size: 11px;
                 font-weight: 500;
                 color: #374151;
                 text-align: center;
                 padding: 12px 8px;
                 margin: 5px;
             }
             QPushButton:hover {
                 background: #f8fafc;
                 border: 1px solid #3b82f6;
                 margin: 3px;
             }
             QPushButton:pressed {
                 background: #f1f5f9;
                 margin: 5px;
             }
         """)
         
         # Create layout for icon and text
         layout = QtWidgets.QVBoxLayout(btn)
         layout.setContentsMargins(8, 12, 8, 8)
         layout.setSpacing(8)
         
         icon_label = QtWidgets.QLabel(icon)
         icon_label.setStyleSheet("""
             font-size: 28px;
             color: #3b82f6;
             background: transparent;
             border: none;
         """)
         icon_label.setAlignment(QtCore.Qt.AlignCenter)
         
         text_label = QtWidgets.QLabel(text)
         text_label.setStyleSheet("""
             font-size: 11px; 
             color: #6b7280; 
             font-weight: 600;
             background: transparent;
             border: none;
         """)
         text_label.setAlignment(QtCore.Qt.AlignCenter)
         text_label.setWordWrap(True)
         
         layout.addWidget(icon_label)
         layout.addWidget(text_label)
         
         btn.clicked.connect(callback)
         return btn

    def create_list_item(self, icon, text, callback):
        """Create mobile-style list item"""
        item = QtWidgets.QPushButton()
        item.setFixedHeight(60)
        item.setStyleSheet("""
            QPushButton {
                background: white;
                border: 1px solid #f3f4f6;
                border-radius: 12px;
                text-align: left;
                padding: 15px;
                font-size: 14px;
                font-weight: 500;
                color: #374151;
            }
            QPushButton:hover {
                background: #f9fafb;
                border: 1px solid #e5e7eb;
            }
        """)
        
        # Create horizontal layout
        layout = QtWidgets.QHBoxLayout(item)
        layout.setContentsMargins(15, 0, 15, 0)
        
        icon_label = QtWidgets.QLabel(icon)
        icon_label.setStyleSheet("font-size: 20px;")
        icon_label.setFixedWidth(30)
        
        text_label = QtWidgets.QLabel(text)
        text_label.setStyleSheet("font-size: 14px; color: #374151;")
        
        arrow_label = QtWidgets.QLabel("›")
        arrow_label.setStyleSheet("font-size: 18px; color: #9ca3af;")
        arrow_label.setAlignment(QtCore.Qt.AlignRight)
        
        layout.addWidget(icon_label)
        layout.addWidget(text_label)
        layout.addStretch()
        layout.addWidget(arrow_label)
        
        item.clicked.connect(callback)
        return item

    def create_card(self, title, buttons):
        """Create a card widget with title and buttons"""
        card = QtWidgets.QFrame()
        card.setStyleSheet("""
            QFrame {
                background: rgba(255, 255, 255, 0.08);
                border-radius: 20px;
                border: 1px solid rgba(255, 255, 255, 0.1);
            }
            QFrame:hover {
                background: rgba(255, 255, 255, 0.12);
                border: 1px solid rgba(99, 102, 241, 0.3);
            }
        """)
        card.setFixedHeight(280)
        
        layout = QtWidgets.QVBoxLayout(card)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(12)

        # Title with modern styling
        title_label = QtWidgets.QLabel(title)
        title_label.setStyleSheet("""
            color: #ffffff; 
            font-size: 20px; 
            font-weight: 600;
            margin-bottom: 12px;
        """)
        layout.addWidget(title_label)

        # Buttons
        for button_text, callback in buttons:
            btn = QtWidgets.QPushButton(button_text)
            btn.setStyleSheet(self.card_button_style())
            btn.clicked.connect(callback)
            layout.addWidget(btn)

        layout.addStretch()
        return card

    def card_button_style(self):
        return """
            QPushButton {
                background: rgba(255, 255, 255, 0.05);
                color: #ffffff;
                border: 1px solid rgba(255, 255, 255, 0.1);
                border-radius: 10px;
                padding: 12px 16px;
                font-size: 14px;
                font-weight: 500;
                text-align: left;
            }
            QPushButton:hover {
                background: rgba(99, 102, 241, 0.1);
                border: 1px solid rgba(99, 102, 241, 0.3);
                color: #6366f1;
                padding-left: 20px;
            }
        """

    def logout_button_style(self):
        return """
            QPushButton {
                background: rgba(239, 68, 68, 0.1);
                color: #ef4444;
                border: 1px solid rgba(239, 68, 68, 0.3);
                border-radius: 10px;
                padding: 10px 16px;
                font-size: 14px;
                font-weight: 500;
            }
            QPushButton:hover {
                background: rgba(239, 68, 68, 0.2);
                border: 1px solid #ef4444;
                margin: 2px;
            }
        """

    def update_balance(self):
        """Update balance from database"""
        try:
            conn = sqlite3.connect(self.database_path)
            cursor = conn.cursor()
            cursor.execute('SELECT balance FROM customers WHERE id = ?', (self.customer.id,))
            result = cursor.fetchone()
            conn.close()
            if result:
                self.customer.balance = result[0]
                self.balance_label.setText(f"{self.customer.balance:,} TL")
        except Exception as e:
            print(f"Database error: {e}")

    def check_balance(self):
        self.update_balance()
        AppMessageDialog.show_info(self, "Bakiye", f"Mevcut bakiyeniz: {self.customer.balance} TL")

    def deposit_money(self):
        amount, ok = AppNumberInputDialog.get_int(self, "Para Yatır", "Yatırılacak miktar:", minimum=1)
        if ok and amount > 0:
            try:
                conn = sqlite3.connect(self.database_path)
                cursor = conn.cursor()
                new_balance = self.customer.balance + amount
                cursor.execute('UPDATE customers SET balance = ? WHERE id = ?', (new_balance, self.customer.id))
                
                # İşlem geçmişine kaydet
                cursor.execute('''
                    INSERT INTO transactions (customer_id, transaction_type, amount, description)
                    VALUES (?, ?, ?, ?)
                ''', (self.customer.id, 'DEPOSIT', amount, f'Para yatırma işlemi'))
                
                conn.commit()
                conn.close()
                self.customer.balance = new_balance
                self.update_balance()
                AppMessageDialog.show_success(self, "Başarılı", f"{amount} TL hesabınıza yatırıldı.")
            except Exception as e:
                AppMessageDialog.show_error(self, "Hata", f"İşlem gerçekleştirilemedi: {e}")

    def withdraw_money(self):
        amount, ok = AppNumberInputDialog.get_int(self, "Para Çek", f"Çekilecek miktar (Max: {self.customer.balance} TL):", minimum=1, maximum=self.customer.balance)
        if ok and amount > 0:
            if amount <= self.customer.balance:
                try:
                    conn = sqlite3.connect(self.database_path)
                    cursor = conn.cursor()
                    new_balance = self.customer.balance - amount
                    cursor.execute('UPDATE customers SET balance = ? WHERE id = ?', (new_balance, self.customer.id))
                    
                    # İşlem geçmişine kaydet
                    cursor.execute('''
                        INSERT INTO transactions (customer_id, transaction_type, amount, description)
                        VALUES (?, ?, ?, ?)
                    ''', (self.customer.id, 'WITHDRAW', amount, f'Para çekme işlemi'))
                    
                    conn.commit()
                    conn.close()
                    self.customer.balance = new_balance
                    self.update_balance()
                    AppMessageDialog.show_success(self, "Başarılı", f"{amount} TL hesabınızdan çekildi.")
                except Exception as e:
                    AppMessageDialog.show_error(self, "Hata", f"İşlem gerçekleştirilemedi: {e}")
            else:
                AppMessageDialog.show_warning(self, "Yetersiz Bakiye", "Yetersiz bakiye!")

    def transfer_money(self):
        dialog = TransferDialog(self.customer, self.database_path)
        if dialog.exec_() == QtWidgets.QDialog.Accepted:
            self.update_balance()

    def stock_prices(self):
        # Varsayılan BIST sembolleri (.IS)
        default_syms = "XU100.IS,THYAO.IS,ASELS.IS,BIMAS.IS,SISE.IS,GARAN.IS,AKBNK.IS,TUPRS.IS,EREGL.IS,PGSUS.IS,YKBNK.IS,HEKTS.IS"
        text, ok = QtWidgets.QInputDialog.getText(
            self,
            "Borsa Sembolleri",
            "Semboller (virgülle ayırın, BIST için '.IS' ekleyin):",
            text=default_syms
        )
        if not ok:
            return
        symbols = [s.strip() for s in text.split(",") if s.strip()]
        try:
            quotes = fetch_stock_quotes(tuple(symbols))
            if not quotes:
                AppMessageDialog.show_warning(self, "Hisse Senetleri", "Veri alınamadı.")
                return
            dialog = StockListDialog(self, quotes)
            dialog.exec_()
        except Exception as e:
            AppMessageDialog.show_error(self, "Hisse Senetleri", f"Veri alınamadı: {e}")

    def currency_rates(self):
        try:
            rates = fetch_currency_rates(symbols=("USD", "EUR", "GBP"))
            if not rates:
                AppMessageDialog.show_warning(self, "Döviz Kurları", "Kurlar alınamadı.")
                return
            
            # Döviz kodlarını Türkçe isimlerle eşleştir
            currency_names = {
                "USD": "Amerikan Doları",
                "EUR": "Euro", 
                "GBP": "İngiliz Sterlini"
            }
            
            lines = ["📊 GÜNCEL DÖVİZ KURLARI\n"]
            for code, value in rates.items():
                name = currency_names.get(code, code)
                # Alış fiyatı %0.5 düşük, satış fiyatı %0.5 yüksek
                buy_rate = value * 0.995
                sell_rate = value * 1.005
                lines.append(f"{name} ({code})")
                lines.append(f"  💰 Alış: {buy_rate:.4f} TL")
                lines.append(f"  💸 Satış: {sell_rate:.4f} TL")
                lines.append("")  # Boş satır
            
            AppMessageDialog.show_info(self, "Döviz Kurları", "\n".join(lines[:-1]))  # Son boş satırı çıkar
        except Exception as e:
            AppMessageDialog.show_error(self, "Döviz Kurları", f"Kurlar alınamadı: {e}")

    def precious_metals(self):
        try:
            metals = fetch_precious_metals()
            if not metals:
                AppMessageDialog.show_warning(self, "Kıymetli Madenler", "Veriler alınamadı.")
                return
            
            # Döviz kurunu al (USD/TRY)
            usd_rates = fetch_currency_rates(symbols=("USD",))
            usd_rate = usd_rates.get("USD", 34.0)  # Fallback rate
            
            lines = ["🥇 KIYMETLİ MADEN FİYATLARI\n"]
            
            # Metal ikonları
            metal_icons = {
                "XAU": "🥇",  # Altın
                "XAG": "🥈",  # Gümüş
                "XPT": "⚪",  # Platin
                "XPD": "⚫"   # Paladyum
            }
            
            for code, data in metals.items():
                name = data.get("name", code)
                price_usd = data.get("price", 0)
                unit = data.get("unit", "ons")
                icon = metal_icons.get(code, "🔶")
                
                # USD ve TRY fiyatları (ons bazında)
                price_try = price_usd * usd_rate
                
                # Gram bazında fiyatlar (1 ons = 31.1 gram)
                price_usd_gram = price_usd / 31.1
                price_try_gram = price_try / 31.1
                
                lines.append(f"{icon} {name} ({code})")
                lines.append(f"  💵 {price_usd:.2f} USD/ons • {price_usd_gram:.2f} USD/gram")
                lines.append(f"  💰 {price_try:.2f} TL/ons • {price_try_gram:.2f} TL/gram")
                lines.append("")  # Boş satır
            
            AppMessageDialog.show_info(self, "Kıymetli Madenler", "\n".join(lines[:-1]))  # Son boş satırı çıkar
        except Exception as e:
            AppMessageDialog.show_error(self, "Kıymetli Madenler", f"Veriler alınamadı: {e}")

    def crypto_prices(self):
        try:
            cryptos = fetch_crypto_prices()
            if not cryptos:
                AppMessageDialog.show_warning(self, "Kripto Para", "Veriler alınamadı.")
                return
            dialog = CryptoListDialog(self, cryptos)
            dialog.exec_()
        except Exception as e:
            AppMessageDialog.show_error(self, "Kripto Para", f"Veriler alınamadı: {e}")

    def account_info(self):
        info = f"Kullanıcı ID: {self.customer.id}\nİsim: {self.customer.name}\nBakiye: {self.customer.balance} TL"
        AppMessageDialog.show_info(self, "Hesap Bilgileri", info)

    def transaction_history(self):
        dialog = TransactionHistoryDialog(self, self.customer, self.database_path)
        dialog.exec_()

    def logout(self):
        confirmed = AppMessageDialog.show_question(self, "Çıkış", "Çıkış yapmak istediğinizden emin misiniz?")
        if confirmed:
            self.close()
            login_window = ModernMainWindow()
            login_window.show()

    def build_investments_page(self):
        """Yatırım alt menüsü: Döviz, Hisse, Kıymetli Madenler, Çevirici vb."""
        page = QtWidgets.QWidget()
        v = QtWidgets.QVBoxLayout(page)
        v.setContentsMargins(10, 10, 10, 10)
        v.setSpacing(16)

        # Üst çubuk: Geri + Başlık
        top = QtWidgets.QHBoxLayout()
        back_btn = QtWidgets.QPushButton("‹ Geri")
        back_btn.setCursor(QtCore.Qt.PointingHandCursor)
        back_btn.setFixedHeight(34)
        back_btn.setStyleSheet("""
            QPushButton {
                background: #f3f4f6; color: #374151;
                border: 1px solid #e5e7eb; border-radius: 8px;
                padding: 0 12px; font-weight: 600;
            }
            QPushButton:hover { background: #e5e7eb; }
        """)
        back_btn.clicked.connect(self.go_home)

        title = QtWidgets.QLabel("Yatırım")
        title.setStyleSheet("color:#1f2937; font-size:18px; font-weight:700;")
        title.setAlignment(QtCore.Qt.AlignCenter)

        top.addWidget(back_btn)
        top.addStretch()
        top.addWidget(title)
        top.addStretch()
        top.addSpacing(46)  # başlık ortalansın diye back_btn genişliği kadar boşluk
        v.addLayout(top)

        # Alt menü grid
        grid_wrap = QtWidgets.QWidget()
        grid = QtWidgets.QGridLayout(grid_wrap)
        grid.setSpacing(10)
        grid.setContentsMargins(0, 0, 0, 0)

        items = [
            ("💱", "Döviz Kurları", self.currency_rates),
            ("📈", "Hisse Senetleri", self.stock_prices),
            ("🪙", "Kıymetli Madenler", self.precious_metals),
            ("₿", "Kripto Para", self.crypto_prices),
            # İsteğe bağlı ekler:
            # ("📊", "Portföy Özeti", lambda: AppMessageDialog.show_info(self, "Portföy", "Yakında...")),
        ]

        for i, (icon, text, cb) in enumerate(items):
            btn = self.create_action_button(icon, text, cb)
            row, col = divmod(i, 2)
            grid.addWidget(btn, row, col)

        grid.setColumnStretch(0, 1)
        grid.setColumnStretch(1, 1)
        v.addWidget(grid_wrap)
        v.addStretch()

        return page

    def update_header_labels(self):
        # Sayfa durumuna göre hangi bakiyeyi göstereceğimizi seç
        if getattr(self.pages, "currentIndex", lambda:0)() == 1:
            # Yatırım alt menüsü
            self.balance_title.setText("Toplam Yatırım Bakiyesi")
            self.balance_label.setText(f"{self.customer.investment_balance:,} TL")
        else:
            self.balance_title.setText("Toplam Bakiye")
            self.balance_label.setText(f"{self.customer.balance:,} TL")

    def refresh_balances_from_db(self):
        try:
            conn = sqlite3.connect(self.database_path)
            cur = conn.cursor()
            cur.execute('SELECT balance, investment_balance FROM customers WHERE id = ?', (self.customer.id,))
            row = cur.fetchone()
            conn.close()
            if row:
                self.customer.balance = row[0]
                self.customer.investment_balance = row[1]
                self.update_header_labels()
        except Exception as e:
            print("Balance refresh error:", e)

    def open_investments_menu(self):
        """Yatırım alt menüsüne geç"""
        self.pages.setCurrentIndex(1)
        self.update_header_labels()

    def go_home(self):
        """Ana sayfaya dön"""
        self.pages.setCurrentIndex(0)
        self.update_header_labels()

    def open_accounts_dialog(self):
        dlg = AccountsDialog(self)
        dlg.exec_()


class TransferDialog(QtWidgets.QDialog):
    def __init__(self, customer, database_path):
        super().__init__()
        self.customer = customer
        self.database_path = database_path
        self.setWindowTitle("Para Transfer")
        self.setFixedSize(400, 240)
        self.setStyleSheet("""
            QDialog {
                background: white;
            }
            QLabel {
                color: #374151;
                font-size: 14px;
                font-weight: 500;
            }
            QLineEdit, QSpinBox {
                background: white;
                color: #374151;
                border: 1px solid #e5e7eb;
                border-radius: 8px;
                padding: 12px;
                font-size: 14px;
            }
            QLineEdit:focus, QSpinBox:focus {
                border: 2px solid #3b82f6;
                outline: none;
            }
        """)
        self.initUI()

    def initUI(self):
        layout = QtWidgets.QVBoxLayout(self)
        layout.setSpacing(15)

        # Target ID
        layout.addWidget(QtWidgets.QLabel("Hedef Kullanıcı ID:"))
        self.target_id = QtWidgets.QLineEdit()
        layout.addWidget(self.target_id)

        # Amount
        layout.addWidget(QtWidgets.QLabel("Miktar:"))
        self.amount = QtWidgets.QSpinBox()
        self.amount.setMaximum(self.customer.balance)
        self.amount.setMinimum(1)
        layout.addWidget(self.amount)

        # Buttons
        button_layout = QtWidgets.QHBoxLayout()
        transfer_btn = QtWidgets.QPushButton("Transfer Et")
        cancel_btn = QtWidgets.QPushButton("İptal")
        
        transfer_btn.setStyleSheet("""
            QPushButton {
                background: #3b82f6;
                color: white;
                border: none;
                border-radius: 8px;
                padding: 12px;
                font-size: 14px;
                font-weight: 600;
            }
            QPushButton:hover {
                background: #2563eb;
            }
        """)
        
        cancel_btn.setStyleSheet("""
            QPushButton {
                background: #f9fafb;
                color: #6b7280;
                border: 1px solid #e5e7eb;
                border-radius: 8px;
                padding: 12px;
                font-size: 14px;
                font-weight: 500;
            }
            QPushButton:hover {
                background: #f3f4f6;
                color: #374151;
            }
        """)

        transfer_btn.clicked.connect(self.transfer)
        cancel_btn.clicked.connect(self.reject)
        
        button_layout.addWidget(transfer_btn)
        button_layout.addWidget(cancel_btn)
        layout.addLayout(button_layout)

    def transfer(self):
        target_id = self.target_id.text().strip()
        amount = self.amount.value()

        if not target_id:
            AppMessageDialog.show_warning(self, "Hata", "Hedef kullanıcı ID'si gerekli!")
            return

        try:
            conn = sqlite3.connect(self.database_path)
            cursor = conn.cursor()
            
            # Check if target exists
            cursor.execute('SELECT id, name, balance FROM customers WHERE id = ?', (target_id,))
            target = cursor.fetchone()
            
            if not target:
                AppMessageDialog.show_warning(self, "Hata", "Hedef kullanıcı bulunamadı!")
                conn.close()
                return

            if amount > self.customer.balance:
                AppMessageDialog.show_warning(self, "Hata", "Yetersiz bakiye!")
                conn.close()
                return

            # Perform transfer
            new_sender_balance = self.customer.balance - amount
            new_target_balance = target[2] + amount
            
            cursor.execute('UPDATE customers SET balance = ? WHERE id = ?', (new_sender_balance, self.customer.id))
            cursor.execute('UPDATE customers SET balance = ? WHERE id = ?', (new_target_balance, target_id))
            
            # Gönderen için işlem geçmişine kaydet
            cursor.execute('''
                INSERT INTO transactions (customer_id, transaction_type, amount, target_customer, description)
                VALUES (?, ?, ?, ?, ?)
            ''', (self.customer.id, 'TRANSFER_OUT', amount, target_id, f'{target[1]} kullanıcısına transfer'))
            
            # Alıcı için işlem geçmişine kaydet
            cursor.execute('''
                INSERT INTO transactions (customer_id, transaction_type, amount, target_customer, description)
                VALUES (?, ?, ?, ?, ?)
            ''', (target_id, 'TRANSFER_IN', amount, self.customer.id, f'{self.customer.name} kullanıcısından transfer'))
            
            conn.commit()
            conn.close()
            
            AppMessageDialog.show_success(self, "Başarılı", f"{amount} TL {target[1]} kullanıcısına transfer edildi.")
            self.accept()
            
        except Exception as e:
            AppMessageDialog.show_error(self, "Hata", f"Transfer gerçekleştirilemedi: {e}")


class TransactionHistoryDialog(QtWidgets.QDialog):
    def __init__(self, parent, customer, database_path):
        super().__init__(parent)
        self.customer = customer
        self.database_path = database_path
        self.setModal(True)
        self.setWindowFlags(QtCore.Qt.FramelessWindowHint | QtCore.Qt.Dialog)
        self.setAttribute(QtCore.Qt.WA_TranslucentBackground)

        # full overlay sized to parent
        if parent is not None:
            self.resize(parent.width(), parent.height())
            self.move(parent.mapToGlobal(QtCore.QPoint(0, 0)))

        root = QtWidgets.QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.addStretch()

        row = QtWidgets.QHBoxLayout()
        row.addStretch()

        card = QtWidgets.QFrame()
        card.setStyleSheet("QFrame { background: white; border-radius: 16px; }")
        card.setFixedSize(520, 650)
        v = QtWidgets.QVBoxLayout(card)
        v.setContentsMargins(16, 16, 16, 16)
        v.setSpacing(10)

        title = QtWidgets.QLabel("İşlem Geçmişi")
        title.setAlignment(QtCore.Qt.AlignCenter)
        title.setStyleSheet("color:#111827; font-size:18px; font-weight:700;")
        v.addWidget(title)

        table = QtWidgets.QTableWidget()
        table.setColumnCount(5)
        table.setHorizontalHeaderLabels(["Tarih", "İşlem", "Miktar", "Açıklama", "Durum"])
        table.horizontalHeader().setStretchLastSection(True)
        table.horizontalHeader().setSectionResizeMode(QtWidgets.QHeaderView.Stretch)
        table.setEditTriggers(QtWidgets.QAbstractItemView.NoEditTriggers)
        table.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)
        table.setAlternatingRowColors(True)
        
        table.setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarAsNeeded)
        table.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAsNeeded)
        table.setMinimumHeight(480)
        
        table.setStyleSheet("""
            QTableWidget { 
                background: white; 
                color: #111827; 
                gridline-color: #e5e7eb;
                font-size: 11px;
            }
            QHeaderView::section { 
                background: #f3f4f6; 
                padding: 6px; 
                border: none; 
                font-weight: 600; 
                font-size: 11px;
            }
            QTableWidget::item { 
                padding: 6px; 
                border-bottom: 1px solid #f3f4f6;
            }
        """)

        # Load transactions
        transactions = self.load_transactions()
        table.setRowCount(len(transactions))
        
        for r, transaction in enumerate(transactions):
            date_item = QtWidgets.QTableWidgetItem(transaction['date'])
            type_item = QtWidgets.QTableWidgetItem(transaction['type'])
            amount_item = QtWidgets.QTableWidgetItem(transaction['amount'])
            desc_item = QtWidgets.QTableWidgetItem(transaction['description'])
            status_item = QtWidgets.QTableWidgetItem(transaction['status'])

            # Renklendirme
            if transaction['transaction_type'] in ['DEPOSIT', 'TRANSFER_IN']:
                amount_item.setForeground(QtGui.QBrush(QtGui.QColor("#10b981")))
                status_item.setForeground(QtGui.QBrush(QtGui.QColor("#10b981")))
            elif transaction['transaction_type'] in ['WITHDRAW', 'TRANSFER_OUT']:
                amount_item.setForeground(QtGui.QBrush(QtGui.QColor("#ef4444")))
                status_item.setForeground(QtGui.QBrush(QtGui.QColor("#ef4444")))

            table.setItem(r, 0, date_item)
            table.setItem(r, 1, type_item)
            table.setItem(r, 2, amount_item)
            table.setItem(r, 3, desc_item)
            table.setItem(r, 4, status_item)

        table.resizeRowsToContents()
        table.resizeColumnsToContents()
        
        v.addWidget(table)

        btn_row = QtWidgets.QHBoxLayout()
        btn_row.addStretch()
        close_btn = QtWidgets.QPushButton("Kapat")
        close_btn.setFixedHeight(36)
        close_btn.setCursor(QtCore.Qt.PointingHandCursor)
        close_btn.setStyleSheet("QPushButton { background: #1e40af; color: white; border: none; border-radius: 8px; padding: 0 16px; font-weight: 600; }")
        close_btn.clicked.connect(self.accept)
        btn_row.addWidget(close_btn)
        btn_row.addStretch()
        v.addLayout(btn_row)

        row.addWidget(card)
        row.addStretch()
        root.addLayout(row)
        root.addStretch()
        self.setStyleSheet("QDialog { background: rgba(0,0,0,0.45); }")

    def load_transactions(self):
        """Load transaction history from database"""
        try:
            conn = sqlite3.connect(self.database_path)
            cursor = conn.cursor()
            cursor.execute('''
                SELECT transaction_type, amount, target_customer, description, timestamp
                FROM transactions 
                WHERE customer_id = ? 
                ORDER BY timestamp DESC 
                LIMIT 50
            ''', (self.customer.id,))
            
            results = cursor.fetchall()
            conn.close()
            
            transactions = []
            type_names = {
                'DEPOSIT': 'Para Yatırma',
                'WITHDRAW': 'Para Çekme',
                'TRANSFER_OUT': 'Transfer (Giden)',
                'TRANSFER_IN': 'Transfer (Gelen)'
            }
            
            for result in results:
                transaction_type, amount, target_customer, description, timestamp = result
                
                # Tarih formatı
                try:
                    from datetime import datetime
                    dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
                    formatted_date = dt.strftime('%d.%m.%Y %H:%M')
                except:
                    formatted_date = timestamp[:16]
                
                # Miktar formatı
                if transaction_type in ['DEPOSIT', 'TRANSFER_IN']:
                    amount_str = f"+{amount:,} TL"
                    status = "✅ Başarılı"
                else:
                    amount_str = f"-{amount:,} TL"
                    status = "✅ Başarılı"
                
                transactions.append({
                    'date': formatted_date,
                    'type': type_names.get(transaction_type, transaction_type),
                    'amount': amount_str,
                    'description': description,
                    'status': status,
                    'transaction_type': transaction_type
                })
                
            return transactions
            
        except Exception as e:
            print(f"Transaction history load error: {e}")
            return []


class RegisterDialog(QtWidgets.QDialog):
    def __init__(self, database_path):
        super().__init__()
        self.database_path = database_path
        self.setWindowTitle("Hesap Oluştur")
        self.setFixedSize(600, 450)
        self.setStyleSheet("""
            QDialog {
                background: white;
            }
            QLabel {
                color: #374151;
                font-size: 12px;
                font-weight: 500;
            }
            QLineEdit {
                background: white;
                color: #374151;
                border: 1px solid #e5e7eb;
                border-radius: 8px;
                padding: 12px;
                font-size: 12px;
            }
            QLineEdit:focus {
                border: 2px solid #3b82f6;
                outline: none;
            }
            QLineEdit::placeholder {
                color: #9ca3af;
            }
        """)
        self.initUI()

    def initUI(self):
        layout = QtWidgets.QVBoxLayout(self)
        layout.setSpacing(15)
        layout.setContentsMargins(10, 10, 10, 10)

        # Title
        title = QtWidgets.QLabel("Hesap Oluştur")
        title.setStyleSheet("""
            color: #1f2937; 
            font-size: 20px; 
            font-weight: 600;
            margin-bottom: 10px;
        """)
        title.setAlignment(QtCore.Qt.AlignCenter)
        layout.addWidget(title)

        # User ID
        layout.addWidget(QtWidgets.QLabel("Kullanıcı ID:"))
        self.user_id = QtWidgets.QLineEdit()
        self.user_id.setPlaceholderText("Benzersiz kullanıcı ID'si girin")
        layout.addWidget(self.user_id)

        # Name
        layout.addWidget(QtWidgets.QLabel("Ad Soyad:"))
        self.name = QtWidgets.QLineEdit()
        self.name.setPlaceholderText("Ad ve soyadınızı girin")
        layout.addWidget(self.name)

        # Password
        layout.addWidget(QtWidgets.QLabel("Şifre:"))
        self.password = QtWidgets.QLineEdit()
        self.password.setEchoMode(QtWidgets.QLineEdit.Password)
        self.password.setPlaceholderText("Güvenli bir şifre girin")
        layout.addWidget(self.password)

        # Confirm Password
        layout.addWidget(QtWidgets.QLabel("Şifre Tekrar:"))
        self.confirm_password = QtWidgets.QLineEdit()
        self.confirm_password.setEchoMode(QtWidgets.QLineEdit.Password)
        self.confirm_password.setPlaceholderText("Şifrenizi tekrar girin")
        layout.addWidget(self.confirm_password)

        # Buttons
        button_layout = QtWidgets.QHBoxLayout()
        register_btn = QtWidgets.QPushButton("Hesap Oluştur")
        cancel_btn = QtWidgets.QPushButton("İptal")
        
        register_btn.setStyleSheet("""
            QPushButton {
                background: #3b82f6;
                color: white;
                border: none;
                border-radius: 8px;
                padding: 12px;
                font-size: 16px;
                font-weight: 600;
            }
            QPushButton:hover {
                background: #2563eb;
            }
        """)
        
        cancel_btn.setStyleSheet("""
            QPushButton {
                background: #f9fafb;
                color: #6b7280;
                border: 1px solid #e5e7eb;
                border-radius: 8px;
                padding: 12px;
                font-size: 16px;
                font-weight: 500;
            }
            QPushButton:hover {
                background: #f3f4f6;
                color: #374151;
            }
        """)

        register_btn.clicked.connect(self.register)
        cancel_btn.clicked.connect(self.reject)
        
        button_layout.addWidget(register_btn)
        button_layout.addWidget(cancel_btn)
        layout.addLayout(button_layout)

    def register(self):
        user_id = self.user_id.text().strip()
        name = self.name.text().strip()
        password = self.password.text().strip()
        confirm_password = self.confirm_password.text().strip()

        if not all([user_id, name, password, confirm_password]):
            AppMessageDialog.show_warning(self, "Hata", "Lütfen tüm alanları doldurun!")
            return

        if password != confirm_password:
            AppMessageDialog.show_warning(self, "Hata", "Şifreler eşleşmiyor!")
            return

        if len(password) < 4:
            AppMessageDialog.show_warning(self, "Hata", "Şifre en az 4 karakter olmalıdır!")
            return

        try:
            conn = sqlite3.connect(self.database_path)
            cursor = conn.cursor()
            
            # Check if user ID already exists
            cursor.execute('SELECT id FROM customers WHERE id = ?', (user_id,))
            if cursor.fetchone():
                AppMessageDialog.show_warning(self, "Hata", "Bu kullanıcı ID'si zaten kullanılıyor!")
                conn.close()
                return

            # Create new customer
            cursor.execute('''
                INSERT INTO customers (id, password, name, balance, investment_balance) VALUES (?, ?, ?, ?, ?)
            ''', (user_id, password, name, 0, 0))
            
            conn.commit()
            conn.close()
            
            self.accept()
            
        except Exception as e:
            AppMessageDialog.show_error(self, "Hata", f"Hesap oluşturulamadı: {e}")


class AccountsDialog(QtWidgets.QDialog):
    def __init__(self, parent):
        super().__init__(parent)
        self.parent = parent
        self.setModal(True)
        self.setWindowFlags(QtCore.Qt.FramelessWindowHint | QtCore.Qt.Dialog)
        self.setAttribute(QtCore.Qt.WA_TranslucentBackground)

        # tam ekran overlay
        self.resize(parent.width(), parent.height())
        self.move(parent.mapToGlobal(QtCore.QPoint(0, 0)))

        root = QtWidgets.QVBoxLayout(self); root.setContentsMargins(0,0,0,0)
        root.addStretch()
        row = QtWidgets.QHBoxLayout(); row.addStretch()

        card = QtWidgets.QFrame()
        card.setStyleSheet("QFrame { background: white; border-radius: 16px; }")
        card.setFixedSize(420, 360)
        v = QtWidgets.QVBoxLayout(card); v.setContentsMargins(16,16,16,16); v.setSpacing(12)

        title = QtWidgets.QLabel("🏦 Hesaplarım")
        title.setAlignment(QtCore.Qt.AlignCenter)
        title.setStyleSheet("color:#111827; font-size:18px; font-weight:700;")
        v.addWidget(title)

        # Ana Hesap
        main_box = QtWidgets.QGroupBox("Vadesiz (Ana Hesap)")
        mv = QtWidgets.QVBoxLayout(main_box)
        self.lbl_main = QtWidgets.QLabel()
        self.lbl_main.setStyleSheet("font-size:16px; font-weight:700; color:#111827;")
        mv.addWidget(self.lbl_main)

        # Yatırım Hesabı
        inv_box = QtWidgets.QGroupBox("Yatırım Hesabı")
        iv = QtWidgets.QVBoxLayout(inv_box)
        self.lbl_inv = QtWidgets.QLabel()
        self.lbl_inv.setStyleSheet("font-size:16px; font-weight:700; color:#111827;")
        iv.addWidget(self.lbl_inv)

        v.addWidget(main_box)
        v.addWidget(inv_box)

        # (Opsiyonel) aralarında transfer
        btns = QtWidgets.QHBoxLayout()
        btn_m2i = QtWidgets.QPushButton("Ana → Yatırım")
        btn_i2m = QtWidgets.QPushButton("Yatırım → Ana")
        for b in (btn_m2i, btn_i2m):
            b.setCursor(QtCore.Qt.PointingHandCursor)
            b.setStyleSheet("QPushButton{background:#1e40af; color:white; border:none; border-radius:8px; padding:8px 12px; font-weight:600;}")
        btn_m2i.clicked.connect(lambda: self._xfer("m2i"))
        btn_i2m.clicked.connect(lambda: self._xfer("i2m"))
        btns.addWidget(btn_m2i); btns.addWidget(btn_i2m)
        v.addLayout(btns)

        close_row = QtWidgets.QHBoxLayout(); close_row.addStretch()
        close_btn = QtWidgets.QPushButton("Kapat")
        close_btn.setCursor(QtCore.Qt.PointingHandCursor)
        close_btn.setStyleSheet("QPushButton{background:#e5e7eb; color:#374151; border:none; border-radius:8px; padding:8px 16px; font-weight:600;}")
        close_btn.clicked.connect(self.accept)
        close_row.addWidget(close_btn); close_row.addStretch()
        v.addLayout(close_row)

        row.addWidget(card); row.addStretch()
        root.addLayout(row); root.addStretch()
        self.setStyleSheet("QDialog { background: rgba(0,0,0,0.45); }")
        self._refresh_labels()

    def _refresh_labels(self):
        c = self.parent.customer
        self.lbl_main.setText(f"{c.balance:,} TL")
        self.lbl_inv.setText(f"{c.investment_balance:,} TL")

    def _xfer(self, direction):
        amount, ok = AppNumberInputDialog.get_int(self, "Tutar", "Aktarılacak tutarı girin", minimum=1, maximum=10**9)
        if not ok: 
            return
        c = self.parent.customer
        main_bal, inv_bal = c.balance, c.investment_balance

        if direction == "m2i":
            if amount > main_bal:
                AppMessageDialog.show_warning(self, "Uyarı", "Yetersiz bakiye (Ana Hesap)."); return
            main_bal -= amount; inv_bal += amount
        else:  # i2m
            if amount > inv_bal:
                AppMessageDialog.show_warning(self, "Uyarı", "Yetersiz bakiye (Yatırım Hesabı)."); return
            inv_bal -= amount; main_bal += amount

        try:
            conn = sqlite3.connect(self.parent.database_path)
            cur = conn.cursor()
            cur.execute('UPDATE customers SET balance=?, investment_balance=? WHERE id=?',
                        (main_bal, inv_bal, self.parent.customer.id))
            
            # İşlem kaydı ekle
            tx_type = 'TRANSFER_OUT' if direction == 'm2i' else 'TRANSFER_IN'
            desc = 'Hesap içi transfer: Ana → Yatırım' if direction == 'm2i' else 'Hesap içi transfer: Yatırım → Ana'
            
            cur.execute('''
                INSERT INTO transactions (customer_id, transaction_type, amount, target_customer, description)
                VALUES (?, ?, ?, ?, ?)
            ''', (self.parent.customer.id, tx_type, amount, self.parent.customer.id, desc))
            
            conn.commit(); conn.close()
            # model + header güncelle
            c.balance, c.investment_balance = main_bal, inv_bal
            self.parent.update_header_labels()
            self._refresh_labels()
            AppMessageDialog.show_success(self, "Başarılı", "Transfer tamamlandı.")
        except Exception as e:
            AppMessageDialog.show_error(self, "Hata", f"İşlem başarısız: {e}")


if __name__ == "__main__":
    import sys
    app = QtWidgets.QApplication(sys.argv)
    app.setStyle("Fusion")
    # Ensure application icon is set for taskbar/dock as well
    _icon_path = os.path.normpath(os.path.join(os.path.dirname(__file__), '..', 'Images', 'logo.png'))
    if os.path.exists(_icon_path):
        app.setWindowIcon(QtGui.QIcon(_icon_path))
    win = ModernMainWindow()
    win.show()
    sys.exit(app.exec_())
