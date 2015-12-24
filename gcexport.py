#!/usr/bin/python

"""
File: gcexport.py
Author: Kyle Krafka (https://github.com/kjkjava/)
Date: April 28, 2015

Description:	Use this script to export your fitness data from Garmin Connect.
				See README.md for more information.
"""

from urllib import urlencode
from datetime import datetime
from getpass import getpass
from sys import argv
from os.path import isdir
from os.path import isfile
from os import mkdir
from os import remove
from xml.dom.minidom import parseString

import urllib2, cookielib, json
from fileinput import filename

import argparse
import zipfile

from GarminHandler import GarminHandler
from ActivityJSON import ActivityJSON

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
	help="export format; can be 'gpx', 'tcx', or 'original' (default: 'gpx')")

parser.add_argument('-d', '--directory', nargs='?', default=activities_directory,
	help="the directory to export to (default: './YYYY-MM-DD_garmin_connect_export')")

parser.add_argument('-u', '--unzip',
	help="if downloading ZIP files (format: 'original'), unzip the file and removes the ZIP file",
	action="store_true")

parser.add_argument('-r', '--reverse',
	help="start with oldest activity (otherwise starts with newest)",
	action="store_true")
    
args = parser.parse_args()

if args.version:
	print argv[0] + ", version " + script_version
	exit(0)

# Convert the count to integer or empty if all.
if args.count == 'all': 
    total_to_download = None
else:
    total_to_download = int(args.count)

print 'Welcome to Garmin Connect Exporter!'

# Create directory for data files.
if isdir(args.directory):
	print 'Warning: Output directory already exists. Will skip already-downloaded files and append to the CSV file.'

username = args.username if args.username else raw_input('Username: ')
password = args.password if args.password else getpass()

# Login and initialize the handler. Raises exception if login failed.
garmin_handler = GarminHandler( username, password )

if not isdir(args.directory):
	mkdir(args.directory)

csv_filename = args.directory + '/activities.csv'
csv_existed = isfile(csv_filename)

csv_file = open(csv_filename, 'a')

# Write header to CSV file
if not csv_existed:
	csv_file.write('Activity ID,Activity Name,Description,Begin Timestamp,Begin Timestamp (Raw Milliseconds),End Timestamp,End Timestamp (Raw Milliseconds),Device,Activity Parent,Activity Type,Event Type,Activity Time Zone,Max. Elevation,Max. Elevation (Raw),Begin Latitude (Decimal Degrees Raw),Begin Longitude (Decimal Degrees Raw),End Latitude (Decimal Degrees Raw),End Longitude (Decimal Degrees Raw),Average Moving Speed,Average Moving Speed (Raw),Max. Heart Rate (bpm),Average Heart Rate (bpm),Max. Speed,Max. Speed (Raw),Calories,Calories (Raw),Duration (h:m:s),Duration (Raw Seconds),Moving Duration (h:m:s),Moving Duration (Raw Seconds),Average Speed,Average Speed (Raw),Distance,Distance (Raw),Max. Heart Rate (bpm),Min. Elevation,Min. Elevation (Raw),Elevation Gain,Elevation Gain (Raw),Elevation Loss,Elevation Loss (Raw)\n')

# Create generator for activities. Generates activities until specified number of activities are retrieved.
# Activity is a dictionary object of the json. (without the redundant first 'activity' key)
activities_generator = garmin_handler.activitiesGenerator( limit = total_to_download, reversed = args.reverse )

