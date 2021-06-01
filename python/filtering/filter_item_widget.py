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

from .filter_item import FilterItem
from ..shotgun_menus import ShotgunMenu
from ..search_widget import SearchWidget


class FilterItemWidget(QtGui.QWidget):
    """
    A widget to represent a FilterItem object.
    """

    SINGLE_VALUE_TYPES = [
        FilterItem.TYPE_NUMBER,
        FilterItem.TYPE_STR,
        FilterItem.TYPE_TEXT,
    ]

    filter_item_checked = QtCore.Signal(int)
    filter_item_text_changed = QtCore.Signal(str)

    def __init__(self, filter_id, group_id, filter_data, parent=None):
        """
        """

        super(FilterItemWidget, self).__init__(parent)

        self._id = filter_id
        self._group_id = group_id

        # Widget style
        # self.setStyleSheet(":hover{background:palette(light)}");

        self.checkbox = None
        self.line_edit = None

        layout = QtGui.QHBoxLayout()
        layout.setAlignment(QtCore.Qt.AlignLeft)
        self.setLayout(layout)

    @property
    def id(self):
        """
        Get the id for this widget.
        """

        return self._id

    @property
    def group_id(self):
        """
        Get the group id for this widget.
        """

        return self._group_id

    @classmethod
    def create(cls, filter_id, group_id, filter_data, parent=None):
        """
        """

        filter_type = filter_data.get("filter_type")
        if not filter_type:
            raise sgtk.TankError("Missing required filter type.")

        if filter_type in (
            FilterItem.TYPE_NUMBER,
            FilterItem.TYPE_STR,
            FilterItem.TYPE_TEXT,
        ):
            return TextFilterItemWidget(filter_id, group_id, filter_data, parent)

        # Default to choices filter widget
        return ChoicesFilterItemWidget(filter_id, group_id, filter_data, parent)

    def restore(self, widget):
        """
        Restore the widget state from another widget.
        """

    def name(self):
        """
        """

    def has_value(self):
        """
        """
        raise sgtk.TankError("Abstract class method not overriden")

    def action_triggered(self, value=None):
        """
        Override this method to provide any functionality.
        """

    def update_widget(self, data):
        """
        Override this method to provide any functionality.
        """

    def clear_value(self):
        """
        Override this method to provide any functionality.
        """

        raise sgtk.TankError("Abstract class method not overriden")

    def paintEvent(self, event):
        """
        """

        super(FilterItemWidget, self).paintEvent(event)

        painter = QtGui.QPainter()
        painter.begin(self)

        painter.end()


class ChoicesFilterItemWidget(FilterItemWidget):
    """
    """

    def __init__(self, filter_id, group_id, filter_data, parent=None):
        """
        Constructor
        """

        super(ChoicesFilterItemWidget, self).__init__(
            filter_id, group_id, filter_data, parent
        )

        layout = self.layout()

        self.checkbox = QtGui.QCheckBox()
        self.checkbox.stateChanged.connect(self.filter_item_checked)
        layout.addWidget(self.checkbox)

        icon = filter_data.get("icon")
        if icon:
            icon_label = QtGui.QLabel()
            icon_label.setPixmap(icon.pixmap(14))
            layout.addWidget(icon_label)

        name = filter_data.get("display_name", filter_data.get("filter_value"))
        self.label = QtGui.QLabel(name)
        layout.addWidget(self.label)

        self.count_label = QtGui.QLabel()
        count = filter_data.get("count")
        if count:
            self.count_label.setText(str(count))
            layout.addStretch()
            layout.addWidget(self.count_label)

    def name(self):
        return self.label.text()

    def restore(self, widget):
        """
        Restore this filter widget from another widget, of the same type.
        """

        self.action_triggered(widget.has_value())

    def update_widget(self, data):
        """
        """

        count = str(data.get("count", 0))
        self.count_label.setText(count)
        self.count_label.repaint()

    def has_value(self):
        """
        Return True if the the filter widget currently has a value.
        """

        return self.checkbox.isChecked()

    def action_triggered(self, value=None):
        """
        """

        # Keep the item checkbox with the action check
        if value is None:
            self.checkbox.setChecked(not self.checkbox.isChecked())
        else:
            was_checked = self.checkbox.isChecked()
            self.checkbox.setChecked(value)

            if was_checked == self.checkbox.isChecked():
                # We want to know that the action was triggered, even if the state did not
                # necessary change.
                self.filter_item_checked.emit(self.checkbox.checkState())

    def clear_value(self):
        """
        Clear the filter widget current value.
        """

        self.checkbox.setChecked(False)


class TextFilterItemWidget(FilterItemWidget):
    """
    A filter widget for searching text values.
    """

    def __init__(self, filter_id, group_id, filter_data, parent=None):
        """
        Constructor.
        """

        super(TextFilterItemWidget, self).__init__(
            filter_id, group_id, filter_data, parent=parent
        )

        # TODO filter operation may demand a different tyep of filter widget

        self.line_edit = SearchWidget(self)
        self.line_edit.search_edited.connect(self._search_edited_cb)

        layout = self.layout()
        layout.addWidget(self.line_edit)

    def restore(self, widget):
        """
        Restore this filter widget from another widget, of the same type.
        """

        self.line_edit._set_search_text(widget.line_edit.search_text)

    def has_value(self):
        """
        Return True if the the filter widget currently has a value.
        """

        return bool(self.line_edit.search_text)

    def clear_value(self):
        """
        Clear the filter widget current value.
        """

        self.line_edit.clear()

    def _search_edited_cb(self, text):
        """
        Callback triggered on the SearchWidget text changed.
        """

        self.filter_item_text_changed.emit(text)
