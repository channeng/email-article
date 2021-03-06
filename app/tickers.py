import re
import requests
import json

import pandas as pd
from sqlalchemy import func

from app.models import Ticker, TickerUser, TickerRecommendation, get_columns
from app.models_items import handleError
from config import Config


_TICKER_COLUMNS = get_columns(Ticker)
_ENDPOINT = (
    "https://www.alphavantage.co/query?"
    "apikey={api_key}&datatype=json&"
).format(api_key=Config.ALPHAVANTAGE_API_KEY)


def validate_ticker(ticker):
    return re.sub(r"[^A-Z0-9\.]", "", ticker.upper())


def get_ticker_stats(ticker_validated):
    api_function = "Global Quote"
    response = requests.get(
        _ENDPOINT + "function={function}&symbol={ticker}".format(
            function=api_function.replace(" ", "_").upper(),
            ticker=ticker_validated))
    if response.ok:
        results = json.loads(response.content)
        if results.get(api_function, None) is None:
            return {}
        # empty {} if ticker is not found
        return results[api_function]


def get_ticker_details(ticker_validated):
    response = requests.get(
        _ENDPOINT + "function={function}&keywords={ticker}&".format(
            function="SYMBOL_SEARCH",
            ticker=ticker_validated))
    if response.ok:
        results = json.loads(response.content)
        if results.get("bestMatches", None) is None:
            return []

        results = results["bestMatches"]
        # empty [] if ticker is not found
        if results:
            return results[0]
        return results


def clean_ticker_stats(ticker_stats):
    ticker_data = {}
    for metric, val in ticker_stats.items():
        metric_name = metric.split(". ")[1]
        metric_name = metric_name.lower().replace(" ", "_")
        if metric_name[-7:] == "percent":
            val = float(val.strip('%')) / 100
        if metric_name == "name":  # Conflict with ticker symbol name
            metric_name = "full_name"
        if metric_name in _TICKER_COLUMNS:
            ticker_data[metric_name] = val

    return ticker_data


def get_ticker_data(ticker_validated, update_details=False):
    ticker_stats = get_ticker_stats(ticker_validated)
    if ticker_stats is None or not ticker_stats:
        return False
    if update_details:
        ticker_details = get_ticker_details(ticker_validated)
        if ticker_details:
            ticker_stats.update(ticker_details)

    ticker_data = clean_ticker_stats(ticker_stats)

    return ticker_data


