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

