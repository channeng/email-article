from app.models import Ticker, TickerUser
from app.models_items import handleError


class TickerItems(object):
    def __init__(self, Model, ModelUser):
        self.model = Model
        self.model_user = ModelUser

    @handleError
    def get_models_by_user_id(self, user_id, num_results=100):
        ticker_users = (
            self.model_user.query
            .filter_by(user_id=user_id)
            .filter_by(is_deleted=False)
            .all()
        )
        ticker_ids = [ticker_user.ticker_id for ticker_user in ticker_users]
        return (
            self.model.query
            .filter(self.model.id.in_(ticker_ids))
            .filter_by(is_deleted=False)
            .order_by(self.model.id.desc())
            .limit(num_results)
            .all()
        )

    @handleError
    def create_model(self, db, ticker):
        new_ticker = self.model(name=ticker)
        db.session.add(new_ticker)
        db.session.commit()

    @handleError
    def get_model_name(self, model_id):
        model_obj = self.model.query.filter_by(
            id=model_id, is_deleted=False).first()
        model_name = model_obj.name
        return model_name

    def get_model_id(self, ticker):
        model_obj = self.model.query.filter_by(
            name=ticker, is_deleted=False).first()
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
            filter_ticker = "AND name = '{}'".format(ticker.upper())
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
    ticker_id = model_template.get_model_id(ticker.upper())
    if not isinstance(ticker_id, int):
        _create_ticker(db, ticker)
        ticker_id = model_template.get_model_id(ticker.upper())
    return model_template.create_modeluser(db, ticker_id, user_id)


def delete_tickeruser(db, ticker_id, user_id):
    return model_template.delete_modeluser(db, ticker_id, user_id)


def get_ticker_emails(db, ticker=None, limit=100):
    return model_template.get_ticker_emails(
        db, ticker=ticker, limit=limit)
