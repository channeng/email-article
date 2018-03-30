from app.models import List, ListItem
from app.models_items import ModelsItems


class ListsItems(ModelsItems):
    def create_model(self, db, model_name, user_id):
        new_list = self.model(name=model_name, user_id=int(user_id))
        db.session.add(new_list)
        db.session.commit()

    def create_modelitems(self, db, item_name, desc, url, list_id):
        new_modelitems = self.model_item(
            name=item_name, body=desc, url=url,
            list_id=int(list_id))
        db.session.add(new_modelitems)
        db.session.commit()
        # flash("Added new item: {}".format(item_name))

model_template = ListsItems(List, ListItem)


def get_lists(user_id, num_results=100):
    return model_template.get_models(user_id, num_results)


def create_list(db, list_name, user_id):
    return model_template.create_model(db, list_name, user_id)


def delete_list(db, list_id):
    return model_template.delete_model(db, list_id)


def get_list_name_items(list_id, is_active_only=False):
    return model_template.get_model_name_items(list_id, is_active_only)


def create_listitems(db, item_name, desc, url, list_id):
    return model_template.create_modelitems(
        db, item_name, desc, url, list_id)


def update_listitems(db, item_ids, status="Done"):
    return model_template.update_modelitems(db, item_ids, status)


def delete_listitems(db, item_id):
    return model_template.delete_modelitems(db, item_id)
