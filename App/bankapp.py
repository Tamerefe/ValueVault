import os
import sqlite3
from currency_converter import CurrencyConverter
from rich.table import Table
from rich.console import Console
import pwinput
from urllib.request import urlopen
import xml.etree.ElementTree as ET
import yfinance as yf
from colorama import Fore, Style, init
import matplotlib.pyplot as plt
import pandas as pd
import datetime
from plyer import notification
from random import randrange

conn = sqlite3.connect('./App/database.db')
cursor = conn.cursor()

cursor.execute('''
    CREATE TABLE IF NOT EXISTS customers (
    id TEXT PRIMARY KEY,
    password TEXT,
    name TEXT,
    balance INTEGER
    )
''')
conn.commit()

class Customer():
    def __init__(self, ID, PASSWORD, NAME):
        self.id = ID
        self.password = PASSWORD
        self.name = NAME
        self.balance = 0

    def deposit(self, amount):
        self.balance += amount
        cursor.execute('UPDATE customers SET balance = ? WHERE id = ?', (self.balance, self.id))
        conn.commit()

    def withdraw(self, amount):
        if amount <= self.balance:
            self.balance -= amount
            cursor.execute('UPDATE customers SET balance = ? WHERE id = ?', (self.balance, self.id))
            conn.commit()
            return True
        else:
            return False

class Bank():
    def __init__(self):
        self.customers = list()

    def register_customer(self, ID, PASSWORD, NAME):
        cursor.execute('SELECT id FROM customers WHERE id = ?', (ID,))
        if cursor.fetchone():
            print("Customer ID already exists. Please choose a different ID.")
            return
        self.customers.append(Customer(ID, PASSWORD, NAME))
        cursor.execute('''
        INSERT INTO customers (id, password, name, balance) VALUES (?, ?, ?, ?)
        ''', (ID, PASSWORD, NAME, 0))
        conn.commit()
        print("Welcome to our Internet Banking")

    def find_customer(self, ID):
        cursor.execute('SELECT id, password, name, balance FROM customers WHERE id = ?', (ID,))
        result = cursor.fetchone()
        if result:
            customer = Customer(result[0], result[1], result[2])
            customer.balance = result[3]
            return customer
        return None

def currencyconverter(amount, fromto, tocurrency):
    return CurrencyConverter().convert(amount, fromto, tocurrency)

def authenticate(username, password):
    cursor.execute('SELECT password FROM customers WHERE id = ?', (username,))
    result = cursor.fetchone()
    if result and result[0] == password:
        return True
    return False

def int_to_roman(input):
    if not isinstance(input, type(1)):
        raise TypeError("expected integer, got %s" % type(input))
    if not 0 < input < 4000:
        raise ValueError("Argument must be between 1 and 3999")
    integers = (1000, 900, 500, 400, 100, 90, 50, 40, 10, 9, 5, 4, 1)
    numerals = ("M", "CM", "D", "CD", "C", "XC", "L", "XL", "X", "IX", "V", "IV", "I")
    result = []
    for i in range(len(integers)):
        count = int(input / integers[i])
        result.append(numerals[i] * count)
        input -= integers[i] * count
    return ''.join(result)

def get_current_date_in_roman():
    now = datetime.datetime.now()
    day = int_to_roman(now.day)
    month = int_to_roman(now.month)
    year = int_to_roman(now.year)
    return f"{day}/{month}/{year}"

def totalcoin(selected_coin):
    def applycoin(current_total):
        return current_total + selected_coin
    return applycoin

def get_valid_coin():
    while True:
        slctcoin = input("You can select 50c, 25c, 10c, 5c, 1c: ")
        if slctcoin in ("50", "25", "10", "5", "1"):
            return int(slctcoin)
        else:
            print("Invalid input. Please enter one of the following values: 50, 25, 10, 5, 1.")

def play_coin_guess_game():
    coinr = randrange(1, 101)
    ttlslctcoin = 0
    while True:
        slctcoin = get_valid_coin()
        ttlslctcoin = totalcoin(slctcoin)(ttlslctcoin)
        print(f"Your coin value is {ttlslctcoin}c")

        if ttlslctcoin == coinr:
            print("Congratulations! You won the game.")
            break
        elif ttlslctcoin > coinr:
            print("Sorry, you have exceeded the target value. You lose.")
            break

