#!/usr/bin/env python2
"""
Android Open Accessory device interface.
Copyright (C) Christian Unhold 2011, all rights reserved.
Based on code from the Android ADK Release 0512,
copyright (C) 2011 The Android Open Source Project,
licensed under the Apache License, Version 2.0,
available at http://developer.android.com/guide/topics/usb/adk.html.
"""

import time, logging

import usb.core, usb.util
# PyUSB 1.0 from http://sourceforge.net/projects/pyusb/

USB_VENDOR_ID_GOOGLE = 0x18D1

ANDROID_DEVICE_IDS = {
	(USB_VENDOR_ID_GOOGLE, 0x4e11) : "HTC Nexus One",
	(USB_VENDOR_ID_GOOGLE, 0x4e12) : "HTC Nexus One ADB",	
	(USB_VENDOR_ID_GOOGLE, 0x4e21) : "Samsung Nexus S",
	(USB_VENDOR_ID_GOOGLE, 0x4e22) : "Samsung Nexus S ADB",	
	(0x04e8, 0x685c): "Samsung Galaxy Nexus",
	(0x04e8, 0x6860): "Samsung Galaxy Nexus ADB"}
	# Add your device here

ACCESSORY_PRODUCT_IDS = {
	0x2D00: "Accessory",
	0x2D01: "Accessory with ADB",
	0x2D04: "Accessory with Audio",
	0x2D05: "Accessory with Audio and ADB"}

AUDIO_PRODUCT_IDS = {
	0x2D02: "Audio",
	0x2D03: "Audio with ADB",
	0x2D04: "Accessory with Audio",
	0x2D05: "Accessory with Audio and ADB"}

STRING_MANUFACTURER = 0
STRING_MODEL = 1
STRING_DESCRIPTION = 2
STRING_VERSION = 3
STRING_URI = 4
STRING_SERIAL = 5

GET_PROTOCOL = 51
SEND_STRING = 52
START = 53
REGISTER_HID = 54
UNREGISTER_HID = 55
SET_HID_REPORT_DESC = 56
SEND_HID_EVENT = 57
SET_AUDIO_MODE = 58

STRINGS_ADK = {
	STRING_MANUFACTURER: "Google, Inc.",
	STRING_MODEL:        "DemoKit",
	STRING_DESCRIPTION:  "DemoKit Arduino Board",
	STRING_VERSION:      "1.0",
	STRING_URI:          "http://www.android.com",
	STRING_SERIAL:       "0000000012345678"}

STRINGS_HANDBAG = {
	STRING_MANUFACTURER: "rancidbacon.com",
	STRING_MODEL:        "Handbag",
	STRING_DESCRIPTION:  "Handbag (Arduino Board)",
	STRING_VERSION:      "0.1",
	STRING_URI:          "http://rancidbacon.com",
	STRING_SERIAL:       "0000000000000001"}

def is_android_device(device):
	return (device.idVendor, device.idProduct) in ANDROID_DEVICE_IDS

def is_accessory_device(device):
	return device.idVendor == USB_VENDOR_ID_GOOGLE and \
		device.idProduct in ACCESSORY_PRODUCT_IDS

class AndroidDevice:
	def __init__(self, device):
		assert device
		assert not is_accessory_device(device)
		self.device = device

	def get_protocol(self):
		rt = usb.util.build_request_type(usb.util.CTRL_IN,
			usb.util.CTRL_TYPE_VENDOR, usb.util.CTRL_RECIPIENT_DEVICE)
		data = self.device.ctrl_transfer(rt, GET_PROTOCOL, data_or_wLength=2)
		assert len(data) == 2
		self.protocol = data[0] + data[1]
		return self.protocol

	def send_string(self, index, string):
		rt = usb.util.build_request_type(usb.util.CTRL_OUT,
			usb.util.CTRL_TYPE_VENDOR, usb.util.CTRL_RECIPIENT_DEVICE)
		data = string + "\00"
		length = self.device.ctrl_transfer(rt, SEND_STRING, wIndex=index,
			data_or_wLength=data)
		assert length == len(data)

	def switch_device(self, strings, to_audio=False):
		assert strings or to_audio
		protocol = self.get_protocol()
		if protocol < 1:
			raise IOError("Android Accessory mode not supported")	
		if protocol < 2 and to_audio:
			raise IOError("Audio not supported")
		if strings:
			for index, string in strings.iteritems():
				self.send_string(index, string)
		rt = usb.util.build_request_type(usb.util.CTRL_OUT,
			usb.util.CTRL_TYPE_VENDOR, usb.util.CTRL_RECIPIENT_DEVICE)
		if to_audio:
			length = self.device.ctrl_transfer(rt, SET_AUDIO_MODE, 1)
			assert length == 0
		length = self.device.ctrl_transfer(rt, START)
		assert length == 0
		del self.device
		
	def switch_device_old(self, strings):
		self.protocol = protocol = self.get_protocol()
		if protocol < 1:
			raise IOError("Protocol version %d not supported" % (protocol,))
		for index, string in strings.iteritems():
			self.send_string(index, string)
		rt = usb.util.build_request_type(usb.util.CTRL_OUT,
			usb.util.CTRL_TYPE_VENDOR, usb.util.CTRL_RECIPIENT_DEVICE)
		length = self.device.ctrl_transfer(rt, START)
		assert length == 0
		del self.device

