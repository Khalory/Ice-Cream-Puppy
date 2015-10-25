#!/usr/bin/env python
# -*- coding: utf-8 -*-
# 27 May 2015

###########################################################################
# Copyright (c) 2015 iRobot Corporation
# http://www.irobot.com/
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions
# are met:
#
#   Redistributions of source code must retain the above copyright
#   notice, this list of conditions and the following disclaimer.
#
#   Redistributions in binary form must reproduce the above copyright
#   notice, this list of conditions and the following disclaimer in
#   the documentation and/or other materials provided with the
#   distribution.
#
#   Neither the name of iRobot Corporation nor the names
#   of its contributors may be used to endorse or promote products
#   derived from this software without specific prior written
#   permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
# "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
# LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR
# A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT
# OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
# SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT
# LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
# DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY
# THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
# OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
###########################################################################

from Tkinter import *
import tkMessageBox
import tkSimpleDialog

from time import clock
import struct
import sys, glob # for listing serial ports
import win32pipe
import win32file

try:
	import serial
except ImportError:
	tkMessageBox.showerror('Import error', 'Please install pyserial.')
	raise

connection = None

TEXTWIDTH = 40 # window width, in characters
TEXTHEIGHT = 16 # window height, in lines

VELOCITYCHANGE = 200
ROTATIONCHANGE = 300

helpText = """\
Supported Keys:
P\tPassive
S\tSafe
F\tFull
C\tClean
D\tDock
R\tReset
Space\tBeep
Arrows\tMotion

If nothing happens after you connect, try pressing 'P' and then 'S' to get into safe mode.
"""

