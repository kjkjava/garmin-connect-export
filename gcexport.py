#!/usr/bin/python

"""
File: gcexport.py
Author: Kyle Krafka (https://github.com/kjkjava/), 2015
Modified by Jorge Aranda (https://github.com/jorgearanda/)

Description: Export your fitness data from Garmin Connect. See README.md for more information.
"""

import argparse
import cookielib
from datetime import datetime
from fileinput import filename
from getpass import getpass
import json
from os.path import isdir, isfile
from os import mkdir, remove, utime
from sys import argv
from urllib import urlencode
import urllib2
from xml.dom.minidom import parseString
import zipfile

MAX_REQUESTS = 100  # Enforced by Garmin
VERSION = '1.1.0'

url_gc_login = 'https://sso.garmin.com/sso/login?service=https%3A%2F%2Fconnect.garmin.com%2Fpost-auth%2Flogin&' + \
    'webhost=olaxpw-connect04&source=https%3A%2F%2Fconnect.garmin.com%2Fen-US%2Fsignin&' + \
    'redirectAfterAccountLoginUrl=https%3A%2F%2Fconnect.garmin.com%2Fpost-auth%2Flogin&' + \
    'redirectAfterAccountCreationUrl=https%3A%2F%2Fconnect.garmin.com%2Fpost-auth%2Flogin&' + \
    'gauthHost=https%3A%2F%2Fsso.garmin.com%2Fsso&locale=en_US&id=gauth-widget&' + \
    'cssUrl=https%3A%2F%2Fstatic.garmincdn.com%2Fcom.garmin.connect%2Fui%2Fcss%2Fgauth-custom-v1.1-min.css&' + \
    'clientId=GarminConnect&rememberMeShown=true&rememberMeChecked=false&createAccountShown=true&' + \
    'openCreateAccount=false&usernameShown=false&displayNameShown=false&consumeServiceTicket=false&' + \
    'initialFocus=true&embedWidget=false&generateExtraServiceTicket=false'
url_gc_post_auth = 'https://connect.garmin.com/post-auth/login?'
url_gc_search = 'http://connect.garmin.com/proxy/activity-search-service-1.0/json/activities?'
url_gc_tcx_activity = 'https://connect.garmin.com/modern/proxy/download-service/export/tcx/activity/'
url_gc_gpx_activity = 'https://connect.garmin.com/modern/proxy/download-service/export/gpx/activity/'
url_gc_original_activity = 'http://connect.garmin.com/proxy/download-service/files/activity/'


def parse_args():
    """Parse and return command line arguments."""
    current_date = datetime.now().strftime('%Y-%m-%d')
    activities_directory = './' + current_date + '_garmin_connect_export'

    parser = argparse.ArgumentParser()

    parser.add_argument('--version', help="print version and exit", action="store_true")
    parser.add_argument('--username', help="your Garmin Connect username (otherwise, you will be prompted)", nargs='?')
    parser.add_argument('--password', help="your Garmin Connect password (otherwise, you will be prompted)", nargs='?')

    parser.add_argument('-c', '--count', nargs='?', default="1",
        help="number of recent activities to download, or 'all' (default: 1)")

    parser.add_argument('-f', '--format', nargs='?', choices=['gpx', 'tcx', 'original'], default="gpx",
        help="export format; can be 'gpx', 'tcx', or 'original' (default: 'gpx')")

    parser.add_argument('-d', '--directory', nargs='?', default=activities_directory,
        help="the directory to export to (default: './YYYY-MM-DD_garmin_connect_export')")

    parser.add_argument('-u', '--unzip',
        help="if downloading ZIP files (format: 'original'), unzip the file and removes the ZIP file",
        action="store_true")

    parser.add_argument('-ot', '--originaltime',
        help="will set downloaded (and possibly unzipped) file time to the activity start time",
        action="store_true")

    args = parser.parse_args()

    if args.version:
        print argv[0] + ", version " + VERSION
        exit(0)

    return args


def http_request(url, post=None, headers={}):
    """Perform an HTTP request."""
    request = urllib2.Request(url)
    request.add_header(
        'User-Agent',
        'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/1337 Safari/537.36')

    for key in headers:
        request.add_header(key, headers[key])

    if post:
        post = urlencode(post)

    response = opener.open(request, data=post)

    response_code = response.getcode()
    if response_code not in [200, 204]:
        raise Exception('Bad return code (' + str(response_code) + ') for: ' + url)

    return (response.read(), response_code)


