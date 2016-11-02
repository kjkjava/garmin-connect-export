#!/usr/bin/python
# -*- coding: utf-8 -*-
"""
Created on Fri Oct 23 20:14:46 2015

@author: Maxim
"""
from urllib import urlencode #somehow not in the urllib2 package
import urllib2, cookielib, json, re
from ActivityJSON import ActivityJSON

class GarminHandler( object ):
    ## Global Constants
    # URLs for various services.
    URL_LOGIN      = 'https://sso.garmin.com/sso/login?service=https%3A%2F%2Fconnect.garmin.com%2Fpost-auth%2Flogin&webhost=olaxpw-connect04&source=https%3A%2F%2Fconnect.garmin.com%2Fen-US%2Fsignin&redirectAfterAccountLoginUrl=https%3A%2F%2Fconnect.garmin.com%2Fpost-auth%2Flogin&redirectAfterAccountCreationUrl=https%3A%2F%2Fconnect.garmin.com%2Fpost-auth%2Flogin&gauthHost=https%3A%2F%2Fsso.garmin.com%2Fsso&locale=en_US&id=gauth-widget&cssUrl=https%3A%2F%2Fstatic.garmincdn.com%2Fcom.garmin.connect%2Fui%2Fcss%2Fgauth-custom-v1.1-min.css&clientId=GarminConnect&rememberMeShown=true&rememberMeChecked=false&createAccountShown=true&openCreateAccount=false&usernameShown=false&displayNameShown=false&consumeServiceTicket=false&initialFocus=true&embedWidget=false&generateExtraServiceTicket=false'
    URL_POST_AUTH  = 'https://connect.garmin.com/post-auth/login?'
    URL_POST_AUTH2 = 'http://connect.garmin.com/modern'
    URL_POST_AUTH3 = 'https://connect.garmin.com/legacy/session'

    # Documentation API:
    # https://connect.garmin.com/proxy/activity-search-service-1.2/
    # https://connect.garmin.com/proxy/activity-service-1.3/
    URL_SEARCH    = 'http://connect.garmin.com/proxy/activity-search-service-1.2/json/activities?'
    URL_GPX_ACTIVITY = 'https://connect.garmin.com/modern/proxy/download-service/export/gpx/activity/%s'
    URL_TCX_ACTIVITY = 'https://connect.garmin.com/modern/proxy/download-service/export/tcx/activity/%s'
    URL_CSV_ACTIVITY = 'https://connect.garmin.com/modern/proxy/download-service/export/csv/activity/%s'
    URL_ZIP_ACTIVITY = 'https://connect.garmin.com/modern/proxy/download-service/files/activity/%s'

    # Maximum number of activities to request at once. 100 is the maximum set and enforced by Garmin
    JSON_DOWNLOAD_LIMIT = 100 # 10 is faster if few activities to retrieve.

    def __init__( self ):
        self.opener = None
        self.logged_in = False

    def login( self, username, password ):
        """ Returns True if logged in, raises error if not."""
        # Initially, we need to get a valid session cookie, so we pull the login page.
        cookie_jar = cookielib.CookieJar()
        self.opener = urllib2.build_opener( urllib2.HTTPCookieProcessor(cookie_jar) )
        http_req( self.opener, self.URL_LOGIN )

        # Now we'll actually login. Post data with Fields that are passed in a typical Garmin login.
        post_data = {'username': username, 'password': password,
                     'embed': 'true', 'lt': 'e1s1', '_eventId': 'submit', 'displayNameRequired': 'false'}
        http_req ( self.opener, self.URL_LOGIN, post_data )

        # Get the key.
        try:
            login_ticket = filter(lambda x: x.name == 'CASTGC', cookie_jar)[0].value
        except:
            raise Exception('Did not get a ticket cookie. Cannot log in. Did you enter the correct username and password?')

        # Post Authorize.
        login_response = self._postAuthorize( login_ticket )

        # Extra check that account name can be retrieved
        account_name = self._getAccountName(login_response)
        if not account_name:
            print ('Not logged in, post-authorization probably went wrong.')
            return False

        print( 'Logged in to account of %s' % account_name )
        self.logged_in = True

    def _postAuthorize( self, login_ticket ):
        # Post Authorize. Chop of 'TGT-' off the beginning, prepend 'ST-0'.
        login_ticket = 'ST-0' + login_ticket[4:]
        login_response = http_req( self.opener, self.URL_POST_AUTH + 'ticket=' + login_ticket )
        # Additional post-authorization 02-11-2016
        http_req( self.opener, self.URL_POST_AUTH2 )
        http_req( self.opener, self.URL_POST_AUTH3 )
        return login_response

    def _getAccountName( self, post_login_response ):
        res = re.search(r'fullName.+?:(.+?),', post_login_response)
        if not res:
            return False
        return res.group(1).strip( '\\"' )

    def activitiesGenerator( self, limit = None, reversed = False ):
        """ Yields the json as dict for every activity found,
            either from new to old or reversed. """

        if not self.logged_in:
            raise Exception('Please login first with .login(<username>,<password>)')

        # Prevent downloading too large chunks (saves time)
        if limit and limit < self.JSON_DOWNLOAD_LIMIT:
            max_chunk_size = limit
        else:
            max_chunk_size = self.JSON_DOWNLOAD_LIMIT

        # Determine index to start at
        if reversed:
            # Download one activity. Result will contain how many activities
            # there are in total
            url = self.URL_SEARCH + urlencode({'start': 0, 'limit': 1})
            result = http_req(self.opener, url )
            json_results = json.loads(result)
            n_activities = int( json_results['results']['search']['totalFound'])
            # Start
            start_index = n_activities - max_chunk_size
            if start_index < 0: #Negative index gives problems
                start_index = 0
        else:
            start_index = 0

        # Download data in multiple chunks of *max_chunk_size* activities
        total_downloaded = 0
        downloaded_chunk_size = max_chunk_size #initialize
        while downloaded_chunk_size >= max_chunk_size: # If downloaded chunk smaller, all activities are retrieved.
            # Query Garmin Connect
            search_params = {'start': start_index, 'limit': max_chunk_size}
            url = self.URL_SEARCH + urlencode(search_params)

            try:
                result = http_req(self.opener, url )
                json_results = json.loads(result)
            except urllib2.HTTPError as e:
                raise Exception('Failed to retrieve json of activities. (' + str(e) + ').')

            # Pull out just the list of activities.
            activities = json_results['results']['activities']
            downloaded_chunk_size = len(activities)

            if reversed:
                activities = activities[::-1] #reverse

            for activity in activities:
                activity_details = activity['activity']
                yield activity_details

                total_downloaded += 1
                # Stop if limit is reached
                if total_downloaded == limit:
                    raise StopIteration

            # Increment start index
            if reversed:
                if start_index - max_chunk_size < 0: # Negative start is not allowed
                    max_chunk_size = start_index # Next batch will be up to last start_index
                    start_index = 0
                else:
                    start_index -= max_chunk_size #Backwards
            else:
                start_index += max_chunk_size #Forwards

    def getNewRuns( self, existing_ids ):
        """ Iterate until an existing activiity is found.
            Returns list of new activities. """

        activities = self.activitiesGenerator()
        for activity_dict in activities:
            act = ActivityJSON( activity_dict )

            act_id = act.getID()
            if act_id in existing_ids:
                break

            if act.isRun():
                yield activity_dict

    def getFileByID( self, activity_id, fileformat = 'tcx' ):
        """ Downloads and returns data of given activity """

        if fileformat == 'tcx':
            download_url = self.URL_TCX_ACTIVITY % activity_id

        elif fileformat == 'gpx':
            download_url = self.URL_GPX_ACTIVITY % activity_id

        elif fileformat == 'original':
            download_url = self.URL_ZIP_ACTIVITY % activity_id

        elif fileformat == 'csv': #lap data
            download_url = self.URL_CSV_ACTIVITY % activity_id

        else:
            raise Exception('Unrecognized download file format. Supported: tcx,gpx,original and csv')

        # Download
        try:
            data = http_req( self.opener, download_url )
        except urllib2.HTTPError as e:
            # Handle expected (though unfortunate) error codes; die on unexpected ones.
            if e.code == 500:
                # Garmin will give an internal server error (HTTP 500) when downloading TCX files if the original was a manual GPX upload.
                # One could be generated here, but that's a bit much. Use the GPX format if you want actual data in every file, as I believe Garmin provides a GPX file for every activity.
                print 'Returning empty file since Garmin did not generate a TCX file for this activity...'
                data = ''
            elif e.code == 404:
                # For manual activities (i.e., entered in online without a file upload), there is no original file.
                # Write an empty file to prevent redownloading it.
                print 'Returning empty file since there was no original activity data...',
                data = ''
            else:
                raise Exception('Failed. Got an unexpected HTTP error (' + str(e.code) + ').')

        return data

## End of Class ##

## Tools ##
def http_req(opener, url, post=None, headers={}):
    """ url is a string, post is a dictionary of POST parameters, headers is a dictionary of headers. """
    request = urllib2.Request(url)
    request.add_header('User-Agent', 'Mozilla/5.0 (Windows NT 5.2; rv:2.0.1) Gecko/20100101 Firefox/4.0.1')  # Tell Garmin we're some supported browser.
    for header_key, header_value in headers.iteritems():
        request.add_header(header_key, header_value)
    if post:
        post = urlencode(post)  # Convert dictionary to POST parameter string.
    response = opener.open(request, data=post)  # This line may throw a urllib2.HTTPError.

    # N.B. urllib2 will follow any 302 redirects. Also, the "open" call above may throw a urllib2.HTTPError which is checked for below.
    if response.getcode() != 200:
        raise Exception('Bad return code (' + response.getcode() + ') for: ' + url)

    return response.read()
