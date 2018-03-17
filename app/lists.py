from flask import flash

from app.models import List, ListItem


def get_lists(user_id, num_results=100):
    return List.query.filter_by(
        user_id=user_id, is_deleted=False).order_by(
            List.id.desc()).limit(
                num_results).all()


def create_list(db, list_name, user_id):
    new_list = List(name=list_name, user_id=int(user_id))
    db.session.add(new_list)
    db.session.commit()
    flash("Created a new list: {}".format(list_name))


def delete_list(db, list_id):
    list_obj = List.query.filter_by(id=list_id).first()
    list_obj.is_deleted = True
    db.session.merge(list_obj)
    db.session.commit()
    flash("Deleted list: {}".format(list_obj.name))


def get_list_name_items(list_id):
    list_obj = List.query.filter_by(id=list_id, is_deleted=False).first()
    list_name = list_obj.name
    list_items = list_obj.items.filter_by(is_deleted=False).all()
    return list_name, list_items


def create_listitems(db, item_name, list_id):
    new_listitems = ListItem(name=item_name, list_id=int(list_id))
    db.session.add(new_listitems)
    db.session.commit()
    flash("Added new item: {}".format(item_name))


def update_listitems(db, item_id, status="Done"):
    list_item = ListItem.query.filter_by(id=item_id).first()
    list_item.status = status
    db.session.merge(list_item)
    db.session.commit()
    flash("Item {} status updated: {}".format(
        list_item.name, list_item.status))


def delete_listitems(db, item_id):
    list_item = ListItem.query.filter_by(id=item_id).first()
    list_item.is_deleted = True
    db.session.merge(list_item)
    db.session.commit()
    flash("Deleted item: {}".format(list_item.name))
