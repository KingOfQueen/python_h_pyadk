#!/usr/bin/env python2.6
"""\
Handbag device interface.
Copyright (C) Christian Unhold 2011, all rights reserved.
Implementing the protocol and based on code from the Handbag Arduino Library
by Follower, licensed under the LGPL Version 2.0,
avail. at http://http://www.labradoc.com/i/follower/p/android-arduino-handbag.
"""

import time, logging
import usb.core, usb.util
import android_accessory

class Handbag:
	def __init__(self, android_accessory):
		self.aa = android_accessory
		self.is_ui_setup = False
		self.log = logging.info

	def refresh(self):
		self.log("write(\"HB\\01\")")
		length = self.aa.write("HB\01")
		assert length == 3
		self.log("read(3)")
		data = self.aa.read(3)
		assert data == "HB\01"
		
if __name__ == "__main__":
	logging.root.setLevel(logging.INFO)
	global aa
	aa = android_accessory.open()
	if aa:
		try:
			handbag = Handbag(aa)
			time.sleep(1)
			handbag.refresh()
		except usb.core.USBError as e:
			logging.error(e)
	else:
		print "No device found."
