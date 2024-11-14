# pip install yfinance colorama

import yfinance as yf
from colorama import Fore, Style, init

# Initialize colorama
init(autoreset=True)

def get_stock_price(symbol):
    data = yf.Ticker(symbol).history(period="1d")
    return data['Close'].iloc[-1]

def display_menu():
    print(f"{Fore.MAGENTA}Menu:")
    print(f"{Fore.CYAN}1. {Style.RESET_ALL}Get stock price")
    print(f"{Fore.CYAN}2. {Style.RESET_ALL}Exit{Style.RESET_ALL}")

def main():
    while True:
        display_menu()
        choice = input("Enter your choice: ")
        if choice == '1':
            stk = input("Enter the stock symbol: ")
            market_price = get_stock_price(stk)
            print(f"{Fore.GREEN}The current market price of {Fore.YELLOW}{stk}{Fore.GREEN} is {Fore.CYAN}{market_price}{Style.RESET_ALL}")
        elif choice == '2':
            print(f"{Fore.RED}Exiting...{Style.RESET_ALL}")
            break
        else:
            print(f"{Fore.RED}Invalid choice, please try again.{Style.RESET_ALL}")

if __name__ == "__main__":
    main()