class TickerItems(object):
    def __init__(self, Model, ModelUser, ModelRecommendation):
        self.model = Model
        self.model_user = ModelUser
        self.model_recommendation = ModelRecommendation

    @handleError
    def get_models_by_user_id(self, user_id, num_results=100):
        return (
            self.model_user.query
            .filter_by(user_id=user_id, is_deleted=False)
            .join(
                self.model,
                self.model_user.ticker_id == self.model.id,
                isouter=True)
            .filter(self.model.is_deleted == 0)
            .with_entities(
                self.model.id, self.model.name, self.model.full_name,
                self.model.latest_trading_day, self.model.currency,
                self.model.price, self.model.change, self.model.change_percent)
            .order_by(self.model_user.id.desc())
            .limit(num_results)
            .all()
        )

    @handleError
    def get_models(self, num_results=100):
        return (
            self.model.query
            .with_entities(self.model.name, self.model.time_updated)
            .filter_by(is_deleted=False)
            .order_by(self.model.id.desc())
            .limit(num_results)
            .all()
        )

    @handleError
    def get_popular_models(self, top_k):
        return (
            self.model_user.query
            .filter_by(is_deleted=False)
            .join(
                self.model,
                self.model_user.ticker_id == self.model.id,
                isouter=True)
            .filter(self.model.is_deleted == 0)
            .with_entities(
                self.model.name,
                func.count(self.model_user.ticker_id))
            .group_by(self.model.name)
            .order_by(func.count(self.model_user.ticker_id).desc())
            .limit(top_k)
            .all()
        )

    @handleError
    def update_model(self, db, ticker, update_details=False):
        ticker_validated = validate_ticker(ticker)
        model_obj = (
            self.model.query
            .filter_by(is_deleted=False, name=ticker_validated)
            .order_by(self.model.id.desc())
            .first()
        )

        if model_obj is None:
            return {
                "ticker": ticker_validated,
                "updated": False,
                "error": "Ticker not found."
            }

        ticker_data = get_ticker_data(
            model_obj.name, update_details=update_details)
        if ticker_data == False or ticker_data == {}:  # noqa E712
            return {
                "ticker": model_obj.name,
                "updated": False,
                "error": "No ticker data retrieved."
            }

        for key in ticker_data:
            setattr(model_obj, key, ticker_data[key])

        db.session.merge(model_obj)
        db.session.commit()
        return {
            "ticker": model_obj.name,
            "updated": True
        }

    @handleError
    def delete_model(self, db, ticker, set_active=False):
        ticker_validated = validate_ticker(ticker)
        models = (
            self.model.query
            .filter_by(name=ticker_validated)
            .all()
        )
        if len(models) < 1:
            return {
                "ticker": ticker_validated,
                "deleted": False,
                "error": "Ticker not found."
            }

        for model_obj in models:
            model_obj.is_deleted = not set_active
            db.session.merge(model_obj)
            db.session.commit()

        return {
            "ticker": ticker_validated,
            "deleted": not set_active
        }

    @handleError
    def create_model(self, db, ticker):
        # Remove all spaces and symbols that is not A-Z, 1-9 or .
        ticker_validated = validate_ticker(ticker)
        ticker_data = get_ticker_data(ticker_validated, update_details=True)
        if ticker_data == False:  # noqa E712
            return False
        new_ticker = self.model(name=ticker_validated, **ticker_data)
        db.session.add(new_ticker)
        db.session.commit()
        return True

    @handleError
    def get_model(self, model_id):
        return (
            self.model.query
            .filter_by(id=model_id, is_deleted=False)
            .order_by(self.model.id.desc())
            .first()
        )

    @handleError
    def get_model_name(self, model_id):
        model_obj = self.get_model(model_id)
        model_name = model_obj.name
        return model_name

    def get_model_by_name(self, ticker):
        ticker_validated = validate_ticker(ticker)
        model_obj = (
            self.model.query
            .filter_by(name=ticker_validated)
            .order_by(self.model.id.desc())
            .first()
        )
        return model_obj

    @handleError
    def create_modeluser(self, db, model_id, user_id):
        new_modeluser = self.model_user(
            user_id=int(user_id),
            ticker_id=int(model_id))
        db.session.add(new_modeluser)
        db.session.commit()
        return True

    @handleError
    def delete_modeluser(self, db, model_id, user_id):
        model_users = (
            self.model_user.query
            .filter_by(user_id=int(user_id), ticker_id=int(model_id))
            .all()
        )
        for model_user in model_users:
            model_user.is_deleted = True
            db.session.merge(model_user)
            db.session.commit()

    def get_ticker_emails(self, db, ticker=None, limit=100):
        ticker_emails_query = """
        SELECT
            ticker.id,
            ticker.name,
            ticker.full_name,
            ticker.currency,
            CASE WHEN ticker_rec.ticker_id IS NULL
                 THEN 0 ELSE 1 END AS has_recommendation,
            GROUP_CONCAT(DISTINCT user.email) emails
        FROM ticker_user
        LEFT JOIN user ON user.id = ticker_user.user_id
        INNER JOIN (
            SELECT id, name, full_name, currency
            FROM ticker
            -- Retrieve from latest id for each ticker
            WHERE id in (
                SELECT id FROM (
                    SELECT name, max(id) as id
                    FROM ticker
                    WHERE is_deleted = 0
                    GROUP by name
                )
            )
            {filter_ticker}
            GROUP BY 1,2,3,4
        ) AS ticker ON ticker.id = ticker_user.ticker_id
        LEFT JOIN (
            SELECT ticker_id
            FROM ticker_recommendation
            GROUP BY 1
        ) AS ticker_rec ON ticker_rec.ticker_id = ticker_user.ticker_id
        WHERE ticker_user.is_deleted = 0
        GROUP BY 1,2,3,4
        LIMIT {limit};
        """
        filter_ticker = ""
        if ticker is not None:
            ticker_validated = validate_ticker(ticker)
            filter_ticker = "AND name = '{}'".format(ticker_validated)
        result = db.engine.execute(
            ticker_emails_query.format(
                filter_ticker=filter_ticker, limit=limit))
        result = list(result)
        return result

    def create_modelrecommendations(self, db, model_id, model_version, data):
        """Add a recommendation for given ticker."""
        ticker_id = int(model_id)
        new_recommendations = []
        for closing_date, recommendation in data.items():
            is_strong = recommendation["is_strong"]
            if not isinstance(is_strong, bool):
                is_strong = is_strong.lower() == "true"

            new_recommendations.append(
                self.model_recommendation(
                    ticker_id=ticker_id,
                    model_version=model_version,
                    closing_date=closing_date,
                    recommendation=recommendation["buy_or_sell"],
                    is_strong=is_strong,
                    closing_price=recommendation["closing_price"],
                )
            )

        db.session.add_all(new_recommendations)
        db.session.commit()

        return {
            "ticker": model_id,
            "updated": True,
            "num_recommendations": len(new_recommendations)
        }

    @handleError
    def get_modelrecommendations_by_user_id(
            self, db, user_id, num_results=100):
        ticker_recommendation_query = """
        WITH ticker_region AS (
            SELECT id AS ticker_id, region
            FROM ticker
            WHERE is_deleted = 0
        ), ticker_recommendation_region AS (
            SELECT * FROM ticker_recommendation
            LEFT JOIN ticker_region USING(ticker_id)
        ), closing_date_per_region AS (
            SELECT region, MAX(closing_date) AS closing_date
            FROM ticker_recommendation_region
            GROUP BY 1
        ), user_tickers AS (
            SELECT ticker_id
            FROM ticker_user
            WHERE user_id = {user_id}
            AND is_deleted = 0
            GROUP BY 1
        ), recommendations_for_user AS (
            -- all recommendations for user on the latest date
            SELECT *
            FROM ticker_recommendation_region
            INNER JOIN user_tickers USING (ticker_id)
            INNER JOIN closing_date_per_region USING (region, closing_date)
        )

        SELECT
            ticker_id,
            closing_date,
            MAX(recommendation) AS recommendation,
            MAX(is_strong) AS is_strong
        FROM recommendations_for_user
        GROUP BY 1,2
        LIMIT {limit};
        """

        query = ticker_recommendation_query.format(
            user_id=user_id, limit=num_results)
        result = db.engine.execute(query)
        result = list(result)

        return result

    def get_modelrecommendations_for_model(self, model_id):
        """Get all recommendations for given ticker."""
        return (
            self.model_recommendation.query
            .filter_by(ticker_id=model_id)
            .filter(
                self.model_recommendation.recommendation.in_(["buy", "sell"]))
            .with_entities(
                self.model_recommendation.closing_date,
                self.model_recommendation.recommendation,
                self.model_recommendation.is_strong
            )
            .order_by(self.model_recommendation.id)
            .all()
        )

    def get_latest_modelrecommendation(self, model_id):
        """Get latest recommendation for a given ticker."""
        return (
            self.model_recommendation.query
            .filter_by(ticker_id=model_id)
            .with_entities(
                self.model_recommendation.time_created,
                self.model_recommendation.closing_date,
                self.model_recommendation.recommendation,
                self.model_recommendation.is_strong
            )
            .order_by(self.model_recommendation.id.desc())
            .first()
        )

    def get_all_users_tickers(self, db, user_id=None):
        query = """
        WITH valid_tickers AS (
            SELECT id AS ticker_id, currency
            FROM ticker
            WHERE is_deleted = 0
            GROUP BY 1,2
        )

        SELECT
            user_id,
            username,
            email,
            GROUP_CONCAT(ticker_id) AS ticker_ids,
            GROUP_CONCAT(DISTINCT currency) AS currencies
        FROM ticker_user
        LEFT JOIN user ON ticker_user.user_id = user.id
        INNER JOIN valid_tickers USING(ticker_id)
        WHERE is_deleted = 0
        {}
        GROUP BY 1,2,3;
        """

        filter_user = ""
        if user_id is not None:
            user_id = int(user_id)
            filter_user = "AND user_id = {}".format(user_id)

        result = db.engine.execute(query.format(filter_user))
        result = list(result)

        return result

    def get_auth_users(self, ticker_id):
        return (
            self.model_user.query
            .filter_by(ticker_id=int(ticker_id), is_deleted=False)
            .with_entities(self.model_user.user_id)
            .group_by(self.model_user.user_id)
            .all()
        )


