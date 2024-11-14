import yfinance as yf
import matplotlib.pyplot as plt
import pandas as pd

# Select a specific stock symbol and time range (e.g., 'AAPL' for Apple)
ticker = input("Enter the stock symbol: ")
data = yf.download(ticker, start="2023-01-01", end="2023-12-31")

# Prepare data to plot closing prices
plt.figure(figsize=(12, 6))
plt.plot(data['Close'], label=f'{ticker} Closing Price')
plt.title(f'{ticker} Stock Price Chart')
plt.xlabel('Date')
plt.ylabel('Price ($)')
plt.legend()
plt.grid()
plt.show()
