# Copyright (c) 2015 Shotgun Software Inc.
#
# CONFIDENTIAL AND PROPRIETARY
#
# This work is provided "AS IS" and subject to the Shotgun Pipeline Toolkit
# Source Code License included in this distribution package. See LICENSE.
# By accessing, using, copying or modifying this work you indicate your
# agreement to the Shotgun Pipeline Toolkit Source Code License. All rights
# not expressly granted therein are reserved by Shotgun Software Inc.

import sgtk
from sgtk.platform.qt import QtGui
from .shotgun_field_factory import ShotgunFieldFactory

shotgun_globals = sgtk.platform.import_framework("tk-framework-shotgunutils", "shotgun_globals")


class StatusListWidget(QtGui.QLabel):
    def __init__(self, parent=None, value=None):
        QtGui.QLabel.__init__(self, parent)

        if value is not None:
            str_val = shotgun_globals.get_status_display_name(value)
            color_str = shotgun_globals.get_status_color(value)

            if color_str:
                # append colored box to indicate status color
                str_val = ("<span style='color: rgb(%s)'>&#9608;</span>&nbsp;%s" % (color_str, str_val))

            self.setText(str_val)

ShotgunFieldFactory.register("status_list", StatusListWidget)