model_template = TickerItems(Ticker, TickerUser, TickerRecommendation)


def get_tickers(user_id, num_results=100):
    return model_template.get_models_by_user_id(user_id, num_results)


def _create_ticker(db, ticker):
    return model_template.create_model(db, ticker)


def get_ticker(ticker_id):
    return model_template.get_model(ticker_id)


def get_ticker_name(ticker_id):
    return model_template.get_model_name(ticker_id)


def create_tickeruser(db, ticker, user_id):
    model_obj = model_template.get_model_by_name(ticker)
    if model_obj is None:
        ticker_is_created = _create_ticker(db, ticker)
        if not ticker_is_created:
            return False, "Ticker {} is invalid.".format(ticker)
    elif model_obj.is_deleted:
        return False, "Ticker {} has insufficient data.".format(ticker)

    model_obj = model_template.get_model_by_name(ticker)
    return (
        model_template.create_modeluser(db, model_obj.id, user_id),
        "Ticker {} added.".format(ticker))


def delete_tickeruser(db, ticker_id, user_id):
    return model_template.delete_modeluser(db, ticker_id, user_id)


def get_ticker_emails(db, ticker=None, limit=100):
    return model_template.get_ticker_emails(db, ticker=ticker, limit=limit)


def update_ticker_data(db, ticker, update_details=False):
    return model_template.update_model(
        db, ticker, update_details=update_details)


