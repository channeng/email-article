import os
import shutil
import logging
import requests
import pathlib
from io import StringIO
import time
from datetime import date, datetime, timedelta

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import seaborn as sns

from app.tickers import get_ticker_recommendations_df
from config import Config
from IPython import embed

sns.set()


def _get_response(ticker, output_type="compact"):
        """Get daily historical data for given ticker from AlphaVantage API.

        Args:
            output_type: If 'compact', retrieve data only for past 100 days.
                         If 'full', retrieve data for the past 20 years.
        """

        url = (
            "https://www.alphavantage.co/query?"
            "function=TIME_SERIES_DAILY_ADJUSTED&symbol={ticker}&"
            "outputsize={output_type}&datatype=csv&apikey={api_key}"
        ).format(
            ticker=ticker,
            output_type=output_type,
            api_key=Config.ALPHAVANTAGE_API_KEY
        )
        return requests.get(url)


def _try_get_response(ticker, output_type, delay=16, max_tries=5):
    response_ok = False
    timeout = 0
    request_count = 0
    while not response_ok and request_count <= max_tries:
        request_count += 1
        time.sleep(timeout)
        logging.info(
            "Retrieving data: {} - {}  num_requests: {}".format(
                ticker, output_type, request_count))
        response = _get_response(ticker, output_type=output_type)
        response_ok = response.status_code == 200
        timeout += delay
    return response


def _get_df_from_response(response):
    """Create Pandas DataFrame sorted by date as index."""
    response_io = StringIO(response.text)
    df = pd.read_csv(response_io)
    df["date"] = pd.to_datetime(df["timestamp"], format='%Y-%m-%d')
    df = df.drop("timestamp", axis="columns")
    df = df.set_index("date")
    df = df.sort_index()
    return df


def get_ticker_df(
        ticker, output_type="full", df_start_date=datetime(2017, 1, 1)):
    response = _try_get_response(ticker, output_type)
    df = _get_df_from_response(response)
    if df_start_date is not None:
        df = df[df.index > df_start_date]
    df = df[["close"]]
    return df


def merge_ticker_df(ticker):
    # Construct ticker and recommendations df
    datetime_one_year_ago = datetime.combine(
        datetime.today(), datetime.min.time()) - timedelta(days=365)

    recommendations_df, currency = get_ticker_recommendations_df(ticker)
    if recommendations_df is None:  # noqa
        return None, currency

    ticker_df = get_ticker_df(ticker, df_start_date=datetime_one_year_ago)
    ticker_df = ticker_df[ticker_df["close"] > 0]
    ticker_df = ticker_df.merge(recommendations_df, how="left", on="date")
    for buy_or_sell in ["buy", "sell"]:
        to_buy_or_sell = (
            ticker_df["recommendation"].shift(1) == buy_or_sell)
        ticker_df[buy_or_sell] = ticker_df[to_buy_or_sell]["close"]
        to_double = (
            to_buy_or_sell & ticker_df["is_strong"].shift(1))
        ticker_df["{}_double".format(buy_or_sell)] = (
            ticker_df[to_double]["close"])

    return ticker_df, currency


def _plot_x_df(x_df, ax, buy_color="green", sell_color="red"):
    has_grouped = False
    if "to_double_buy" in x_df.columns:
        has_grouped = True

    x_df.plot(ax=ax, y="close", color="lightblue", marker="o")
    x_df.plot(ax=ax, y="sell", color=sell_color, marker="o")
    x_df.plot(ax=ax, y="buy", color=buy_color, marker="o")
    if has_grouped:
        x_df.plot(
            ax=ax, y="sell_double", color=sell_color, marker="x", ms=15)
        x_df.plot(
            ax=ax, y="buy_double", color=buy_color, marker="x", ms=15)


def simulate(ticker_df):
    buy_sell_df = ticker_df[
        ~np.isnan(ticker_df["buy"]) | ~np.isnan(ticker_df["sell"])
    ][["close", "buy", "sell"]].fillna(0)
    buy_sell_list = []
    for row in buy_sell_df.values:
        _, buy, sell = row
        buy_sell_list.append(sell - buy)

    stocks_inventory = []
    purchase_list = []
    num_stocks_list = []
    max_num_stocks = 3
    for val in buy_sell_list:
        if val >= 0 and len(stocks_inventory) == 0:
            purchase_list.append(0)
        elif val < 0 and len(stocks_inventory) < max_num_stocks:
            stocks_inventory.append(val)
            purchase_list.append(val)
        elif val < 0:
            purchase_list.append(0)
        elif val >= 0:
            stocks_inventory = stocks_inventory[1:]
            purchase_list.append(val)
        num_stocks_list.append(len(stocks_inventory))

    buy_sell_df["simulated_purchases"] = purchase_list
    buy_sell_df["num_stocks_held"] = num_stocks_list
    return buy_sell_df


