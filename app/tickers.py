import re
import requests
import json

from app.models import Ticker, TickerUser, get_columns
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


def _clean_ticker_stats(ticker_stats):
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

    ticker_data = _clean_ticker_stats(ticker_stats)

    return ticker_data


class TickerItems(object):
    def __init__(self, Model, ModelUser):
        self.model = Model
        self.model_user = ModelUser

    @handleError
    def get_models_by_user_id(self, user_id, num_results=100):
        return (
            self.model_user.query
            .filter_by(user_id=user_id)
            .filter_by(is_deleted=False)
            .join(
                self.model,
                self.model_user.ticker_id == self.model.id,
                isouter=True)
            .with_entities(
                self.model.id, self.model.name, self.model.full_name)
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
    def update_model(self, db, ticker, update_details=False):
        ticker_validated = validate_ticker(ticker)
        model_obj = (
            self.model.query
            .filter_by(is_deleted=False)
            .filter_by(name=ticker_validated)
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

        model_obj.__dict__.update(ticker_data)
        db.session.merge(model_obj)
        db.session.commit()
        return {
            "ticker": model_obj.name,
            "updated": True
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
    def get_model_name(self, model_id):
        model_obj = self.model.query.filter_by(
            id=model_id, is_deleted=False).first()
        model_name = model_obj.name
        return model_name

    def get_model_id(self, ticker):
        ticker_validated = validate_ticker(ticker)
        model_obj = self.model.query.filter_by(
            name=ticker_validated, is_deleted=False).first()
        if model_obj is not None:
            return model_obj.id
        return

    @handleError
    def create_modeluser(self, db, model_id, user_id):
        """Create model-user for sharing Model with multiple Users."""
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
            .filter_by(user_id=int(user_id))
            .filter_by(ticker_id=int(model_id))
            .all()
        )
        for model_user in model_users:
            model_user.is_deleted = True
            db.session.merge(model_user)
            db.session.commit()

    def get_ticker_emails(self, db, ticker=None, limit=100):
        ticker_emails_query = """
        SELECT ticker.name, GROUP_CONCAT(DISTINCT user.email) emails
        FROM ticker_user
        LEFT JOIN user ON user.id = ticker_user.user_id
        INNER JOIN (
            SELECT id, name
            FROM ticker
            WHERE is_deleted = 0
            {filter_ticker}
        ) AS ticker
        ON ticker.id = ticker_user.ticker_id
        WHERE ticker_user.is_deleted = 0
        GROUP BY 1
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

model_template = TickerItems(Ticker, TickerUser)


def get_tickers(user_id, num_results=100):
    return model_template.get_models_by_user_id(user_id, num_results)


def _create_ticker(db, ticker):
    return model_template.create_model(db, ticker)


def get_ticker_name(ticker_id):
    return model_template.get_model_name(ticker_id)


def create_tickeruser(db, ticker, user_id):
    ticker_id = model_template.get_model_id(ticker)
    if not isinstance(ticker_id, int):
        ticker_is_created = _create_ticker(db, ticker)
        if ticker_is_created:
            ticker_id = model_template.get_model_id(ticker)
        else:
            return False
    return model_template.create_modeluser(db, ticker_id, user_id)


def delete_tickeruser(db, ticker_id, user_id):
    return model_template.delete_modeluser(db, ticker_id, user_id)


def get_ticker_emails(db, ticker=None, limit=100):
    return model_template.get_ticker_emails(db, ticker=ticker, limit=limit)


def update_ticker_data(db, ticker, update_details=False):
    return model_template.update_model(
        db, ticker, update_details=update_details)


def get_all_tickers(num_results=100):
    return model_template.get_models(num_results=num_results)