def main_menu():
    os.system("cls")
    date_in_roman = get_current_date_in_roman()
    print(Fore.GREEN + f"""
                                                                        {date_in_roman}
                    
                    Welcome to Dolliet's Mint-Looking Bank $

    """ + Style.RESET_ALL)
    print(Fore.CYAN + "    1) I am a Customer" + Style.RESET_ALL)
    print(Fore.CYAN + "    2) I Want to Become a Customer" + Style.RESET_ALL)
    print(Fore.CYAN + "    3) Search Current Currency Rates" + Style.RESET_ALL)
    print(Fore.CYAN + "    4) Customer List (Admin Only)" + Style.RESET_ALL)
    print(Fore.CYAN + "    5) Play Coin Guess Game" + Style.RESET_ALL)
    print("")

def customer_menu(customer):
    while True:
        os.system("cls")
        cursor.execute('SELECT balance FROM customers WHERE id = ?', (customer.id,))
        customer.balance = cursor.fetchone()[0]
        print(Fore.GREEN + "                                 Welcome Mr/Ms {}".format(customer.name) + Style.RESET_ALL)
        print(Fore.CYAN + """

        1) Check Balance
        2) Transfer Money
        3) Investment(Stocks, Bonds, ETFs, REITs, Mutual Funds)
        4) Currency Exchange
        Q) Exit

        """ + Style.RESET_ALL)
        choice = input(Fore.YELLOW + "Enter Transaction Number: " + Style.RESET_ALL)

        if choice == "1":
            cursor.execute('SELECT balance FROM customers WHERE id = ?', (customer.id,))
            customer.balance = cursor.fetchone()[0]
            print("Your Balance: {}".format(customer.balance))
            input("Press Enter to Return to Main Menu!")

        elif choice == "2":

            print(Fore.GREEN + "                                Welcome Mr/Ms {}".format(customer.name) + Style.RESET_ALL)
            print(Fore.CYAN + """

            1) Deposit Money [To Own Account]
            2) Deposit Money [To Another Account]
            3) Withdraw Money
            Q) Exit

            """ + Style.RESET_ALL)
            choice = input(Fore.YELLOW + "Enter Transaction Number: " + Style.RESET_ALL)

            if choice == "1":
                amount = int(input("Amount: "))
                confirmation = input("Do you confirm depositing {} TL to your own account? Y/N\n".format(amount))
                if confirmation.lower() == "y":
                    customer.deposit(amount)
                    notification.notify(
                        title = "Your money has been deposited!",
                        message = "You have successfully deposited {} TL to your account".format(amount),
                        app_name = "Dolliet's Mint-Looking Bank",
                        timeout = 10
                    )
                else:
                    print("Transaction Cancelled")
                input("Press Enter to Return to Main Menu")
            elif choice == "2":
                target_id = input("Customer ID: ")
                target_customer = bank.find_customer(target_id)
                if target_customer:
                    amount = int(input("Amount: "))
                    if amount <= customer.balance:
                        confirmation = input("Do you confirm depositing {} TL to {}'s account? Y/N\n".format(amount, target_customer.name))
                        if confirmation.lower() == "y":
                            customer.withdraw(amount)
                            target_customer.deposit(amount)
                            notification.notify(
                                title = "Money Transfer Successful!",
                                message = "You have successfully transferred {} TL to {}'s account".format(amount, target_customer.name),	
                                app_name = "Dolliet's Mint-Looking Bank",
                                timeout = 10
                            )
                        else:
                            print("Transaction Cancelled")
                    else:
                        print("Insufficient Balance, Transaction Cancelled")
                else:
                    print("Customer Not Found")
                input("Press Enter to Return to Main Menu")
            elif choice == "3":
                amount = int(input("Amount: "))
                if customer.withdraw(amount):
                    notification.notify(
                                title = "Transaction Completed, Please Take Your Money",
                                message = "You have withdrawn {} TL from your account".format(amount),	
                                app_name = "Dolliet's Mint-Looking Bank",
                                timeout = 10
                    )
                else:
                    print("Insufficient Balance, Transaction Cancelled")
                input("Press Enter to Return to Main Menu")
        elif choice == "3":
            init(autoreset=True)

            def get_stock_price(symbol):
                data = yf.Ticker(symbol).history(period="1d")
                return data['Close'].iloc[-1]

            def display_menu():
                print(f"{Fore.MAGENTA}Menu:")
                print(f"{Fore.CYAN}1. {Style.RESET_ALL}Get stock price")
                print(f"{Fore.CYAN}2. {Style.RESET_ALL}Get stock chart{Style.RESET_ALL}")
                print(f"{Fore.CYAN}q. {Style.RESET_ALL}Exit{Style.RESET_ALL}")
            def investment_menu():
                while True:
                    display_menu()
                    choice = input("Enter your choice: ")
                    if choice == '1':
                        stk = input("Enter the stock symbol: ")
                        market_price = get_stock_price(stk)
                        print(f"{Fore.GREEN}The current market price of {Fore.YELLOW}{stk}{Fore.GREEN} is {Fore.CYAN}{market_price}{Style.RESET_ALL}")
                        input(Fore.YELLOW + "Press Enter to Return to Main Menu" + Style.RESET_ALL)
                    elif choice == '2':
                        ticker = input("Enter the stock symbol: ")
                        data = yf.download(ticker, start="2023-01-01", end="2023-12-31")
                        plt.figure(figsize=(12, 6))
                        plt.plot(data['Close'], label=f'{ticker} Closing Price')
                        plt.title(f'{ticker} Stock Price Chart')
                        plt.xlabel('Date')
                        plt.ylabel('Price ($)')
                        plt.legend()
                        plt.grid()
                        plt.show()
                        input(Fore.YELLOW + "Press Enter to Return to Main Menu" + Style.RESET_ALL)
                    elif choice == 'q' or choice == 'Q':
                        print(f"{Fore.RED}Exiting...{Style.RESET_ALL}")
                        break
                    else:
                        input(Fore.YELLOW + "Press Enter to Return to Main Menu" + Style.RESET_ALL)

            investment_menu()
        elif choice == "4": 
            try:
                response = urlopen('http://www.tcmb.gov.tr/kurlar/today.xml')
                xml = ET.parse(response)
                root = xml.getroot()

                print(Fore.YELLOW + "Currency To TL" + Style.RESET_ALL)
                print('-' * 40)
                for i in root.findall('Currency'):
                    currency_name = i.find('CurrencyName').text or 'N/A'
                    forex_buying = i.find('ForexBuying').text or 'N/A'
                    forex_selling = i.find('ForexSelling').text or 'N/A'

                    print(Fore.CYAN + f"{currency_name}" + Style.RESET_ALL)
                    print(Fore.GREEN + f"  Forex Buying: {forex_buying}" + Style.RESET_ALL)
                    print(Fore.RED + f"  Forex Selling: {forex_selling}" + Style.RESET_ALL)
                    print('-' * 40)
            except Exception as e:
                print(Fore.RED + f"An error occurred: {e}" + Style.RESET_ALL)
            input(Fore.YELLOW + "Press Enter to Return to Main Menu" + Style.RESET_ALL)   
        elif choice.lower() == "q":
            break

        else:
            print(Fore.RED + "Invalid Choice, Please Try Again" + Style.RESET_ALL)
            input(Fore.YELLOW + "Press Enter to Return to Main Menu" + Style.RESET_ALL)

