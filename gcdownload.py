#!/usr/bin/python
import json

from gclogin import GarminLogin
from properties import Properties
from deviceinfo import DeviceInfo
from typeinfo import TypeInfo
from cmdlineargs import get_args
from utils import csvFormat, dictFind, activity_to_csv
from sys import argv
from os.path import isdir
from os.path import isfile
from os import mkdir
from getpass import getpass

script_version = '1.4.0'
args = get_args()
if args.version:
  print argv[0] + ", version " + script_version
  exit(0)

# utilities - put these somewhere else?

gcl = GarminLogin()
username = args.username if args.username else raw_input('Username: ')
password = args.password if args.password else getpass()
session = gcl._get_session(email=username, password=password)

devInfo = DeviceInfo(session)
# print("\nDevices:")
# devInfo.do_print()

# activity properties
activity_properties_url = 'https://connect.garmin.com/modern/main/js/properties/activity_types/activity_types.properties?bust=4.10.1.0'
activity_properties = Properties(session, activity_properties_url, "activity_type_")
# print("\nActivity Properties:")
# activity_properties.do_print()

activity_type_url = "https://connect.garmin.com/modern/proxy/activity-service/activity/activityTypes"
activity_type_info = TypeInfo(session, activity_type_url, activity_properties)
# print("\nActivity Type Info:")
# activity_type_info.do_print()

event_properties_url = 'https://connect.garmin.com/modern/main/js/properties/event_types/event_types.properties?bust=4.10.1.0'
event_properties = Properties(session, event_properties_url)
# print("\nEvent Properties:")
# event_properties.do_print()

event_type_url = 'https://connect.garmin.com/modern/proxy/activity-service/activity/eventTypes'
event_type_info = TypeInfo(session, event_type_url, event_properties)
# print("\nEvent Type Info:")
# event_type_info.do_print()

if not isdir(args.directory):
  mkdir(args.directory)


csv_filename = args.directory + '/activities.csv'
csv_existed = isfile(csv_filename)

csv_file = open(csv_filename, 'a')

# Write header to CSV file
if not csv_existed:
  csv_file.write('Activity ID,Activity Name,Description,Begin Timestamp,Begin Timestamp (Raw Milliseconds),End Timestamp,End Timestamp (Raw Milliseconds),Device,Activity Parent,Activity Type,Event Type,Activity Time Zone,Max. Elevation,Max. Elevation (Raw),Begin Latitude (Decimal Degrees Raw),Begin Longitude (Decimal Degrees Raw),End Latitude (Decimal Degrees Raw),End Longitude (Decimal Degrees Raw),Average Moving Speed,Average Moving Speed (Raw),Max. Heart Rate (bpm),Average Heart Rate (bpm),Max. Speed,Max. Speed (Raw),Calories,Calories (Raw),Duration (h:m:s),Duration (Raw Seconds),Moving Duration (h:m:s),Moving Duration (Raw Seconds),Average Speed,Average Speed (Raw),Distance,Distance (Raw),Max. Heart Rate (bpm),Min. Elevation,Min. Elevation (Raw),Elevation Gain,Elevation Gain (Raw),Elevation Loss,Elevation Loss (Raw)\n')

# start of experimental get-activities code
total_to_download = int(args.count)
total_downloaded = 0
url_gc_search = 'http://connect.garmin.com/modern/proxy/activitylist-service/activities/search/activities?'
url_gc_modern_activity = 'https://connect.garmin.com/modern/proxy/activity-service/activity/'
while total_downloaded < total_to_download:
  # Maximum of 100... 400 return status if over 100.  So download 100 or whatever remains if less than 100.
  if total_to_download - total_downloaded > 100:
    num_to_download = 100
  else:
    num_to_download = total_to_download - total_downloaded

  search_params = {'start': total_downloaded, 'limit': num_to_download}
  http_data = session.get(url_gc_search, params=search_params)
  activities = json.loads(http_data.text)

  # print "### activities:"
  # print json.dumps(activities, indent=4, sort_keys=True)
  # print "###"

  for a in activities:
    activityId = str(a['activityId'])

    if not args.quiet:
       print 'activity: [' + activityId + ']',
       print a['activityName']
    modern_activity_url = url_gc_modern_activity + activityId
    if args.debug:
      print "url: " + modern_activity_url

    result = session.get(modern_activity_url)
    results = json.loads(result.text)

    activity_filename = args.directory + '/' + activityId + '.json'
    if args.debug:
      print "filename: " + activity_filename

    save_file = open(activity_filename, 'w')
    save_file.write(json.dumps(results, indent=4, sort_keys=True))
    save_file.close()

    # Write stats to CSV.
    csv_record = activity_to_csv(results, a, devInfo, activity_type_info, event_type_info)
    if args.debug:
      print "data: " + csv_record

    csv_file.write(csv_record.encode('utf8'))

  total_downloaded += num_to_download
# End while loop for multiple chunks.

csv_file.close()

if not args.quiet:
  print 'Done!'