class AndroidAccessory:
	"""
	Android Open Accessory device interface.
	Use the function open() to find and setup a connected device.
	"""
	def __init__(self, device):
		assert device
		self.device = device

	def close(self):
		try: self.device.close()
		except AttributeError: pass

	def __enter__(self):
		return self

	def __exit__(self, exc_type, exc_value, traceback):
		self.close()

	def configure_android(self):
		assert is_accessory_device(self.device)
		self.configuration = self.device[0]
		self.configuration.set()
		self.interface = self.configuration[(0, 0)]
		assert self.interface.bNumEndpoints == 2
		for endpoint in self.interface:
			address = endpoint.bEndpointAddress
			if usb.util.endpoint_direction(address) == usb.util.ENDPOINT_IN:
				self.endpoint_in = endpoint
			else: # ENDPOINT_OUT
				self.endpoint_out = endpoint

	def read(self, length, timeout=None):
		return self.endpoint_in.read(length, timeout)

	def write(self, data, timeout=None):
		return self.endpoint_out.write(data, timeout)

def _get_first_device():
	logging.info("usb.core.find(custom_match=is_android_device)")
	device = usb.core.find(custom_match=is_android_device)
	if device:
		device_id = (device.idVendor, device.idProduct)
		description = ANDROID_DEVICE_IDS[device_id]
		logging.info("Device found: %s" % (description,))
	else:
		logging.info("No device found.")
	return device

def _get_first_accessory():
	logging.info("usb.core.find(custom_match=is_accessory_device)")
	device = usb.core.find(custom_match=is_accessory_device)
	if device:
		description = ACCESSORY_PRODUCT_IDS[device.idProduct]
		logging.info("Device found: %s" % (description,))
	else:
		logging.info("No device found.")
	return device

def open(strings):
	device = _get_first_accessory() or _get_first_device()
	if not device:
		logging.info("No device found")
		return None
	if not is_accessory_device(device):
		try:
			android_device = AndroidDevice(device)
			logging.info("Android device found")
			logging.info("android_device.switch_device(strings)")
			android_device.switch_device(strings)
			del android_device, device
			time.sleep(1)
		except Exception as e:
			logging.info(e)
			logging.info("switch_device() failed (vendor requests not supported?)")
			return None
		logging.info("Looking for switched device")
		device = _get_first_accessory()
		if not device:
			logging.info("Switched device not found")
			return None
	assert(is_accessory_device(device))
	logging.info("Android Accessory device found: %s" % (
		ACCESSORY_PRODUCT_IDS[device.idProduct],))
	android_accessory = AndroidAccessory(device)
	logging.info("android_accessory.configure_android()")
	android_accessory.configure_android()
	return android_accessory

def test_accessory():
	global aa
	aa = None
	print "Waiting for device..."
	for i in range(10):
		aa = open(STRINGS_HANDBAG)
		if aa: break
		time.sleep(1)
	if aa:
		print " Found."
		print "Check for popup!"
		print "Use instance \'aa\' to communicate with device."
	else:
		print " Timeout."
		print "No device found."

def test_audio():
	print "Waiting for device..."
	for i in range(10):
		device = _get_first_device()
		if device: break
		time.sleep(1)
	if device:
		print " Found."
		print "Enable audio..."
		android_device = AndroidDevice(device)
		android_device.switch_device(strings=STRINGS_HANDBAG, to_audio=True)
		del android_device, device
		time.sleep(1)
		print " Audio enabled."
	else:
		print " Timeout."
		print "No device found."

if __name__ == "__main__":
	logging.root.setLevel(logging.INFO)
	test_accessory()
