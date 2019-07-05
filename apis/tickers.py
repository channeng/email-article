from datetime import datetime, timedelta
import json

from flask import jsonify, request
from flask_basicauth import BasicAuth
from flask_restful import Resource

from app import db
from app.tickers_plot import plot_ticker_df
from app.tickers import (
    get_ticker_emails, update_ticker_data, delete_ticker,
    get_tickers, get_ticker_recommendations_for_user,
    get_all_users_tickers, get_all_tickers, create_ticker_recommendations)

basic_auth = BasicAuth()


def stocks_recommendations_for_user(user_id):
    tickers = get_tickers(user_id)
    results = get_ticker_recommendations_for_user(
        db, user_id, num_results=len(tickers))

    ticker_recommendations = {}
    for ticker in tickers:
        ticker_recommendations[ticker.id] = {
            "recommendation": None,
            "is_strong": False,
            "closing_date": datetime.strptime(
                ticker.latest_trading_day, "%Y-%m-%d")
        }

    for row in results:
        ticker_id, closing_date, recommendation, is_strong = row
        closing_date = datetime.strptime(closing_date, "%Y-%m-%d")
        timedelta_diff = (
            closing_date - ticker_recommendations[ticker_id]["closing_date"])
        if timedelta_diff >= timedelta(days=0):
            recommend = recommendation.title()
            ticker_recommendations[ticker_id]["recommendation"] = recommend
            ticker_recommendations[ticker_id]["is_strong"] = is_strong == 1

    return tickers, ticker_recommendations


# Ticker API
class TickerEmails(Resource):
    @basic_auth.required
    def get(self):
        ticker = request.form.get("ticker", None)
        limit = int(request.form.get("limit", 100))
        result = get_ticker_emails(db, ticker=ticker, limit=limit)
        result_dict = {}
        for row in result:
            emails = row[5].split(",")
            if emails:
                result_dict[row[1]] = {
                    "ticker_id": row[0],
                    "name": row[2],
                    "currency": row[3],
                    "has_recommendations": row[4] == 1,
                    "emails": emails
                }
        return jsonify(result_dict)


class UpdateTicker(Resource):
    @basic_auth.required
    def post(self):
        ticker = str(request.form.get("ticker", None))
        if ticker is None:
            return jsonify({"error": "Ticker must be provided."})
        update_details = request.form.get("update_details", "false")
        update_details = update_details.lower() == "true"
        result = update_ticker_data(
            db, ticker, update_details=update_details)
        return jsonify(dict(result))


class DeleteTicker(Resource):
    @basic_auth.required
    def post(self):
        ticker = str(request.form.get("ticker", None))
        if ticker is None:
            return jsonify({"error": "Ticker must be provided."})
        set_active = request.form.get("set_active", "false")
        set_active = set_active.lower() == "true"
        result = delete_ticker(db, ticker, set_active=set_active)
        return jsonify(dict(result))


class GetAllTickers(Resource):
    @basic_auth.required
    def get(self):
        limit = int(request.form.get("limit", 100))
        results = get_all_tickers(num_results=limit)
        tickers_list = []
        for ticker, last_updated in results:
            tickers_list.append({
                "ticker": ticker,
                "last_updated": last_updated
            })

        return jsonify(dict({
            "all_tickers": tickers_list
        }))


class AddTickerRecommendations(Resource):
    @basic_auth.required
    def post(self):
        """Batch endpoint for creating recommendations for given ticker."""

        ticker = request.form.get("ticker", None)
        model_version = request.form.get("model_version", None)
        data_str = request.form.get("recommendations", None)
        if ticker is None or model_version is None or data_str is None:
            return jsonify({
                "error": (
                    "Ticker, model_version and recommendations "
                    "must be provided.")
            })

        # Validate recommendations data structure
        recommendations = json.loads(data_str)
        for closing_date, recommendation in recommendations.items():
            keys = list(recommendation.keys())
            validate_keys = (
                "buy_or_sell" in keys and
                "closing_price" in keys and
                "is_strong" in keys
            )
            if not validate_keys:
                return jsonify({
                    "error": (
                        "Recommendation keys does not consist of "
                        "'buy_or_sell', 'closing_price' or 'is_strong' for "
                        "the closing date {}.".format(closing_date))
                })

        result = create_ticker_recommendations(
            db, ticker, model_version, recommendations)

        if not result:
            return jsonify(
                {"error": "Ticker {} does not exist.".format(ticker)})

        return jsonify(dict(result))


class PlotTickerRecommendations(Resource):
    @basic_auth.required
    def post(self):
        ticker = str(request.form.get("ticker", None))
        if ticker is None:
            return jsonify({"error": "Ticker must be provided."})
        updated_at, plot_exists = plot_ticker_df(ticker)
        if not updated_at:
            return jsonify(
                {"error": "Ticker {} does not exist.".format(ticker)})

        return jsonify({
            "ticker": ticker,
            "updated_at": updated_at,
            "plot_exists": plot_exists
        })


class GetAllUsersTickers(Resource):
    @basic_auth.required
    def get(self):
        user_id = request.form.get("user_id", None)
        results = get_all_users_tickers(db, user_id=user_id)
        response = {}
        for row in results:
            user_id, username, email, ticker_ids, currencies = row
            response[email] = {
                "user_id": user_id,
                "username": username,
                "ticker_ids": [
                    int(ticker_id) for ticker_id in ticker_ids.split(",")],
                "currencies": currencies.split(",")
            }
        return jsonify(response)


class GetTickersForUser(Resource):
    @basic_auth.required
    def get(self):
        user_id = request.form.get("user_id", None)
        if user_id is None:
            return

        user_id = int(user_id)
        tickers, ticker_recommendations = (
            stocks_recommendations_for_user(user_id))

        recommendations = {}
        for row in tickers:
            ticker_id, ticker, full_name, last_updated, currency = row
            recommendations[ticker] = ticker_recommendations[ticker_id]
            recommendations[ticker]["full_name"] = full_name
            recommendations[ticker]["ticker_id"] = ticker_id
            recommendations[ticker]["last_updated"] = last_updated
            recommendations[ticker]["currency"] = currency

        return jsonify(recommendations)
