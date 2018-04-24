#!/usr/bin/python
# -*- coding: utf-8 -*-

"""
File: gcexport.py
Original author: Kyle Krafka (https://github.com/kjkjava/)
Date: April 28, 2015
Fork author: Michae P (https://github.com/moderation/)
Date: February 21, 2016

Description:	Use this script to export your fitness data from Garmin Connect.
				See README.md for more information.
"""

# The version of the script in this branch tries to recreate the CSV output of
# the original version by kjkjava using the activity-search-service-1.0
# endpoint (which stopped working somewhere around February 2018). The goal
# is to minimise the differences to spot remaining issues. To achieve this
# some shortcomings of the old endpoint are reproduced, e.g. that the
# endTimestamp is calculated based on the duration and not the elapsed
# duration (and truncated, not rounded)
#
# Remaining differences:
# - the old version has wrong time zone offsets (no summertime in summer...)
# - the old version sometimes (or always?) used elapsedDuration for duration
# - the old version sometimes provided endLongitude/endLatitude when both new JSON outputs won't (e.g. my activity 2134702283)
# - the old script filled the maxElevation into the minElevation column
# - the old CSV output has some inexplainable differences (e.g. end timestamp of 87966658,
#   because the old JSON outputs were not kept
# - the new endpoint fails to deliver a complete JSON output in about 0.5% of the calls
# - elevationGain/elevationLoss of null may mean 0 (in particular of the other value is non-null)
# - for some activities, e.g. 86497297, the data in activities.json and activity_86497297.json differ.
#   - differences observed in these fields: elevationGain, elevationLoss, maxSpeed, movingDuration
#   - fields sometimes missing from details even though present in summary: startLatitude, startLongitude
# TODO: multi-sport activities, e.g. 2536264424 (typeId 89, typeKey 'multi_sport')

from math import floor
from sets import Set
from urllib import urlencode
from datetime import datetime, timedelta, tzinfo
from getpass import getpass
from sys import argv
from os.path import isdir
from os.path import isfile
from os import mkdir
from os import remove
from os import stat
from xml.dom.minidom import parseString
from subprocess import call

import urllib, urllib2, cookielib, json, re
from fileinput import filename
import json

import argparse
import zipfile

script_version = '1.0.0'
current_date = datetime.now().strftime('%Y-%m-%d')
activities_directory = './' + current_date + '_garmin_connect_export'

parser = argparse.ArgumentParser()

# TODO: Implement verbose and/or quiet options.
# parser.add_argument('-v', '--verbose', help="increase output verbosity", action="store_true")
parser.add_argument('--version', help="print version and exit", action="store_true")
parser.add_argument('--username', help="your Garmin Connect username (otherwise, you will be prompted)", nargs='?')
parser.add_argument('--password', help="your Garmin Connect password (otherwise, you will be prompted)", nargs='?')

parser.add_argument('-c', '--count', nargs='?', default="1",
	help="number of recent activities to download, or 'all' (default: 1)")

parser.add_argument('-f', '--format', nargs='?', choices=['gpx', 'tcx', 'original'], default="gpx",
	help="export format; can be 'gpx', 'tcx', 'original' (default: 'gpx')")

parser.add_argument('-d', '--directory', nargs='?', default=activities_directory,
	help="the directory to export to (default: './YYYY-MM-DD_garmin_connect_export')")

parser.add_argument('-u', '--unzip',
	help="if downloading ZIP files (format: 'original'), unzip the file and removes the ZIP file",
	action="store_true")

args = parser.parse_args()

if args.version:
	print argv[0] + ", version " + script_version
	exit(0)

cookie_jar = cookielib.CookieJar()
opener = urllib2.build_opener(urllib2.HTTPCookieProcessor(cookie_jar))
# print cookie_jar

