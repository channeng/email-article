from app import db
from app.models import UserReferral
from app.models import User


class ReferralCode(object):
    def __init__(self, Model, User):
        self.model = Model
        self.user = User

    def create_model(self, user_id, username):
        new_referral = self.model(user_id=user_id, code=username)
        db.session.add(new_referral)
        db.session.commit()
        return new_referral

    def get_model(self, user_id):
        result = (
            self.model.query
            .filter_by(user_id=user_id)
            .order_by(self.model.id.desc())
            .with_entities(self.model.code)
            .first()
        )
        if result:
            result = result[0]

        return result


model_template = ReferralCode(UserReferral, User)


def create_referral_code(user_id, username):
    return model_template.create_model(user_id, username)


def get_referral_code(user_id):
    return model_template.get_model(user_id)
