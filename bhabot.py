import requests
import yfinance as yf
import pandas as pd
import matplotlib.pyplot as plt
from datetime import datetime
from io import BytesIO
import time
import ta as ta

TOKEN = "6346404742:AAE__Qef0kikLEehZ6bq7VprTtZDyuRATZw"
user_data = {}
start_date = "2020-01-01"


def get_stocks_below_ema200():
    # TradingView'den verileri almak için API isteği yapalım
    url = "https://scanner.tradingview.com/turkey/scan"

    payload = {
        "filter": [
            {
                "left": "EMA200",
                "operation": "less",
                "right": 0
            }
        ],
        "options": {
            "active_symbols_only": True,
            "lang": "tr"
        },
        "symbols": {
            "query": {
                "types": []
            },
            "tickers": []
        }
    }

    response = requests.post(url, json=payload)
    if response.status_code == 200:
        data = response.json()
        if 'data' in data:
            for stock in data['data']:
                symbol = stock['d'][0]
                ema200 = stock['d'][1]
                print(f"{symbol}: EMA200: {ema200}")


get_stocks_below_ema200()


def send_message(chat_id, text):
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    params = {'chat_id': chat_id, 'text': text}
    requests.post(url, json=params)


def send_photo(chat_id, photo):
    url = f"https://api.telegram.org/bot{TOKEN}/sendPhoto"
    files = {"photo": ("chart.png", photo)}
    params = {"chat_id": chat_id}
    response = requests.post(url, params=params, files=files)
    return response.json()


def get_macd_rsi_data(symbol, start_date, end_date):
    data = yf.download(symbol, start=start_date, end=end_date)
    data['macd'] = ta.trend.macd_diff(data['Close'], window_fast=12, window_slow=26, window_sign=9)
    data['rsi'] = ta.momentum.rsi(data['Close'], window=14)
    return data


def get_ema_data(symbol, start_date, end_date):
    data = yf.download(symbol, start=start_date, end=end_date)
    ema5 = data['Close'].ewm(span=5, adjust=False).mean()
    ema9 = data['Close'].ewm(span=9, adjust=False).mean()
    ema200 = data['Close'].ewm(span=200, adjust=False).mean()
    ema377 = data['Close'].ewm(span=377, adjust=False).mean()
    ema610 = data['Close'].ewm(span=610, adjust=False).mean()

    ema_data = pd.DataFrame({
        'EMA5': ema5,
        'EMA9': ema9,
        'EMA200': ema200,
        'EMA377': ema377,
        'EMA610': ema610
    })

    return ema_data


def plot_ema_chart(ema_data, symbol, start_date, live_price=None):
    colors = ['black', 'lime', 'red', 'purple', 'orange']

    plt.figure(figsize=(12, 6))
    for i, col in enumerate(ema_data.columns):
        plt.plot(ema_data.index[-2:], ema_data[col].tail(2), color=colors[i], label=col)

        for i, value in enumerate(ema_data[col].tail(2)):
            plt.text(ema_data.index[-2:][i], value, f'{col}: {value:.2f}', fontsize=8, color=colors[i])

        plt.text(ema_data.index[-1], ema_data[col].iloc[-1], f'{col}: {ema_data[col].iloc[-1]:.2f}', fontsize=8,
                 color='black')

    plt.title(f'{symbol} EMA Analysis (Last 2 Days)')
    plt.xlabel('Date')
    plt.ylabel('EMA Values')
    plt.legend()

    current_date = datetime.today().strftime('%Y-%m-%d')
    plt.text(ema_data.index[-1], ema_data.iloc[-1].max(),
             f'Execution Date: {current_date}', ha='right', va='bottom', fontsize=8, color='black')

    if live_price is not None:
        plt.title(f'{symbol} EMA Analysis (Last 2 Days) - Price: {live_price:.2f}')
    else:
        plt.title(f'{symbol} Error')

    plt.grid(True)
    plt.legend()

    image_stream = BytesIO()
    plt.savefig(image_stream, format='png')
    image_stream.seek(0)

    return image_stream