# url is a string, post is a dictionary of POST parameters, headers is a dictionary of headers.
def http_req(url, post=None, headers={}):
	request = urllib2.Request(url)
	# request.add_header('User-Agent', 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/1337 Safari/537.36')  # Tell Garmin we're some supported browser.
	request.add_header('User-Agent', 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/54.0.2816.0 Safari/537.36')  # Tell Garmin we're some supported browser.
	for header_key, header_value in headers.iteritems():
		request.add_header(header_key, header_value)
	if post:
		# print "POSTING"
		post = urlencode(post)  # Convert dictionary to POST parameter string.
	# print request.headers
	# print cookie_jar
	# print post
	# print request
	response = opener.open(request, data=post)  # This line may throw a urllib2.HTTPError.

	# N.B. urllib2 will follow any 302 redirects. Also, the "open" call above may throw a urllib2.HTTPError which is checked for below.
	# print response.getcode()
	if response.getcode() == 204:
		# For activities without GPS coordinates, there is no GPX download (204 = no content).
		# Write an empty file to prevent redownloading it.
		print 'Writing empty file since there was no GPX activity data...'
		return ''
	elif response.getcode() != 200:
		raise Exception('Bad return code (' + str(response.getcode()) + ') for: ' + url)

	return response.read()

def writeToFile(filename, content):
	json_file = open(filename, 'a')
	json_file.write(content)
	json_file.close()

# idea stolen from https://stackoverflow.com/a/31852401/3686
def loadProperties(multiline, sep='=', comment_char='#'):
	props = {}
	for line in multiline.splitlines():
		l = line.strip()
		if l and not l.startswith(comment_char):
			key_value = l.split(sep)
			key = key_value[0].strip()
			value = sep.join(key_value[1:]).strip().strip('"')
			props[key] = value
	return props

def valueIfFoundElseKey(dict, key):
	return dict.get(key, key)

def absentOrNull(element, a):
	if not a:
		return True
	elif element not in a:
		return True
	elif a[element]:
		return False
	else:
		return True

def fromActivitiesOrDetail(element, a, detail, detailContainer):
	if absentOrNull(detailContainer, detail) or absentOrNull(element, detail[detailContainer]):
		return None if absentOrNull(element, a) else a[element]
	else:
		return details[detailContainer][element]

def trunc6(f):
	return "{0:12.6f}".format(floor(f*1000000)/1000000).lstrip()

# A class building tzinfo objects for fixed-offset time zones.
# (copied from https://docs.python.org/2/library/datetime.html)
class FixedOffset(tzinfo):
    """Fixed offset in minutes east from UTC."""

    def __init__(self, offset, name):
        self.__offset = timedelta(minutes = offset)
        self.__name = name

    def utcoffset(self, dt):
        return self.__offset

    def tzname(self, dt):
        return self.__name

    def dst(self, dt):
        return timedelta(0)

# build an 'aware' datetime from two 'naive' datetime objects (that is timestamps
# as present in the activities.json), using the time difference as offset
def offsetDateTime(timeLocal, timeGMT):
	localDT = datetime.strptime(timeLocal, "%Y-%m-%d %H:%M:%S")
	gmtDT = datetime.strptime(timeGMT, "%Y-%m-%d %H:%M:%S")
	offset = localDT - gmtDT
	offsetTz = FixedOffset(offset.seconds/60, "LCL")
	return localDT.replace(tzinfo=offsetTz)

def hhmmssFromSeconds(sec):
	return str(timedelta(seconds=int(sec))).zfill(8)

# this is almost the datetime format Garmin used in the activity-search-service
# JSON 'display' fields (Garmin didn't zero-pad the date and the hour, but %d and %H do)
ALMOST_RFC_1123 = "%a, %d %b %Y %H:%M"

# map the numeric parentTypeId to its name for the CSV output
parent_type_id = {
	1: 'running',
	2: 'cycling',
	3: 'hiking',
	4: 'other',
	9: 'walking',
	17: 'any activity type',
	26: 'swimming',
	29: 'fitness equipment',
	71: 'motorcycling',
	83: 'transition',
	144: 'diving',
	149: 'yoga' }

# typeId values using pace instead of speed
uses_pace = Set([1, 3, 9]) # running, hiking, walking

def paceOrSpeedRaw(typeId, parentTypeId, mps):
	kmh = 3.6 * mps
	if (typeId in uses_pace) or (parentTypeId in uses_pace):
		return 60 / kmh
	else:
		return kmh

def paceOrSpeedFormatted(typeId, parentTypeId, mps):
	kmh = 3.6 * mps
	if (typeId in uses_pace) or (parentTypeId in uses_pace):
		# format seconds per kilometer as MM:SS, see https://stackoverflow.com/a/27751293
		return '{0:02d}:{1:02d}'.format(*divmod(int(round(3600 / kmh)), 60))
	else:
		return "{0:.1f}".format(round(kmh, 1))


print 'Welcome to Garmin Connect Exporter!'

# Create directory for data files.
if isdir(args.directory):
	print 'Warning: Output directory already exists. Will skip already-downloaded files and append to the CSV file.'

username = args.username if args.username else raw_input('Username: ')
password = args.password if args.password else getpass()

# Maximum number of activities you can request at once.
# Used to be 100 and enforced by Garmin for older endpoints; for the current endpoint 'url_gc_search'
# the limit is not known (I have less than 1000 activities and could get them all in one go)
limit_maximum = 1000

max_tries = 3

WEBHOST = "https://connect.garmin.com"
REDIRECT = "https://connect.garmin.com/post-auth/login"
BASE_URL = "http://connect.garmin.com/en-US/signin"
GAUTH = "http://connect.garmin.com/gauth/hostname"
SSO = "https://sso.garmin.com/sso"
CSS = "https://static.garmincdn.com/com.garmin.connect/ui/css/gauth-custom-v1.2-min.css"

data = {'service': REDIRECT,
    'webhost': WEBHOST,
    'source': BASE_URL,
    'redirectAfterAccountLoginUrl': REDIRECT,
    'redirectAfterAccountCreationUrl': REDIRECT,
    'gauthHost': SSO,
    'locale': 'en_US',
    'id': 'gauth-widget',
    'cssUrl': CSS,
    'clientId': 'GarminConnect',
    'rememberMeShown': 'true',
    'rememberMeChecked': 'false',
    'createAccountShown': 'true',
    'openCreateAccount': 'false',
    'usernameShown': 'false',
    'displayNameShown': 'false',
    'consumeServiceTicket': 'false',
    'initialFocus': 'true',
    'embedWidget': 'false',
    'generateExtraServiceTicket': 'false'}

print urllib.urlencode(data)

# URLs for various services.
url_gc_login     = 'https://sso.garmin.com/sso/login?' + urllib.urlencode(data)
url_gc_post_auth = 'https://connect.garmin.com/modern/activities?'
url_gc_summary   = 'http://connect.garmin.com/proxy/activity-search-service-1.2/json/activities?start=0&limit=1'
url_gc_search    = 'https://connect.garmin.com/modern/proxy/activitylist-service/activities/search/activities?'
url_gc_activity  = 'https://connect.garmin.com/modern/proxy/activity-service/activity/'
url_gc_device    = 'https://connect.garmin.com/modern/proxy/device-service/deviceservice/app-info/'
url_gc_act_props = 'https://connect.garmin.com/modern/main/js/properties/activity_types/activity_types.properties'
url_gc_evt_props = 'https://connect.garmin.com/modern/main/js/properties/event_types/event_types.properties'
url_gc_gpx_activity = 'https://connect.garmin.com/modern/proxy/download-service/export/gpx/activity/'
url_gc_tcx_activity = 'https://connect.garmin.com/modern/proxy/download-service/export/tcx/activity/'
url_gc_original_activity = 'http://connect.garmin.com/proxy/download-service/files/activity/'

# Initially, we need to get a valid session cookie, so we pull the login page.
print 'Request login page'
http_req(url_gc_login)
print 'Finish login page'

# Now we'll actually login.
post_data = {'username': username, 'password': password, 'embed': 'true', 'lt': 'e1s1', '_eventId': 'submit', 'displayNameRequired': 'false'}  # Fields that are passed in a typical Garmin login.
print 'Post login data'
login_response = http_req(url_gc_login, post_data)
print 'Finish login post'
# print login_response

# extract the ticket from the login response
pattern = re.compile(r".*\?ticket=([-\w]+)\";.*", re.MULTILINE|re.DOTALL)
match = pattern.match(login_response)
if not match:
	raise Exception('Did not get a ticket in the login response. Cannot log in. Did you enter the correct username and password?')
login_ticket = match.group(1)
print 'login ticket=' + login_ticket

print 'Request authentication'
# print url_gc_post_auth + 'ticket=' + login_ticket
http_req(url_gc_post_auth + 'ticket=' + login_ticket)
print 'Finished authentication'

# We should be logged in now.
if not isdir(args.directory):
	mkdir(args.directory)

if args.count == 'all':
	# If the user wants to download all activities, first download one,
	# then the result of that request will tell us how many are available
	# so we will modify the variables then.
	print "Making result summary request ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~"
	print url_gc_summary
	result = http_req(url_gc_summary)
	print "Finished result summary request ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~"

	# Modify total_to_download based on how many activities the server reports.
	json_results = json.loads(result)  # TODO: Catch possible exceptions here.
	total_to_download = int(json_results['results']['totalFound'])
else:
	total_to_download = int(args.count)
total_downloaded = 0

device_dict = dict()

# load some dictionaries with lookup data from REST services
activityTypeProps = http_req(url_gc_act_props)
# writeToFile(args.directory + '/activity_types.properties', activityTypeProps)
activityTypeName = loadProperties(activityTypeProps)
eventTypeProps = http_req(url_gc_evt_props)
# writeToFile(args.directory + '/event_types.properties', eventTypeProps)
eventTypeName = loadProperties(eventTypeProps)

# This while loop will download data from the server in multiple chunks, if necessary.
while total_downloaded < total_to_download:
	# Maximum chunk size 'limit_maximum' ... 400 return status if over maximum.  So download maximum or whatever remains if less than maximum.
	# As of 2018-03-06 I get return status 500 if over maximum
	if total_to_download - total_downloaded > limit_maximum:
		num_to_download = limit_maximum
	else:
		num_to_download = total_to_download - total_downloaded

	search_params = {'start': total_downloaded, 'limit': num_to_download}
	# Query Garmin Connect
	result = http_req(url_gc_search + urlencode(search_params))
	json_results = json.loads(result)  # TODO: Catch possible exceptions here.

	activities = json_results

	# Process each activity.
	for activity in activities:
		# Display which entry we're working on.
		activityId = activity['activityId']
		print 'Garmin Connect activity: [' + str(activityId) + ']',
		print activity['activityName']
		print '\t' + str(activity['startTimeLocal']) + ',',
		print str(activity['elapsedDuration']) + ',',
		print str(activity['distance'])

		if args.format == 'gpx':
			data_filename = args.directory + '/activity_' + str(activityId) + '.gpx'
			download_url = url_gc_gpx_activity + str(activityId) + '?full=true'
			# download_url = url_gc_gpx_activity + str(a['activity']['activityId']) + '?full=true' + '&original=true'
			print download_url
			file_mode = 'w'
		elif args.format == 'tcx':
			data_filename = args.directory + '/activity_' + str(activityId) + '.tcx'
			download_url = url_gc_tcx_activity + str(activityId) + '?full=true'
			file_mode = 'w'
		elif args.format == 'original':
			data_filename = args.directory + '/activity_' + str(activityId) + '.zip'
			fit_filename = args.directory + '/' + str(activityId) + '.fit'
			download_url = url_gc_original_activity + str(activityId)
			file_mode = 'wb'
		else:
			raise Exception('Unrecognized format.')

		json_filename = args.directory + '/activity_' + str(activityId) + '.json'
		json_file_mode = 'w'

		if isfile(data_filename):
			print '\tData file already exists; skipping...'
			continue
		if args.format == 'original' and isfile(fit_filename):  # Regardless of unzip setting, don't redownload if the ZIP or FIT file exists.
			print '\tFIT data file already exists; skipping...'
			continue

		# Download the data file from Garmin Connect.
		# If the download fails (e.g., due to timeout), this script will die, but nothing
		# will have been written to disk about this activity, so just running it again
		# should pick up where it left off.
		print '\tDownloading file...',

		try:
			data = http_req(download_url)
		except urllib2.HTTPError as e:
			# Handle expected (though unfortunate) error codes; die on unexpected ones.
			if e.code == 500 and args.format == 'tcx':
				# Garmin will give an internal server error (HTTP 500) when downloading TCX files if the original was a manual GPX upload.
				# Writing an empty file prevents this file from being redownloaded, similar to the way GPX files are saved even when there are no tracks.
				# One could be generated here, but that's a bit much. Use the GPX format if you want actual data in every file,
				# as I believe Garmin provides a GPX file for every activity.
				print 'Writing empty file since Garmin did not generate a TCX file for this activity...',
				data = ''
			elif e.code == 404 and args.format == 'original':
				# For manual activities (i.e., entered in online without a file upload), there is no original file.
				# Write an empty file to prevent redownloading it.
				print 'Writing empty file since there was no original activity data...',
				data = ''
			else:
				raise Exception('Failed. Got an unexpected HTTP error (' + str(e.code) + download_url +').')

		save_file = open(data_filename, file_mode)
		save_file.write(data)
		save_file.close()

		save_file = open(json_filename, json_file_mode)
		save_file.write(json.dumps(activity))
		save_file.close()

		if args.format == 'gpx' and data:
			# Validate GPX data. If we have an activity without GPS data (e.g., running on a treadmill),
			# Garmin Connect still kicks out a GPX (sometimes), but there is only activity information, no GPS data.
			# N.B. You can omit the XML parse (and the associated log messages) to speed things up.
			gpx = parseString(data)
			gpx_data_exists = len(gpx.getElementsByTagName('trkpt')) > 0

			if gpx_data_exists:
				print 'Done. GPX data saved.'
			else:
				print 'Done. No track points found.'
		elif args.format == 'original':
			if args.unzip and data_filename[-3:].lower() == 'zip':  # Even manual upload of a GPX file is zipped, but we'll validate the extension.
				print "Unzipping and removing original files...",
				print 'Filesize is: ' + str(stat(data_filename).st_size)
				if stat(data_filename).st_size > 0:
					zip_file = open(data_filename, 'rb')
					z = zipfile.ZipFile(zip_file)
					for name in z.namelist():
						z.extract(name, args.directory)
					zip_file.close()
				else:
					print 'Skipping 0Kb zip file.'
				remove(data_filename)
			print 'Done.'
		elif args.format == 'json':
			# print nothing here
			pass
		else:
			# TODO: Consider validating other formats.
			print 'Done.'
	total_downloaded += num_to_download
# End while loop for multiple chunks.

print 'Done!'
