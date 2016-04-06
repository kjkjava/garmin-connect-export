#!/usr/bin/python

"""
File: gcexport.py
Author: Kyle Krafka (https://github.com/kjkjava/)
Date: April 28, 2015

Description:	Use this script to export your fitness data from Garmin Connect.
                See README.md for more information.
Usage:			python gcexport.py [how_many] [format] [directory]
                    how_many - number of recent activities to download, or "all" (default: 1)
                    format - export format; can be "gpx," "tcx," "csvonly," (activity list) or "original" (default: gpx)
                    directory - the directory to export to (default: "YYYY-MM-DD_garmin_connect_export")

2015-09-23 v01dma1n: converted to Python 3, added csvonly data format
2016-04-06 Irek Rybark: split device name and device version fields; device version appended as last column
"""

from urllib.parse import urlencode
from datetime import datetime
from configparser import ConfigParser
from getpass import getpass
from sys import argv
from os.path import isdir
from os.path import isfile
from os import mkdir
from xml.dom.minidom import parseString
import urllib.request, urllib.error, urllib.parse, http.cookiejar, json
from fileinput import filename

if len(argv) > 4:
    raise Exception('Too many arguments.')

if len(argv) > 3:
    activities_directory = argv[3]
else:
    current_date = datetime.now().strftime('%Y-%m-%d')
    activities_directory = './' + current_date + '_garmin_connect_export'

if len(argv) > 2:
    data_format = argv[2].lower()
    if data_format != 'gpx' and data_format != 'tcx' and data_format != 'original' and data_format != 'csvonly':
        raise Exception('Format can only be "gpx," "tcx," "csvonly," or "original."')
else:
    data_format = 'gpx'



cookie_jar = http.cookiejar.CookieJar()
opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cookie_jar))


# url is a string, post is a dictionary of POST parameters, headers is a dictionary of headers.
def http_req(url, post=None, headers={}):
    request = urllib.request.Request(url)
    request.add_header('User-Agent',
                       'Mozilla/5.0 (Windows NT 5.2; rv:2.0.1) Gecko/20100101 Firefox/4.0.1')  # Tell Garmin we're some supported browser.
    for header_key, header_value in headers.items():
        request.add_header(header_key, header_value)
    if post:
        post = urlencode(post).encode('utf-8')  # Convert dictionary to POST parameter string.
    response = opener.open(request, data=post)  # This line may throw a urllib2.HTTPError.

    # N.B. urllib2 will follow any 302 redirects. Also, the "open" call above may throw a urllib2.HTTPError which is checked for below.
    if response.getcode() != 200:
        raise Exception('Bad return code (' + response.getcode() + ') for: ' + url)

    return response.read()


print('Welcome to Garmin Connect Exporter!')

# Create directory for data files.
if isdir(activities_directory):
    print('Warning: Output directory already exists. Will skip already-downloaded files and append to the CSV file.')

username = ''
password = ''
# try to read config...
config = ConfigParser()
try:
    config.read('gcexport.config')
    username = config['login']['username']
    password = config['login']['password']
except Exception:
    pass
# ...otherwise prompt
if username == '' or password == '':
    username = input('Username: ')
    password = getpass()


# Maximum number of activities you can request at once.  Set and enforced by Garmin.
limit_maximum = 100

# URLs for various services.
url_gc_login = 'https://sso.garmin.com/sso/login?service=https%3A%2F%2Fconnect.garmin.com%2Fpost-auth%2Flogin&webhost=olaxpw-connect04&source=https%3A%2F%2Fconnect.garmin.com%2Fen-US%2Fsignin&redirectAfterAccountLoginUrl=https%3A%2F%2Fconnect.garmin.com%2Fpost-auth%2Flogin&redirectAfterAccountCreationUrl=https%3A%2F%2Fconnect.garmin.com%2Fpost-auth%2Flogin&gauthHost=https%3A%2F%2Fsso.garmin.com%2Fsso&locale=en_US&id=gauth-widget&cssUrl=https%3A%2F%2Fstatic.garmincdn.com%2Fcom.garmin.connect%2Fui%2Fcss%2Fgauth-custom-v1.1-min.css&clientId=GarminConnect&rememberMeShown=true&rememberMeChecked=false&createAccountShown=true&openCreateAccount=false&usernameShown=false&displayNameShown=false&consumeServiceTicket=false&initialFocus=true&embedWidget=false&generateExtraServiceTicket=false'
url_gc_post_auth = 'https://connect.garmin.com/post-auth/login?'
url_gc_search = 'http://connect.garmin.com/proxy/activity-search-service-1.0/json/activities?'
url_gc_gpx_activity = 'http://connect.garmin.com/proxy/activity-service-1.1/gpx/activity/'
url_gc_tcx_activity = 'http://connect.garmin.com/proxy/activity-service-1.1/tcx/activity/'
url_gc_original_activity = 'http://connect.garmin.com/proxy/download-service/files/activity/'

