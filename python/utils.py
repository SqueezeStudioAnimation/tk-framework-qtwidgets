# Copyright (c) 2016 Shotgun Software Inc.
#
# CONFIDENTIAL AND PROPRIETARY
#
# This work is provided "AS IS" and subject to the Shotgun Pipeline Toolkit
# Source Code License included in this distribution package. See LICENSE.
# By accessing, using, copying or modifying this work you indicate your
# agreement to the Shotgun Pipeline Toolkit Source Code License. All rights
# not expressly granted therein are reserved by Shotgun Software Inc.

import datetime
import re

import sgtk
from sgtk import TankError

shotgun_globals = sgtk.platform.import_framework(
    "tk-framework-shotgunutils", "shotgun_globals",
)


def get_hyperlink_html(url, name):
    """
    Provides an html string for a hyperlink pointing to the given URL
    and displaying the provided string name.

    :param str url: The URL that the hyperlink navigates to.
    :param str name: The string name to display.

    :return: HTML string.
    """
    # Older versions of core don't have the SG_LINK_COLOR constant, so we'll
    # just fall back on SG_FOREGROUND_COLOR in that case.
    color = sgtk.platform.constants.SG_STYLESHEET_CONSTANTS.get(
        "SG_LINK_COLOR",
        sgtk.platform.constants.SG_STYLESHEET_CONSTANTS["SG_FOREGROUND_COLOR"],
    )

    html = "<a href='%s' style='text-decoration: none; color: %s'><b>%s</b></a>" % (
        url,
        color,
        name,
    )

    return html


def resolve_sg_fields(token_str):
    """
    Returns the sg fields for all tokens given a token_str.

    :param token_str: String with tokens, e.g. "{code}_{created_by}"
    :returns: All shotgun fields, e.g. ["code", "created_by"]
    """

    fields = []

    for token in resolve_tokens(token_str):
        fields.extend(token["sg_fields"])

    return fields


def convert_token_string(token_str, sg_data):
    """
    Convert a string with {tokens} given a shotgun data dict

    :param token_str: Token string as defined in the shotgun fields hook
    :param sg_data: Data dictionary to get values from
    :returns: string with tokens replaced with actual values
    """

    if not token_str:
        return ""

    for token in resolve_tokens(token_str):

        # no value has been found in the Shotgun data for the fields
        if not list(set(token["sg_fields"]) & set(sg_data.keys())):
            continue

        for sg_field in token["sg_fields"]:
            sg_value = sg_data.get(sg_field)
            if sg_value:
                break

        if (sg_value is None or sg_value == []) and (
            token["pre_roll"] or token["post_roll"]
        ):
            # shotgun value is empty
            # if we have a pre or post roll part of the token
            # then we basicaly just skip the display of both
            # those and the value entirely
            # e.g. Hello {[Shot:]sg_shot} becomes:
            # for shot abc: 'Hello Shot:abc'
            # for shot <empty>: 'Hello '
            token_str = token_str.replace("{%s}" % token["full_token"], "")

        else:
            resolved_value = sg_field_to_str(
                sg_data["type"], sg_field, sg_value, token["directive"]
            )

            # potentially add pre/and post
            if token["pre_roll"]:
                resolved_value = "%s%s" % (token["pre_roll"], resolved_value)
            if token["post_roll"]:
                resolved_value = "%s%s" % (resolved_value, token["post_roll"])
            # and replace the token with the value
            token_str = token_str.replace("{%s}" % token["full_token"], resolved_value)

    return token_str


def resolve_tokens(token_str):
    """
    Resolve a list of tokens from a string.

    Tokens are on the following form:

        {[preroll]shotgun.field.name|sg_field_name_fallback::directive[postroll]}

    Basic Examples:

    - {code}                         # simple format
    - {sg_sequence.Sequence.code}    # deep links
    - {artist|created_by}            # if artist is null, use creted_by

    Directives are also supported - these are used by the formatting logic
    and include the following:

    - {sg_sequence::showtype}        # will generate a link saying
                                     # 'Sequence ABC123' instead of just
                                     # 'ABC123' like it does by default
    - {sg_sequence::nolink}          # no url link will be created

    Optional pre/post roll - if a value is null, pre- and post-strings are
    omitted from the final result. Examples of this syntax:

    - {[Name: ]code}                 # If code is set, 'Name: xxx' will be
                                     # printed out, otherwise nothing.
    - {[Name: ]code[<br>]}           # Same but with a post line break

    :param token_str: String with tokens, e.g. "{code}_{created_by}"
    :returns: a list of tuples with (full_token, sg_fields, directive, preroll, postroll)
    """

    if not token_str:
        return []

    try:
        # find all field names ["xx", "yy", "zz.xx"] from "{xx}_{yy}_{zz.xx}"
        raw_tokens = set(re.findall(r"{([^}^{]*)}", token_str))
    except Exception as error:
        raise TankError("Could not parse '%s' - Error: %s" % (token_str, error))

    fields = []
    for raw_token in raw_tokens:

        pre_roll = None
        post_roll = None
        directive = None

        processed_token = raw_token

        match = re.match(r"^\[([^\]]+)\]", processed_token)
        if match:
            pre_roll = match.group(1)
            # remove preroll part from main token
            processed_token = processed_token[len(pre_roll) + 2 :]

        match = re.match(r".*\[([^\]]+)\]$", processed_token)
        if match:
            post_roll = match.group(1)
            # remove preroll part from main token
            processed_token = processed_token[: -(len(post_roll) + 2)]

        if "::" in processed_token:
            # we have a special formatting directive
            # e.g. created_at::ago
            (sg_field_str, directive) = processed_token.split("::")
        else:
            sg_field_str = processed_token

        if "|" in sg_field_str:
            # there is more than one sg field, we have a
            # series of fallbacks
            sg_fields = sg_field_str.split("|")
        else:
            sg_fields = [sg_field_str]

        fields.append(
            {
                "full_token": raw_token,
                "sg_fields": sg_fields,
                "directive": directive,
                "pre_roll": pre_roll,
                "post_roll": post_roll,
            }
        )

    return fields