def login(username, password):
    http_request(url_gc_login)  # Get a valid session cookie

    post_data = {
        'username': username,
        'password': password,
        'embed': 'true',
        'lt': 'e1s1',
        '_eventId': 'submit',
        'displayNameRequired':
        'false'
    }
    http_request(url_gc_login, post_data)  # Actual login

    login_ticket = None
    for cookie in cookie_jar:
        if cookie.name == 'CASTGC':
            login_ticket = cookie.value
            break

    if not login_ticket:
        raise Exception('Did not get a ticket cookie. Cannot log in. Did you enter the correct username and password?')

    # Chop of 'TGT-' off the beginning, prepend 'ST-0'. (no idea why -JA)
    login_ticket = 'ST-0' + login_ticket[4:]

    http_request(url_gc_post_auth + 'ticket=' + login_ticket)


def create_directory(directory):
    """Create directory for data files, if one does not already exist."""
    if isdir(directory):
        print('Warning: Output directory already exists. Running in append mode.')
    else:
        mkdir(directory)


def prepare_summary_file(directory):
    filename = args.directory + '/activities.csv'
    already_existed = isfile(filename)
    summary_file = open(filename, 'a')

    if not already_existed:
        # Write the CSV header
        summary_file.write('Activity ID,Activity Name,Description,Begin Timestamp,Begin Timestamp (Raw Milliseconds),' +
            'End Timestamp,End Timestamp (Raw Milliseconds),Device,Activity Parent,Activity Type,Event Type,' +
            'Activity Time Zone,Max. Elevation,Max. Elevation (Raw),Begin Latitude (Decimal Degrees Raw),' +
            'Begin Longitude (Decimal Degrees Raw),End Latitude (Decimal Degrees Raw),' +
            'End Longitude (Decimal Degrees Raw),Average Moving Speed,Average Moving Speed (Raw),' +
            'Max. Heart Rate (bpm),Average Heart Rate (bpm),Max. Speed,Max. Speed (Raw),Calories,Calories (Raw),' +
            'Duration (h:m:s),Duration (Raw Seconds),Moving Duration (h:m:s),Moving Duration (Raw Seconds),' +
            'Average Speed,Average Speed (Raw),Distance,Distance (Raw),Max. Heart Rate (bpm),Min. Elevation,' +
            'Min. Elevation (Raw),Elevation Gain,Elevation Gain (Raw),Elevation Loss,Elevation Loss (Raw)\n')

    return summary_file


def get_activities_list(start, limit=100):  # TODO: I think the pagination here is broken
    """Get list of activities, starting on `start` and including up to `limit` items."""
    response, _ = http_request(url_gc_search + urlencode({'start': start, 'limit': limit}))

    return json.loads(response)


def print_activity_summary(a):
    if 'sumElapsedDuration' in a:
        duration = a['sumElapsedDuration']['display']
    else:
        duration = '??:??:??,'

    if 'sumDistance' in a:
        distance = a['sumDistance']['withUnit']
    else:
        distance = '0.00 Kms'

    print('Activity: [' + a['activityId'] + ']')
    print(a['activityName']['value'])
    print('\t' + a['beginTimestamp']['display'] + ', ' + duration + ', ' + distance)


def process_activity(act, args):
    print_activity_summary(act['activity'])

    data_filename = args.directory + '/activity_' + act['activity']['activityId']
    if args.format == 'gpx':
        data_filename += '.gpx'
        act_url = url_gc_gpx_activity + act['activity']['activityId'] + '?full=true'
        file_mode = 'w'
    elif args.format == 'tcx':
        data_filename += '.tcx'
        act_url = url_gc_tcx_activity + act['activity']['activityId'] + '?full=true'
        file_mode = 'w'
    elif args.format == 'original':
        data_filename += '.zip'
        fit_filename = args.directory + '/' + act['activity']['activityId'] + '.fit'
        act_url = url_gc_gpx_activity + act['activity']['activityId']
        file_mode = 'wb'
    else:
        raise Exception('Unrecognized format')

    if isfile(data_filename):
        print('\tData file already exists; skipping...')
        return
    if args.format == 'original' and isfile(fit_filename):
        print('\tFIT data file already exists; skipping...')
        return

    print('\tDownloading file...')
    try:
        data, code = http_request(act_url)
    except urllib2.HTTPError as e:
        if e.code == 500 and args.format == 'tcx':
            # Garmin will give an internal server error (HTTP 500) when downloading TCX files
            # if the original was a manual GPX upload.
            print('\tWriting empty file since Garmin did not generate a TCX file for this activity...')
            data = ''
        elif e.code == 404 and args.format == 'original':
            # For manual activities (i.e., entered in online without a file upload), there is no original file.
            # Write an empty file to prevent redownloading it.
            print('\tWriting empty file since there was no original activity data...')
            data = ''
        else:
            raise Exception('Failed. Got an unexpected HTTP error (' + str(e.code) + act_url + ').')

    save_file = open(data_filename, file_mode)
    save_file.write(data)
    save_file.close()

    if args.originaltime:
        start_time = int(act['activity']['beginTimestamp']['millis']) // 1000
        utime(data_filename, (start_time, start_time))


