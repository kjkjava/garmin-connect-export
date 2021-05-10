import json
class DeviceInfo():
  devices_url = "https://connect.garmin.com/modern/proxy/device-service/deviceregistration/devices"
  keys = [
    'currentFirmwareVersion',
    'displayName',
    'partNumber',
    'serialNumber',
  ]

  def __init__(self, session):
    self.session = session
    http_data = session.get(DeviceInfo.devices_url, allow_redirects=False)
    if http_data.status_code != 200:
        print("DeviceInfo error code: %d" % (http_data.status_code))
        self.devices = None
        return

    devices = json.loads(http_data.text)
    self.device_info = {}
    for dev in devices:
      dev_id = dev['deviceId']
      this_device = {}
      for key in DeviceInfo.keys:
        this_device[key] = dev.get(key, None)
      self.device_info[dev_id] = this_device

    # backward compatibility hack: prepend ' ', append ".0.0"
    # to firmware version.
    for dev_id in self.device_info:
      fw = self.device_info[dev_id]['currentFirmwareVersion']
      fw = ' ' + fw + ".0.0"
      self.device_info[dev_id]['currentFirmwareVersion'] = fw

  def do_print(self):
    for dev_id in self.device_info:
      print(dev_id)
      for dev_parameter in self.device_info[dev_id]:
        print("    " + dev_parameter + ": " + self.device_info[dev_id][dev_parameter])

  def displayName(self, deviceId):
    try:
      device = self.device_info[deviceId]['displayName']
    except KeyError:
      device = ""

    try:
      version = self.device_info[deviceId]['currentFirmwareVersion']
    except KeyError:
      version = ""

    displayName = device + ' ' + version
    return displayName