for a in activities_generator:
    # Display which entry we're working on.
    print 'Garmin Connect activity: [' + a['activityId'] + ']',
    print a['activityName']['value']
    print '\t' + a['beginTimestamp']['display'] + ',',
    if 'sumElapsedDuration' in a:
        print a['sumElapsedDuration']['display'] + ',',
    else:
        print '??:??:??,',
    if 'sumDistance' in a:
        print a['sumDistance']['withUnit']
    else:
        print '0.00 Miles'
    
    # Download the data file from Garmin Connect.
    # If the download fails (e.g., due to timeout), this script will die, but nothing
    # will have been written to disk about this activity, so just running it again
    # should pick up where it left off.
    print '\tDownloading file...'
    data = garmin_handler.getFileByID( a['activityId'], args.format )
    
    if args.format == 'original':
        data_filename = "%s/activity_%s.%s" % (args.directory, a['activityId'], 'zip')
        fit_filename = args.directory + '/' + a['activityId'] + '.fit'
        file_mode = 'wb'
    else:
        data_filename = "%s/activity_%s.%s" % (args.directory, a['activityId'], args.format)
        file_mode = 'w'

    if isfile(data_filename):
        print '\tData file already exists; skipping...'
        continue
    if args.format == 'original' and isfile(fit_filename):  # Regardless of unzip setting, don't redownload if the ZIP or FIT file exists.
        print '\tFIT data file already exists; skipping...'
        continue

    save_file = open(data_filename, file_mode)
    save_file.write(data)
    save_file.close()

    # Write stats to CSV.
    
    empty_record = '"",'

    csv_record = ''
    csv_record += empty_record if 'activityId' not in a else '"' + a['activityId'].replace('"', '""') + '",'
    csv_record += empty_record if 'activityName' not in a else '"' + a['activityName']['value'].replace('"', '""') + '",'
    csv_record += empty_record if 'activityDescription' not in a else '"' + a['activityDescription']['value'].replace('"', '""') + '",'
    csv_record += empty_record if 'beginTimestamp' not in a else '"' + a['beginTimestamp']['display'].replace('"', '""') + '",'
    csv_record += empty_record if 'beginTimestamp' not in a else '"' + a['beginTimestamp']['millis'].replace('"', '""') + '",'
    csv_record += empty_record if 'endTimestamp' not in a else '"' + a['endTimestamp']['display'].replace('"', '""') + '",'
    csv_record += empty_record if 'endTimestamp' not in a else '"' + a['endTimestamp']['millis'].replace('"', '""') + '",'
    csv_record += empty_record if 'device' not in a else '"' + a['device']['display'].replace('"', '""') + ' ' + a['device']['version'].replace('"', '""') + '",'
    csv_record += empty_record if 'activityType' not in a else '"' + a['activityType']['parent']['display'].replace('"', '""') + '",'
    csv_record += empty_record if 'activityType' not in a else '"' + a['activityType']['display'].replace('"', '""') + '",'
    csv_record += empty_record if 'eventType' not in a else '"' + a['eventType']['display'].replace('"', '""') + '",'
    csv_record += empty_record if 'activityTimeZone' not in a else '"' + a['activityTimeZone']['display'].replace('"', '""') + '",'
    csv_record += empty_record if 'maxElevation' not in a else '"' + a['maxElevation']['withUnit'].replace('"', '""') + '",'
    csv_record += empty_record if 'maxElevation' not in a else '"' + a['maxElevation']['value'].replace('"', '""') + '",'
    csv_record += empty_record if 'beginLatitude' not in a else '"' + a['beginLatitude']['value'].replace('"', '""') + '",'
    csv_record += empty_record if 'beginLongitude' not in a else '"' + a['beginLongitude']['value'].replace('"', '""') + '",'
    csv_record += empty_record if 'endLatitude' not in a else '"' + a['endLatitude']['value'].replace('"', '""') + '",'
    csv_record += empty_record if 'endLongitude' not in a else '"' + a['endLongitude']['value'].replace('"', '""') + '",'
    csv_record += empty_record if 'weightedMeanMovingSpeed' not in a else '"' + a['weightedMeanMovingSpeed']['display'].replace('"', '""') + '",'  # The units vary between Minutes per Mile and mph, but withUnit always displays "Minutes per Mile"
    csv_record += empty_record if 'weightedMeanMovingSpeed' not in a else '"' + a['weightedMeanMovingSpeed']['value'].replace('"', '""') + '",'
    csv_record += empty_record if 'maxHeartRate' not in a else '"' + a['maxHeartRate']['display'].replace('"', '""') + '",'
    csv_record += empty_record if 'weightedMeanHeartRate' not in a else '"' + a['weightedMeanHeartRate']['display'].replace('"', '""') + '",'
    csv_record += empty_record if 'maxSpeed' not in a else '"' + a['maxSpeed']['display'].replace('"', '""') + '",'  # The units vary between Minutes per Mile and mph, but withUnit always displays "Minutes per Mile"
    csv_record += empty_record if 'maxSpeed' not in a else '"' + a['maxSpeed']['value'].replace('"', '""') + '",'
    csv_record += empty_record if 'sumEnergy' not in a else '"' + a['sumEnergy']['display'].replace('"', '""') + '",'
    csv_record += empty_record if 'sumEnergy' not in a else '"' + a['sumEnergy']['value'].replace('"', '""') + '",'
    csv_record += empty_record if 'sumElapsedDuration' not in a else '"' + a['sumElapsedDuration']['display'].replace('"', '""') + '",'
    csv_record += empty_record if 'sumElapsedDuration' not in a else '"' + a['sumElapsedDuration']['value'].replace('"', '""') + '",'
    csv_record += empty_record if 'sumMovingDuration' not in a else '"' + a['sumMovingDuration']['display'].replace('"', '""') + '",'
    csv_record += empty_record if 'sumMovingDuration' not in a else '"' + a['sumMovingDuration']['value'].replace('"', '""') + '",'
    csv_record += empty_record if 'weightedMeanSpeed' not in a else '"' + a['weightedMeanSpeed']['withUnit'].replace('"', '""') + '",'
    csv_record += empty_record if 'weightedMeanSpeed' not in a else '"' + a['weightedMeanSpeed']['value'].replace('"', '""') + '",'
    csv_record += empty_record if 'sumDistance' not in a else '"' + a['sumDistance']['withUnit'].replace('"', '""') + '",'
    csv_record += empty_record if 'sumDistance' not in a else '"' + a['sumDistance']['value'].replace('"', '""') + '",'
    csv_record += empty_record if 'minHeartRate' not in a else '"' + a['minHeartRate']['display'].replace('"', '""') + '",'
    csv_record += empty_record if 'maxElevation' not in a else '"' + a['maxElevation']['withUnit'].replace('"', '""') + '",'
    csv_record += empty_record if 'maxElevation' not in a else '"' + a['maxElevation']['value'].replace('"', '""') + '",'
    csv_record += empty_record if 'gainElevation' not in a else '"' + a['gainElevation']['withUnit'].replace('"', '""') + '",'
    csv_record += empty_record if 'gainElevation' not in a else '"' + a['gainElevation']['value'].replace('"', '""') + '",'
    csv_record += empty_record if 'lossElevation' not in a else '"' + a['lossElevation']['withUnit'].replace('"', '""') + '",'
    csv_record += empty_record if 'lossElevation' not in a else '"' + a['lossElevation']['value'].replace('"', '""') + '"'
    csv_record += '\n'

    csv_file.write(csv_record.encode('utf8'))
    
    # TODO MM replace csv creation thing by:
    # activity_obj = ActivityJSON( activity_dict )
    # csv_record = "%s;%s;%s;%s;%s;%s;%s;%s;%s;%s;%s;%s" % (
            # activity_obj.getID(),
            # activity_obj.getName(),
            # activity_obj.getCategory(),
            # activity_obj.getDistance(),
            # activity_obj.getDuration(),
            # activity_obj.getComment(),
            # activity_obj.getDate(), #datetime object
            # activity_obj.getStartTime(),
            # activity_obj.getBpmMax(),
            # activity_obj.getBpmAvg(),
            # activity_obj.getLatitude(),
            # activity_obj.getLongitude()
        # )
    
    # TODO MM file validation?

    # Validate data. 24-12-2015: is this needed?
    if args.format == 'gpx':
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
        if args.unzip and data_filename[-3:].lower() == 'zip':  # Even manual upload of a GPX file is zipped, but we'll validate the extension.
            print "Unzipping and removing original files...",
            zip_file = open(data_filename, 'rb')
            z = zipfile.ZipFile(zip_file)
            for name in z.namelist():
                z.extract(name, args.directory)
            zip_file.close()
            remove(data_filename)
        print 'Done.'
    else:
        # TODO: Consider validating other formats.
        print 'Done.'
         
csv_file.close()

print 'Done!'
