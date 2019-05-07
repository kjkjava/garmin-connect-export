import json

from gclogin import GarminLogin
from properties import Properties
from deviceinfo import DeviceInfo
from typeinfo import TypeInfo

gcl = GarminLogin()
session = gcl._get_session(email='aaronferrucci', password='Adh0r3w38x4k1u8Z')

deviceinfo = DeviceInfo(session)
# print("\nDevices:")
# deviceinfo.do_print()

# activity properties
activity_properties_url = 'https://connect.garmin.com/modern/main/js/properties/activity_types/activity_types.properties?bust=4.10.1.0'
activity_properties = Properties(session, activity_properties_url, "activity_type_")
print("\nActivity Properties:")
activity_properties.do_print()

activity_type_url = "https://connect.garmin.com/modern/proxy/activity-service/activity/activityTypes"
activity_type_info = TypeInfo(session, activity_type_url, activity_properties)
print("\nActivity Type Info:")
activity_type_info.do_print()

event_properties_url = 'https://connect.garmin.com/modern/main/js/properties/event_types/event_types.properties?bust=4.10.1.0'
event_properties = Properties(session, event_properties_url)
print("\nEvent Properties:")
event_properties.do_print()

event_type_url = 'https://connect.garmin.com/modern/proxy/activity-service/activity/eventTypes'
event_type_info = TypeInfo(session, event_type_url, event_properties)
print("\nEvent Type Info:")
event_type_info.do_print()

# start of experimental get-activities code
total_to_download = 5 # int(args.count)
total_downloaded = 0
url_gc_search = 'http://connect.garmin.com/modern/proxy/activitylist-service/activities/search/activities?'
while total_downloaded < total_to_download:
  # Maximum of 100... 400 return status if over 100.  So download 100 or whatever remains if less than 100.
  if total_to_download - total_downloaded > 100:
    num_to_download = 100
  else:
    num_to_download = total_to_download - total_downloaded

  search_params = {'start': total_downloaded, 'limit': num_to_download}
  http_data = session.get(url_gc_search, params=search_params)
  json_results = json.loads(http_data.text)
  # result = http_req(query_url)
  # json_results = json.loads(result)  # TODO: Catch possible exceptions here.

  print "### json_results:"
  print json.dumps(json_results, indent=4, sort_keys=True)
  print "###"
  total_downloaded += num_to_download
# end of experiment