if __name__ == '__main__':
    args = parse_args()
    cookie_jar = cookielib.CookieJar()
    opener = urllib2.build_opener(urllib2.HTTPCookieProcessor(cookie_jar))

    print('Welcome to Garmin Connect Exporter!')
    username = args.username if args.username else raw_input('Username: ')
    password = args.password if args.password else getpass()

    login(username, password)
    create_directory(args.directory)
    summary = prepare_summary_file(args.directory)

    if args.count == 'all':
        requested_all = True
        requested = None
    else:
        requested_all = False
        requested = int(args.count)
    processed = 0
    existing = 0
    done = False

    while not done:
        activities = get_activities_list(processed)  # TODO: I think the pagination here is broken
        existing = int(activities['results']['search']['totalFound'])
        if requested_all and not requested:
            requested = existing

        for act in activities['results']['activities']:
            process_activity(act, args)
            processed += 1
            done = processed >= existing
            if done:
                break

    summary.close()
    print('Done!')


############################
# Refactored up to above

while total_downloaded < total_to_download:
    # Process each activity.
    for a in activities:
        # Write stats to CSV.
        empty_record = '"",'

        csv_record = ''

        csv_record += empty_record if 'activityId' not in a['activity'] else '"' + a['activity']['activityId'].replace('"', '""') + '",'
        csv_record += empty_record if 'activityName' not in a['activity'] else '"' + a['activity']['activityName']['value'].replace('"', '""') + '",'
        csv_record += empty_record if 'activityDescription' not in a['activity'] else '"' + a['activity']['activityDescription']['value'].replace('"', '""') + '",'
        csv_record += empty_record if 'beginTimestamp' not in a['activity'] else '"' + a['activity']['beginTimestamp']['display'].replace('"', '""') + '",'
        csv_record += empty_record if 'beginTimestamp' not in a['activity'] else '"' + a['activity']['beginTimestamp']['millis'].replace('"', '""') + '",'
        csv_record += empty_record if 'endTimestamp' not in a['activity'] else '"' + a['activity']['endTimestamp']['display'].replace('"', '""') + '",'
        csv_record += empty_record if 'endTimestamp' not in a['activity'] else '"' + a['activity']['endTimestamp']['millis'].replace('"', '""') + '",'
        csv_record += empty_record if 'device' not in a['activity'] else '"' + a['activity']['device']['display'].replace('"', '""') + ' ' + a['activity']['device']['version'].replace('"', '""') + '",'
        csv_record += empty_record if 'activityType' not in a['activity'] else '"' + a['activity']['activityType']['parent']['display'].replace('"', '""') + '",'
        csv_record += empty_record if 'activityType' not in a['activity'] else '"' + a['activity']['activityType']['display'].replace('"', '""') + '",'
        csv_record += empty_record if 'eventType' not in a['activity'] else '"' + a['activity']['eventType']['display'].replace('"', '""') + '",'
        csv_record += empty_record if 'activityTimeZone' not in a['activity'] else '"' + a['activity']['activityTimeZone']['display'].replace('"', '""') + '",'
        csv_record += empty_record if 'maxElevation' not in a['activity'] else '"' + a['activity']['maxElevation']['withUnit'].replace('"', '""') + '",'
        csv_record += empty_record if 'maxElevation' not in a['activity'] else '"' + a['activity']['maxElevation']['value'].replace('"', '""') + '",'
        csv_record += empty_record if 'beginLatitude' not in a['activity'] else '"' + a['activity']['beginLatitude']['value'].replace('"', '""') + '",'
        csv_record += empty_record if 'beginLongitude' not in a['activity'] else '"' + a['activity']['beginLongitude']['value'].replace('"', '""') + '",'
        csv_record += empty_record if 'endLatitude' not in a['activity'] else '"' + a['activity']['endLatitude']['value'].replace('"', '""') + '",'
        csv_record += empty_record if 'endLongitude' not in a['activity'] else '"' + a['activity']['endLongitude']['value'].replace('"', '""') + '",'
        csv_record += empty_record if 'weightedMeanMovingSpeed' not in a['activity'] else '"' + a['activity']['weightedMeanMovingSpeed']['display'].replace('"', '""') + '",'  # The units vary between Minutes per Mile and mph, but withUnit always displays "Minutes per Mile"
        csv_record += empty_record if 'weightedMeanMovingSpeed' not in a['activity'] else '"' + a['activity']['weightedMeanMovingSpeed']['value'].replace('"', '""') + '",'
        csv_record += empty_record if 'maxHeartRate' not in a['activity'] else '"' + a['activity']['maxHeartRate']['display'].replace('"', '""') + '",'
        csv_record += empty_record if 'weightedMeanHeartRate' not in a['activity'] else '"' + a['activity']['weightedMeanHeartRate']['display'].replace('"', '""') + '",'
        csv_record += empty_record if 'maxSpeed' not in a['activity'] else '"' + a['activity']['maxSpeed']['display'].replace('"', '""') + '",'  # The units vary between Minutes per Mile and mph, but withUnit always displays "Minutes per Mile"
        csv_record += empty_record if 'maxSpeed' not in a['activity'] else '"' + a['activity']['maxSpeed']['value'].replace('"', '""') + '",'
        csv_record += empty_record if 'sumEnergy' not in a['activity'] else '"' + a['activity']['sumEnergy']['display'].replace('"', '""') + '",'
        csv_record += empty_record if 'sumEnergy' not in a['activity'] else '"' + a['activity']['sumEnergy']['value'].replace('"', '""') + '",'
        csv_record += empty_record if 'sumElapsedDuration' not in a['activity'] else '"' + a['activity']['sumElapsedDuration']['display'].replace('"', '""') + '",'
        csv_record += empty_record if 'sumElapsedDuration' not in a['activity'] else '"' + a['activity']['sumElapsedDuration']['value'].replace('"', '""') + '",'
        csv_record += empty_record if 'sumMovingDuration' not in a['activity'] else '"' + a['activity']['sumMovingDuration']['display'].replace('"', '""') + '",'
        csv_record += empty_record if 'sumMovingDuration' not in a['activity'] else '"' + a['activity']['sumMovingDuration']['value'].replace('"', '""') + '",'
        csv_record += empty_record if 'weightedMeanSpeed' not in a['activity'] else '"' + a['activity']['weightedMeanSpeed']['withUnit'].replace('"', '""') + '",'
        csv_record += empty_record if 'weightedMeanSpeed' not in a['activity'] else '"' + a['activity']['weightedMeanSpeed']['value'].replace('"', '""') + '",'
        csv_record += empty_record if 'sumDistance' not in a['activity'] else '"' + a['activity']['sumDistance']['withUnit'].replace('"', '""') + '",'
        csv_record += empty_record if 'sumDistance' not in a['activity'] else '"' + a['activity']['sumDistance']['value'].replace('"', '""') + '",'
        csv_record += empty_record if 'minHeartRate' not in a['activity'] else '"' + a['activity']['minHeartRate']['display'].replace('"', '""') + '",'
        csv_record += empty_record if 'maxElevation' not in a['activity'] else '"' + a['activity']['maxElevation']['withUnit'].replace('"', '""') + '",'
        csv_record += empty_record if 'maxElevation' not in a['activity'] else '"' + a['activity']['maxElevation']['value'].replace('"', '""') + '",'
        csv_record += empty_record if 'gainElevation' not in a['activity'] else '"' + a['activity']['gainElevation']['withUnit'].replace('"', '""') + '",'
        csv_record += empty_record if 'gainElevation' not in a['activity'] else '"' + a['activity']['gainElevation']['value'].replace('"', '""') + '",'
        csv_record += empty_record if 'lossElevation' not in a['activity'] else '"' + a['activity']['lossElevation']['withUnit'].replace('"', '""') + '",'
        csv_record += empty_record if 'lossElevation' not in a['activity'] else '"' + a['activity']['lossElevation']['value'].replace('"', '""') + '"'
        csv_record += '\n'

        csv_file.write(csv_record.encode('utf8'))

        if args.format == 'gpx' and code != 204:
            # Validate GPX data. If we have an activity without GPS data (e.g., running on a treadmill),
            # Garmin Connect still kicks out a GPX, but there is only activity information, no GPS data.
            # N.B. You can omit the XML parse (and the associated log messages) to speed things up.
            gpx = parseString(data)
            gpx_data_exists = len(gpx.getElementsByTagName('trkpt')) > 0

            if gpx_data_exists:
                print 'Done. GPX data saved.'
            else:
                print 'Done. No track points found.'
        elif args.format == 'original':
            if args.unzip and data_filename[-3:].lower() == 'zip':
                # Even manual upload of a GPX file is zipped, but we'll validate the extension.
                print "Unzipping and removing original files...",
                zip_file = open(data_filename, 'rb')
                z = zipfile.ZipFile(zip_file)
                for name in z.namelist():
                    ef = z.extract(name, args.directory)
                    if args.originaltime:
                        utime(ef, (start_time, start_time))
                zip_file.close()
                remove(data_filename)
            print 'Done.'
        else:
            # TODO: Consider validating other formats.
            print 'Done.'
    total_downloaded += num_to_download