class TetheredDriveApp(Tk):
	# static variables for keyboard callback -- I know, this is icky
	callbackKeyUp = False
	callbackKeyDown = False
	callbackKeyLeft = False
	callbackKeyRight = False
	callbackKeyLastDriveCommand = ''
	
	commandMode = False

	def __init__(self):
		Tk.__init__(self)
		self.title("iRobot Create 2 Tethered Drive")
		self.option_add('*tearOff', FALSE)

		self.menubar = Menu()
		self.configure(menu=self.menubar)

		createMenu = Menu(self.menubar, tearoff=False)
		self.menubar.add_cascade(label="Create", menu=createMenu)

		createMenu.add_command(label="Connect", command=self.onConnect)
		createMenu.add_command(label="Help", command=self.onHelp)
		createMenu.add_command(label="Quit", command=self.onQuit)

		self.text = Text(self, height = TEXTHEIGHT, width = TEXTWIDTH, wrap = WORD)
		self.scroll = Scrollbar(self, command=self.text.yview)
		self.text.configure(yscrollcommand=self.scroll.set)
		self.text.pack(side=LEFT, fill=BOTH, expand=True)
		self.scroll.pack(side=RIGHT, fill=Y)

		self.text.insert(END, helpText)

		self.bind("<Key>", self.callbackKey)
		self.bind("<KeyRelease>", self.callbackKey)

	# sendCommandASCII takes a string of whitespace-separated, ASCII-encoded base 10 values to send
	def sendCommandASCII(self, command):
		cmd = ""
		for v in command.split():
			cmd += chr(int(v))

		self.sendCommandRaw(cmd)

	# sendCommandRaw takes a string interpreted as a byte array
	def sendCommandRaw(self, command):
		global connection

		try:
			if connection is not None:
				connection.write(command)
			else:
				tkMessageBox.showerror('Not connected!', 'Not connected to a robot!')
				print "Not connected."
		except serial.SerialException:
			print "Lost connection"
			tkMessageBox.showinfo('Uh-oh', "Lost connection to the robot!")
			connection = None

		print ' '.join([ str(ord(c)) for c in command ])
		self.text.insert(END, ' '.join([ str(ord(c)) for c in command ]))
		self.text.insert(END, '\n')
		self.text.see(END)

	# getDecodedBytes returns a n-byte value decoded using a format string.
	# Whether it blocks is based on how the connection was set up.
	def getDecodedBytes(self, n, fmt):
		global connection
		
		try:
			temp = struct.unpack(fmt, connection.read(n))
			print temp
			return temp[0]
		except serial.SerialException:
			print "Lost connection"
			tkMessageBox.showinfo('Uh-oh', "Lost connection to the robot!")
			connection = None
			return None
		except struct.error:
			print "Got unexpected data from serial port."
			return None

	# get8Unsigned returns an 8-bit unsigned value.
	def get8Unsigned(self):
		return getDecodedBytes(1, "B")

	# get8Signed returns an 8-bit signed value.
	def get8Signed(self):
		return getDecodedBytes(1, "b")

	# get16Unsigned returns a 16-bit unsigned value.
	def get16Unsigned(self):
		return getDecodedBytes(2, ">H")

	# get16Signed returns a 16-bit signed value.
	def get16Signed(self):
		return getDecodedBytes(2, ">h")

	# A handler for keyboard events. Feel free to add more!
	def callbackKey(self, event):
		k = event.keysym.upper()
		motionChange = False

		if event.type == '2': # KeyPress; need to figure out how to get constant
			if k == 'P':   # Passive
				self.sendCommandASCII('128')
			elif k == 'S': # Safe
				self.sendCommandASCII('131')
			elif k == 'F': # Full
				self.sendCommandASCII('132')
			elif k == 'C': # Clean
				self.sendCommandASCII('135')
			elif k == 'D': # Dock
				self.sendCommandASCII('143')
			elif k == 'SPACE': # Beep
				#self.ic1()
				self.mario1()
			elif k == 'R': # Reset
				self.sendCommandASCII('7')
			elif k == '8': # Special commands
				self.sendCommandASCII('149 3 43 44 20')
				self.getDecodedBytes(6, ">BBhhhh")
			elif k == 'UP':
				self.callbackKeyUp = True
				self.callbackKeyRight = False
				self.callbackKeyLeft = False
				motionChange = True
			elif k == 'DOWN':
				self.callbackKeyDown = True
				motionChange = True
			elif k == 'LEFT':
				self.callbackKeyLeft = True
				self.callbackKeyRight = False
				self.callbackKeyUp = False
				motionChange = True
			elif k == 'RIGHT':
				self.callbackKeyRight = True
				self.callbackKeyUp = False
				self.callbackKeyLeft = False
				motionChange = True
			else:
				pass#print repr(k), "not handled"
		elif event.type == '3': # KeyRelease; need to figure out how to get constant
			if k == 'UP':
				self.callbackKeyUp = False
				self.callbackKeyDown = False
				self.callbackKeyRight = False
				self.callbackKeyLeft = False
				motionChange = True
			elif k == 'DOWN':
				self.callbackKeyDown = False
				motionChange = True
			elif k == 'LEFT':
				self.callbackKeyLeft = False
				motionChange = True
			elif k == 'RIGHT':
				self.callbackKeyRight = False
				motionChange = True
			
		if motionChange == True:
			velocity = 0
			velocity += VELOCITYCHANGE if self.callbackKeyUp is True else 0
			velocity -= VELOCITYCHANGE if self.callbackKeyDown is True else 0
			rotation = 0
			rotation += ROTATIONCHANGE if self.callbackKeyLeft is True else 0
			rotation -= ROTATIONCHANGE if self.callbackKeyRight is True else 0

			# compute left and right wheel velocities
			vr = velocity + (rotation/2)
			vl = velocity - (rotation/2)

			# create drive command
			cmd = struct.pack(">Bhh", 145, vr, vl)
			if cmd != self.callbackKeyLastDriveCommand:
				self.sendCommandRaw(cmd)
				self.callbackKeyLastDriveCommand = cmd
			
	def ic1(self):
		self.sendCommandASCII('140 1 16 71 16 69 16 67 16 67 16 67 16 59 8 60 8 62 8 64 8 62 8 59 8 62 16 67 8 69 8 71 8 71 8 141 1')
		self.after(2750, self.ic2)
	def ic2(self):
		self.sendCommandASCII('140 1 16 71 8 71 8 71 16 67 8 69 8 71 8 69 8 69 8 68 8 69 16 71 8 69 8 67 8 69 8 67 8 69 8 141 1')
		self.after(2250, self.ic3)
	def ic3(self):
		self.sendCommandASCII('140 1 15 67 8 62 8 59 8 60 8 62 8 64 8 62 8 59 8 62 8 62 8 67 8 69 8 71 32 69 32 67 64 141 1')
		
	def mario1(self):
		self.sendCommandASCII('140 2 16 76 6 76 6 10 6 76 6 10 6 72 6 76 6 10 6 79 6 10 18 67 6 10 18 72 6 10 12 67 6 10 12 141 2')
		self.after(2062, self.mario2)
	def mario2(self):
		self.sendCommandASCII('140 2 16 64 6 10 12 69 6 10 6 71 6 10 6 70 6 68 6 10 6 67 8 76 8 79 8 81 6 10 6 77 6 79 6 141 2')
		self.after(1688, self.mario3)
	def mario3(self):
		self.sendCommandASCII('140 2 16 10 6 76 6 10 6 72 6 74 6 71 6 10 12 72 6 10 12 67 6 10 12 64 6 10 12 69 6 10 6 71 6 141 2')
		self.after(1876, self.mario4)
	def mario4(self):
		self.sendCommandASCII('140 2 16 10 6 70 6 69 6 10 6 67 8 76 8 79 8 81 6 10 6 77 6 79 6 10 6 76 6 10 6 72 6 74 6 141 2')
		self.after(1594, self.mario5)
	def mario5(self):
		self.sendCommandASCII('140 2 16 71 6 10 12 141 2')
		
