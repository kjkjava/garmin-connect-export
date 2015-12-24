# -*- coding: utf-8 -*-
"""
Created on Sun Oct 25 09:48:32 2015

@author: Maxim
"""
from datetime import datetime
import re

class ActivityJSON(object):
    """
    Handles for the dictionary representation of the json activity.
    Initialize with: activity = ActivityJSON( json_dict )
    Then selected details can be retrieved with: activity.get...
    """
    
    def __init__( self, json_dict ):
        self.json_dict = json_dict

    def getID( self ):
        return self.json_dict['activityId']

    def getName( self ):
        return self.json_dict['activityName']['value']
        
    def getCategory( self ):
        """ The 'general' type of an activity, disregarding the subtype. e.g. running, cycling, swimming, hiking... """
        return self.json_dict['activityType']['type']['key']
    
    def isRun( self ):
        if self.getCategory() == 'running':
            return True
        else:
            return False
    
    def getDistance( self ):
        parent = self.json_dict['sumDistance']
        
        distance = float( parent['value'] )
        unit = parent['uom']
        if unit != 'kilometer':
            raise Exception("Distance has the wrong unit: '%s'" % unit)
        
        return distance
    
    def getDuration( self ):
        parent = self.json_dict['sumMovingDuration'] 
    
        time = float( parent['value'] )
        unit = parent['uom']
        if unit != 'second':
            raise Exception("Time has the wrong unit: '%s'" % unit)
        
        return time
        
    def getComment( self ):
        return self.json_dict['activityDescription']['value'] #TODO remove end of lines
        
    def getDate( self ):
        """ Returns datetime object """
        #NOTE: date also available in milliseconds ('millis', UTC)
        date_yyyymmdd = self.json_dict['beginTimestamp']['value']
        date = datetime.strptime(date_yyyymmdd,"%Y-%m-%d")
        return date
        
    def getStartTime( self ):
        """ Returns string 'hh:mm' """
        full_date = self.json_dict['beginTimestamp']['display'] # 'Thu, 2015 Oct 22 17:19'
        match = re.search( r'\d{2}:\d{2}', full_date ) # Get the time hh:mm
        return match.group()
        
    def getBpmMax( self ):
        if 'maxHeartRate' in self.json_dict:
            parent = self.json_dict['maxHeartRate']
            return float( parent['value'] ) #Assume uom is always bpm
        else:
            return None
    
    def getBpmAvg( self ):
        if 'weightedMeanHeartRate' in self.json_dict:
            parent = self.json_dict['weightedMeanHeartRate']
            return float( parent['value'] ) #Assume uom is always bpm
        else:
            return None
            
    def getLatitude( self ):
        if 'beginLatitude' in self.json_dict:
            parent = self.json_dict['beginLatitude']
            return float( parent['value'] ) #Always in decimal degrees
        else:
            return None
    
    def getLongitude( self ):
        if 'beginLongitude' in self.json_dict:
            parent = self.json_dict['beginLongitude']
            return float( parent['value'] ) #Always in decimal degrees
        else:
            return None   
    
    
    