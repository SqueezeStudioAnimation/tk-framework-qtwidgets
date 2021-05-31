# Copyright (c) 2021 Autodesk Inc.
#
# CONFIDENTIAL AND PROPRIETARY
#
# This work is provided "AS IS" and subject to the Shotgun Pipeline Toolkit
# Source Code License included in this distribution package. See LICENSE.
# By accessing, using, copying or modifying this work you indicate your
# agreement to the Shotgun Pipeline Toolkit Source Code License. All rights
# not expressly granted therein are reserved by Autodesk Inc.
import sgtk
from sgtk.platform.qt import QtCore, QtGui

from .ui import resources_rc

from .filter_item import FilterItem
from .filter_item_widget import FilterItemWidget
from ..shotgun_menus import ShotgunMenu

shotgun_globals = sgtk.platform.import_framework(
    "tk-framework-shotgunutils", "shotgun_globals"
)


class FilterMenu(ShotgunMenu):
    """"""

    filters_changed = QtCore.Signal()

    def __init__(self, filters, parent, fields=None):
        """
        Constructor
        """

        super(FilterMenu, self).__init__(parent)

        # FIXME Let it be resizable
        # self.setMinimumWidth(250)
        # self.setMaximumWidth(250)

        self._popout_widget = QtGui.QWidget()
        self._popout_widget.hide()

        # TODO add filter -- would need to requery with added fields if data is not available
        # TODO save filter state
        if fields:
            self._visible_fields = fields or []
        else:
            # Take the first three if visible filters is not defined (to avoid overwhelming number of filters)
            if isinstance(filters, dict):
                filter_fields = filters.keys()
                if len(filter_fields) > 3:
                    self._visible_fields = filters.keys()[:3]
                else:
                    self._visible_fields = filter_fields
            else:
                # self._visible_fields = [f["field"] for f in filters[:3]]
                self._visible_fields = []

        self._group_filters = []
        self._filters_by_field = {}
        self._actions_by_filter = {}
        self._config_menu = ShotgunMenu(self)
        self._config_menu.setTitle("More Filters")

        self.build_menu(filters)

    def build_menu(self, filters_list):
        """
        """

        actions_by_filter = dict(self._actions_by_filter)

        self.clear_menu()

        if not filters_list:
            return

        if isinstance(filters_list, dict):
            for field, data in filters_list.items():
                filters = []
                actions = []

                if data.get("type") in (
                    FilterItem.TYPE_NUMBER,
                    FilterItem.TYPE_STR,
                    FilterItem.TYPE_TEXT,
                ):
                    filter_data = {
                        "filter_type": data["type"],
                        "filter_op": FilterItem.default_op_for_type(data["type"]),
                        "data_func": lambda i, f=field: get_index_data(i, f),
                    }
                    (filter_item, action) = self.create_filter_item_and_action(
                        filter_data
                    )
                    filters.append((filter_item, action))
                    actions.append(action)

                else:
                    for filter_name, filter_value in data.get("values", {}).items():
                        filter_data = {
                            "filter_type": data["type"],
                            "filter_op": FilterItem.default_op_for_type(data["type"]),
                            "data_func": lambda i, f=field: get_index_data(i, f),
                            "filter_value": filter_value.get("value"),
                            "display_name": filter_value.get("name", str(filter_name)),
                            "count": filter_value.get("count", 0),
                        }
                        (filter_item, action) = self.create_filter_item_and_action(
                            filter_data
                        )

                        filter_id = "{field}.{value_name}".format(
                            field=field, value_name=filter_name
                        )
                        # self._filter_items[filter_id] = filter_item
                        self._actions_by_filter[filter_id] = action

                        filters.append((filter_item, action))
                        actions.append(action)

                        # FIXME
                        # filter UI seems to refresh OK but maybe the proxy model needs to be updated on refresh?
                        # prev_action = actions_by_filter.get(filter_id)
                        # if prev_action:
                        # checked = prev_action.isChecked()
                        # action.defaultWidget().action_triggered(checked)
                        # action.setChecked(checked)

                self._group_filters.append(filters)
                self._filters_by_field[field] = filters

                sorted_actions = sorted(actions, key=lambda item: item.text())
                group_actions = self.add_group(sorted_actions, data.get("name"))

                self._add_config_action(data.get("name"), field, group_actions)

                for a in group_actions:
                    a.setProperty("id", field)

        else:
            assert False, "Unsupported filter list data format"

        if self.actions():
            self.addSeparator()
            clear_action = self.addAction("Clear All Filters")
            clear_action.triggered.connect(self.clear_filters)

            self.addMenu(self._config_menu)

            # TODO allow the menu to "undock" from the button and show as its own widget
            # this isn't as simple as setting the parent to None for QMenu
            # popout_action = self.addAction("Pop Out Menu")
            # popout_action.triggered.connect(self.popout_menu)

        # Defaults to no filters active after rebuild
        self._active_filter = FilterItem(
            FilterItem.TYPE_GROUP, FilterItem.OP_AND, filters=[]
        )
        self._build_filter()

        # Clear it to clean up
        actions_by_filter = None

        # self.filters_changed.emit()

    def _add_config_action(self, name, field, group_actions):
        """
        """

        config_action = QtGui.QWidgetAction(self._config_menu)
        config_widget = FilterItemWidget.create(
            {"id": field, "filter_type": FilterItem.TYPE_LIST, "display_name": name,}
        )
        config_action.setDefaultWidget(config_widget)
        self._config_menu.addAction(config_action)

        config_widget.filter_item_checked.connect(
            lambda state, a=config_widget: self.toggle_action_group_cb(a, state)
        )

        # FIXME this shows nothing if not sg fields
        # config_action.setChecked(
        # not self._visible_fields
        # or field in self._visible_fields
        # )
        config_widget.action_triggered(
            not self._visible_fields or field in self._visible_fields
        )

        # Should we not even add it in the first place if its not visible?
        self.toggle_action_group(config_widget, group_actions)
        # self.toggle_action_group(config_action, group_actions)
        # config_action.triggered.connect(self.toggle_action_group_cb)

    def refresh_menu(self, filters):
        """
        Do not rebuild the whole menu, just update it.
        """

        for field, filter_list in filters.items():
            if not filter_list.get("values"):
                continue

            for filter_name, filter_value in filter_list.get("values").items():
                filter_id = "{field}.{value_name}".format(
                    field=field, value_name=filter_name
                )
                action = self._actions_by_filter.get(filter_id)
                if action:
                    action.defaultWidget().update_widget(filter_value)

        for field, field_filters in self._filters_by_field.items():
            for filter_item, action in field_filters:
                name = action.defaultWidget().name()
                if not filters.get(field, {}).get("values", {}).get(name):
                    # action.setVisible(False)
                    action.defaultWidget().update_widget({"count": 0})

    def clear_menu(self):
        """
        """

        self._group_filters = []
        self._actions_by_filter = {}
        self._filters_by_field = {}
        self._config_menu.clear()
        self.clear()

    # def toggle_action_group_cb(self, *args, **kwargs):
    def toggle_action_group_cb(self, widget, state):
        # action = self.sender()
        # checked = action.isChecked()
        checked = widget.has_value()
        actions = self.actions()
        for a in actions:
            # FIXME the action text is not guaranteed to be unique?
            # p = a.property("id")
            # t = action.text()
            # if p == t:
            if widget._id == a.property("id"):
                try:
                    a.defaultWidget().setVisible(checked)
                except:
                    # No worries
                    pass
                a.setVisible(checked)

    # def toggle_action_group(self, action, actions):
    def toggle_action_group(self, widget, actions):
        checked = widget.has_value()
        for a in actions:
            try:
                a.defaultWidget().setVisible(checked)
            except:
                # No worries
                pass
            a.setVisible(checked)

    def create_filter_item_and_action(self, filter_data):
        """
        """

        filter_item = FilterItem.create(filter_data)

        action = QtGui.QWidgetAction(self.parentWidget())
        widget = FilterItemWidget.create(filter_data)
        widget.filter_item_checked.connect(
            lambda state, a=action: self._filter_item_changed(a, state)
        )
        widget.filter_item_text_changed.connect(
            lambda text, f=filter_item: self._filter_item_text_changed(f, text)
        )

        action.setDefaultWidget(widget)
        action.setCheckable(True)

        action.triggered.connect(
            lambda checked=False, w=widget: self._filter_changed(w)
        )

        return (filter_item, action)

    @property
    def active_filter(self):
        """"""

        return self._active_filter

    @property
    def has_filtering(self):
        """
        Return True if the menu has any active filtering.
        """

        return bool(self._active_filter and self._active_filter.filters)

    def _filter_item_changed(self, action, state):
        """
        """

        # action.setChecked(state == QtCore.Qt.Checked)
        action.setChecked(action.defaultWidget().has_value())
        self._build_filter()
        self.filters_changed.emit()

    def _filter_item_text_changed(self, filter_item, text):
        """
        """

        filter_item.filter_value = text
        # TODO support multiple values via comma separated list
        # filter_item.filter_value = text.split(",")

        self._build_filter()
        self.filters_changed.emit()

    def _filter_changed(self, filter_menu_item_widget):
        """
        Callback on filter action triggered.

        Rebuild the active filter.
        """

        # Update the filter widget which will then trigger a re-build of the filters and signal emitting
        filter_menu_item_widget.action_triggered()

    def _build_filter(self):
        """"""

        active_group_filters = []

        for filters in self._group_filters:
            active_filters = [
                filter_item
                for filter_item, action in filters
                if action.defaultWidget().has_value()
            ]
            if active_filters:
                active_group_filters.append(
                    (
                        FilterItem(
                            FilterItem.TYPE_GROUP,
                            FilterItem.OP_OR,
                            filters=active_filters,
                        )
                    )
                )

        self._active_filter.filters = active_group_filters

    def _get_group_filter(self, group_field):
        """
        """

        group_filter = []

        for field, filters in self._filters_by_field.items():
            if field == group_field:
                continue

            active_filters = [
                filter_item
                for filter_item, filter_action in filters
                if filter_action.defaultWidget().has_value()
            ]
            if active_filters:
                group_filter.append(
                    FilterItem(
                        FilterItem.TYPE_GROUP, FilterItem.OP_OR, filters=active_filters
                    )
                )

        return group_filter

    def clear_filters(self):
        """
        """

        for filters in self._group_filters:
            for _, action in filters:
                # FIXME block signals to avoid retriggering the filter model each time a filter item is cleared -- just do it once at the end
                action.setChecked(False)
                action.defaultWidget().clear_value()

        self._active_filter.filters = []
        self.filters_changed.emit()


