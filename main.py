import requests
from datetime import datetime, timedelta
import configparser
import matplotlib.pyplot as plt
import logging
import time
import json
import os

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

CACHE_FILE = 'exchange_rate_cache.json'

def load_cache():
    if os.path.exists(CACHE_FILE):
        with open(CACHE_FILE, 'r') as f:
            return json.load(f)
    return {}

def save_cache(cache):
    with open(CACHE_FILE, 'w') as f:
        json.dump(cache, f)

def get_exchange_rate(api_key, from_currency, date=None, retries=5, delay=10):
    cache = load_cache()
    cache_key = f"{from_currency}_{date}"
    
    if cache_key in cache:
        return cache[cache_key]
    
    if date:
        url = f"https://api.apilayer.com/exchangerates_data/{date}?base={from_currency}"
    else:
        url = f"https://api.apilayer.com/exchangerates_data/latest?base={from_currency}"
    
    headers = {
        'apikey': api_key
    }
    
    for attempt in range(retries):
        try:
            response = requests.get(url, headers=headers)
            response.raise_for_status()  # Raise an HTTPError for bad responses
            data = response.json()
            rates = data.get('rates')
            cache[cache_key] = rates
            save_cache(cache)
            return rates
        except requests.exceptions.RequestException as e:
            logging.error(f"Error fetching exchange rates: {e}")
            if attempt < retries - 1:
                time.sleep(delay)  # Wait before retrying
            else:
                return None

def convert_currency(api_key, amount, from_currency, to_currency, date=None):
    rates = get_exchange_rate(api_key, from_currency, date)
    if rates and to_currency in rates:
        converted_amount = amount * rates[to_currency]
        return converted_amount
    else:
        logging.error(f"Error: Unable to convert from {from_currency} to {to_currency}.")
        return None

def plot_exchange_rate(api_key, from_currency, to_currency, start_date, end_date):
    dates = []
    rates = []
    current_date = start_date

    while current_date <= end_date:
        rate = get_exchange_rate(api_key, from_currency, current_date)
        if rate and to_currency in rate:
            dates.append(current_date)
            rates.append(rate[to_currency])
        current_date += timedelta(days=1)

    plt.figure(figsize=(10, 5))
    plt.plot(dates, rates, marker='o')
    plt.title(f'Exchange Rate from {from_currency} to {to_currency}')
    plt.xlabel('Date')
    plt.ylabel(f'Exchange Rate ({to_currency})')
    plt.grid(True)
    plt.show()

def validate_currency_code(code):
    # List of valid ISO 4217 currency codes
    valid_codes = ["USD", "EUR", "GBP", "JPY", "AUD", "CAD", "CHF", "CNY", "SEK", "NZD"]
    return code in valid_codes

def main():
    print("Welcome to the Currency Converter!")
    
    # Load configuration
    config = configparser.ConfigParser()
    config.read('config.ini')
    api_key = config['DEFAULT']['API_KEY']
    
    try:
        amount = float(input("Enter the amount: "))
    except ValueError:
        print("Invalid amount. Please enter a numeric value.")
        return

    from_currency = input("Enter the from currency (e.g., USD): ").upper()
    if not validate_currency_code(from_currency):
        print("Invalid currency code. Please enter a valid ISO 4217 currency code.")
        return

    to_currency = input("Enter the to currency (e.g., EUR): ").upper()
    if not validate_currency_code(to_currency):
        print("Invalid currency code. Please enter a valid ISO 4217 currency code.")
        return
    
    # Prompt for date in UK format
    date_input = input("Enter the date for historical exchange rates (DD-MM-YYYY) to see past values, or press Enter for today's date: ")
    if date_input:
        try:
            date = datetime.strptime(date_input, "%d-%m-%Y").date()
        except ValueError:
            print("Invalid date format. Please enter the date in DD-MM-YYYY format.")
            return
    else:
        date = datetime.today().date()
    
    # Check if the date is within the supported range
    if date < datetime(1999, 1, 1).date():
        print("Error: Historical data is only available from 1999 onwards.")
        return
    
    # Calculate the value on the given date
    amount_on_date = convert_currency(api_key, amount, from_currency, to_currency, date)
    
    # Calculate the value today
    amount_today = convert_currency(api_key, amount, from_currency, to_currency)
    
    if amount_on_date is not None and amount_today is not None:
        print(f"On {date}, {amount} {from_currency} was equal to {amount_on_date:.2f} {to_currency}")
        print(f"Today, {amount} {from_currency} is equal to {amount_today:.2f} {to_currency}")
        change = amount_today - amount_on_date
        print(f"The change in value from {date} to today is {change:.2f} {to_currency}")
    
    # Prompt for date range for graphical output
    start_date_input = input("Enter the start date for the graph (DD-MM-YYYY): ")
    end_date_input = input("Enter the end date for the graph (DD-MM-YYYY): ")
    
    try:
        start_date = datetime.strptime(start_date_input, "%d-%m-%Y").date()
        end_date = datetime.strptime(end_date_input, "%d-%m-%Y").date()
    except ValueError:
        print("Invalid date format. Please enter the dates in DD-MM-YYYY format.")
        return
    
    plot_exchange_rate(api_key, from_currency, to_currency, start_date, end_date)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nProcess interrupted by user. Exiting...")