# Initially, we need to get a valid session cookie, so we pull the login page.
http_req(url_gc_login)

# Now we'll actually login.
post_data = {'username': username, 'password': password, 'embed': 'true', 'lt': 'e1s1', '_eventId': 'submit',
             'displayNameRequired': 'false'}  # Fields that are passed in a typical Garmin login.
http_req(url_gc_login, post_data)

# Get the key.
# TODO: Can we do this without iterating?
login_ticket = None
for cookie in cookie_jar:
    if cookie.name == 'CASTGC':
        login_ticket = cookie.value
        break

if not login_ticket:
    raise Exception('Did not get a ticket cookie. Cannot log in. Did you enter the correct username and password?')

# Chop of 'TGT-' off the beginning, prepend 'ST-0'.
login_ticket = 'ST-0' + login_ticket[4:]

http_req(url_gc_post_auth + 'ticket=' + login_ticket)

# We should be logged in now.
if not isdir(activities_directory):
    mkdir(activities_directory)

csv_filename = activities_directory + '/activities.csv'
csv_existed = isfile(csv_filename)

csv_file = open(csv_filename, 'a')

# Write header to CSV file
if not csv_existed:
    csv_file.write(
        'Activity ID,Activity Name,Description,Begin Timestamp,Begin Timestamp (Raw Milliseconds),End Timestamp,End Timestamp (Raw Milliseconds),Device,Activity Parent,Activity Type,Event Type,Activity Time Zone,Max. Elevation,Max. Elevation (Raw),Begin Latitude (Decimal Degrees Raw),Begin Longitude (Decimal Degrees Raw),End Latitude (Decimal Degrees Raw),End Longitude (Decimal Degrees Raw),Average Moving Speed,Average Moving Speed (Raw),Max. Heart Rate (bpm),Average Heart Rate (bpm),Max. Speed,Max. Speed (Raw),Calories,Calories (Raw),Duration (h:m:s),Duration (Raw Seconds),Moving Duration (h:m:s),Moving Duration (Raw Seconds),Average Speed,Average Speed (Raw),Distance,Distance (Raw),Max. Heart Rate (bpm),Min. Elevation,Min. Elevation (Raw),Elevation Gain,Elevation Gain (Raw),Elevation Loss,Elevation Loss (Raw)\n')

download_all = False
if len(argv) > 1 and argv[1].isdigit():
    total_to_download = int(argv[1])
elif len(argv) > 1 and argv[1] == 'all':
    # If the user wants to download all activities, first download one,
    # then the result of that request will tell us how many are available
    # so we will modify the variables then.
    total_to_download = 1
    download_all = True
