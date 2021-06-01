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

    def __init__(self, filters_def, parent, fields=None):
        """
        Constructor
        """

        super(FilterMenu, self).__init__(parent)

        # TODO add filter -- would need to requery with added fields if data is not available
        # TODO save filter state

        # A mapping of filter group id (the filter field) to list of filters that belong to that group.
        self._filters_by_field = {}
        # A mapping of filter id to its corresponding Qt action widget.
        self._actions_by_filter = {}

        if fields:
            self._visible_fields = fields

        elif filters_def:
            # Take the first three if visible filters is not defined (to avoid overwhelming number of filters)
            filter_fields = filters_def.keys()
            if len(filter_fields) > 3:
                self._visible_fields = filter_fields[:3]
            else:
                self._visible_fields = filter_fields
        else:
            self._visible_fields = []

        # Initialize the menu
        self.build_menu(filters_def)

    @property
    def active_filter(self):
        """
        Return the current filters that are set within the menu.
        """

        return self._active_filter

    @property
    def has_filtering(self):
        """
        Return True if the menu has any active filtering.
        """

        return bool(self._active_filter and self._active_filter.filters)

    def build_menu(self, filters_def):
        """
        Build the filter menu. Reset and clear the current menu before building.
        """

        if not filters_def:
            return

        assert isinstance(filters_def, dict), "Unsupported filters type"
        if not isinstance(filters_def, dict):
            return

        prev_actions = dict(self._actions_by_filter)

        # First reset and clear the menu.
        self.clear_menu()

        # Iterate through te filter definitions, given by field id (the grouping), and create the
        # filter item object and widgets to manage each filter.
        for field_id, data in filters_def.items():
            # For each grouping, build up a list of filter items and Qt actions, to then add to the
            # menu once all filter items for the grouping are created.
            filter_items = []
            actions = []
            filter_item_data = {
                "filter_type": data["type"],
                "filter_op": FilterItem.default_op_for_type(data["type"]),
                "filter_role": data.get("filter_role"),
                "data_func": data.get("data_func"),
            }

            if data["type"] in FilterItemWidget.SINGLE_VALUE_TYPES:
                # There is only one filter widget/action for this filter type; e.g. there is a
                # line edit widget to perform the filtering for this type.

                # FIXME let the FilterItem define the id
                filter_id = field_id

                (filter_item, action) = self._create_filter_item_and_action(
                    filter_id, field_id, filter_item_data
                )

                prev_action = prev_actions.get(filter_id)
                if prev_action:
                    widget = prev_action.defaultWidget()
                    action.defaultWidget().restore(widget)

                filter_items.append(filter_item)
                actions.append(action)
                self._actions_by_filter[filter_id] = action

            else:
                # There are multiple filter widgets for this filter type; e.g. there is a list
                # of choices to select from, where each choice is a filter widget.
                for filter_value_name, filter_value in data.get("values", {}).items():
                    filter_item_data.update(
                        {
                            "filter_value": filter_value.get("value"),
                            "display_name": filter_value.get(
                                "name", str(filter_value_name)
                            ),
                            "count": filter_value.get("count", 0),
                        }
                    )

                    # FIXME let the FilterItem define the id
                    filter_id = "{field_id}.{value_name}".format(
                        field_id=field_id, value_name=filter_value_name
                    )

                    (filter_item, action) = self._create_filter_item_and_action(
                        filter_id, field_id, filter_item_data
                    )

                    prev_action = prev_actions.get(filter_id)
                    if prev_action:
                        widget = prev_action.defaultWidget()
                        action.defaultWidget().restore(widget)

                    filter_items.append(filter_item)
                    actions.append(action)
                    self._actions_by_filter[filter_id] = action

            # Add the entry to map the group to its filter items.
            self._filters_by_field[field_id] = filter_items

            # Sort the filter actions and add them to the menu.
            sorted_actions = sorted(actions, key=lambda item: item.text())
            group_actions = self.add_group(sorted_actions, data.get("name"))
            # Add the group id as a property on the actions.
            for action in group_actions:
                action.setProperty("group_id", field_id)

        if self.actions():
            self.addSeparator()
            clear_action = self.addAction("Clear All Filters")
            clear_action.triggered.connect(self.clear_filters)

        # Build and add the configuration menu as a submenu to the main filter menu.
        config_menu = self._build_config_menu(filters_def)
        self.addMenu(config_menu)

        # FIXME update this to restore menu actions checked from previous state.
        # Defaults to no filters active after rebuild
        self._active_filter = FilterItem(
            FilterItem.TYPE_GROUP, FilterItem.OP_AND, filters=[]
        )

    def _build_config_menu(self, filters_def):
        """
        Build the configuration menu to add as a submenu to the main filter menu.
        """

        menu = ShotgunMenu(self)
        menu.setTitle("More Filters")

        for field_id, data in filters_def.items():
            filter_id = "{}.Config".format(field_id)
            filter_widget = FilterItemWidget.create(
                filter_id,
                field_id,
                {
                    "filter_type": FilterItem.TYPE_LIST,
                    "display_name": data.get("name"),
                },
            )
            filter_widget.filter_item_checked.connect(self.toggle_action_group_cb)

            checked = not self._visible_fields or field_id in self._visible_fields
            filter_widget.action_triggered(checked)

            action = QtGui.QWidgetAction(menu)
            action.setDefaultWidget(filter_widget)
            menu.addAction(action)

        return menu

    def refresh_menu(self, updated_filters):
        """
        Do not rebuild the whole menu, just update it.
        """

        # TODO this does not append any new filters that appear in updated_filters, if any. This
        # simply updates the existing filters.

        for field_id, filter_items in self._filters_by_field.items():
            for item in filter_items:
                action = self._actions_by_filter[item.id]

                name = action.defaultWidget().name()
                filter_value = (
                    updated_filters.get(field_id, {}).get("values", {}).get(name)
                )
                if filter_value:
                    action.defaultWidget().update_widget(filter_value)
                else:
                    # TODO hide items if count is 0 - toggling the visibilty conflicts with the
                    # visible fields, so would need to ensure not showing actions that should be
                    # hidden even if their count is more than 0
                    action.defaultWidget().update_widget({"count": 0})

    def clear_menu(self):
        """
        Reset and clear the menu.
        """

        self._actions_by_filter = {}
        self._filters_by_field = {}

        self.clear()

    def clear_filters(self):
        """
        Reset the filter values.
        """

        for filter_items in self._filters_by_field.values():
            for item in filter_items:
                action = self._actions_by_filter[item.id]
                action.setChecked(False)
                action.defaultWidget().clear_value()

        self._active_filter.filters = []
        self.filters_changed.emit()

    def _create_filter_item_and_action(self, filter_id, group_id, filter_data):
        """
        Create the FilterItem and FilterItemWidget obejcts for the given filter data.
        """

        filter_item = FilterItem.create(filter_data, filter_id)

        action = QtGui.QWidgetAction(self.parentWidget())
        action.setProperty("filter_id", filter_id)

        widget = FilterItemWidget.create(filter_id, group_id, filter_data)
        widget.filter_item_checked.connect(
            lambda state, a=action: self._filter_item_checked(a, state)
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

    def toggle_action_group_cb(self, state):
        """
        Show or hide the actions corresponding to the widget that was toggled to show/hide filter groups.
        """

        widget = self.sender()
        checked = widget.has_value()
        group_id = widget.group_id

        for action in self.actions():
            action_group_id = action.property("group_id")
            if group_id == action_group_id:
                try:
                    action.defaultWidget().setVisible(checked)
                # except AttributeError:
                except:
                    pass
                action.setVisible(checked)

    def _filter_item_checked(self, action, state):
        """
        Callback triggered when a FilterItemWidget filter_item_checked signal emitted.
        """

        action.setChecked(state == QtCore.Qt.Checked)
        self._build_filter()
        self.filters_changed.emit()

    def _filter_item_text_changed(self, filter_item, text):
        """
        Callback triggered when a FilterItemWidget filter_item_text_changed signal emitted.
        """

        filter_item.filter_value = text

        # TODO support multiple values via comma separated list
        # filter_item.filter_value = text.split(",")

        self._build_filter()
        self.filters_changed.emit()

    def _filter_changed(self, filter_menu_item_widget):
        """
        Callback triggered when an action in the menu is triggered.
        """

        # Trigger the FilterItemWidget which will then trigger rebuilding the filter
        filter_menu_item_widget.action_triggered()

    def _build_filter(self):
        """"""

        active_group_filters = []

        for filter_items in self._filters_by_field.values():
            active_filters = [
                item
                for item in filter_items
                if self._actions_by_filter[item.id].defaultWidget().has_value()
            ]
            if active_filters:
                active_group_filters.append(
                    FilterItem(
                        FilterItem.TYPE_GROUP, FilterItem.OP_OR, filters=active_filters,
                    )
                )

        self._active_filter.filters = active_group_filters

    def _get_group_filter(self, group_field):
        """
        """

        group_filter = []

        for field_id, filter_items in self._filters_by_field.items():
            if field_id == group_field:
                continue

            active_filters = [
                item
                for item in filter_items
                if self._actions_by_filter[item.id].defaultWidget().has_value()
            ]
            if active_filters:
                group_filter.append(
                    FilterItem(
                        FilterItem.TYPE_GROUP, FilterItem.OP_OR, filters=active_filters
                    )
                )

        return group_filter


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
        # FIXME
        self.proxy_model.enable_caching(False)

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

        if name in filter_data:
            filter_data[name]["values"].setdefault(value, {}).setdefault("count", 0)
            filter_data[name]["values"][value]["count"] += 1
            filter_data[name]["values"][value]["value"] = value

        else:
            filter_data[name] = {
                "name": name,
                "type": FilterItem.TYPE_LIST,
                "values": {value: {"value": value, "count": 1}},
                # "data_func": lambda i, f=QtCore.Qt.DisplayRole: get_index_data(i, f),
                "filter_role": filter_role,
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

            sg_type = shotgun_globals.get_type_display_name(entity_type, project_id)
            field_id = "{type}.{field}".format(type=sg_type, field=sg_field)

            if proxy_filter:
                pfs = self._get_group_filter(field_id)
                if pfs:
                    self.proxy_model._filter_items = pfs
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
            # field_id = sg_field

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
                        "field": sg_field,
                        "field_type": sg_type,
                        "name": field_display,
                        "type": field_type,
                        "values": {value_id: {"value": filter_value, "count": 1}},
                        "data_func": lambda i, f=sg_field: get_index_data(i, f),
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
