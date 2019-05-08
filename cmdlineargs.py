import argparse
from datetime import datetime
def get_args():
    current_date = datetime.now().strftime('%Y-%m-%d')
    activities_directory = './' + current_date + '_garmin_connect_export'
    parser = argparse.ArgumentParser()

    parser.add_argument(
        '--quiet',
        help="stifle all output",
        action="store_true"
    )
    parser.add_argument(
        '--debug',
        help="lots of console output",
        action="store_true"
    )
    parser.add_argument(
        '--version',
        help="print version and exit",
        action="store_true"
    )
    parser.add_argument(
        '--username',
        help="your Garmin Connect username (otherwise, you will be prompted)",
        nargs='?'
    )
    parser.add_argument(
        '--password',
        help="your Garmin Connect password (otherwise, you will be prompted)",
        nargs='?'
    )

    parser.add_argument(
        '-c',
        '--count',
        nargs='?',
        default="1",
        help="number of recent activities to download (default: 1)"
    )

    parser.add_argument(
        '-d',
        '--directory',
        nargs='?',
        default=activities_directory,
        help="save directory (default: './YYYY-MM-DD_garmin_connect_export')"
    )

    args = parser.parse_args()
    return args


