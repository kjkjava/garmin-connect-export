#!/usr/bin/python

"""
File: gcexport.py
Author: Kyle Krafka (https://github.com/kjkjava/), 2015
Modified by Jorge Aranda (https://github.com/jorgearanda/)

Description: Export your fitness data from Garmin Connect. See README.md for more information.
"""

import argparse
from http import cookiejar
from datetime import datetime
from fileinput import filename
from getpass import getpass
import json
from os.path import isdir, isfile
from os import mkdir, remove, utime
from sys import argv
from urllib.parse import urlencode
from urllib.request import HTTPCookieProcessor, build_opener, Request
from urllib.error import HTTPError

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

cookie_jar = cookiejar.CookieJar()


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

    parser.add_argument('-f', '--format', nargs='?', choices=['gpx', 'tcx'], default="gpx",
        help="export format; can be 'gpx' or 'tcx' (default: 'gpx')")

    parser.add_argument('-d', '--directory', nargs='?', default=activities_directory,
        help="the directory to export to (default: './YYYY-MM-DD_garmin_connect_export')")

    parser.add_argument('-ot', '--originaltime',
        help="will set downloaded file time to the activity start time",
        action="store_true")

    args = parser.parse_args()

    if args.version:
        print(argv[0] + ", version " + VERSION)
        exit(0)

    return args


def http_request(url, post=None, headers={}):
    """Perform an HTTP request."""
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
    summary_file = open(filename, 'ab')

    if not already_existed:
        # Write the CSV header
        header = 'Activity ID,Activity Name,Description,Begin Timestamp,Begin Timestamp (Raw Milliseconds),' + \
            'End Timestamp,End Timestamp (Raw Milliseconds),Device,Activity Parent,Activity Type,Event Type,' + \
            'Activity Time Zone,Max. Elevation,Max. Elevation (Raw),Begin Latitude (Decimal Degrees Raw),' + \
            'Begin Longitude (Decimal Degrees Raw),End Latitude (Decimal Degrees Raw),' + \
            'End Longitude (Decimal Degrees Raw),Average Moving Speed,Average Moving Speed (Raw),' + \
            'Max. Heart Rate (bpm),Average Heart Rate (bpm),Max. Speed,Max. Speed (Raw),Calories,Calories (Raw),' + \
            'Duration (h:m:s),Duration (Raw Seconds),Moving Duration (h:m:s),Moving Duration (Raw Seconds),' + \
            'Average Speed,Average Speed (Raw),Distance,Distance (Raw),Max. Heart Rate (bpm),Min. Elevation,' + \
            'Min. Elevation (Raw),Elevation Gain,Elevation Gain (Raw),Elevation Loss,Elevation Loss (Raw)\n'
        summary_file.write(header.encode('utf8'))

    return summary_file


