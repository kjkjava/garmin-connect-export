#!/usr/bin/python

"""
File: gcexport.py
Original author: Kyle Krafka (https://github.com/kjkjava/)
Description: Use this script to export your fitness data from Garmin's servers.
             See README.md for more information.
"""

from urllib import urlencode
import urllib2, cookielib, json
from datetime import datetime
from getpass import getpass
from sys import argv
from os.path import isdir
from os.path import isfile
from os import mkdir
from os import remove

import argparse

class DeviceInfo():
  devices_url = "https://connect.garmin.com/modern/proxy/device-service/deviceregistration/devices"
  keys = [
    'currentFirmwareVersion',
    'displayName',
    'partNumber',
    'serialNumber',
  ]

  def __init__(self):
    self.device_info = {}
    devices = json.loads(http_req(self.devices_url))
    for dev in devices:
      dev_id = dev['deviceId']
      this_device = {}
      for key in self.keys:
        this_device[key] = dictFind(dev, [key, ])
      self.device_info[dev_id] = this_device

    # backward compatibility hack: prepend ' ', append ".0.0"
    # to firmware version.
    for dev_id in self.device_info:
      fw = self.device_info[dev_id]['currentFirmwareVersion']
      fw = ' ' + fw + ".0.0"
      self.device_info[dev_id]['currentFirmwareVersion'] = fw

  def printit(self):
    for dev_id in self.device_info:
      print dev_id
      for dev_parameter in self.device_info[dev_id]:
        print "    " + dev_parameter + ": " + self.device_info[dev_id][dev_parameter]

  def displayName(self, deviceId):
    try:
      device = self.device_info[deviceId]['displayName']
    except KeyError:
      device = ""

    try:
      version = self.device_info[deviceId]['currentFirmwareVersion']
    except KeyError:
      version = ""

    displayName = device + ' ' + version
    return displayName

class Properties():
  """Properties: utility class that stores data from a URL in a dict. Values
     in the dict are accessed by get(), which provides a default value.

     Data from the URL are expected be in string form, with multiple lines
     in key=value format.

     Keys may be decorated with a to-be-removed prefix
  """
  def __init__(self, url, key_trim_prefix = None):
    self.key_trim_prefix = key_trim_prefix

    self.properties = {}
    http_data = http_req(url)
    http_lines = http_data.splitlines()
    for line in http_lines:
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

script_version = '1.3.2'
current_date = datetime.now().strftime('%Y-%m-%d')
activities_directory = './' + current_date + '_garmin_connect_export'

parser = argparse.ArgumentParser()

parser.add_argument(
  '--quiet',
  help="stifle all output",
  action="store_true"
)
parser.add_argument(
  '--debug',
  help="lots of console output",
  action="store_true"
)
parser.add_argument(
  '--version',
  help="print version and exit",
  action="store_true"
)
parser.add_argument(
  '--username',
  help="your Garmin Connect username (otherwise, you will be prompted)",
  nargs='?'
)
parser.add_argument(
  '--password',
  help="your Garmin Connect password (otherwise, you will be prompted)",
  nargs='?'
)

parser.add_argument(
  '-c',
  '--count',
  nargs='?',
  default="1",
  help="number of recent activities to download (default: 1)"
)

parser.add_argument(
  '-d',
  '--directory',
  nargs='?',
  default=activities_directory,
  help="save directory (default: './YYYY-MM-DD_garmin_connect_export')"
)

args = parser.parse_args()

if args.version:
  print argv[0] + ", version " + script_version
  exit(0)

cookie_jar = cookielib.CookieJar()
opener = urllib2.build_opener(urllib2.HTTPCookieProcessor(cookie_jar))

def csvFormat(value):
  csv_record = '"' + str(value).replace('"', '""') + '",'
  return csv_record

def dictFind(data, keys):
  try:
    for key in keys:
      data = data[key]
  except KeyError:
    return ""
  return data

