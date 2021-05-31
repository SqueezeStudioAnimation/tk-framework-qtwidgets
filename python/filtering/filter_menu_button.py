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
from .filter_menu import FilterMenu
from ..shotgun_menus import ShotgunMenu

shotgun_globals = sgtk.platform.import_framework(
    "tk-framework-shotgunutils", "shotgun_globals"
)


class FilterMenuButton(QtGui.QToolButton):
    """
    """

    def __init__(self, menu, name=None, icon=None, *args, **kwargs):
        """
        Constructor
        """

        assert isinstance(
            menu, FilterMenu
        ), "FilterMenuButton menu must be of type '{}'".format(
            FilterMenu.__class__.__name__
        )

        super(FilterMenuButton, self).__init__(*args, **kwargs)

        if not icon:
            icon = QtGui.QIcon()
            icon.addPixmap(
                QtGui.QPixmap(
                    ":tk_framework_qtwidgets.filtering/icons/filter-active.png"
                ),
                QtGui.QIcon.Normal,
                QtGui.QIcon.On,
            )
            icon.addPixmap(
                QtGui.QPixmap(
                    ":tk_framework_qtwidgets.filtering/icons/filter-inactive.png"
                ),
                QtGui.QIcon.Normal,
                QtGui.QIcon.Off,
            )

        self.setCheckable(True)
        self.setPopupMode(QtGui.QToolButton.InstantPopup)
        self.setToolButtonStyle(QtCore.Qt.ToolButtonTextBesideIcon)
        self.setIcon(icon)
        self.setText(name or "Filters")
        self.setMenu(menu)

    def setMenu(self, menu):
        """
        """

        if self.menu():
            self.menu().disconnect(self.menu().filters_changed)

        super(FilterMenuButton, self).setMenu(menu)

        self.menu().filters_changed.connect(self._filters_changed)

    def _filters_changed(self):
        """
        Callback on filter menu changes.
        """

        self.setChecked(self.menu().has_filtering)
