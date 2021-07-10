def csvFormat(value):
  csv_record = '"' + str(value).replace('"', '""') + '",'
  return csv_record

# recursive dict get
def dictFind(data, keys):
  try:
    for key in keys:
      data = data[key]
  except KeyError:
    return ""
  return data

def activity_to_csv(results, a, devInfo, activity_type_info, event_type_info):
    empty_record = '"",'
    csv_record = ''
    # Activity ID
    activityId = str(a['activityId'])
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
    csv_record += csvFormat(devInfo.displayName(deviceId))

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

    return csv_record


