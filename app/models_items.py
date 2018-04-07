class ModelsItems():
    """Generic Model, ModelItems class to package standard CRUD methods."""

    def __init__(self, Model, ModelItem):
        self.model = Model
        self.model_item = ModelItem

    def get_models(self, user_id, num_results=100):
        return self.model.query.filter_by(
            user_id=user_id, is_deleted=False).order_by(
                self.model.id.desc()).limit(
                    num_results).all()

    def create_model(self, db, model_name, user_id):
        """Create model item."""
        raise NotImplementedError("Sub-classes should implement this method.")

    def delete_model(self, db, model_id):
        model_obj = self.model.query.filter_by(id=model_id).first()
        model_obj.is_deleted = True
        db.session.merge(model_obj)
        db.session.commit()

    def get_model_name_items(self, model_id, is_active_only=False):
        model_obj = self.model.query.filter_by(
            id=model_id, is_deleted=False).first()
        model_name = model_obj.name
        if is_active_only:
            model_items = model_obj.items.filter_by(
                is_deleted=False, status="Active").all()
        else:
            model_items = model_obj.items.filter_by(
                is_deleted=False).all()
        return model_name, model_items

    def get_model_auth_user_ids(self, model_id, is_active_only=False):
        model_obj = self.model.query.filter_by(
            id=model_id, is_deleted=False).first()
        return [model_obj.user_id]

    def create_modelitems(self):
        """Create model item."""
        raise NotImplementedError("Sub-classes should implement this method.")

    def update_modelitems(self, db, item_ids, status="Done"):
        item_ids = [int(item_id) for item_id in item_ids]
        model_items = db.session.query(self.model_item).filter(
            self.model_item.id.in_(item_ids))
        model_items.update({'status': status}, synchronize_session='fetch')
        db.session.commit()
        # for item in model_items:
        #     flash("Item {} status updated: {}".format(
        #         item.name, item.status))

    def delete_modelitems(self, db, item_id):
        model_item = self.model_item.query.filter_by(id=item_id).first()
        model_item.is_deleted = True
        db.session.merge(model_item)
        db.session.commit()
        # flash("Deleted item: {}".format(model_item.name))
