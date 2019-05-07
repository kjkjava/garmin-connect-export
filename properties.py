import requests

class Properties():
  """Properties: utility class that stores data from a URL in a dict. Values
     in the dict are accessed by get(), which provides a default value.

     Data from the URL are expected to be in string form, with multiple lines
     in key=value format.

     If key_trim_prefix is provided, its value is deleted from key names.
  """
  def __init__(self, session, url, key_trim_prefix = None):
    self.properties = {}

    http_data = session.get(url, allow_redirects=False)
    for line in http_data.iter_lines():
      (key, value) = line.split('=')
      if (key_trim_prefix != None):
        key = key.replace(key_trim_prefix, "")
      self.properties[key] = value

  # Get a value, default to key as value
  def get(self, key):
    try:
      value = self.properties[key]
    except KeyError:
      value = key
    return value

  def do_print(self):
    for key in self.properties:
      print("  %s=%s" % (key, self.properties[key]))