def create_directory(dir):
    # To do recursive dir creation
    # Don't use subprocess in low-memory conditions
    # cmd = 'mkdir -p {}'.format(dir)
    # subprocess.check_output(['bash', '-c', cmd])
    pathlib.Path(dir).mkdir(parents=True, exist_ok=True)


def plot_ticker_df(ticker):
    plots_dir = "app/static/ticker_plots"
    ticker_plot_filename = "{}.png".format(ticker.lower().replace(".", ""))
    ticker_plot_filepath = os.path.join(plots_dir, ticker_plot_filename)
    plot_exists = False
    date_today = date.today()
    try:
        plots = os.listdir(plots_dir)
        if ticker_plot_filename in plots:
            last_modified_date = date.fromtimestamp(
                os.path.getmtime(
                    os.path.join(plots_dir, ticker_plot_filename)))
            if last_modified_date == date_today:
                plot_exists = True
                return date_today.strftime("%Y-%m-%d"), plot_exists

        for plot in plots:
            if plot.split(".")[0] == ticker.lower():
                os.remove(os.path.join(plots_dir, plot))

    except FileNotFoundError:  # noqa
        create_directory(plots_dir)

    temp_dir = "/tmp/ticker_plots"
    create_directory(temp_dir)
    temp_ticker_plot_filepath = os.path.join(temp_dir, ticker_plot_filename)

    ticker_df, currency = merge_ticker_df(ticker)
    if ticker_df is None:
        return False, False

    buy_sell_df = simulate(ticker_df)
    last_row = buy_sell_df.tail(1)
    total_profit = buy_sell_df["simulated_purchases"].sum() + (
        last_row["close"] * last_row["num_stocks_held"]).values[0]
    embed()

    # save_ensemble_test_plot
    plot_colors = {
        'xtick.color': Config.PLOT_FORMATTING["text_color"],
        'ytick.color': Config.PLOT_FORMATTING["text_color"],
        'xtick.labelsize': Config.PLOT_FORMATTING["font_size"],
        'ytick.labelsize': Config.PLOT_FORMATTING["font_size"],
        'axes.labelsize': Config.PLOT_FORMATTING["font_size"],
        'text.color': Config.PLOT_FORMATTING["text_color"],
        'axes.labelcolor': Config.PLOT_FORMATTING["text_color"],
        'grid.color': Config.PLOT_FORMATTING["inner_grid_color"],
        'axes.edgecolor': Config.PLOT_FORMATTING["outer_grid_color"],
    }
    with plt.rc_context(plot_colors):
        fig, ax1 = plt.subplots(
            1, 1, figsize=Config.PLOT_FORMATTING["figsize"])
        # fig.suptitle("Predictions on Test period", fontsize=18)
        _plot_x_df(
            ticker_df, ax1,
            buy_color=Config.PLOT_FORMATTING["buy_color"],
            sell_color=Config.PLOT_FORMATTING["sell_color"])

        # Fix duplicate xticks
        last_date = ax1.get_xticks()[::-1][0]
        new_xticks = []
        for d in ax1.get_xticks()[::-1][1:]:
            if last_date - d > 3:
                new_xticks.append(d)
            last_date = d
        new_xticks = new_xticks[::-1]
        new_xticks.append(ax1.get_xticks()[::-1][0])
        ax1.set_xticks(new_xticks)
        ax1.xaxis.set_major_formatter(mdates.DateFormatter("%b '%y"))
        ax1.set_ylabel(currency)
        plt.savefig(
            temp_ticker_plot_filepath,
            bbox_inches='tight',
            transparent=True,
            facecolor=Config.PLOT_FORMATTING["background_color"]
        )

    plt.close()

    # Replace existing ticker plot
    shutil.move(temp_ticker_plot_filepath, ticker_plot_filepath)

    return date_today.strftime("%Y-%m-%d"), plot_exists
