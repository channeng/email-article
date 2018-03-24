# from flask import flash

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
    # flash("Created a new list: {}".format(list_name))


def delete_list(db, list_id):
    list_obj = List.query.filter_by(id=list_id).first()
    list_obj.is_deleted = True
    db.session.merge(list_obj)
    db.session.commit()
    # flash("Deleted list: {}".format(list_obj.name))


def get_list_name_items(list_id, is_active_only=False):
    list_obj = List.query.filter_by(id=list_id, is_deleted=False).first()
    list_name = list_obj.name
    if is_active_only:
        list_items = list_obj.items.filter_by(
            is_deleted=False, status="Active").all()
    else:
        list_items = list_obj.items.filter_by(
            is_deleted=False).all()
    return list_name, list_items


def create_listitems(db, item_name, desc, url, list_id):
    new_listitems = ListItem(
        name=item_name, body=desc, url=url, list_id=int(list_id))
    db.session.add(new_listitems)
    db.session.commit()
    # flash("Added new item: {}".format(item_name))


def update_listitems(db, item_ids, status="Done"):
    item_ids = [int(item_id) for item_id in item_ids]
    list_items = db.session.query(ListItem).filter(ListItem.id.in_(item_ids))
    list_items.update({'status': status}, synchronize_session='fetch')
    db.session.commit()
    # for item in list_items:
    #     flash("Item {} status updated: {}".format(
    #         item.name, item.status))


def delete_listitems(db, item_id):
    list_item = ListItem.query.filter_by(id=item_id).first()
    list_item.is_deleted = True
    db.session.merge(list_item)
    db.session.commit()
    # flash("Deleted item: {}".format(list_item.name))
