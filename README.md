# Stock Market Analysis and Trading Bot

This project includes a Python and C program to analyze stock prices and determine the best times to buy and sell. It also includes a Python script to display exchange rates.

## Project Structure

### C Folder

- **bot.c**: A C program that analyzes stock prices and determines the best times to buy and sell.
- **bot.exe**: The compiled version of `bot.c`.
- **graph.txt**: A file containing stock price data.

### Python Folder

- **chart.py**: A Python script that plots the closing prices of a specific stock.
- **forex.py**: A Python script that displays exchange rates.
- **value.py**: A Python script that displays stock prices and presents a menu to the user.

## Usage

### C Program

1. Fill the `graph.txt` file with appropriate stock price data.
2. Compile and run the `bot.c` file:
    ```sh
    gcc -o bot bot.c
    ./bot
    ```

### Python Scripts

#### chart.py

1. Install the required libraries:
    ```sh
    pip install yfinance matplotlib pandas
    ```
2. Run the `chart.py` file and enter the stock symbol:
    ```sh
    python chart.py
    ```

#### forex.py

1. Install the required libraries:
    ```sh
    pip install termcolor
    ```
2. Run the `forex.py` file:
    ```sh
    python forex.py
    ```

#### value.py

1. Install the required libraries:
    ```sh
    pip install yfinance colorama
    ```
2. Run the `value.py` file:
    ```sh
    python value.py
    ```

## License

This project is licensed under the [MIT License](LICENSE.md).