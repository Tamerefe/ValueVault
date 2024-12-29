import os
import sqlite3
from currency_converter import CurrencyConverter
from rich.table import Table
from rich.console import Console

conn = sqlite3.connect('./BankApp/database.db')
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

def main_menu():
    os.system("cls")
    print("""

                    Welcome to Dolliet's Mint-Looking Bank $

    1) I am a Customer
    2) I Want to Become a Customer
    3) Search Current Currency Rates
    4) Customer List (Admin Only)

    """)

def customer_menu(customer):
    while True:
        os.system("cls")
        cursor.execute('SELECT balance FROM customers WHERE id = ?', (customer.id,))
        customer.balance = cursor.fetchone()[0]
        print("                                 Welcome Mr/Ms {}".format(customer.name))
        print("""

        1) Check Balance
        2) Deposit Money [To Own Account]
        3) Deposit Money [To Another Account]
        4) Withdraw Money
        Q) Exit

        """)
        choice = input("Enter Transaction Number: ")

        if choice == "1":
            cursor.execute('SELECT balance FROM customers WHERE id = ?', (customer.id,))
            customer.balance = cursor.fetchone()[0]
            print("Your Balance: {}".format(customer.balance))
            input("Press Enter to Return to Main Menu!")

        elif choice == "2":
            amount = int(input("Amount: "))
            confirmation = input("Do you confirm depositing {} TL to your own account? Y/N\n".format(amount))
            if confirmation.lower() == "y":
                customer.deposit(amount)
                print("Your money has been deposited!")
            else:
                print("Transaction Cancelled")
            input("Press Enter to Return to Main Menu")

        elif choice == "3":
            target_id = input("Customer ID: ")
            target_customer = bank.find_customer(target_id)
            if target_customer:
                amount = int(input("Amount: "))
                if amount <= customer.balance:
                    confirmation = input("Do you confirm depositing {} TL to {}'s account? Y/N\n".format(amount, target_customer.name))
                    if confirmation.lower() == "y":
                        customer.withdraw(amount)
                        target_customer.deposit(amount)
                        print("Money Transferred!")
                    else:
                        print("Transaction Cancelled")
                else:
                    print("Insufficient Balance, Transaction Cancelled")
            else:
                print("Customer Not Found")
            input("Press Enter to Return to Main Menu")

        elif choice == "4":
            amount = int(input("Amount: "))
            if customer.withdraw(amount):
                print("Transaction Completed, Please Take Your Money")
            else:
                print("Insufficient Balance, Transaction Cancelled")
            input("Press Enter to Return to Main Menu")

        elif choice.lower() == "q":
            break

        else:
            print("Invalid Choice, Please Try Again")
            input("Press Enter to Return to Main Menu")

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
            password = input("Enter Your Password: ")
            if password == customer.password:
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
        PASSWORD = input("Enter Password: ")
        bank.register_customer(ID, PASSWORD, NAME)
        input("Press Enter to Return to Main Menu")

    elif choice == 3:
        
        amount = int(input("Enter Amount: "))
        fromto = input("Enter Currency to Convert From: ")
        tocurrency = input("Enter Currency to Convert To: ")
        print("{} {} is equal to {} {}".format(amount,fromto,currencyconverter(amount, fromto, tocurrency),tocurrency))
        break

    elif choice == 4:
        adminpass = int(input("Enter Password: "))
        if(adminpass == 1234):
            display_customer_list()    
        input("Press Enter to Return to Main Menu")

    else:
        print("Something Went Wrong, Maybe You Made an Invalid Choice")
        input("Press Enter to Return to Main Menu")