def sg_field_to_str(sg_type, sg_field, value, directive=None):
    """
    Converts a Shotgun field value to a string.

    Formatting directives can be passed to alter the conversion behaviour:

    Entity Dictionary directives:
        - showtype: Show the type for links, e.g. return "Shot ABC123" instead
        of just "ABC123"

        - nolink: don't return a <a href> style hyperlink for links, instead just
        return a string.

    Version Number directives:
        - zeropadded: Pad the version number with up to three zeros
        - A format string that contains a single argument specifier to substitute the
          version number integer value; e.g. '%03d' will achieve the same as 'zeropadded'.

    :param sg_type: Shotgun data type
    :param sg_field: Shotgun field name
    :param value: value to turn into a string
    :param directive: Formatting directive, see above
    :returns: The Shotgun field formatted as a string
    """

    str_val = ""

    if value is None:
        return shotgun_globals.get_empty_phrase(sg_type, sg_field)

    elif isinstance(value, dict) and set(["type", "id", "name"]) == set(value.keys()):

        # entity link

        if directive == "showtype":
            # links are displayed as "Shot ABC123"

            # get the nice name from our schema
            # this is so that it says "Level" instead of "CustomEntity013"
            entity_type_display_name = shotgun_globals.get_type_display_name(
                value["type"]
            )
            link_name = "%s %s" % (entity_type_display_name, value["name"])
        else:
            # links are just "ABC123"
            link_name = value["name"]

        if directive == "nolink":
            str_val = link_name
        else:
            str_val = get_hyperlink_html(
                url="sgtk:%s:%s" % (value["type"], value["id"]), name=link_name,
            )

    elif isinstance(value, list):
        # list of items
        link_urls = []
        for list_item in value:
            link_urls.append(sg_field_to_str(sg_type, sg_field, list_item, directive))
        str_val = ", ".join(link_urls)

    elif sg_field in ["created_at", "updated_at"]:
        created_datetime = datetime.datetime.fromtimestamp(value)
        (str_val, _) = create_human_readable_timestamp(created_datetime)

    elif sg_field == "sg_status_list":
        str_val = shotgun_globals.get_status_display_name(value)

        color_str = shotgun_globals.get_status_color(value)
        if color_str:
            # append colored box to indicate status color
            str_val = "<span style='color: rgb(%s)'>" "&#9608;</span>&nbsp;%s" % (
                color_str,
                str_val,
            )
    elif sg_field == "version_number":
        if directive:
            if directive == "zeropadded":
                directive = "%03d"
            str_val = directive % value

    elif sg_field == "type":
        if directive == "showtype":
            str_val = shotgun_globals.get_type_display_name(value)

    else:
        str_val = str(value)
        # make sure it gets formatted correctly in html
        str_val = str_val.replace("\n", "<br>")

    return str_val


def create_human_readable_timestamp(datetime_obj):
    """
    Formats a time stamp the way dates are formatted in the
    Shotgun activity stream. Examples of output:

    Recent posts: 10:32
    This year: 24 June 10:32
    Last year and earlier: 12 December 2007

    :param datetime_obj: Datetime obj to format
    :returns: date str
    """
    # standard format
    full_time_str = datetime_obj.strftime("%a %d %b %Y %H:%M")

    if datetime_obj > datetime.datetime.now():
        # future times are reported precisely
        return full_time_str, full_time_str

    # get the delta and components
    delta = datetime.datetime.now() - datetime_obj

    # the timedelta structure does not have all units; bigger units are converted
    # into given smaller ones (hours -> seconds, minutes -> seconds, weeks > days, ...)
    # but we need all units:
    delta_weeks = delta.days // 7
    delta_days = delta.days

    if delta_weeks > 52:
        # more than one year ago - 26 June 2012
        time_str = datetime_obj.strftime("%d %b %Y %H:%M")

    elif delta_days > 1:
        # ~ more than one week ago - 26 June
        time_str = datetime_obj.strftime("%d %b %H:%M")

    else:
        # earlier today - display timestamp - 23:22
        time_str = datetime_obj.strftime("%H:%M")

    return time_str, full_time_str
