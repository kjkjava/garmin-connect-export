garmin-connect-export
=====================

Download a copy of your Garmin Connect data, including stats and GPX tracks.

Description
-----------
This script will backup your personal Garmin Connect data.
All downloaded data will go into a directory called `YYYY-MM-DD_garmin_connect_export/`,
either in the current working directory (by default) or wherever you specify.
Activity records and details will go into a CSV file called `activities.csv`.
GPX files (or, alternatively, TCX) containing track data, activity title,
and activity descriptions are saved as well, using the Activity ID.

If there is no GPS track data (e.g., due to an indoor treadmill workout),a data file is still saved.
If the GPX format is used, activity title and description data are saved.
For activities where a GPX file was uploaded, Garmin may not have a TCX file available for download,
so an empty file will be created.
Since GPX is the only format Garmin should have for every activity, it is the default and preferred download format.

If you have many activities, you may find that this script crashes with an "Operation timed out" message.
Just run the script again and it will pick up where it left off.

Usage
-----
You will need a little experience running things from the command line to use this script.
That said, here are the usage details from the `--help` flag:

```
usage: gcexport.py [-h] [--version] [--username [USERNAME]]
                   [--password [PASSWORD]] [-c [COUNT]]
                   [-f [{gpx,tcx,original}]] [-d [DIRECTORY]] [-u]

optional arguments:
  -h, --help            show this help message and exit
  --version             print version and exit
  --username [USERNAME]
                        your Garmin Connect username (otherwise, you will be
                        prompted)
  --password [PASSWORD]
                        your Garmin Connect password (otherwise, you will be
                        prompted)
  -c [COUNT], --count [COUNT]
                        number of recent activities to download, or 'all'
                        (default: 'all')
  -f [{gpx,tcx}], --format [{gpx,tcx}]
                        export format; can be 'gpx' or 'tcx'
                        (default: 'gpx')
  -d [DIRECTORY], --directory [DIRECTORY]
                        the directory to export to (default: './YYYY-MM-
                        DD_garmin_connect_export')
  -ot, --originaltime   will set downloaded file time to the activity start time
```

Examples:
`python gcexport.py --count all` will download all of your data to a dated directory.

`python gcexport.py -d ~/MyActivities -c 3 -f tcx -u --username bobbyjoe --password bestpasswordever1`
will download your three most recent activities in the TCX file format into the `~/MyActivities` directory
(unless they already exist).
Using the `--username` and `--password` flags is *not recommended*,
because your password will be stored in your command line history.
Instead, omit them to be prompted (and note that nothing will be displayed when you type your password).

Alternatively, you may run it with `./gcexport.py` if you set the file as executable (i.e., `chmod u+x gcexport.py`).

Of course, you must have Python installed to run this.
Most Mac and Linux users should already have it.
Note that this is a Python 3 fork of https://github.com/tobiaslj/garmin-connect-export;
if you only have Python 2 and don't wish to upgrade, you should use Tobias's version.
Note as well that this fork does not currently support downloads in the `original` file format that Tobias's does,
only GPX and TCX.


Data
----
This tool is not guaranteed to get all of your data, or even download it correctly.
It is not an official feature of Garmin Connect, and Garmin may very well make changes that break this utility.

Some information is missing, such as "Favorite" or "Avg Strokes."
This is available from the web interface, but is not included in data given to this script.

Also, be careful with speed data, because sometimes it is measured as a pace (minutes per mile)
and sometimes it is measured as a speed (miles per hour).

Garmin Connect API
------------------
This script is for personal use only. It simulates a standard user session (i.e., in the browser),
logging in using cookies and an authorization ticket.
This makes the script pretty brittle.
If you're looking for a more reliable option,
particularly if you wish to use this for some production service,
Garmin does offer a paid API service.

Contributions
-------------
Contributions are welcome, particularly if this script stops working with Garmin Connect.
You may consider opening a GitHub Issue first.
New features, however simple, are encouraged.

License
-------
[MIT](https://github.com/kjkjava/garmin-connect-export/blob/master/LICENSE) &copy; 2015 Kyle Krafka;
Python 3 refactor and updates by Jorge Aranda.

Thank You
---------
Thanks for using this script and I hope you find it as useful as I do! :smile:
