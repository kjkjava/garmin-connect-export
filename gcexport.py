#!/usr/bin/python

from __future__ import unicode_literals  # for Python 2 and 3 compatibility
from datetime import datetime
from getpass import getpass
import sys
import os
from xml.dom.minidom import parseString
import requests
import argparse
import zipfile
import logging

logging.basicConfig(  # filename='import.log',
    format='%(levelname)s:%(message)s',
    level=logging.DEBUG)


CURRENT_DATE = datetime.now().strftime('%Y-%m-%d')

DEFAULT_DIRECTORY = './' + CURRENT_DATE + '_garmin_connect_export'
CSV_FILENAME = "activities.csv"

py3 = sys.version_info > (3,)  # is this python 3?


parser = argparse.ArgumentParser()

parser.add_argument("--username",
                    help=("your Garmin Connect username "
                          "(otherwise, you will be prompted)"),
                    nargs='?')

parser.add_argument("--password",
                    help=("your Garmin Connect password "
                          "(otherwise, you will be prompted)"),
                    nargs='?')

parser.add_argument('-c', '--count', nargs='?', default="1",
                    help=("number of recent activities to download, or 'all'"
                          " (default: 1)"))


parser.add_argument('-f', '--format', nargs='?',
                    choices=['gpx', 'tcx', 'original'], default="gpx",
                    help=("export format; can be 'gpx', 'tcx',"
                          " or 'original' (default: 'gpx')"))

parser.add_argument('-d', '--directory', nargs='?',
                    default=DEFAULT_DIRECTORY,
                    help=("the directory to export to"
                          " (default: './YYYY-MM-DD_garmin_connect_export')"))

parser.add_argument('-u', '--unzip',
                    help=("if downloading ZIP files (format: 'original'),"
                          " unzip the file and removes the ZIP file"),
                    action="store_true")

args = parser.parse_args()

logging.info('Welcome to Garmin Connect Exporter!')

# Create directory for data files.
if os.path.isdir(args.directory):
    logging.info("Warning: Output directory already exists."
                 " Will skip already-downloaded files and append to the"
                 " CSV file.")
if args.username:
    username = args.username
else:
    username = input('Username: ') if py3 else raw_input('Username: ')

password = args.password if args.password else getpass()

# Maximum number of activities you can request at once.  Set and enforced
# by Garmin.
limit_maximum = 100

# URLs for various services.
url_gc_login = ("https://sso.garmin.com/sso/login?"
                "service=https://connect.garmin.com/post-auth/login"
                "&webhost=olaxpw-connect04"
                "&source=https://connect.garmin.com/en-US/signin"
                "&redirectAfterAccountLoginUrl=https://connect.garmin.com/post-auth/login"
                "&redirectAfterAccountCreationUrl=https://connect.garmin.com/post-auth/login"
                "&gauthHost=https://sso.garmin.com/sso"
                "&locale=en_US"
                "&id=gauth-widget"
                "&cssUrl=https://static.garmincdn.com/com.garmin.connect/ui/css/gauth-custom-v1.1-min.css"
                "&clientId=GarminConnect"
                "&rememberMeShown=true"
                "&rememberMeChecked=false"
                "&createAccountShown=true"
                "&openCreateAccount=false"
                "&usernameShown=false"
                "&displayNameShown=false"
                "&consumeServiceTicket=false"
                "&initialFocus=true"
                "&embedWidget=false"
                "&generateExtraServiceTicket=false")

url_gc_post_auth = 'https://connect.garmin.com/post-auth/login?'

url_gc_search = 'http://connect.garmin.com/proxy/activity-search-service-1.0/json/activities?'
url_gc_gpx_activity = 'http://connect.garmin.com/proxy/activity-service-1.1/gpx/activity/'
url_gc_tcx_activity = 'http://connect.garmin.com/proxy/activity-service-1.1/tcx/activity/'
url_gc_original_activity = 'http://connect.garmin.com/proxy/download-service/files/activity/'


