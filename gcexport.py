#!/usr/local/bin/python3

"""
File: gcexport.py
Author: Kyle Krafka (https://github.com/kjkjava/), 2015
Modified by Jorge Aranda (https://github.com/jorgearanda/)

Description: Export your fitness data from Garmin Connect. See README.md for more information.
"""

import argparse
import json
from datetime import datetime
from getpass import getpass
from http import cookiejar
from os import mkdir, utime
from os.path import isdir, isfile
from sys import argv
from urllib.error import HTTPError
from urllib.parse import urlencode
from urllib.request import HTTPCookieProcessor, build_opener, Request

MAX_REQUESTS = 100  # Enforced by Garmin
VERSION = '1.1.0'

url_gc_login = 'https://sso.garmin.com/sso/login?service=https%3A%2F%2Fconnect.garmin.com%2Fpost-auth%2Flogin&' + \
               'webhost=' \
               'olaxpw-connect04&source=https%3A%2F%2Fconnect.garmin.com%2Fen-US%2Fsignin&' + \
               'redirectAfterAccountLoginUrl=' \
               'https%3A%2F%2Fconnect.garmin.com%2Fpost-auth%2Flogin&' + \
               'redirectAfterAccountCreationUrl=' \
               'https%3A%2F%2Fconnect.garmin.com%2Fpost-auth%2Flogin&' + \
               'gauthHost=' \
               'https%3A%2F%2Fsso.garmin.com%2Fsso&locale=en_US&id=gauth-widget&' + \
               'cssUrl=' \
               'https%3A%2F%2Fstatic.garmincdn.com%2Fcom.garmin.connect%2Fui%2Fcss%2Fgauth-custom-v1.1-min.css&' + \
               'clientId=' \
               'GarminConnect&rememberMeShown=true&rememberMeChecked=false&createAccountShown=true&' + \
               'openCreateAccount=' \
               'false&usernameShown=' \
               'false&displayNameShown=false&consumeServiceTicket=false&' + \
               'initialFocus=true&embedWidget=false&generateExtraServiceTicket=false'
url_gc_post_auth = 'https://connect.garmin.com/post-auth/login?'
url_gc_search = 'http://connect.garmin.com/proxy/activity-search-service-1.0/json/activities?'
url_gc_tcx_activity = 'https://connect.garmin.com/modern/proxy/download-service/export/tcx/activity/'
url_gc_gpx_activity = 'https://connect.garmin.com/modern/proxy/download-service/export/gpx/activity/'

cookie_jar = cookiejar.CookieJar()


def parse_args():
    """Parse and return command line arguments."""
    current_date = datetime.now().strftime('%Y-%m-%d')
    activities_directory = './' + current_date + '_garmin_connect_export'

    parser = argparse.ArgumentParser()

    parser.add_argument('--version', help="print version and exit", action="store_true")
    parser.add_argument('--username', help="your Garmin Connect username (otherwise, you will be prompted)", nargs='?')
    parser.add_argument('--password', help="your Garmin Connect password (otherwise, you will be prompted)", nargs='?')

    parser.add_argument('-c', '--count', nargs='?', default="all",
                        help="number of recent activities to download, or 'all' (default: 'all')")

    parser.add_argument('-f', '--format', nargs='?', choices=['gpx', 'tcx', 'none'], default="gpx",
                        help="export format; can be 'gpx' 'tcx' or 'none' (default: 'gpx')")

    parser.add_argument('-d', '--directory', nargs='?', default=activities_directory,
                        help="the directory to export to (default: './YYYY-MM-DD_garmin_connect_export')")

    parser.add_argument('-ot', '--originaltime',
                        help="will set downloaded file time to the activity start time",
                        action="store_true")

    arguments = parser.parse_args()

    if arguments.version:
        print(argv[0] + ", version " + VERSION)
        exit(0)

    return arguments


def http_request(url, post=None, headers=None):
    """Perform an HTTP request."""
    if headers is None:
        headers = {}
    request = Request(url)
    request.add_header(
        'User-Agent',
        'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/1337 Safari/537.36')

    for key in headers:
        request.add_header(key, headers[key])

    if post:
        post = urlencode(post).encode("utf-8")

    opener = build_opener(HTTPCookieProcessor(cookie_jar))
    response = opener.open(request, data=post)

    response_code = response.getcode()
    if response_code not in [200, 204]:
        raise Exception('Bad return code (' + str(response_code) + ') for: ' + url)

    return response.read(), response_code


def login(usrname, passwd):
    http_request(url_gc_login)  # Get a valid session cookie

    post_data = {
        'username': usrname,
        'password': passwd,
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


def prepare_summary_file():
    filename = args.directory + '/activities.csv'
    already_existed = isfile(filename)
    summary_file = open(filename, 'ab')

    if not already_existed:
        # Write the CSV header
        header = 'Activity ID,Activity Name,Description,Begin Timestamp,Begin Timestamp (Raw Milliseconds),' + \
                 'End Timestamp,End Timestamp (Raw Milliseconds),Device,Activity Parent,Activity Type,Event Type,' + \
                 'Activity Time Zone,Max. Elevation,Max. Elevation (Raw),Begin Latitude (Decimal Degrees Raw),' + \
                 'Begin Longitude (Decimal Degrees Raw),End Latitude (Decimal Degrees Raw),' + \
                 'End Longitude (Decimal Degrees Raw),Average Moving Speed,Average Moving Speed (Raw),' + \
                 'Max. Heart Rate (bpm),Average Heart Rate (bpm),Max. Speed,Max. Speed (Raw),Calories' \
                 ',Calories (Raw),' + \
                 'Duration (h:m:s),Duration (Raw Seconds),Moving Duration (h:m:s),Moving Duration (Raw Seconds),' + \
                 'Average Speed,Average Speed (Raw),Distance,Distance (Raw),Max. Heart Rate (bpm),Min. Elevation,' + \
                 'Min. Elevation (Raw),Elevation Gain,Elevation Gain (Raw),Elevation Loss,Elevation Loss (Raw),' + \
                 'Min. Temp,Min. Temp (raw),Max. Temp,Max. Temp (raw),Avg. Temp,Avg. Temp (raw),' + \
                 'Min. Cad,Min. Cad (raw),Max. Cad,Max. Cad (raw),Avg. Cad,Avg. Cad (raw)\n'
        summary_file.write(header.encode('utf8'))

    return summary_file


def get_activities_list(start, limit=MAX_REQUESTS):
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


def process_activity(read_act, arguments):
    print_activity_summary(read_act['activity'])

    data_filename = arguments.directory + '/activity_' + read_act['activity']['activityId']
    act_url = read_act['activity']['activityId'] + '?full=true'
    if arguments.format == 'gpx':
        data_filename += '.gpx'
        act_url = url_gc_gpx_activity + act_url
    elif arguments.format == 'tcx':
        data_filename += '.tcx'
        act_url = url_gc_tcx_activity + act_url
    elif arguments.format == 'none':
        print('no download')
    else:
        raise Exception('Unrecognized format')

    if arguments.format != 'none':
        if isfile(data_filename):
            print('\tData file already exists; skipping...')
            return

        print('\tDownloading file...')
        try:
            data, code = http_request(act_url)
        except HTTPError as e:
            if e.code == 500 and arguments.format == 'tcx':
                # Garmin will give an internal server error (HTTP 500) when downloading TCX files
                # if the original was a manual GPX upload.
                print('\tWriting empty file since Garmin did not generate a TCX file for this activity...')
                data = ''
            else:
                raise Exception('Failed. Got an unexpected HTTP error (' + str(e.code) + act_url + ').')

        save_file = open(data_filename, 'wb')
        save_file.write(data)
        save_file.close()

    if arguments.originaltime:
        start_time = int(read_act['activity']['beginTimestamp']['millis']) // 1000
        utime(data_filename, (start_time, start_time))

    a = read_act['activity']
    csv = '"' + a.get('activityId', '').replace('"', '""') + '",'
    csv += '"' + a.get('activityName', {}).get('value', '').replace('"', '""') + '",'
    csv += '"' + a.get('activityDescription', {}).get('value', '').replace('"', '""') + '",'
    csv += '"' + a.get('beginTimestamp', {}).get('display', '').replace('"', '""') + '",'
    csv += '"' + a.get('beginTimestamp', {}).get('millis', '').replace('"', '""') + '",'
    csv += '"' + a.get('endTimestamp', {}).get('display', '').replace('"', '""') + '",'
    csv += '"' + a.get('endTimestamp', {}).get('millis', '').replace('"', '""') + '",'
    if 'device' in a:
        csv += '"' + a['device']['display'].replace('"', '""') + a['device']['version'].replace('"', '""') + '","'
    else:
        csv += '"",'
    csv += '"' + a.get('activityType', {}).get('parent', {}).get('display', '').replace('"', '""') + '",'
    csv += '"' + a.get('activityType', {}).get('display', '').replace('"', '""') + '",'
    csv += '"' + a.get('eventType', {}).get('display', '').replace('"', '""') + '",'
    csv += '"' + a.get('activityTimeZone', {}).get('display', '').replace('"', '""') + '",'
    csv += '"' + a.get('maxElevation', {}).get('withUnit', '').replace('"', '""') + '",'
    csv += '"' + a.get('maxElevation', {}).get('value', '').replace('"', '""') + '",'
    csv += '"' + a.get('beginLatitude', {}).get('value', '').replace('"', '""') + '",'
    csv += '"' + a.get('beginLongitude', {}).get('value', '').replace('"', '""') + '",'
    csv += '"' + a.get('endLatitude', {}).get('value', '').replace('"', '""') + '",'
    csv += '"' + a.get('endLongitude', {}).get('value', '').replace('"', '""') + '",'
    csv += '"' + a.get('weightedMeanMovingSpeed', {}).get('display', '').replace('"', '""') + '",'
    csv += '"' + a.get('weightedMeanMovingSpeed', {}).get('value', '').replace('"', '""') + '",'
    csv += '"' + a.get('maxHeartRate', {}).get('display', '').replace('"', '""') + '",'
    csv += '"' + a.get('weightedMeanHeartRate', {}).get('display', '').replace('"', '""') + '",'
    csv += '"' + a.get('maxSpeed', {}).get('display', '').replace('"', '""') + '",'
    csv += '"' + a.get('maxSpeed', {}).get('value', '').replace('"', '""') + '",'
    csv += '"' + a.get('sumEnergy', {}).get('display', '').replace('"', '""') + '",'
    csv += '"' + a.get('sumEnergy', {}).get('value', '').replace('"', '""') + '",'
    csv += '"' + a.get('sumElapsedDuration', {}).get('display', '').replace('"', '""') + '",'
    csv += '"' + a.get('sumElapsedDuration', {}).get('value', '').replace('"', '""') + '",'
    csv += '"' + a.get('sumMovingDuration', {}).get('display', '').replace('"', '""') + '",'
    csv += '"' + a.get('sumMovingDuration', {}).get('value', '').replace('"', '""') + '",'
    csv += '"' + a.get('weightedMeanSpeed', {}).get('withUnit', '').replace('"', '""') + '",'
    csv += '"' + a.get('weightedMeanSpeed', {}).get('value', '').replace('"', '""') + '",'
    csv += '"' + a.get('sumDistance', {}).get('withUnit', '').replace('"', '""') + '",'
    csv += '"' + a.get('sumDistance', {}).get('value', '').replace('"', '""') + '",'
    csv += '"' + a.get('minHeartRate', {}).get('display', '').replace('"', '""') + '",'
    csv += '"' + a.get('minElevation', {}).get('withUnit', '').replace('"', '""') + '",'
    csv += '"' + a.get('minElevation', {}).get('value', '').replace('"', '""') + '",'
    csv += '"' + a.get('gainElevation', {}).get('withUnit', '').replace('"', '""') + '",'
    csv += '"' + a.get('gainElevation', {}).get('value', '').replace('"', '""') + '",'
    csv += '"' + a.get('lossElevation', {}).get('withUnit', '').replace('"', '""') + '",'
    csv += '"' + a.get('lossElevation', {}).get('value', '').replace('"', '""') + '",'
    csv += '"' + a.get('minAirTemperature', {}).get('withUnit', '').replace('"', '""') + '",'
    csv += '"' + a.get('minAirTemperature', {}).get('value', '').replace('"', '""') + '",'
    csv += '"' + a.get('maxAirTemperature', {}).get('withUnit', '').replace('"', '""') + '",'
    csv += '"' + a.get('maxAirTemperature', {}).get('value', '').replace('"', '""') + '",'
    csv += '"' + a.get('weightedMeanAirTemperature', {}).get('withUnit', '').replace('"', '""') + '",'
    csv += '"' + a.get('weightedMeanAirTemperature', {}).get('value', '').replace('"', '""') + '",'
    csv += '"' + a.get('minBikeCadence', {}).get('withUnit', '').replace('"', '""') + '",'
    csv += '"' + a.get('minBikeCadence', {}).get('value', '').replace('"', '""') + '",'
    csv += '"' + a.get('maxBikeCadence', {}).get('withUnit', '').replace('"', '""') + '",'
    csv += '"' + a.get('maxBikeCadence', {}).get('value', '').replace('"', '""') + '",'
    csv += '"' + a.get('weightedMeanBikeCadence', {}).get('withUnit', '').replace('"', '""') + '",'
    csv += '"' + a.get('weightedMeanBikeCadence', {}).get('value', '').replace('"', '""') + '"'
    csv += '\n'

    return csv


if __name__ == '__main__':
    args = parse_args()

    print('Welcome to Garmin Connect Exporter!')
    username = args.username if args.username else input('Username: ')
    password = args.password if args.password else getpass()

    login(username, password)
    create_directory(args.directory)
    summary = prepare_summary_file()

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
        activities = get_activities_list(processed)
        existing = int(activities['results']['search']['totalFound'])
        if requested_all and not requested:
            requested = existing

        for act in activities['results']['activities']:
            act_csv = process_activity(act, args)
            summary.write(act_csv.encode('utf8'))
            processed += 1
            done = processed >= requested
            if done:
                break

    summary.close()
    print('Done!')