class ShotgunFilterMenu(FilterMenu):
    """
    Subclass of FilterMenu. The only thing this class does is it builds the filters based on the given
    entity type to the FilterMenu.
    """

    def __init__(self, shotgun_model, proxy_model, parent, fields=None):
        """
        """

        # FIXME this class needs major clean up -- just exploring how filtering can work right now

        self._invalid_field_types = ["image"]

        self.entity_model = shotgun_model
        self.proxy_model = proxy_model

        self.entity_model.data_refreshed.connect(self.rebuild)
        self.proxy_model.layoutChanged.connect(self.refresh)

        bundle = sgtk.platform.current_bundle()
        if bundle.tank.pipeline_configuration.is_site_configuration():
            # site configuration (no project id). Return None which is
            # consistent with core.
            self._project_id = None
        else:
            self._project_id = bundle.tank.pipeline_configuration.get_project_id()

        filters = self.get_entity_filters()
        super(ShotgunFilterMenu, self).__init__(filters, parent, fields)

    def refresh(self):
        """
        """

        filters = self.get_entity_filters(proxy_filter=True)

        self.refresh_menu(filters)
        # self.build_menu(filters)

    def rebuild(self):
        """
        """

        filters = self.get_entity_filters()
        self.build_menu(filters)

    def get_entity_filters(self, proxy_filter=None):
        """
        Return a list of filters for task entity.
        """

        # check if it's a ShotgunModel specifically?
        if not hasattr(self.entity_model, "get_entity_type"):
            return []

        entity_type = self.entity_model.get_entity_type()
        if not entity_type:
            return []

        fields = shotgun_globals.get_entity_fields(
            entity_type, project_id=self._project_id
        )
        fields.sort()

        filter_data = {}
        self._get_item_filters(
            self.entity_model.invisibleRootItem(),
            entity_type,
            self._project_id,
            fields,
            filter_data,
            proxy_filter,
        )
        return filter_data

    def _get_item_filters(
        self, item, entity_type, project_id, fields, filter_data, proxy_filter=None
    ):
        """
        """

        # FIXME this does not generically go through whole tree or list model data

        for group_row in range(item.rowCount()):
            entity_item = item.child(group_row)

            # FIXME uncomment to support filtering through all levels in tree model
            # children = entity_item.hasChildren()
            # if children:
            #     self._get_item_filters(entity_item, entity_type, project_id, fields, filter_data)

            sg_data = entity_item.get_sg_data()

            if not sg_data:
                # NOTE this is shotgun data but it's not stored in the SG_DATA_ROLE but rather
                # each item in the model has some of the entity data as a hierarchy.. we could just
                # show ALL fields for the entity
                self._add_item_filter(entity_item, entity_type, filter_data)

            else:
                self._add_sg_field_filter(
                    entity_type,
                    project_id,
                    fields,
                    sg_data,
                    filter_data,
                    proxy_filter,
                    entity_item,
                )

    def _add_item_filter(self, item, name, filter_data):
        """
        """
        filter_role = QtCore.Qt.DisplayRole

        # Is it OK to assume this is a string?
        value = item.data(filter_role)

        if filter_role in filter_data:
            filter_data[filter_role]["values"].setdefault(value, {}).setdefault(
                "count", 0
            )
            filter_data[filter_role]["values"][value]["count"] += 1
            filter_data[filter_role]["values"][value]["value"] = value

        else:
            filter_data[filter_role] = {
                "name": name,
                "type": FilterItem.TYPE_LIST,
                "values": {value: {"value": value, "count": 1}},
            }

    def _add_sg_field_filter(
        self,
        entity_type,
        project_id,
        fields,
        sg_data,
        filter_data,
        proxy_filter=None,
        entity_item=None,
    ):
        """
        """

        for sg_field, value in sg_data.items():
            if sg_field not in fields:
                # if sg_field not in fields or (self._visible_fields and sg_field not in self._visible_fields):
                continue

            if proxy_filter:
                pfs = self._get_group_filter(sg_field)
                if pfs:
                    self.proxy_model._filter_items = self._get_group_filter(sg_field)
                    parent_idx = (
                        entity_item.parent().index()
                        if entity_item.parent()
                        else QtCore.QModelIndex()
                    )
                    if not self.proxy_model.filterAcceptsRow(
                        entity_item.row(), parent_idx
                    ):
                        continue

            field_type = shotgun_globals.get_data_type(
                entity_type, sg_field, project_id
            )
            # if field_type not in valid_field_types:
            if field_type in self._invalid_field_types:
                continue

            field_display = shotgun_globals.get_field_display_name(
                entity_type, sg_field, project_id
            )
            field_id = sg_field

            if isinstance(value, list):
                values_list = value
            else:
                values_list = [value]

            for val in values_list:
                if isinstance(val, dict):
                    # assuming it is an entity dict
                    value_id = val.get("name", str(val))
                    filter_value = val
                elif field_type in (FilterItem.TYPE_DATE, FilterItem.TYPE_DATETIME):
                    datetime_bucket = FilterItem.get_datetime_bucket(value)
                    value_id = datetime_bucket
                    filter_value = datetime_bucket
                else:
                    value_id = val
                    filter_value = val

                if field_id in filter_data:
                    filter_data[field_id]["values"].setdefault(value_id, {}).setdefault(
                        "count", 0
                    )
                    filter_data[field_id]["values"][value_id]["count"] += 1
                    filter_data[field_id]["values"][value_id]["value"] = filter_value
                else:
                    filter_data[field_id] = {
                        "name": field_display,
                        "type": field_type,
                        "values": {value_id: {"value": filter_value, "count": 1}},
                    }

                # TODO icons?
                # filter_data[field]["values"][value]["icon"] = entity_item.model().get_entity_icon(entity_type)


def get_index_data(index, field):
    """
    Callback
    """

    # FIXME more automated way to retrieve shotgun field data from model
    if not index.isValid():
        return None
    item = index.model().item(index.row(), index.column())
    sg_data = item.get_sg_data()
    if sg_data:
        return sg_data.get(field)

    # Non-sg data, the 'field' is the item data role to extract data from the item itself
    return index.data(field)