def logged_in_session(username, password):
    # Create a session that will persist thorughout this script
    sesh = requests.Session()

    sesh.headers['User-Agent'] = ("Mozilla/5.0 (X11; Linux x86_64) "
                                  "AppleWebKit/537.36 (KHTML, like Gecko) "
                                  "Chrome/29.0.1547.62 Safari/537.36")

    # Initially, we need to get a valid session cookie,
    # so we pull the login page.
    r1 = sesh.get(url_gc_login)

    # Now we'll actually login, using
    # fields that are passed in a typical Garmin login.
    post_data = {
        'username': username,
        'password': password,
        'embed': 'true',
        'lt': 'e1s1',
        '_eventId': 'submit',
        'displayNameRequired': 'false'
    }

    r2 = sesh.post(url_gc_login, data=post_data)

    if "CASTGC" in r2.cookies:
        # Construct login ticket from the  cookie with "CASTCG" key
        login_ticket = "ST-0" + r2.cookies["CASTGC"][4:]

    else:
        raise Exception(
            "Did not get a ticket cookie. Cannot log in."
            " Did you enter the correct username and password?"
        )

    r3 = sesh.post(url_gc_post_auth, params={"ticket": login_ticket})

    return sesh


# We should be logged in now.
sesh = logged_in_session(username, password)


if not os.path.isdir(args.directory):
    os.mkdir(args.directory)

csv_fullpath = args.directory + "/" + CSV_FILENAME

csv_existed = os.path.isfile(csv_fullpath)


download_all = False

if args.count == 'all':
    # If the user wants to download all activities, first download one,
    # then the result of that request will tell us how many are available
    # so we will modify the variables then.
    total_to_download = 1
    download_all = True
else:
    total_to_download = int(args.count)
total_downloaded = 0

# This while loop will download data from the server in multiple chunks,
# if necessary.