def get_current_stock_price(symbol):
    try:
        stock = yf.Ticker(symbol)
        current_price = stock.history(period='1d')['Close'][-1]
        print(f"{symbol} anlık fiyat: {current_price}")
        return current_price
    except Exception as e:
        print(f"Hata: {e}")
        return None


def plot_stock_chart(stock_data, symbol):
    plt.figure(figsize=(12, 6))
    plt.plot(stock_data.index, stock_data['Close'], label=f'{symbol} Stock Price')
    plt.title(f'{symbol} Stock Price Chart with MACD and RSI')
    plt.xlabel('Date')
    plt.ylabel('Stock Price (USD)')
    plt.plot(stock_data.index, stock_data['macd'], label='MACD', linestyle='dashed')
    plt.legend(loc='upper left')
    ax2 = plt.gca().twinx()
    ax2.plot(stock_data.index, stock_data['rsi'], label='RSI', color='orange')
    ax2.set_ylabel('RSI')
    ax2.legend(loc='upper right')
    last_date = stock_data.index[-1]
    last_close = stock_data['Close'].iloc[-1]
    last_macd = stock_data['macd'].iloc[-1]
    last_rsi = stock_data['rsi'].iloc[-1]
    plt.text(last_date, last_close, f'Close: {last_close:.2f}', fontsize=8, color='black')
    plt.text(last_date, last_macd, f'MACD: {last_macd:.2f}', fontsize=8, color='black')
    plt.text(last_date, last_rsi, f'RSI: {last_rsi:.2f}', fontsize=8, color='black')
    plt.legend()
    stock_chart_stream = BytesIO()
    plt.savefig(stock_chart_stream, format='png')
    stock_chart_stream.seek(0)
    return stock_chart_stream


def main():
    while True:
        update_id = None
        while True:
            updates = requests.get(f"https://api.telegram.org/bot{TOKEN}/getUpdates?offset={update_id}").json()
            if len(updates["result"]) > 0:
                break
            time.sleep(1)

        if "message" in updates["result"][-1] and "text" in updates["result"][-1]["message"]:
            chat_id = updates["result"][-1]["message"]["chat"]["id"]
            user_message = updates["result"][-1]["message"]["text"]

            if user_message.startswith("/start") and 'started' not in user_data.get(chat_id, {}):
                user_data[chat_id] = {'started': True, 'photo_sent': False}
                send_message(chat_id, "Merhaba,/analyze hisse_adı.ıs şeklinde komutunuzu giriniz:")

            elif user_message.startswith("/analyze") and 'started' in user_data.get(chat_id, {}) and not user_data.get(
                    chat_id, {}).get('photo_sent', False):

                parts = user_message.split()

                if len(parts) != 2:
                    send_message(chat_id, "Hatalı Giriş. Lütfen doğru şekilde girdiğinizden emin olun.")
                else:
                    symbol = parts[1]
                    start_date = "2020-01-01"

                    # Get historical stock data
                    stock_data = yf.download(symbol, start=start_date, end=None)

                    # Calculate MACD and RSI
                    stock_data = get_macd_rsi_data(symbol, start_date, None)

                    # Plot stock chart with values
                    stock_chart_stream = plot_stock_chart(stock_data, symbol)
                    send_photo(chat_id, stock_chart_stream)

                    # Get EMA data and plot EMA chart (similar to your existing code)
                    ema_data = get_ema_data(symbol, start_date, None)
                    live_price = get_current_stock_price(symbol)
                    ema_chart_stream = plot_ema_chart(ema_data, symbol, start_date, live_price=live_price)
                    send_photo(chat_id, ema_chart_stream)

                    # Update user data
                    user_data[chat_id]['photo_sent'] = True

            elif user_message.startswith("/start") and 'started' in user_data.get(chat_id, {}):
                user_data[chat_id]['started'] = False
                user_data[chat_id]['photo_sent'] = False

            update_id = updates["result"][-1]["update_id"] + 1
        else:
            time.sleep(1)


if __name__ == '__main__':
    main()