def get_all_tickers(num_results=100):
    return model_template.get_models(num_results=num_results)


def create_ticker_recommendations(db, ticker, model_version, data):
    """Create batch of recommendations for a ticker by a given model.

    Args:
        db
        ticker (String): Ticker name.
        model_version (String): Model name.
        data (Dict): Dictionary with closing_date as keys, and values of Dict
                     containing "buy_or_sell", "is_strong", "closing_price".
                     Example:
                     {
                        "2019-07-02": {
                            "buy_or_sell": "Sell",
                            "is_strong": True,
                            "closing_price": 97.9
                        }
                      }
    """
    model_obj = model_template.get_model_by_name(ticker)
    if model_obj is None:
        return False

    return model_template.create_modelrecommendations(
        db, model_obj.id, model_version, data)


def delete_ticker(db, ticker, set_active=False):
    return model_template.delete_model(db, ticker, set_active=set_active)


def get_ticker_recommendations_df(ticker):
    model_obj = model_template.get_model_by_name(ticker)
    if model_obj is None:
        return None, None
    recommendations = model_template.get_modelrecommendations_for_model(
        model_obj.id)
    columns = ["date", "recommendation", "is_strong"]
    recommendations_df = pd.DataFrame(
        recommendations,
        columns=columns)
    recommendations_df["date"] = recommendations_df["date"].apply(
        lambda x: pd.datetime.strptime(x, '%Y-%m-%d'))
    recommendations_df = recommendations_df.groupby("date").first()
    return recommendations_df, model_obj.currency


def get_ticker_latest_recommendation(ticker_id):
    return model_template.get_latest_modelrecommendation(ticker_id)


def get_ticker_recommendations_for_user(db, user_id, num_results=100):
    results = model_template.get_modelrecommendations_by_user_id(
        db, user_id, num_results=100)
    return results


def get_all_users_tickers(db, user_id=None):
    results = model_template.get_all_users_tickers(
        db, user_id=user_id)
    return results


def get_popular_tickers(top_n_tickers):
    return model_template.get_popular_models(top_n_tickers)


def get_ticker_by_name(ticker):
    return model_template.get_model_by_name(ticker)


def get_ticker_auth_users(ticker_id):
    return model_template.get_auth_users(ticker_id)