with open(csv_fullpath, 'a') as csv_file:

    # Write header to CSV file
    if not csv_existed:
        csv_file.write(
            "Activity ID,"
            "Activity Name,"
            "Description,"
            "Begin Timestamp,"
            "Begin Timestamp (Raw Milliseconds),"
            "End Timestamp,"
            "End Timestamp (Raw Milliseconds),"
            "Device,"
            "Activity Parent,"
            "Activity Type,"
            "Event Type,"
            "Activity Time Zone,"
            "Max. Elevation,"
            "Max. Elevation (Raw),"
            "Begin Latitude (Decimal Degrees Raw),"
            "Begin Longitude (Decimal Degrees Raw),"
            "End Latitude (Decimal Degrees Raw),"
            "End Longitude (Decimal Degrees Raw),"
            "Average Moving Speed,"
            "Average Moving Speed (Raw),"
            "Max. Heart Rate (bpm),"
            "Average Heart Rate (bpm),"
            "Max. Speed,"
            "Max. Speed (Raw),"
            "Calories,"
            "Calories (Raw),"
            "Duration (h:m:s),"
            "Duration (Raw Seconds),"
            "Moving Duration (h:m:s),"
            "Moving Duration (Raw Seconds),"
            "Average Speed,"
            "Average Speed (Raw),"
            "Distance,"
            "Distance (Raw),"
            "Max. Heart Rate (bpm),"
            "Min. Elevation,"
            "Min. Elevation (Raw),"
            "Elevation Gain,"
            "Elevation Gain (Raw),"
            "Elevation Loss,"
            "Elevation Loss (Raw)\n"
        )

    while total_downloaded < total_to_download:
        # Maximum of 100... 400 return status if over 100.  So download 100 or
        # whatever remains if less than 100.
        if total_to_download - total_downloaded > 100:
            num_to_download = 100
        else:
            num_to_download = total_to_download - total_downloaded

        search_params = {'start': total_downloaded, 'limit': num_to_download}

        # Query Garmin Connect
        # TODO: Catch possible exceptions here.
        json_results = sesh.get(url_gc_search, params=search_params).json()

        search = json_results['results']['search']

        if download_all:
            # Modify total_to_download based on how many activities the server
            # reports.
            total_to_download = int(search['totalFound'])
            # Do it only once.
            download_all = False

        # Pull out just the list of activities.
        activities = json_results['results']['activities']

        # Process each activity.
        for a in activities:
            A = a['activity']

            # Display which entry we're working on.
            info = {
                "id": A['activityId'],
                "name": A['activityName']['value'],
                "timestamp": A['beginTimestamp']['display'],
                "duration": "??:??:??",
                "distance": "0.00 Miles"
            }

            if "sumElapsedDuration" in A:
                info["duration"] = A["sumElapsedDuration"]["display"]

            if "sumDistance" in A:
                info["distance"] = A["sumDistance"]["withUnit"]

            logging.info("Garmin Connect activity: [{id}] {name}\n"
                         "\t{timestamp}, {duration}, {distance}"
                         .format(**info))

            if args.format == 'gpx':
                data_filename = "activity_{}.gpx".format(info["id"])
                download_url = "{}{}?full=true".format(url_gc_gpx_activity,
                                                       info["id"])
                file_mode = 'w'

            elif args.format == 'tcx':
                data_filename = "activity_{}.tcx".format(info["id"])

                download_url = "{}{}?full=true".format(url_gc_tcx_activity,
                                                       info["id"])
                file_mode = 'w'

            elif args.format == 'original':
                data_filename = "activity_{}.zip".format(info["id"])

                fit_filename = '{}.fit'.format(info["id"])

                download_url = "{}{}".format(
                    url_gc_original_activity, info["id"])
                file_mode = 'wb'

            else:
                raise Exception('Unrecognized format.')

            if os.path.isfile(data_filename):
                logging.info('%s already exists; skipping...', data_filename)
                continue

            # Regardless of unzip setting, don't redownload if the ZIP or FIT file
            # exists.
            if args.format == 'original' and os.path.isfile(fit_filename):
                logging.info('%s already exists; skipping...', data_filename)
                continue

            # Download the data file from Garmin Connect.
            # If the download fails (e.g., due to timeout), this script will
            # die, but nothing will have been written to disk about this
            # activity, so just running it again should pick up where it left
            # off.
            logging.info('Downloading activity...')

            try:
                empty_file = False
                file_response = sesh.get(download_url)

            except requests.HTTPError as e:

                # Handle expected (though unfortunate) error codes; die on
                # unexpected ones.
                if e.code == 500 and args.format == 'tcx':
                    # Garmin will give an internal server error (HTTP 500) when
                    # downloading TCX files if the original was a manual GPX
                    # upload. Writing an empty file prevents this file from
                    # being redownloaded, similar to the way GPX files are
                    # saved even when there are no tracks. One could be
                    # generated here, but that's a bit much. Use the GPX format
                    # if you want actual data in every file, as I believe
                    # Garmin provides a GPX file for every activity.
                    logging.info("Writing empty file since Garmin did not"
                                 " generate a TCX file for this activity...")
                    empty_file = True

                elif e.code == 404 and args.format == 'original':
                    # For manual activities (i.e., entered in online without a
                    # file upload), there is no original file.
                    # Write an empty file to prevent redownloading it.
                    logging.info("Writing empty file since there"
                                 " was no original activity data...")
                    empty_file = True
                else:
                    raise Exception(
                        'Failed. Got an unexpected HTTP error ({}).'
                        .format(str(e.code))
                    )

            if empty_file:
                data = ""
            elif "b" in file_mode:
                # if response contains binary data, i.e. file_mode is "wb"
                data = file_response.content
            else:
                # otherwise data is (auto-detected, most likely utf8)
                # encoded text
                data = file_response.text

            file_path = args.directory + "/" + data_filename
            with open(file_path, file_mode) as save_file:
                save_file.write(data)

            total_downloaded += num_to_download

            if args.format == 'gpx':
                # Validate GPX data. If we have an activity without GPS data
                # (e.g., running on a treadmill), Garmin Connect still kicks
                # out a GPX, but there is only activity information,
                # no GPS data. N.B. You can omit the XML parse
                # (and the associated log messages) to speed things up.
                gpx = parseString(data)
                gpx_data_exists = len(gpx.getElementsByTagName('trkpt')) > 0

                if gpx_data_exists:
                    logging.info('Done. GPX data saved.')
                else:
                    logging.info('Done. No track points found.')
            elif args.format == 'original':
                # Even manual upload of a GPX file is zipped, but we'll
                # validate the extension.
                if args.unzip and file_path[-3:].lower() == 'zip':
                    logging.info("Unzipping and removing original files...")
                    zip_file = open(file_path, 'rb')
                    z = zipfile.ZipFile(zip_file)
                    for name in z.namelist():
                        z.extract(name, args.directory)
                    zip_file.close()
                    os.remove(file_path)

            if not empty_file:
                # Write stats to CSV.
                empty_record = '"",'

                csv_record = ''

                def field_format(key1, key2=None):
                    if key2:
                        return (empty_record if key1 not in A
                                else '"' + A[key1][key2].replace('"', '""') +
                                '",')
                    else:
                        return (empty_record if key1 not in A
                                else '"' + A[key1].replace('"', '""') + '",')

                csv_record += field_format('activityId')
                csv_record += field_format('activityName', 'value')
                csv_record += field_format('activityDescription', 'value')
                csv_record += field_format('beginTimestamp', 'display')
                csv_record += field_format('beginTimestamp', 'millis')
                csv_record += field_format('endTimestamp', 'display')
                csv_record += field_format('endTimestamp', 'millis')

                csv_record += (empty_record if 'device' not in A
                               else '"' +
                               A['device']['display'].replace('"', '""') +
                               ' ' +
                               A['device']['version'].replace('"', '""') +
                               '",')

                csv_record += (empty_record if 'activityType' not in A
                               else '"' +
                               A['activityType']['parent']['display']
                               .replace('"', '""') + '",')

                csv_record += field_format('activityType', 'display')
                csv_record += field_format('eventType', 'display')
                csv_record += field_format('activityTimeZone', 'display')
                csv_record += field_format('maxElevation', 'withUnit')
                csv_record += field_format('maxElevation', 'value')
                csv_record += field_format('beginLatitude', 'value')
                csv_record += field_format('beginLongitude', 'value')
                csv_record += field_format('endLatitude', 'value')
                csv_record += field_format('endLongitude', 'value')

                # The units vary between Minutes per Mile and mph, but withUnit
                # always displays "Minutes per Mile"
                csv_record += field_format('weightedMeanMovingSpeed', 'display')
                csv_record += field_format('weightedMeanMovingSpeed', 'value')
                csv_record += field_format('maxHeartRate', 'display')

                csv_record += field_format('weightedMeanHeartRate', 'display')

                # The units vary between Minutes per Mile and mph, but withUnit
                # always displays "Minutes per Mile"
                csv_record += field_format('maxSpeed', 'display')

                csv_record += field_format('sumEnergy', 'display')
                csv_record += field_format('sumEnergy', 'value')
                csv_record += field_format('sumElapsedDuration', 'display')
                csv_record += field_format('sumElapsedDuration', 'value')
                csv_record += field_format('sumMovingDuration', 'display')
                csv_record += field_format('sumMovingDuration', 'value')
                csv_record += field_format('weightedMeanSpeed', 'withUnit')
                csv_record += field_format('weightedMeanSpeed', 'value')
                csv_record += field_format('sumDistance', 'withUnit')
                csv_record += field_format('sumDistance', 'value')
                csv_record += field_format('minHeartRate', 'display')
                csv_record += field_format('maxElevation', 'withUnit')
                csv_record += field_format('maxElevation', 'value')
                csv_record += field_format('gainElevation', 'withUnit')
                csv_record += field_format('gainElevation', 'value')
                csv_record += field_format('lossElevation', 'withUnit')
                csv_record += field_format('lossElevation', 'value')
                csv_record += '\n'

                csv_file.write(csv_record)
    # End while loop for multiple chunks.
    logging.info("Chunk done!")
logging.info('Done!')
