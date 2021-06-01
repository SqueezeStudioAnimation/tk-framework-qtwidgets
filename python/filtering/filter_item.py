# Copyright (c) 2021 Shotgun Software Inc.
#
# CONFIDENTIAL AND PROPRIETARY
#
# This work is provided "AS IS" and subject to the Shotgun Pipeline Toolkit
# Source Code License included in this distribution package. See LICENSE.
# By accessing, using, copying or modifying this work you indicate your
# agreement to the Shotgun Pipeline Toolkit Source Code License. All rights
# not expressly granted therein are reserved by Shotgun Software Inc.
import datetime

import sgtk
from sgtk.platform.qt import QtCore
from tank_vendor import six
from tank_vendor.shotgun_api3 import sg_timezone


class FilterItem(object):
    """
    Class object to encapsulate all the necessary data to filter items in a model.
    """

    # The filter operations
    OP_AND = "and"
    OP_OR = "or"
    OP_IS_TRUE = "true"
    OP_IS_FALSE = "false"
    OP_IN = "in"
    OP_NOT_IN = "!in"
    OP_EQUAL = "="
    OP_NOT_EQUAL = "!="
    OP_LESS_THAN = "<"
    OP_LESS_THAN_OR_EQUAL = "<="
    OP_GREATER_THAN = ">"
    OP_GREATER_THAN_OR_EQUAL = ">="

    # The filter types
    TYPE_BOOL = "bool"
    TYPE_STR = "str"
    TYPE_NUMBER = "number"
    TYPE_LIST = "list"
    # FIXME mapping types between shotgun and filtering
    # Shotgun field types
    TYPE_TEXT = "text"
    TYPE_DATE = "date"
    TYPE_DATETIME = "date_time"
    TYPE_STATUS_LIST = "status_list"
    TYPE_ENTITY = "entity"
    TYPE_MULTI_ENTITY = "multi_entity"
    # The group type is a special type that contains a list of filters itself and its operation
    # is either AND or OR the list of filters
    TYPE_GROUP = "group"

    DEFAULT_OPS = {
        TYPE_BOOL: OP_EQUAL,  # Should we use OP_IS_TRUE/IS_FALSE ?
        TYPE_STR: OP_IN,
        TYPE_TEXT: OP_IN,
        TYPE_NUMBER: OP_EQUAL,
        TYPE_LIST: OP_IN,
        TYPE_STATUS_LIST: OP_IN,
        TYPE_ENTITY: OP_EQUAL,
        TYPE_MULTI_ENTITY: OP_EQUAL,
        TYPE_DATE: OP_EQUAL,
        TYPE_DATETIME: OP_EQUAL,
        TYPE_GROUP: OP_AND,
    }

    def __init__(
        self,
        filter_type,
        filter_op,
        filter_role=None,
        data_func=None,
        filter_value=None,
        filters=None,
        filter_id=None,
    ):
        """
        Constructor

        :param filter_type: The data type for the filter
        :type filter_type: One of the filter type enums defined for this class; e.g.:
            TYPE_BOOL
            TYPE_STR
            TYPE_NUMBER
            TYPE_LIST
            TYPE_GROUP
        :param filter_op:
        :type filter_op: One of the filter operation enums defined for this class; e.g.:
            OP_AND
            OP_OR
            OP_IS_TRUE
            OP_IS_FALSE
            OP_IN
            OP_NOT_IN
            OP_EQUAL
            OP_NOT_EQUAL
            OP_LESS_THAN
            OP_LESS_THAN_OR_EQUAL
            OP_GREATER_THAN
        :param filter_role: An item data role to extract the index data to filter based on (optional).
        :type filter_role: :class:`sgtk.platform.qt.QtCore.Qt.ItemDataRole`
        :param data_func: A function that can be called to extract the index data to filter based on (optional).
                          NOTE: if a filter_role is defined, this will have no effect.
        :param filter_value: The value the item's data will be filtered by (optional). This value may be set
                             later, if not known at time of init.
        :type filter_value: The data type for this filter
        :param filters: A list of FilterItem objects (optional). This is used for group filters; this list of
                        filter items are the group of filters to apply to the data.
        :type filters: list<FilterItem>
        """

        # TODO make filter_id mandatory
        self._id = filter_id

        self.filter_type = filter_type
        self.filter_role = filter_role
        self.filter_value = filter_value
        self.filter_op = filter_op
        self.filters = filters
        self.data_func = data_func

        self._filter_funcs_by_type = {
            self.TYPE_BOOL: self.is_bool_valid,
            self.TYPE_STR: self.is_str_valid,
            self.TYPE_TEXT: self.is_str_valid,
            self.TYPE_DATE: self.is_datetime_valid,
            self.TYPE_DATETIME: self.is_datetime_valid,
            self.TYPE_STATUS_LIST: self.is_str_valid,
            self.TYPE_NUMBER: self.is_number_valid,
            self.TYPE_LIST: self.is_list_valid,
            self.TYPE_ENTITY: self.is_entity_valid,
            self.TYPE_MULTI_ENTITY: self.is_multi_entity_valid,
        }

    @property
    def id(self):
        """
        Get the id for this FilterItem.
        """

        return self._id

    @staticmethod
    def get_datetime_bucket(dt):
        """
        TODO move to shotgun_globals.date_time
        """

        if dt is None:
            return "No Date"

        if isinstance(dt, six.string_types):
            dt = datetime.datetime.strptime(dt, "%Y-%m-%d")
            epoch = datetime.datetime.utcfromtimestamp(0)
            dt = (dt - epoch).total_seconds()

        if isinstance(dt, float):
            dt = datetime.datetime.fromtimestamp(dt, tz=sg_timezone.LocalTimezone())

        if not isinstance(dt, datetime.datetime):
            raise TypeError(
                "Cannot convert value type '{}' to datetime".format(type(dt))
            )

        now = datetime.datetime.now(sg_timezone.LocalTimezone())
        today = now.date()
        date_value = dt.date()

        if date_value == today:
            return "Today"

        yesterday = now - datetime.timedelta(days=1)
        if date_value == yesterday.date():
            return "Yesterday"

        tomorrow = now + datetime.timedelta(days=1)
        if date_value == tomorrow.date():
            return "Tomorrow"

        # Far future is roughly 4 months (4 times 4 weeks)
        far_future = today + datetime.timedelta(days=-today.weekday(), weeks=4 * 4)
        if date_value > far_future:
            return "Far Future"

        long_ago = today - datetime.timedelta(days=-today.weekday(), weeks=4 * 4)
        if date_value < long_ago:
            return "Long Ago"

        last_monday = today - datetime.timedelta(days=today.weekday())
        last_last_monday = today - datetime.timedelta(days=today.weekday(), weeks=2)
        last_last_last_monday = today - datetime.timedelta(
            days=today.weekday(), weeks=3
        )
        next_monday = today + datetime.timedelta(days=-today.weekday(), weeks=1)
        next_next_monday = today + datetime.timedelta(days=-today.weekday(), weeks=2)
        next_next_next_monday = today + datetime.timedelta(
            days=-today.weekday(), weeks=3
        )

        if date_value < last_last_last_monday:
            return "Last Few Months"

        if date_value < last_last_monday:
            return "Last Few Weeks"

        if date_value < last_monday:
            return "Last Week"

        if last_monday <= date_value < next_monday:
            return "This Week"

        if next_monday <= date_value < next_next_monday:
            return "Next Week"

        if date_value > next_next_next_monday:
            return "Next Few Months"

        if date_value > next_next_monday:
            return "Next Few Weeks"

        assert (
            False
        ), "Datetime value was not able to be converted to bucket, will default to plain datetime string"
        return dt.strftime("%x")

    @classmethod
    def create(cls, data, filter_id=None):
        """
        Factory classmethod to create a new FilterItem object from the provided data.

        :param data: The data to create the FilterItem object from.
        :type data: dict
        """

        try:
            filter_type = data["filter_type"]
            filter_op = data["filter_op"]
        except KeyError:
            raise ValueError(
                "Missing required key-value pairs to create FilterItem object"
            )

        filter_role = data.get("filter_role")
        data_func = data.get("data_func")
        if filter_role is None and data_func is None:
            raise ValueError(
                "Missing required key-value pairs to create FilterItem object"
            )

        filter_value = data.get("filter_value")
        filters = data.get("filters")

        return cls(
            filter_type,
            filter_op,
            filter_role,
            data_func,
            filter_value,
            filters,
            filter_id=filter_id,
        )

    @classmethod
    def default_op_for_type(cls, filter_type):
        """
        """

        return cls.DEFAULT_OPS.get(filter_type, FilterItem.OP_EQUAL)

    @classmethod
    def is_group_op(cls, op):
        """
        Return True if the filter item operation is valid.
        """

        return op in (cls.OP_AND, cls.OP_OR)

    def is_group(self):
        """
        Return True if this filter item is a group
        """

        return self.filter_type == self.TYPE_GROUP and self.is_group_op(self.filter_op)

    def get_index_data(self, index):
        """
        Return the index's data based on the filter item. The index data will be first
        attempted to be retrieved from the index's data method, using the filter role.
        If no role is defined, the data_func will be called to extract the data (if such
        a function is defined).

        A `filter_role` or `data_func` must be defined to reteieve the index data.

        :param index: The index to get the data from
        :type index: :class:`sgtk.platform.qt.QtCore.QModelIndex`

        :return: The index data
        """

        if self.filter_role is not None:
            return index.data(self.filter_role)

        if self.data_func and callable(self.data_func):
            return self.data_func(index)

        assert (
            False
        ), "FilterItem does not have a filter role or data function to retrieve index data to filter on"
        return None

    def accepts(self, index):
        """
        Return True if this filter item accepts the given index.

        :param index: The index that holds the data to filter on.
        :type index: :class:`sgtk.platform.qt.QtCore.QModelIndex`

        :return: True if the filter accepts the index, else False.
        """

        data = self.get_index_data(index)
        filter_func = self._filter_funcs_by_type.get(self.filter_type, None)

        if filter_func is None:
            return False  # Invalid filter type

        return filter_func(data)

    def is_bool_valid(self, value):
        """
        Filter the incoming boolean value.

        :param value: The value to filter.
        :type value: bool

        :return: True if the filter accepts the value, else False.
        """

        if self.filter_op == self.OP_IS_TRUE:
            return value

        if self.filter_op == self.OP_IS_FALSE:
            return not value

        if self.filter_op == self.OP_EQUAL:
            return value == self.filter_value

        assert False, "Unsupported operation for filter type 'bool'"
        return False

    def is_str_valid(self, value):
        """
        Filter the incoming string value.

        :param value: The value to filter.
        :type value: str

        :return: True if the filter accepts the value, else False.
        """

        if self.filter_op == self.OP_EQUAL:
            return value == self.filter_value

        if self.filter_op == self.OP_IN:
            regex = QtCore.QRegularExpression(
                self.filter_value, QtCore.QRegularExpression.CaseInsensitiveOption
            )

            match = regex.match(value)
            return match.hasMatch()

        assert False, "Unsupported operation for filter type 'str'"
        return False

    def is_number_valid(self, value):
        """
        Filter the incoming number value.

        :param value: The value to filter.
        :type value: int | float | ...

        :return: True if the filter accepts the value, else False.
        """

        if isinstance(value, six.string_types):
            # FIXME this only supports int
            value = int(value)

        # FIXME this should be casted on assignment
        if isinstance(self.filter_value, six.string_types):
            # FIXME this only supports int
            self.filter_value = int(self.filter_value)

        if self.filter_op == self.OP_EQUAL:
            return value == self.filter_value

        if self.filter_op == self.OP_EQUAL:
            return value == self.filter_value

        if self.filter_op == self.OP_GREATER_THAN:
            return value > self.filter_value

        if self.filter_op == self.OP_GREATER_THAN_OR_EQUAL:
            return value >= self.filter_value

        if self.filter_op == self.OP_LESS_THAN:
            return value < self.filter_value

        if self.filter_op == self.OP_LESS_THAN_OR_EQUAL:
            return value <= self.filter_value

        assert False, "Unsupported operation for filter type 'number'"
        return False

    def is_datetime_valid(self, value):
        """
        Filter the incoming datetime value.
        """

        if self.filter_op == self.OP_EQUAL:
            datetiem_bucket = self.get_datetime_bucket(value)
            return datetiem_bucket == self.filter_value

        assert False, "Unsupported operation for filter type 'datetime'"
        return False

    def is_list_valid(self, values_list):
        """
        Filter the incoming list value.

        :param value: The values list to filter by.
        :type value: list

        :return: True if the filter accepts the values list, else False.
        """

        values_list = values_list or []

        if not isinstance(values_list, list):
            values_list = [values_list]

        if self.filter_op == self.OP_IN:
            for value in values_list:
                if value == self.filter_value:
                    return True
            return False

        if self.filter_op == self.OP_EQUAL:
            return values_list == self.filter_value

        assert False, "Unsupported operation for filter type 'list'"
        return False

    def is_entity_valid(self, entity):
        """
        Filter the incoming entity value.
        """

        if self.filter_op == self.OP_EQUAL:
            return entity == self.filter_value

        assert False, "Unsupported operation for filter type `{type}`".format(
            type=self.filter_type
        )
        return False

    def is_multi_entity_valid(self, entity_list):
        """
        Filter the incoming list of entities.
        """

        entity_list = entity_list or []

        if self.filter_op == self.OP_EQUAL:
            for entity in entity_list:
                if entity == self.filter_value:
                    return True

            return False

        assert False, "Unsupported operation for filter type `{type}`".format(
            type=self.filter_type
        )
        return False
