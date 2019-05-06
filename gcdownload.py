from gclogin import GarminLogin
from properties import Properties
from deviceinfo import DeviceInfo

gcl = GarminLogin()
session = gcl._get_session(email='aaronferrucci', password='Adh0r3w38x4k1u8Z')

deviceinfo = DeviceInfo(session)
print("\nDevices:")
deviceinfo.do_print()

print("\nProperties:")
props = Properties(session, "activity_type_")
props.do_print()

# http_data = session.get(propUrl, allow_redirects=False)
# for line in http_data.iter_lines():
#     (key, value) = line.split('=')
#     print("%s=%s" % (key, value))
# 