# url is a string, post is a dictionary of POST parameters, headers is a dictionary of headers.
def http_req(url, post=None, headers={}):
  if args.debug:
    print "### http_req(" + url + ")"

  request = urllib2.Request(url)
  request.add_header('User-Agent', 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/69.0.3497.100 Safari/537.36')  # Tell Garmin we're some supported browser.
  for header_key, header_value in headers.iteritems():
    request.add_header(header_key, header_value)
  if post:
    post = urlencode(post)  # Convert dictionary to POST parameter string.
  response = opener.open(request, data=post)  # This line may throw a urllib2.HTTPError.

  # N.B. urllib2 will follow any 302 redirects. Also, the "open" call above may throw a urllib2.HTTPError which is checked for below.
  if response.getcode() != 200:
    raise Exception('Bad return code (' + response.getcode() + ') for: ' + url)

  return response.read()


if not args.quiet:
  print 'Welcome to Garmin Connect Exporter!'

# Create directory for data files.
if isdir(args.directory):
  print 'Warning: Output directory already exists. Will skip already-downloaded files and append to the CSV file.'

username = args.username if args.username else raw_input('Username: ')
password = args.password if args.password else getpass()

# Maximum number of activities you can request at once.  Set and enforced by Garmin.
limit_maximum = 100

# URLs for various services.
url_gc_login = 'https://sso.garmin.com/sso/login?service=https%3A%2F%2Fconnect.garmin.com%2Fpost-auth%2Flogin&webhost=olaxpw-connect04&source=https%3A%2F%2Fconnect.garmin.com%2Fen-US%2Fsignin&redirectAfterAccountLoginUrl=https%3A%2F%2Fconnect.garmin.com%2Fpost-auth%2Flogin&redirectAfterAccountCreationUrl=https%3A%2F%2Fconnect.garmin.com%2Fpost-auth%2Flogin&gauthHost=https%3A%2F%2Fsso.garmin.com%2Fsso&locale=en_US&id=gauth-widget&cssUrl=https%3A%2F%2Fstatic.garmincdn.com%2Fcom.garmin.connect%2Fui%2Fcss%2Fgauth-custom-v1.1-min.css&clientId=GarminConnect&rememberMeShown=true&rememberMeChecked=false&createAccountShown=true&openCreateAccount=false&usernameShown=false&displayNameShown=false&consumeServiceTicket=false&initialFocus=true&embedWidget=false&generateExtraServiceTicket=false'
url_gc_post_auth = 'https://connect.garmin.com/modern/?'
url_gc_search = 'http://connect.garmin.com/modern/proxy/activitylist-service/activities/search/activities?'
url_gc_gpx_activity = 'http://connect.garmin.com/proxy/activity-service-1.1/gpx/activity/'
url_gc_tcx_activity = 'http://connect.garmin.com/proxy/activity-service-1.1/tcx/activity/'
url_gc_original_activity = 'http://connect.garmin.com/proxy/download-service/files/activity/'
url_gc_modern_activity = 'https://connect.garmin.com/modern/proxy/activity-service/activity/'

# Initially, we need to get a valid session cookie, so we pull the login page.
http_req(url_gc_login)

# Now we'll actually login, using fields that are passed in a typical
# Garmin login.
post_data = {
  'username': username,
  'password': password,
  'embed': 'true',
  'lt': 'e1s1',
  '_eventId': 'submit',
  'displayNameRequired': 'false'}
http_req(url_gc_login, post_data)

# Get the key.
# TODO: Can we do this without iterating?
login_ticket = None
for cookie in cookie_jar:
  if args.debug:
    print "### cookie.name: " + cookie.name
  if cookie.name == 'CASTGC':
    login_ticket = cookie.value
    if args.debug:
      print "### selected login_ticket: " + login_ticket
    break

if not login_ticket:
  raise Exception('Did not get a ticket cookie. Cannot log in. Did you enter the correct username and password?')

# Chop 'TGT-' off the beginning, prepend 'ST-0'.
login_ticket = 'ST-0' + login_ticket[4:]
if args.debug:
  print "### modified login_ticket: " + login_ticket

login_url = url_gc_post_auth + 'ticket=' + login_ticket
http_req(login_url)

# We should be logged in now.

deviceInfo = DeviceInfo()

# get activity properties
# This maps cryptic activity typeKeys to display names
# all:: All Activities
# golf:: Golf
# indoor_cycling:: Indoor Cycling
# ...
# street_running:: Street Running
#
# keys appear in activity records, activityType/typeKey
activity_properties_url = 'https://connect.garmin.com/modern/main/js/properties/activity_types/activity_types.properties?bust=4.10.1.0'
activity_properties = Properties(activity_properties_url, "activity_type_")

# get activity type info, put in a dict
activity_type_info = {}
activity_type_url = "https://connect.garmin.com/modern/proxy/activity-service/activity/activityTypes"
activity_types = json.loads(http_req(activity_type_url))
keys = ['typeKey', ]
for a_type in activity_types:
  type_id = a_type['typeId']
  this_type = {}
  for key in keys:
    this_type[key] = dictFind(a_type, [key, ])
  # Set type from typeKey
  this_type['type'] = activity_properties.get(this_type['typeKey'])
  activity_type_info[type_id] = this_type

if args.debug:
  print "### activity_type_info"
  for a_type in activity_type_info:
    print a_type
    for activity_parameter in activity_type_info[a_type]:
      print "    " + activity_parameter + ": " + str(activity_type_info[a_type][activity_parameter])
  print "###"

event_properties_url = 'https://connect.garmin.com/modern/main/js/properties/event_types/event_types.properties?bust=4.10.1.0'
event_properties = Properties(event_properties_url)

# get event type info, put in a dict
event_type_info = {}
event_type_url = 'https://connect.garmin.com/modern/proxy/activity-service/activity/eventTypes'
event_types = json.loads(http_req(event_type_url))
keys = ['typeKey', ]
for e_type in event_types:
  type_id = e_type['typeId']
  this_type = {}
  for key in keys:
    this_type[key] = dictFind(e_type, [key, ])
  # Set type from typeKey
  this_type['type'] = event_properties.get(this_type['typeKey'])
  event_type_info[type_id] = this_type

if args.debug:
  print "### event_type_info"
  for e_type in event_type_info:
    print e_type
    for event_parameter in event_type_info[e_type]:
      print "    " + event_parameter + ": " + str(event_type_info[e_type][event_parameter])
  print "###"

if not isdir(args.directory):
  mkdir(args.directory)

csv_filename = args.directory + '/activities.csv'
csv_existed = isfile(csv_filename)

csv_file = open(csv_filename, 'a')

# Write header to CSV file
if not csv_existed:
  csv_file.write('Activity ID,Activity Name,Description,Begin Timestamp,Begin Timestamp (Raw Milliseconds),End Timestamp,End Timestamp (Raw Milliseconds),Device,Activity Parent,Activity Type,Event Type,Activity Time Zone,Max. Elevation,Max. Elevation (Raw),Begin Latitude (Decimal Degrees Raw),Begin Longitude (Decimal Degrees Raw),End Latitude (Decimal Degrees Raw),End Longitude (Decimal Degrees Raw),Average Moving Speed,Average Moving Speed (Raw),Max. Heart Rate (bpm),Average Heart Rate (bpm),Max. Speed,Max. Speed (Raw),Calories,Calories (Raw),Duration (h:m:s),Duration (Raw Seconds),Moving Duration (h:m:s),Moving Duration (Raw Seconds),Average Speed,Average Speed (Raw),Distance,Distance (Raw),Max. Heart Rate (bpm),Min. Elevation,Min. Elevation (Raw),Elevation Gain,Elevation Gain (Raw),Elevation Loss,Elevation Loss (Raw)\n')

total_to_download = int(args.count)
total_downloaded = 0

# This while loop will download data from the server in multiple chunks, if necessary.
while total_downloaded < total_to_download:
  # Maximum of 100... 400 return status if over 100.  So download 100 or whatever remains if less than 100.
  if total_to_download - total_downloaded > 100:
    num_to_download = 100
  else:
    num_to_download = total_to_download - total_downloaded

  search_params = {'start': total_downloaded, 'limit': num_to_download}
  # Query Garmin Connect
  query_url = url_gc_search + urlencode(search_params)
  result = http_req(query_url)
  json_results = json.loads(result)  # TODO: Catch possible exceptions here.

  if args.debug:
    print "### json_results:"
    print json.dumps(json_results, indent=4, sort_keys=True)
    print "###"

  # Pull out just the list of activities.
  # Only the activityId is used.
  # json_results used to be a deep hierarchy, but ... no longer
  activities = json_results

  # Process each activity.
  for a in activities:
    activityId = str(a['activityId'])

    if not args.quiet:
       print 'activity: [' + activityId + ']',
       print a['activityName']
    modern_activity_url = url_gc_modern_activity + activityId

    if args.debug:
      print "url: " + modern_activity_url

    activity_filename = args.directory + '/' + activityId + '.json'
    if args.debug:
      print "filename: " + activity_filename
    result = http_req(modern_activity_url)
    results = json.loads(result)

    save_file = open(activity_filename, 'w')
    save_file.write(json.dumps(results, indent=4, sort_keys=True))
    save_file.close()

    # Write stats to CSV.
    empty_record = '"",'
    csv_record = ''
    # Activity ID
    csv_record += csvFormat(activityId)
    # Activity Name
    csv_record += csvFormat(dictFind(results, ['activityName', ]))
    # Description
    csv_record += csvFormat(dictFind(results, ['description', ]))
    # Begin Timestamp
    csv_record += csvFormat(dictFind(results, ['summaryDTO', 'startTimeLocal', ]))

    # Begin Timestamp (Raw Milliseconds)
    csv_record += empty_record

    # End Timestamp
    csv_record += empty_record

    # End Timestamp (Raw Milliseconds)
    csv_record += empty_record

    # Device
    deviceId = dictFind(a, ['deviceId', ])
    csv_record += csvFormat(deviceInfo.displayName(deviceId))

    # Activity Parent
    parentTypeId = dictFind(a, ['activityType', 'parentTypeId',])
    csv_record += csvFormat(dictFind(activity_type_info, [parentTypeId, 'type', ]))
    # Activity Type
    typeId = dictFind(a, ['activityType', 'typeId',])
    csv_record += csvFormat(dictFind(activity_type_info, [typeId, 'type', ]))

    # Event Type
    typeId = dictFind(a, ['eventType', 'typeId',])
    csv_record += csvFormat(dictFind(event_type_info, [typeId, 'type', ]))
    # Activity Time Zone
    csv_record += csvFormat(dictFind(results, ['timeZoneUnitDTO', 'timeZone' ]))

    # Max. Elevation
    csv_record += empty_record
    # Max. Elevation (Raw)
    # (was in feet previously, now appears to be meters)
    csv_record += csvFormat(dictFind(results, ['summaryDTO', 'maxElevation', ]))

    # {start, end} X {latitude, longitude}
    # Begin Latitude (Decimal Degrees Raw)
    # Begin Longitude (Decimal Degrees Raw)
    # End Latitude (Decimal Degrees Raw)
    # End Longitude (Decimal Degrees Raw)
    for key in ['startLatitude', 'startLongitude', 'endLatitude', 'endLongitude']:
      csv_record += csvFormat(dictFind(results, ['summaryDTO', key, ]))

    # Average Moving Speed
    csv_record += empty_record

    # Average Moving Speed (Raw)
    csv_record += csvFormat(dictFind(results, ['summaryDTO', 'averageMovingSpeed', ]))

    # Max. Heart Rate (bpm)
    csv_record += empty_record
    # Average Heart Rate (bpm)
    csv_record += empty_record

    # Max. Speed
    csv_record += empty_record
    # Max. Speed (Raw)
    csv_record += csvFormat(dictFind(results, ['summaryDTO', 'maxSpeed', ]))

    # Calories
    csv_record += empty_record
    # Calories (Raw)
    csv_record += csvFormat(dictFind(results, ['summaryDTO', 'calories', ]))

    # Duration (h:m:s)
    csv_record += empty_record
    # Duration (Raw Seconds)
    csv_record += csvFormat(dictFind(results, ['summaryDTO', 'elapsedDuration', ]))
    # Moving Duration (h:m:s)
    csv_record += empty_record
    # Moving Duration (Raw Seconds),
    csv_record += csvFormat(dictFind(results, ['summaryDTO', 'movingDuration', ]))
    # Average Speed
    csv_record += empty_record
    # Average Speed (Raw)
    csv_record += csvFormat(dictFind(results, ['summaryDTO', 'averageSpeed', ]))
    # Distance
    csv_record += empty_record
    # distance.value
    csv_record += csvFormat(dictFind(results, ['summaryDTO', 'distance', ]))

    # Max. Heart Rate (bpm)
    csv_record += empty_record

    # Min. Elevation
    csv_record += empty_record
    # Min. Elevation (Raw)
    csv_record += csvFormat(dictFind(results, ['summaryDTO', 'minElevation', ]))

    # Elevation Gain
    csv_record += empty_record
    # Elevation Gain (Raw)
    csv_record += empty_record
    # Elevation Loss
    csv_record += empty_record
    # Elevation Loss (Raw)
    csv_record += empty_record

    # remove any trailing commas - R read.csv doesn't like them.
    csv_record = csv_record.rstrip(',')

    csv_record += '\n'

    if args.debug:
      print "data: " + csv_record

    csv_file.write(csv_record.encode('utf8'))

  total_downloaded += num_to_download
# End while loop for multiple chunks.

csv_file.close()

if not args.quiet:
  print 'Done!'

