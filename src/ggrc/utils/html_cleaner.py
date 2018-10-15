# Copyright (C) 2018 Google Inc.
# Licensed under http://www.apache.org/licenses/LICENSE-2.0 <see LICENSE file>

"""Provides an HTML cleaner function with sqalchemy compatible API"""

from HTMLParser import HTMLParser

import cgi
import random
import string

import bleach


# Set up custom tags/attributes for bleach
BLEACH_TAGS = [
    'caption', 'strong', 'em', 'b', 'i', 'p', 'code', 'pre', 'tt', 'samp',
    'kbd', 'var', 'sub', 'sup', 'dfn', 'cite', 'big', 'small', 'address',
    'hr', 'br', 'div', 'span', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'ul',
    'ol', 'li', 'dl', 'dt', 'dd', 'abbr', 'acronym', 'a', 'img',
    'blockquote', 'del', 'ins', 'table', 'tbody', 'tr', 'td', 'th',
] + bleach.ALLOWED_TAGS

BLEACH_ATTRS = {}

ATTRS = [
    'href', 'src', 'width', 'height', 'alt', 'cite', 'datetime',
    'title', 'class', 'name', 'xml:lang', 'abbr'
]

for tag in BLEACH_TAGS:
  BLEACH_ATTRS[tag] = ATTRS


def _clean_escaped_html(value):
  """Cleans out unsafe escaped HTML tags.

    Args:
      value: html (string) to be cleaned
    Returns:
      escaped html (string) without unsafe tags.
  """
  value = _clean(value)
  string_length = 10
  sequence = string.ascii_uppercase + string.ascii_lowercase + string.digits
  random_string = ''.join(
      random.SystemRandom().choice(sequence) for _ in range(string_length)
  )
  lt_tag = 'lt%s' % random_string
  gt_tag = 'gt%s' % random_string
  customized_value = value.replace('<', lt_tag).replace('>', gt_tag)
  unescaped_value = HTMLParser().unescape(customized_value)
  cleaned_value = _clean(unescaped_value)
  escaped_value = cgi.escape(cleaned_value)
  return escaped_value.replace(lt_tag, '<').replace(gt_tag, '>')


def _clean(value):
  """Cleans out unsafe HTML tags. Uses bleach

    Args:
      value: html (string) to be cleaned
    Returns:
      html (string) without unsafe tags.
  """
  return bleach.clean(value, BLEACH_TAGS, BLEACH_ATTRS, strip=True)


def cleaner(dummy, value, *args):
  """Cleans out unsafe HTML tags.

  Uses cleaning until it reaches a fix point.

  Args:
    dummy: sqalchemy will pass in the model class
    value: html (string) to be cleaned
  Returns:
    Html (string) without unsafe tags.
  """
  # Some cases don't use the title value and it's nullable, so check for that
  if value is None:
    return value
  if not isinstance(value, basestring):
    # no point in sanitizing non-strings
    return value

  event = args[1]
  escape_keys = getattr(type(dummy), '_escape_html', [])
  escape_html = event and event.key in escape_keys
  parser = HTMLParser()
  value = unicode(value)
  while True:
    lastvalue = value
    if escape_html:
      value = _clean_escaped_html(value)
    else:
      value = parser.unescape(_clean(value))
    if value == lastvalue:
      break
  return value
