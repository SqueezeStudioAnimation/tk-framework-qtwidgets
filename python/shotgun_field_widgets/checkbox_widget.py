# Copyright (c) 2015 Shotgun Software Inc.
#
# CONFIDENTIAL AND PROPRIETARY
#
# This work is provided "AS IS" and subject to the Shotgun Pipeline Toolkit
# Source Code License included in this distribution package. See LICENSE.
# By accessing, using, copying or modifying this work you indicate your
# agreement to the Shotgun Pipeline Toolkit Source Code License. All rights
# not expressly granted therein are reserved by Shotgun Software Inc.

from sgtk.platform.qt import QtCore, QtGui
from .shotgun_field_factory import ShotgunFieldFactory


class CheckBoxWidget(QtGui.QCheckBox):
    def __init__(self, parent=None, value=None):
        QtGui.QCheckBox.__init__(self, parent)
        if value:
            self.setCheckState(QtCore.Qt.Checked)

ShotgunFieldFactory.register("checkbox", CheckBoxWidget)
