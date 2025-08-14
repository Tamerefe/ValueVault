# Modern UI for ValueVault
# This module will contain the main window and navigation logic for the new interface.

import sys
import os

from PyQt5 import QtWidgets, QtGui, QtCore
from PyQt5.QtSvg import QSvgRenderer
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

def _fetch_yahoo_quotes(symbols):
    """Fetch from Yahoo Finance"""
    joined = ",".join(symbols)
    url = f"https://query1.finance.yahoo.com/v7/finance/quote?symbols={joined}"
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"})
    with urllib.request.urlopen(req, timeout=6) as resp:
        data = json.loads(resp.read().decode("utf-8"))
    results = data.get("quoteResponse", {}).get("result", [])
    if not results:
        return []
    
    rows = []
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
    for symbol in symbols[:5]:  # Limit requests
        try:
            url = f"https://finnhub.io/api/v1/quote?symbol={symbol}&token=demo"
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
        
        # Kaydırma çubuklarını kaldır
        table.setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
        table.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
        
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
    def __init__(self, id, password, name, balance=0):
        self.id = id
        self.password = password
        self.name = name
        self.balance = balance

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
                    balance INTEGER
                )
            ''')
            
            # Check if admin account exists
            cursor.execute('SELECT id FROM customers WHERE id = ?', ('admin',))
            admin_exists = cursor.fetchone()
            
            # Create admin account if it doesn't exist
            if not admin_exists:
                cursor.execute('''
                    INSERT INTO customers (id, password, name, balance) 
                    VALUES (?, ?, ?, ?)
                ''', ('admin', 'admin', 'Administrator', 100000))
                print("Admin hesabı oluşturuldu: admin/admin")
            
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
        self.username.setPlaceholderText("Username or Email")
        self.username.setStyleSheet(self.mobile_input_style())
        self.username.setFixedHeight(50)
        bottom_layout.addWidget(self.username)

        # Password input
        self.password = QtWidgets.QLineEdit()
        self.password.setPlaceholderText("Password")
        self.password.setEchoMode(QtWidgets.QLineEdit.Password)
        self.password.setStyleSheet(self.mobile_input_style())
        self.password.setFixedHeight(50)
        bottom_layout.addWidget(self.password)

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
        demo_info = QtWidgets.QLabel("Demo Hesap: admin / admin")
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

    def svg_icon(self, name):
        # Returns a QPixmap SVG icon (user/lock)
        svg_data = {
            "user": '''<svg width="24" height="24" fill="none" stroke="#6366f1" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" viewBox="0 0 24 24"><circle cx="12" cy="7" r="4"/><path d="M5.5 21a7.5 7.5 0 0 1 13 0"/></svg>''',
            "lock": '''<svg width="24" height="24" fill="none" stroke="#6366f1" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" viewBox="0 0 24 24"><rect x="3" y="11" width="18" height="11" rx="2"/><path d="M7 11V7a5 5 0 0 1 10 0v4"/></svg>''',
        }
        svg = svg_data.get(name, "")
        if not svg:
            return QtGui.QPixmap()
        svg_bytes = QtCore.QByteArray(svg.encode("utf-8"))
        pixmap = QtGui.QPixmap(24, 24)
        pixmap.fill(QtCore.Qt.transparent)
        painter = QtGui.QPainter(pixmap)
        renderer = QSvgRenderer(svg_bytes)
        renderer.render(painter)
        painter.end()
        return pixmap

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
                "transform: translateY(-2px);"
                "box-shadow: 0 10px 25px rgba(99, 102, 241, 0.4);"
                "}"
                "QPushButton:pressed {"
                "transform: translateY(0px);"
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
                "transform: translateY(-2px);"
                "}"
            )

    def authenticate_user(self, username, password):
        """Authenticate user with database"""
        try:
            conn = sqlite3.connect(self.database_path)
            cursor = conn.cursor()
            cursor.execute('SELECT id, password, name, balance FROM customers WHERE id = ?', (username,))
            result = cursor.fetchone()
            conn.close()
            
            if result and result[1] == password:
                return Customer(result[0], result[1], result[2], result[3])
            return None
        except Exception as e:
            print(f"Database error: {e}")
            return None

    def handle_login(self):
        username = self.username.text().strip()
        password = self.password.text().strip()
        
        if not username or not password:
            self.status.setText("Lütfen kullanıcı adı ve şifre girin.")
            return
            
        self.current_customer = self.authenticate_user(username, password)
        if self.current_customer:
            self.status.setText("")
            self.show_main_menu()
        else:
            self.status.setText("Hatalı kullanıcı adı veya şifre.")
    
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
        
        balance_title = QtWidgets.QLabel("Toplam Bakiye")
        balance_title.setStyleSheet("""
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
        
        balance_layout.addWidget(balance_title)
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
        content_layout.setSpacing(20)

        # Quick Actions title
        actions_title = QtWidgets.QLabel("Hızlı İşlemler")
        actions_title.setStyleSheet("""
            color: #1f2937;
            font-size: 18px;
            font-weight: 600;
        """)
        content_layout.addWidget(actions_title)

        # Action buttons in a grid
        actions_container = QtWidgets.QWidget()
        actions_grid = QtWidgets.QGridLayout(actions_container)
        actions_grid.setSpacing(10)
        actions_grid.setContentsMargins(0, 0, 0, 0)

        # Banking actions
        actions = [
            ("💰", "Bakiye", self.check_balance),
            ("💳", "Para Yatır", self.deposit_money),
            ("💸", "Para Çek", self.withdraw_money),
            ("🔄", "Transfer", self.transfer_money),
            ("📈", "Yatırım", self.stock_prices),
            ("💱", "Döviz", self.currency_rates)
        ]

        for i, (icon, text, callback) in enumerate(actions):
            action_btn = self.create_action_button(icon, text, callback)
            row = i // 2
            col = i % 2
            actions_grid.addWidget(action_btn, row, col)

        # Set equal column stretches
        actions_grid.setColumnStretch(0, 1)
        actions_grid.setColumnStretch(1, 1)
        
        content_layout.addWidget(actions_container)
        
        # Account section
        account_title = QtWidgets.QLabel("Hesap")
        account_title.setStyleSheet("""
            color: #1f2937;
            font-size: 18px;
            font-weight: 600;
            margin-top: 20px;
        """)
        content_layout.addWidget(account_title)

        # Account buttons
        account_info_btn = self.create_list_item("👤", "Hesap Bilgileri", self.account_info)
        history_btn = self.create_list_item("📊", "İşlem Geçmişi", self.transaction_history)
        
        content_layout.addWidget(account_info_btn)
        content_layout.addWidget(history_btn)
        content_layout.addStretch()

        layout.addWidget(content_section)

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
                 box-shadow: 0 2px 4px rgba(0, 0, 0, 0.05);
             }
             QPushButton:hover {
                 background: #f8fafc;
                 border: 1px solid #3b82f6;
                 transform: translateY(-2px);
                 box-shadow: 0 4px 12px rgba(59, 130, 246, 0.15);
             }
             QPushButton:pressed {
                 background: #f1f5f9;
                 transform: translateY(0px);
                 box-shadow: 0 2px 4px rgba(0, 0, 0, 0.05);
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
                backdrop-filter: blur(20px);
                border-radius: 20px;
                border: 1px solid rgba(255, 255, 255, 0.1);
                box-shadow: 0 8px 32px rgba(0, 0, 0, 0.1);
            }
            QFrame:hover {
                background: rgba(255, 255, 255, 0.12);
                border: 1px solid rgba(99, 102, 241, 0.3);
                transform: translateY(-5px);
                box-shadow: 0 12px 40px rgba(99, 102, 241, 0.15);
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
                transform: translateX(4px);
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
                transform: translateY(-2px);
                box-shadow: 0 4px 12px rgba(239, 68, 68, 0.3);
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
        symbols = ("AAPL", "MSFT", "GOOGL", "AMZN", "NVDA", "TSLA", "BABA", "META", "NFLX", "AMD", "CRM", "ORCL")
        try:
            quotes = fetch_stock_quotes(symbols)
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
            lines = [f"1 {code} = {value:.4f} TL" for code, value in rates.items()]
            AppMessageDialog.show_info(self, "Döviz Kurları", "\n".join(lines))
        except Exception as e:
            AppMessageDialog.show_error(self, "Döviz Kurları", f"Kurlar alınamadı: {e}")

    def currency_converter(self):
        AppMessageDialog.show_info(self, "Döviz Çevirici", "Döviz çevirici özelliği geliştiriliyor...")

    def account_info(self):
        info = f"Kullanıcı ID: {self.customer.id}\nİsim: {self.customer.name}\nBakiye: {self.customer.balance} TL"
        AppMessageDialog.show_info(self, "Hesap Bilgileri", info)

    def transaction_history(self):
        QtWidgets.QMessageBox.information(self, "İşlem Geçmişi", "İşlem geçmişi özelliği geliştiriliyor...")

    def logout(self):
        confirmed = AppMessageDialog.show_question(self, "Çıkış", "Çıkış yapmak istediğinizden emin misiniz?")
        if confirmed:
            self.close()
            login_window = ModernMainWindow()
            login_window.show()


class TransferDialog(QtWidgets.QDialog):
    def __init__(self, customer, database_path):
        super().__init__()
        self.customer = customer
        self.database_path = database_path
        self.setWindowTitle("Para Transfer")
        self.setFixedSize(400, 200)
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
            
            conn.commit()
            conn.close()
            
            AppMessageDialog.show_success(self, "Başarılı", f"{amount} TL {target[1]} kullanıcısına transfer edildi.")
            self.accept()
            
        except Exception as e:
            AppMessageDialog.show_error(self, "Hata", f"Transfer gerçekleştirilemedi: {e}")


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
                INSERT INTO customers (id, password, name, balance) VALUES (?, ?, ?, ?)
            ''', (user_id, password, name, 0))
            
            conn.commit()
            conn.close()
            
            self.accept()
            
        except Exception as e:
            AppMessageDialog.show_error(self, "Hata", f"Hesap oluşturulamadı: {e}")


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