#140 2 16 76 6 76 6 10 6 76 6 10 6 72 6 76 6 10 6 79 6 10 18 67 6 10 18 72 6 10 12 67 6 10 12 141 2
#140 2 16 64 6 10 12 69 6 10 6 71 6 10 6 70 6 68 6 10 6 67 8 76 8 79 8 81 6 10 6 77 6 79 6 141 2
#140 2 16 10 6 76 6 10 6 72 6 74 6 71 6 10 12 72 6 10 12 67 6 10 12 64 6 10 12 69 6 10 6 71 6 141 2
#140 2 16 10 6 70 6 69 6 10 6 67 8 76 8 79 8 81 6 10 6 77 6 79 6 10 6 76 6 10 6 72 6 74 6 141 2
#140 2 16 71 6 10 12 141 2
#[page 2 here]

	def onHelp(self):
		tkMessageBox.showinfo('Help', helpText)

	def onQuit(self):
		if tkMessageBox.askyesno('Really?', 'Are you sure you want to quit?'):
			self.destroy()

	def onConnect(self):
		global connection

		if connection is not None:
			print "Already connected..."
			return

		port = self.getSerialPorts()[0]

		if port is not None:
			print "Trying " + str(port) + "... "
			try:
				connection = serial.Serial(port, baudrate=115200, timeout=1)
				print "Connected!"
			except:
				print "Failed."

	def getSerialPorts(self):
		"""Lists serial ports
		From http://stackoverflow.com/questions/12090503/listing-available-com-ports-with-python

		:raises EnvironmentError:
			On unsupported or unknown platforms
		:returns:
			A list of available serial ports
		"""
		if sys.platform.startswith('win'):
			ports = ['COM' + str(i + 1) for i in range(256)]

		elif sys.platform.startswith('linux') or sys.platform.startswith('cygwin'):
			# this is to exclude your current terminal "/dev/tty"
			ports = glob.glob('/dev/tty[A-Za-z]*')

		elif sys.platform.startswith('darwin'):
			ports = glob.glob('/dev/tty.*')

		else:
			raise EnvironmentError('Unsupported platform')

		result = []
		for port in ports:
			try:
				s = serial.Serial(port)
				s.close()
				result.append(port)
			except (OSError, serial.SerialException):
				pass
		return result


		

class FakeEvent:
	keysym = ' '
	type = '1'

t = 0
app = None
#pose is one of {rest, fist, waveIn, waveOut, fingersSpread, doubleTap, unknown} 
def inReader():
	global t
	event = None
	line = raw_input()
	if line.split()[-1] == "doubleTap":
		if t + 1.0 < clock(): 
			app.commandMode = not app.commandMode
			t = clock()
	print app.commandMode
	if app.commandMode:
		event = controlModeFunc(line)
	else:
		event = commandModeFunc(line)
	app.after(10, inReader)
	app.callbackKey(event)

def controlModeFunc(line):
	data = line.split()
	pose = data[-1]
	arm = data[-2]
	event = FakeEvent()
	event.type = '2'
	if (pose == "rest"):
		if not app.callbackKeyUp:
			event.keysym = 'UP'
			event.type = '3'
	elif (pose == "fingersSpread"):
		event.keysym = 'UP'
	elif (pose == "fist"):
		event.keysym = 'UP'
		event.type = '3'
	elif (pose == "waveOut"):
		if (arm == 'R'):
			event.keysym = 'RIGHT'
		else:
			event.keysym = 'LEFT'
	elif (pose == "waveIn"):
		if (arm == 'R'):
			event.keysym = 'LEFT'
		else:
			event.keysym = 'RIGHT'
	return event
	
def commandModeFunc(line):
	data = line.split()
	pose = data[-1]
	arm = data[-2]
	event = FakeEvent()
	event.type = '2'
	if (pose == "rest"):
		if not app.callbackKeyUp:
			event.keysym = 'UP'
			event.type = '3'
	elif (pose == "fingersSpread"):
		event.keysym = 'DOWN'
	elif (pose == "fist"):
		event.keysym = 'UP'
		event.type = '3'
	elif (pose == "waveOut"):
		if (arm == 'L'):
			event.keysym = 'RIGHT'
		else:
			event.keysym = 'LEFT'
	elif (pose == "waveIn"):
		if (arm == 'L'):
			event.keysym = 'LEFT'
		else:
			event.keysym = 'RIGHT'
	return event

if __name__ == "__main__":
	app = TetheredDriveApp()
	app.after(10, inReader)
	app.after(10, app.onConnect)
	app.mainloop()
	#while True:
    #ball.draw()
    #tk.update_idletasks()
    #tk.update()