def get_activities_list(start, limit=MAX_REQUESTS):  # TODO: I think the pagination here is broken
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
    act_url = act['activity']['activityId'] + '?full=true'
    if args.format == 'gpx':
        data_filename += '.gpx'
        act_url = url_gc_gpx_activity + act_url
    elif args.format == 'tcx':
        data_filename += '.tcx'
        act_url = url_gc_tcx_activity + act_url
    else:
        raise Exception('Unrecognized format')

    if isfile(data_filename):
        print('\tData file already exists; skipping...')
        return

    print('\tDownloading file...')
    try:
        data, code = http_request(act_url)
    except HTTPError as e:
        if e.code == 500 and args.format == 'tcx':
            # Garmin will give an internal server error (HTTP 500) when downloading TCX files
            # if the original was a manual GPX upload.
            print('\tWriting empty file since Garmin did not generate a TCX file for this activity...')
            data = ''
        else:
            raise Exception('Failed. Got an unexpected HTTP error (' + str(e.code) + act_url + ').')

    save_file = open(data_filename, 'wb')
    save_file.write(data)
    save_file.close()

    if args.originaltime:
        start_time = int(act['activity']['beginTimestamp']['millis']) // 1000
        utime(data_filename, (start_time, start_time))

    a = act['activity']
    empty = '"",'
    csv = ''
    csv += empty if 'activityId' not in a else '"' + a['activityId'].replace('"', '""') + '",'
    csv += empty if 'activityName' not in a else '"' + a['activityName']['value'].replace('"', '""') + '",'
    csv += empty if 'activityDescription' not in a else '"' + a['activityDescription']['value'].replace('"', '""') + '",'
    csv += empty if 'beginTimestamp' not in a else '"' + a['beginTimestamp']['display'].replace('"', '""') + '",'
    csv += empty if 'beginTimestamp' not in a else '"' + a['beginTimestamp']['millis'].replace('"', '""') + '",'
    csv += empty if 'endTimestamp' not in a else '"' + a['endTimestamp']['display'].replace('"', '""') + '",'
    csv += empty if 'endTimestamp' not in a else '"' + a['endTimestamp']['millis'].replace('"', '""') + '",'
    csv += empty if 'device' not in a else '"' + a['device']['display'].replace('"', '""') + ' ' + a['device']['version'].replace('"', '""') + '",'
    csv += empty if 'activityType' not in a else '"' + a['activityType']['parent']['display'].replace('"', '""') + '",'
    csv += empty if 'activityType' not in a else '"' + a['activityType']['display'].replace('"', '""') + '",'
    csv += empty if 'eventType' not in a else '"' + a['eventType']['display'].replace('"', '""') + '",'
    csv += empty if 'activityTimeZone' not in a else '"' + a['activityTimeZone']['display'].replace('"', '""') + '",'
    csv += empty if 'maxElevation' not in a else '"' + a['maxElevation']['withUnit'].replace('"', '""') + '",'
    csv += empty if 'maxElevation' not in a else '"' + a['maxElevation']['value'].replace('"', '""') + '",'
    csv += empty if 'beginLatitude' not in a else '"' + a['beginLatitude']['value'].replace('"', '""') + '",'
    csv += empty if 'beginLongitude' not in a else '"' + a['beginLongitude']['value'].replace('"', '""') + '",'
    csv += empty if 'endLatitude' not in a else '"' + a['endLatitude']['value'].replace('"', '""') + '",'
    csv += empty if 'endLongitude' not in a else '"' + a['endLongitude']['value'].replace('"', '""') + '",'
    csv += empty if 'weightedMeanMovingSpeed' not in a else '"' + a['weightedMeanMovingSpeed']['display'].replace('"', '""') + '",'
    csv += empty if 'weightedMeanMovingSpeed' not in a else '"' + a['weightedMeanMovingSpeed']['value'].replace('"', '""') + '",'
    csv += empty if 'maxHeartRate' not in a else '"' + a['maxHeartRate']['display'].replace('"', '""') + '",'
    csv += empty if 'weightedMeanHeartRate' not in a else '"' + a['weightedMeanHeartRate']['display'].replace('"', '""') + '",'
    csv += empty if 'maxSpeed' not in a else '"' + a['maxSpeed']['display'].replace('"', '""') + '",'
    csv += empty if 'maxSpeed' not in a else '"' + a['maxSpeed']['value'].replace('"', '""') + '",'
    csv += empty if 'sumEnergy' not in a else '"' + a['sumEnergy']['display'].replace('"', '""') + '",'
    csv += empty if 'sumEnergy' not in a else '"' + a['sumEnergy']['value'].replace('"', '""') + '",'
    csv += empty if 'sumElapsedDuration' not in a else '"' + a['sumElapsedDuration']['display'].replace('"', '""') + '",'
    csv += empty if 'sumElapsedDuration' not in a else '"' + a['sumElapsedDuration']['value'].replace('"', '""') + '",'
    csv += empty if 'sumMovingDuration' not in a else '"' + a['sumMovingDuration']['display'].replace('"', '""') + '",'
    csv += empty if 'sumMovingDuration' not in a else '"' + a['sumMovingDuration']['value'].replace('"', '""') + '",'
    csv += empty if 'weightedMeanSpeed' not in a else '"' + a['weightedMeanSpeed']['withUnit'].replace('"', '""') + '",'
    csv += empty if 'weightedMeanSpeed' not in a else '"' + a['weightedMeanSpeed']['value'].replace('"', '""') + '",'
    csv += empty if 'sumDistance' not in a else '"' + a['sumDistance']['withUnit'].replace('"', '""') + '",'
    csv += empty if 'sumDistance' not in a else '"' + a['sumDistance']['value'].replace('"', '""') + '",'
    csv += empty if 'minHeartRate' not in a else '"' + a['minHeartRate']['display'].replace('"', '""') + '",'
    csv += empty if 'maxElevation' not in a else '"' + a['maxElevation']['withUnit'].replace('"', '""') + '",'
    csv += empty if 'maxElevation' not in a else '"' + a['maxElevation']['value'].replace('"', '""') + '",'
    csv += empty if 'gainElevation' not in a else '"' + a['gainElevation']['withUnit'].replace('"', '""') + '",'
    csv += empty if 'gainElevation' not in a else '"' + a['gainElevation']['value'].replace('"', '""') + '",'
    csv += empty if 'lossElevation' not in a else '"' + a['lossElevation']['withUnit'].replace('"', '""') + '",'
    csv += empty if 'lossElevation' not in a else '"' + a['lossElevation']['value'].replace('"', '""') + '"'
    csv += '\n'

    return csv


if __name__ == '__main__':
    args = parse_args()

    print('Welcome to Garmin Connect Exporter!')
    username = args.username if args.username else input('Username: ')
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
            act_csv = process_activity(act, args)
            summary.write(act_csv.encode('utf8'))
            processed += 1
            done = processed >= requested
            if done:
                break

    summary.close()
    print('Done!')
