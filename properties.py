import requests

class Properties():
  """Properties: utility class that stores data from a URL in a dict. Values
     in the dict are accessed by get(), which provides a default value.

     Data from the URL are expected be in string form, with multiple lines
     in key=value format.

     Keys may be decorated with a to-be-removed prefix
  """
  propUrl = 'https://connect.garmin.com/modern/main/js/properties/activity_types/activity_types.properties?bust=4.10.1.0'
  def __init__(self, session, key_trim_prefix = None):
    self.key_trim_prefix = key_trim_prefix

    self.properties = {}

    http_data = session.get(Properties.propUrl, allow_redirects=False)
    for line in http_data.iter_lines():
      (key, value) = line.split('=')
      if (key_trim_prefix != None):
        key = key.replace("activity_type_", "")
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

