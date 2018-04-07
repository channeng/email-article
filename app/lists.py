from app.models import List, ListItem, ListUser
from app.models_items import ModelsItems, handleError


class ListsItems(ModelsItems):
    def __init__(self, Model, ModelItem, ModelUser):
        self.model = Model
        self.model_item = ModelItem
        self.model_user = ModelUser

    @handleError
    def get_models(self, user_id, num_results=100):
        list_users = self.model_user.query.filter_by(user_id=user_id).all()
        list_ids = [list_user.list_id for list_user in list_users]
        return self.model.query.filter(
            (self.model.user_id == user_id) |
            (self.model.id.in_(list_ids))
        ).filter_by(
            is_deleted=False
        ).order_by(
            self.model.id.desc()).limit(
                num_results).all()

    @handleError
    def create_model(self, db, model_name, user_id):
        new_list = self.model(name=model_name, user_id=int(user_id))
        db.session.add(new_list)
        db.session.commit()

    @handleError
    def update_model(self, db, model_id, new_name):
        model_obj = self.model.query.filter_by(id=model_id).first()
        model_obj.name = new_name
        db.session.merge(model_obj)
        db.session.commit()

    @handleError
    def create_modelitems(self, db, item_name, desc, url, model_id):
        new_modelitems = self.model_item(
            name=item_name, body=desc, url=url,
            list_id=int(model_id))
        db.session.add(new_modelitems)
        db.session.commit()
        # flash("Added new item: {}".format(item_name))

    @handleError
    def create_modeluser(self, db, model_id, user_id):
        """Create model-user for sharing Model with multiple Users."""
        new_modeluser = self.model_user(
            user_id=int(user_id),
            list_id=int(model_id))
        db.session.add(new_modeluser)
        db.session.commit()

model_template = ListsItems(List, ListItem, ListUser)


def get_lists(user_id, num_results=100):
    return model_template.get_models(user_id, num_results)


def create_list(db, list_name, user_id):
    return model_template.create_model(db, list_name, user_id)


def update_list(db, list_id, new_list_name):
    return model_template.update_model(db, list_id, new_list_name)


def delete_list(db, list_id):
    return model_template.delete_model(db, list_id)


def get_list_name(list_id):
    return model_template.get_model_name(list_id)


def get_list_name_items(list_id, is_active_only=False):
    return model_template.get_model_name_items(list_id, is_active_only)


def get_list_owner(list_id, is_active_only=False):
    return model_template.get_model_owner(list_id, is_active_only)


def get_list_auth_user_ids(list_id, is_active_only=False):
    return model_template.get_model_auth_user_ids(list_id, is_active_only)


def create_listitems(db, item_name, desc, url, list_id):
    return model_template.create_modelitems(
        db, item_name, desc, url, list_id)


def update_listitems(db, item_ids, status="Done"):
    return model_template.update_modelitems(db, item_ids, status)


def delete_listitems(db, item_id):
    return model_template.delete_modelitems(db, item_id)


def create_listuser(db, list_id, user_id):
    return model_template.create_modeluser(db, list_id, user_id)