def display_customer_list():
    cursor.execute('SELECT id, name, balance FROM customers')
    customers = cursor.fetchall()
    
    console = Console()
    table = Table(title="Customer List")
    
    table.add_column("ID", style="blue", no_wrap=True)
    table.add_column("Name", style="purple")
    table.add_column("Balance", style="yellow")
    
    for customer in customers:
        table.add_row(customer[0], customer[1], str(customer[2]))
    
    console.print(table)

bank = Bank()

while True:
    main_menu()
    try:
        choice = int(input("Your Choice: "))
    except ValueError:
        print("Please enter a valid number.")
        continue

    if choice == 1:
        ID = input("ID: ")
        customer = bank.find_customer(ID)
        if customer:
            password = pwinput.pwinput("Enter Your Password: ", mask='*')
            if authenticate(ID, password):
                customer_menu(customer)
            else:
                print("Incorrect Password")
                input("Press Enter to Return to Main Menu")
        else:
            print("Customer Not Found")
            input("Press Enter to Return to Main Menu")

    elif choice == 2:
        ID = input("Enter ID: ")
        NAME = input("Enter Name: ")
        PASSWORD = pwinput.pwinput("Enter Password: ", mask='*')
        bank.register_customer(ID, PASSWORD, NAME)
        input("Press Enter to Return to Main Menu")

    elif choice == 3:
        
        amount = int(input("Enter Amount: "))
        fromto = input("Enter Currency to Convert From: ")
        tocurrency = input("Enter Currency to Convert To: ")
        print("{} {} is equal to {} {}".format(amount,fromto,currencyconverter(amount, fromto, tocurrency),tocurrency))
        input("Press Enter to Return to Main Menu")

    elif choice == 4:
        adminpass = pwinput.pwinput("Enter Password: ", mask='*')
        if adminpass == "adminpass":  # Replace with a secure method to check admin password
            display_customer_list()
        else:
            print("Incorrect Password")
            print(Fore.RED + "Hint: adminpass" + Style.RESET_ALL)
        input("Press Enter to Return to Main Menu")

    elif choice == 5:
        play_coin_guess_game()
        input("Press Enter to Return to Main Menu")

    else:
        print("Something Went Wrong, Maybe You Made an Invalid Choice")
        input("Press Enter to Return to Main Menu")