else:
    total_to_download = 1
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
    result = http_req(url_gc_search + urlencode(search_params))
    json_results = json.loads(result.decode('utf-8'))  # TODO: Catch possible exceptions here.

    search = json_results['results']['search']

    if download_all:
        # Modify total_to_download based on how many activities the server reports.
        total_to_download = int(search['totalFound'])
        # Do it only once.
        download_all = False

    # Pull out just the list of activities.
    activities = json_results['results']['activities']

    # Process each activity.
    for a in activities:
        # Display which entry we're working on.
        print('Garmin Connect activity: [' + a['activity']['activityId'] + ']', end=' ')
        print(a['activity']['beginTimestamp']['display'] + ':', end=' ')
        print(a['activity']['activityName']['value'])

        if data_format != 'csvonly':
            if data_format == 'gpx':
                filename = activities_directory + '/activity_' + a['activity']['activityId'] + '.gpx'
                download_url = url_gc_gpx_activity + a['activity']['activityId'] + '?full=true'
                file_mode = 'wb'
            elif data_format == 'tcx':
                filename = activities_directory + '/activity_' + a['activity']['activityId'] + '.tcx'
                download_url = url_gc_tcx_activity + a['activity']['activityId'] + '?full=true'
                file_mode = 'w'
            else:
                filename = activities_directory + '/activity_' + a['activity']['activityId'] + '.zip'
                download_url = url_gc_original_activity + a['activity']['activityId']
                file_mode = 'wb'

            if isfile(filename):
                print('\tData file already exists; skipping...')
                continue

            # Download the data file from Garmin Connect.
            # If the download fails (e.g., due to timeout), this script will die, but nothing
            # will have been written to disk about this activity, so just running it again
            # should pick up where it left off.
            print('\tDownloading file...', end=' ')

            try:
                data = http_req(download_url)
            except urllib.error.HTTPError as e:
                # Handle expected (though unfortunate) error codes; die on unexpected ones.
                if e.code == 500 and data_format == 'tcx':
                    # Garmin will give an internal server error (HTTP 500) when downloading TCX files if the original was a manual GPX upload.
                    # Writing an empty file prevents this file from being redownloaded, similar to the way GPX files are saved even when there are no tracks.
                    # One could be generated here, but that's a bit much. Use the GPX format if you want actual data in every file, as I believe Garmin provides a GPX file for every activity.
                    print('Writing empty file since Garmin did not generate a TCX file for this activity...', end=' ')
                    data = ''
                elif e.code == 404 and data_format == 'original':
                    # For manual activities (i.e., entered in online without a file upload), there is no original file.
                    # Write an empty file to prevent redownloading it.
                    print('Writing empty file since there was no original activity data...', end=' ')
                    data = ''
                else:
                    raise Exception('Failed. Got an unexpected HTTP error (' + str(e.code) + ').')

            save_file = open(filename, file_mode)
            save_file.write(data)
            save_file.close()

        # Write stats to CSV.
        csv_record = ''

        def append_col(field_name, field_val1="", field_val2=""):
            global csv_record
            if field_name not in a['activity']:
                csv_record += '"",'
            else:
                if field_val1 != "":
                    if field_val2 != "":
                        fval = a['activity'][field_name][field_val1][field_val2]
                    else:
                        fval = a['activity'][field_name][field_val1]
                else:
                    fval = a['activity'][field_name]
                csv_record += '"' + fval.replace('"', '""') + '",'

        append_col('activityId')
        append_col('activityName', 'value')
        append_col('activityDescription', 'value')
        append_col('beginTimestamp', 'display')
        append_col('beginTimestamp', 'millis')
        append_col('endTimestamp', 'display')
        append_col('endTimestamp', 'millis')
        append_col('device', 'display')
        append_col('activityType', 'parent', 'display')
        append_col('activityType', 'display')
        append_col('eventType', 'display')
        append_col('activityTimeZone', 'display')
        append_col('maxElevation', 'withUnit')
        append_col('maxElevation', 'value')
        append_col('beginLatitude', 'value')
        append_col('beginLongitude', 'value')
        append_col('endLatitude', 'value')
        append_col('endLongitude', 'value')
        append_col('weightedMeanMovingSpeed', 'display')
        append_col('weightedMeanMovingSpeed', 'value')
        append_col('maxHeartRate', 'display')
        append_col('weightedMeanHeartRate', 'display')
        append_col('maxSpeed', 'display')
        append_col('maxSpeed', 'value')
        append_col('sumEnergy', 'display')
        append_col('sumEnergy', 'value')
        append_col('sumElapsedDuration', 'display')
        append_col('sumElapsedDuration', 'value')
        append_col('sumMovingDuration', 'display')
        append_col('sumMovingDuration', 'value')
        append_col('weightedMeanSpeed', 'withUnit')
        append_col('weightedMeanSpeed', 'value')
        append_col('sumDistance', 'withUnit')
        append_col('sumDistance', 'value')
        append_col('minHeartRate', 'display')
        append_col('maxElevation', 'withUnit')
        append_col('maxElevation', 'value')
        append_col('gainElevation', 'withUnit')
        append_col('gainElevation', 'value')
        append_col('lossElevation', 'withUnit')
        append_col('lossElevation', 'value')
        append_col('device', 'version')
        csv_record += '\n'

        csv_file.write(csv_record)

        if data_format == 'gpx':
            # Validate GPX data. If we have an activity without GPS data (e.g., running on a treadmill),
            # Garmin Connect still kicks out a GPX, but there is only activity information, no GPS data.
            # N.B. You can omit the XML parse (and the associated log messages) to speed things up.
            gpx = parseString(data)
            gpx_data_exists = len(gpx.getElementsByTagName('trkpt')) > 0

            if gpx_data_exists:
                print('Done. GPX data saved.')
            else:
                print('Done. No track points found.')
        else:
            # TODO: Consider validating other formats.
            print('Done.')
    total_downloaded += num_to_download
# End while loop for multiple chunks.

csv_file.close()

print('Done!')
