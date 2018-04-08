from app.models import Chat, ChatMessage
from app.models_items import ModelsItems, handleError


class ChatItems(ModelsItems):

    @handleError
    def get_models(self, user_id, num_results=100):
        return self.model.query.filter(
            (self.model.user_id == user_id) |
            (self.model.invited_user_id == user_id)
        ).filter_by(is_deleted=False).order_by(
            self.model.id.desc()).limit(
                num_results).all()

    @handleError
    def create_model(self, db, model_name, user_id, invited_user_id):
        new_list = self.model(
            name=model_name,
            user_id=int(user_id),
            invited_user_id=int(invited_user_id))
        db.session.add(new_list)
        db.session.commit()

    @handleError
    def create_modelitems(self, db, message, chat_id, user_id, username):
        new_modelitems = self.model_item(
            message=message,
            chat_id=int(chat_id),
            user_id=int(user_id),
            username=username)
        db.session.add(new_modelitems)
        db.session.commit()
        # flash("Added new item: {}".format(item_name))

    @handleError
    def get_model_name_items(self, model_id, is_active_only=False):
        model_obj = self.model.query.filter_by(
            id=model_id, is_deleted=False).first()
        model_name = model_obj.name
        if is_active_only:
            model_items = model_obj.messages.filter_by(
                is_deleted=False, status="Active").all()
        else:
            model_items = model_obj.messages.filter_by(
                is_deleted=False).all()
        return model_name, model_items

    @handleError
    def get_model_auth_user_ids(self, model_id, is_active_only=False):
        model_obj = self.model.query.filter_by(
            id=model_id, is_deleted=False).first()
        owner = model_obj.user_id
        auth_users = [owner, model_obj.invited_user_id]
        return owner, auth_users


model_template = ChatItems(Chat, ChatMessage)


def get_chats(user_id, num_results=100):
    return model_template.get_models(user_id, num_results)


def create_chat(db, user_id, invited_user_id, chat_name=""):
    return model_template.create_model(
        db, chat_name, user_id, invited_user_id)


def delete_chat(db, chat_id):
    return model_template.delete_model(db, chat_id)


def get_chat_name_messages(chat_id, is_active_only=False):
    return model_template.get_model_name_items(chat_id, is_active_only)


def get_chat_auth_user_ids(chat_id, is_active_only=False):
    return model_template.get_model_auth_user_ids(chat_id, is_active_only)


def create_chatmessage(db, message, chat_id, user_id, username):
    return model_template.create_modelitems(
        db, message, chat_id, user_id, username)


def update_chatmessage(db, item_ids, status="Done"):
    return model_template.update_modelitems(db, item_ids, status)


def delete_chatmessage(db, item_id):
    return model_template.delete_modelitems(db, item_id)
