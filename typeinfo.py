import requests
import json

class TypeInfo():
  """
  TypeInfo: utility dict wrapper class
  Looks up types in a url and an associated Properties instance
  """
  def __init__(self, session, url, props):
    self.type_info = {}
    http_data = session.get(url, allow_redirects=False)
    if http_data.status_code != 200:
        print("TypeInfo error code: %d" % (http_data.status_code))
        self.type_info = None
        return

    types = json.loads(http_data.text)
    key = 'typeKey'
    for _type in types:
      type_id = _type['typeId']
      this_type = {}
      this_type[key] = _type.get(key, "")
      # Set type from typeKey
      this_type['type'] = props.get(this_type[key])
      self.type_info[type_id] = this_type

  def do_print(self):
    print "### type_info"
    for _type in self.type_info:
       print _type
       for param in self.type_info[_type]:
         print "    " + param + ": " + str(self.type_info[_type][param])
    print "###"

  def __getitem__(self, key):
    return self.type_info[key]
