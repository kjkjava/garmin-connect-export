import requests
import tempfile

HTTP_SOURCE_ADDR = '0.0.0.0'
class GarminLogin():
        _garmin_signin_headers = {
            "origin": "https://sso.garmin.com"
        }

        # To do: pull in sessioncache from tapiriik, or omit if that's possible
        # _sessionCache = SessionCache("garminconnect", lifetime=timedelta(minutes=120), freshen_on_get=True)

        def _rate_limit(self):
            import fcntl, struct, time
            min_period = 1  # I appear to been banned from Garmin Connect while determining this.
            fcntl.flock(self._rate_lock,fcntl.LOCK_EX)
            try:
                self._rate_lock.seek(0)
                last_req_start = self._rate_lock.read()
                if not last_req_start:
                    last_req_start = 0
                else:
                    last_req_start = float(last_req_start)

                wait_time = max(0, min_period - (time.time() - last_req_start))
                # print("_rate_limit: wait: '%s'; last_req_start: '%s'" % (wait_time, last_req_start))
                time.sleep(wait_time)

                self._rate_lock.seek(0)
                self._rate_lock.write(str(time.time()))
                self._rate_lock.flush()
            finally:
                fcntl.flock(self._rate_lock,fcntl.LOCK_UN)

        def __init__(self):
            rate_lock_path = tempfile.gettempdir() + "/gc_rate.%s.lock" % HTTP_SOURCE_ADDR
            # print("rate_lock_path: '%s'" % rate_lock_path)
            # Ensure the rate lock file exists (...the easy way)
            open(rate_lock_path, "a").close()
            self._rate_lock = open(rate_lock_path, "r+")

        def _get_session(self, email, password):

            session = requests.Session()

            # JSIG CAS, cool I guess.
            # Not quite OAuth though, so I'll continue to collect raw credentials.
            # Commented stuff left in case this ever breaks because of missing parameters...
            data = {
                "username": email,
                "password": password,
                "_eventId": "submit",
                "embed": "true",
                # "displayNameRequired": "false"
            }
            params = {
                "service": "https://connect.garmin.com/modern",
                # "redirectAfterAccountLoginUrl": "http://connect.garmin.com/modern",
                # "redirectAfterAccountCreationUrl": "http://connect.garmin.com/modern",
                # "webhost": "olaxpw-connect00.garmin.com",
                "clientId": "GarminConnect",
                "gauthHost": "https://sso.garmin.com/sso",
                # "rememberMeShown": "true",
                # "rememberMeChecked": "false",
                "consumeServiceTicket": "false",
                # "id": "gauth-widget",
                # "embedWidget": "false",
                # "cssUrl": "https://static.garmincdn.com/com.garmin.connect/ui/src-css/gauth-custom.css",
                # "source": "http://connect.garmin.com/en-US/signin",
                # "createAccountShown": "true",
                # "openCreateAccount": "false",
                # "usernameShown": "true",
                # "displayNameShown": "false",
                # "initialFocus": "true",
                # "locale": "en"
            }

            # I may never understand what motivates people to mangle a perfectly good protocol like HTTP in the ways they do...
            preResp = session.get("https://sso.garmin.com/sso/signin", params=params)
            if preResp.status_code != 200:
                raise APIException("SSO prestart error %s %s" % (preResp.status_code, preResp.text))

            ssoResp = session.post("https://sso.garmin.com/sso/signin", headers=self._garmin_signin_headers, params=params, data=data, allow_redirects=False)
            if ssoResp.status_code != 200 or "temporarily unavailable" in ssoResp.text:
                raise APIException("SSO error %s %s" % (ssoResp.status_code, ssoResp.text))

            if ">sendEvent('FAIL')" in ssoResp.text:
                raise APIException("Invalid login", block=True, user_exception=UserException(UserExceptionType.Authorization, intervention_required=True))
            if ">sendEvent('ACCOUNT_LOCKED')" in ssoResp.text:
                raise APIException("Account Locked", block=True, user_exception=UserException(UserExceptionType.Locked, intervention_required=True))

            if "renewPassword" in ssoResp.text:
                raise APIException("Reset password", block=True, user_exception=UserException(UserExceptionType.RenewPassword, intervention_required=True))

            # ...AND WE'RE NOT DONE YET!
            self._rate_limit()

            gcRedeemResp = session.get("https://connect.garmin.com/modern", allow_redirects=False)
            if gcRedeemResp.status_code != 302:
                raise APIException("GC redeem-start error %s %s" % (gcRedeemResp.status_code, gcRedeemResp.text))
            url_prefix = "https://connect.garmin.com"
            # There are 6 redirects that need to be followed to get the correct cookie
            # ... :(
            max_redirect_count = 7
            current_redirect_count = 1
            while True:
                self._rate_limit()
                url = gcRedeemResp.headers["location"]
                # Fix up relative redirects.
                if url.startswith("/"):
                    url = url_prefix + url
                url_prefix = "/".join(url.split("/")[:3])
                # print("url: '%s'" % url)
                gcRedeemResp = session.get(url, allow_redirects=False)

                if current_redirect_count >= max_redirect_count and gcRedeemResp.status_code != 200:
                    raise APIException("GC redeem %d/%d error %s %s" % (current_redirect_count, max_redirect_count, gcRedeemResp.status_code, gcRedeemResp.text))
                if gcRedeemResp.status_code == 200 or gcRedeemResp.status_code == 404:
                    break
                current_redirect_count += 1
                if current_redirect_count > max_redirect_count:
                    break

            # self._sessionCache.Set(record.ExternalID if record else email, session)
            # session.headers.update(self._obligatory_headers)

            return session

