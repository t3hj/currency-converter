import requests
from datetime import datetime, timedelta
import configparser
import matplotlib.pyplot as plt
import logging
import time
import json
import os
import tkinter as tk
from tkinter import ttk, messagebox
from tkcalendar import DateEntry

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
            if response.status_code == 429:
                delay = min(delay * 2, 60)  # Exponential backoff with a max delay of 60 seconds
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

# List of valid ISO 4217 currency codes
valid_codes = ["USD", "EUR", "GBP", "JPY", "AUD", "CAD", "CHF", "CNY", "SEK", "NZD"]

def validate_currency_code(code):
    return code in valid_codes

def create_currency_dropdown(parent, row, label_text):
    ttk.Label(parent, text=label_text).grid(column=0, row=row, padx=10, pady=5)
    currency_var = tk.StringVar()
    currency_dropdown = ttk.Combobox(parent, textvariable=currency_var, values=valid_codes, state="readonly")
    currency_dropdown.grid(column=1, row=row, padx=10, pady=5)
    return currency_var

def create_date_picker(parent, row, label_text):
    ttk.Label(parent, text=label_text).grid(column=0, row=row, padx=10, pady=5)
    date_var = tk.StringVar()
    date_entry = DateEntry(parent, textvariable=date_var, date_pattern='dd-MM-yyyy')
    date_entry.grid(column=1, row=row, padx=10, pady=5)
    return date_var

def on_convert():
    try:
        amount = float(amount_entry.get())
    except ValueError:
        messagebox.showerror("Invalid Input", "Please enter a numeric value for the amount.")
        return

    from_currency = from_currency_var.get()
    if not validate_currency_code(from_currency):
        messagebox.showerror("Invalid Input", "Please select a valid ISO 4217 currency code for the from currency.")
        return

    to_currency = to_currency_var.get()
    if not validate_currency_code(to_currency):
        messagebox.showerror("Invalid Input", "Please select a valid ISO 4217 currency code for the to currency.")
        return

    date_input = date_var.get()
    if date_input:
        try:
            date = datetime.strptime(date_input, "%d-%m-%Y").date()
        except ValueError:
            messagebox.showerror("Invalid Input", "Please enter the date in DD-MM-YYYY format.")
            return
    else:
        date = datetime.today().date()

    if date < datetime(1999, 1, 1).date():
        messagebox.showerror("Invalid Input", "Historical data is only available from 1999 onwards.")
        return

    progress_bar.start()
    root.after(100, lambda: fetch_conversion(api_key, amount, from_currency, to_currency, date))

def fetch_conversion(api_key, amount, from_currency, to_currency, date):
    amount_on_date = convert_currency(api_key, amount, from_currency, to_currency, date)
    amount_today = convert_currency(api_key, amount, from_currency, to_currency)
    progress_bar.stop()

    if amount_on_date is not None and amount_today is not None:
        result_label.config(text=f"On {date}, {amount} {from_currency} was equal to {amount_on_date:.2f} {to_currency}\n"
                                 f"Today, {amount} {from_currency} is equal to {amount_today:.2f} {to_currency}\n"
                                 f"The change in value from {date} to today is {amount_today - amount_on_date:.2f} {to_currency}")
    else:
        result_label.config(text="Error: Unable to convert currencies.")

def on_plot():
    start_date_input = start_date_var.get()
    end_date_input = end_date_var.get()

    try:
        start_date = datetime.strptime(start_date_input, "%d-%m-%Y").date()
        end_date = datetime.strptime(end_date_input, "%d-%m-%Y").date()
    except ValueError:
        messagebox.showerror("Invalid Input", "Please enter the dates in DD-MM-YYYY format.")
        return

    if start_date > end_date:
        messagebox.showerror("Invalid Input", "Start date must be before end date.")
        return

    progress_bar.start()
    root.after(100, lambda: fetch_plot(api_key, from_currency_var.get(), to_currency_var.get(), start_date, end_date))

def fetch_plot(api_key, from_currency, to_currency, start_date, end_date):
    plot_exchange_rate(api_key, from_currency, to_currency, start_date, end_date)
    progress_bar.stop()

def main():
    global api_key, amount_entry, from_currency_var, to_currency_var, date_var, result_label, start_date_var, end_date_var, progress_bar, root

    # Load configuration
    config = configparser.ConfigParser()
    config.read('config.ini')
    api_key = config['DEFAULT']['API_KEY']

    root = tk.Tk()
    root.title("Currency Converter")

    ttk.Label(root, text="Amount:").grid(column=0, row=0, padx=10, pady=5)
    amount_entry = ttk.Entry(root)
    amount_entry.grid(column=1, row=0, padx=10, pady=5)

    from_currency_var = create_currency_dropdown(root, 1, "From Currency:")
    to_currency_var = create_currency_dropdown(root, 2, "To Currency:")

    date_var = create_date_picker(root, 3, "Date (DD-MM-YYYY):")

    convert_button = ttk.Button(root, text="Convert", command=on_convert)
    convert_button.grid(column=0, row=4, columnspan=2, padx=10, pady=10)

    result_label = ttk.Label(root, text="")
    result_label.grid(column=0, row=5, columnspan=2, padx=10, pady=10)

    start_date_var = create_date_picker(root, 6, "Start Date for Graph (DD-MM-YYYY):")
    end_date_var = create_date_picker(root, 7, "End Date for Graph (DD-MM-YYYY):")

    plot_button = ttk.Button(root, text="Plot Exchange Rate", command=on_plot)
    plot_button.grid(column=0, row=8, columnspan=2, padx=10, pady=10)

    progress_bar = ttk.Progressbar(root, mode='indeterminate')
    progress_bar.grid(column=0, row=9, columnspan=2, padx=10, pady=10)

    root.mainloop()

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nProcess interrupted by user. Exiting...")
