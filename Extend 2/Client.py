from tkinter import *
import tkinter.messagebox
from PIL import Image, ImageTk
import socket, threading, sys, traceback, os
import time
from RtpPacket import RtpPacket

CACHE_FILE_NAME = "cache-"
CACHE_FILE_EXT = ".jpg"

class Client:
	INIT = 0
	READY = 1
	PLAYING = 2
	state = INIT

	SETUP = 0
	PLAY = 1
	PAUSE = 2
	TEARDOWN = 3
	check = False
	counter = 0
	# Initiation..
	def __init__(self, master, serveraddr, serverport, rtpport, filename):
		self.master = master
		self.master.protocol("WM_DELETE_WINDOW", self.handler)
		self.createWidgets()
		self.serverAddr = serveraddr
		self.serverPort = int(serverport)
		self.rtpPort = int(rtpport)
		self.fileName = filename
		self.rtspSeq = 0
		self.sessionId = 0
		self.requestSent = -1
		self.teardownAcked = 0
		self.connectToServer()
		self.frameNbr = 0
		self.rtpSocket = socket.socket(socket.AF_INET,socket.SOCK_DGRAM)
		self.setupMovie()

	def createWidgets(self):
		"""Build GUI."""

		# Create Play button
		self.start = Button(self.master, width=20, padx=3, pady=3)
		self.start["text"] = "PLAY"
		self.start["command"] = self.playMovie
		self.start["activebackground"] = "red"
		self.start["fg"] = "green"
		self.start.grid(row=1, column=1, padx=2, pady=2)

		# Create Pause button
		self.pause = Button(self.master, width=20, padx=3, pady=3)
		self.pause["text"] = "PAUSE"
		self.pause["command"] = self.pauseMovie
		self.pause["activebackground"] = "red"
		self.pause["fg"] = "orange"
		self.pause.grid(row=1, column=2, padx=2, pady=2)

		# Create Teardown button
		self.teardown = Button(self.master, width=20, padx=3, pady=3)
		self.teardown["text"] = "STOP"
		self.teardown["command"] =  self.reset
		self.teardown["activebackground"] = "red"
		self.teardown.grid(row=1, column=3, padx=2, pady=2)

		# Create a label to display the movie
		self.label = Label(self.master, height=19)
		self.label.grid(row=0, column=0, columnspan=4, sticky=W+E+N+S, padx=5, pady=5)
	
	def reset(self):
		if self.check:
			self.pauseMovie()
			try: os.remove(CACHE_FILE_NAME + str(self.sessionId) + CACHE_FILE_EXT) # Delete the cache image from video
			except: pass
			time.sleep(1)
			self.state = self.INIT
			# self.master.protocol("WM_DELETE_WINDOW", self.handler)
			self.rtspSeq = 0
			self.sessionId = 0
			self.requestSent = -1
			self.teardownAcked = 0
			self.frameNbr = 0
			self.counter = 0
			self.check = False
			self.connectToServer()
			self.rtpSocket = socket.socket(socket.AF_INET,socket.SOCK_DGRAM)
			self.setupMovie()

	def setupMovie(self):
		"""Setup button handler."""
		if self.state == self.INIT:
			self.sendRtspRequest(self.SETUP)

	def exitClient(self):
		"""Teardown button handler."""
		self.sendRtspRequest(self.TEARDOWN)
		#self.handler()
		self.master.destroy() # Close the gui window
		try:
			os.remove(CACHE_FILE_NAME + str(self.sessionId) + CACHE_FILE_EXT) # Delete the cache image from video
		except:
			sys.exit(0)
		rate = float(self.counter/self.frameNbr)
		print('-'*60 + "\nRTP Packet Loss Rate :" + str(rate) +"\n" + '-'*60)
		sys.exit(0)

	def pauseMovie(self):
		"""Pause button handler."""
		if self.state == self.PLAYING:
			self.sendRtspRequest(self.PAUSE)

	def playMovie(self):
		"""Play button handler."""
		if self.state == self.READY:
			self.check = True
			# Create a new thread to listen for RTP packets
			print("Playing Movie")
			threading.Thread(target=self.listenRtp).start()
			self.playEvent = threading.Event()
			self.playEvent.clear()
			self.sendRtspRequest(self.PLAY)

	def listenRtp(self):
		while True:
			try:
				data = self.rtpSocket.recv(20480)
				if data:
					rtpPacket = RtpPacket()
					rtpPacket.decode(data)
					
					currFrameNbr = rtpPacket.seqNum()
					print("Current Seq Num: " + str(currFrameNbr))		
					if currFrameNbr > self.frameNbr: # Discard the late packet
						self.frameNbr = currFrameNbr
						self.updateMovie(self.writeFrame(rtpPacket.getPayload()))

			except:
				# Stop listening upon requesting PAUSE or TEARDOWN
				print("Didn't receive data!")
				if self.playEvent.isSet():
					break

				# Upon receiving ACK for TEARDOWN request,
				# close the RTP socket
				if self.teardownAcked == 1:
					self.rtpSocket.shutdown(socket.SHUT_RDWR)
					self.rtpSocket.close()
					break

	def writeFrame(self, data):
		"""Write the received frame to a temp image file. Return the image file."""

		cachename = CACHE_FILE_NAME + str(self.sessionId) + CACHE_FILE_EXT
		try:
			file = open(cachename, "wb")
		except:
			print("file open error")
		try:
			file.write(data)
		except:
			print("file write error")
		file.close()
		return cachename

	def updateMovie(self, imageFile):
		"""Update the image file as video frame in the GUI."""
		try:
			photo = ImageTk.PhotoImage(Image.open(imageFile)) #stuck here !!!!!!
		except:
			print("photo error")

		self.label.configure(image = photo, height=288)
		self.label.image = photo

	def connectToServer(self):
		"""Connect to the Server. Start a new RTSP/TCP session."""
		self.rtspSocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
		try:
			self.rtspSocket.connect((self.serverAddr, self.serverPort))
		except:
			tkinter.messagebox.showwarning('Connection Failed', 'Connection to \'%s\' failed.' %self.serverAddr)

	def sendRtspRequest(self, requestCode):
		"""Send RTSP request to the server."""
		#-------------
		# TO COMPLETE
		#-------------

		# Setup request
		if requestCode == self.SETUP and self.state == self.INIT:
			threading.Thread(target=self.recvRtspReply).start()
			# Update RTSP sequence number.
			# ...
			self.rtspSeq = 1

			# Write the RTSP request to be sent.
			# request = ...
			request = "SETUP " + str(self.fileName) + "\n" + str(self.rtspSeq) + "\n" + " RTSP/1.0 RTP/UDP " + str(self.rtpPort)

			self.rtspSocket.send(bytes(request, 'utf-8'))
			# Keep track of the sent request.
			# self.requestSent = ...
			self.requestSent = self.SETUP

		# Play request
		elif requestCode == self.PLAY and self.state == self.READY:
			# Update RTSP sequence number.
			# ...
			self.rtspSeq = self.rtspSeq + 1
			# Write the RTSP request to be sent.
			# request = ...
			request = "PLAY " + "\n" + str(self.rtspSeq)

			self.rtspSocket.send(bytes(request, 'utf-8'))
			print('-'*60 + "\nPLAY request sent to Server...\n" + '-'*60)
			# Keep track of the sent request.
			# self.requestSent = ...
			self.requestSent = self.PLAY

		# Pause request
		elif requestCode == self.PAUSE and self.state == self.PLAYING:
			# Update RTSP sequence number.
			# ...
			self.rtspSeq = self.rtspSeq + 1
			# Write the RTSP request to be sent.
			# request = ...
			request = "PAUSE " + "\n" + str(self.rtspSeq)
			self.rtspSocket.send(bytes(request, 'utf-8'))
			print('-'*60 + "\nPAUSE request sent to Server...\n" + '-'*60)
			# Keep track of the sent request.
			# self.requestSent = ...
			self.requestSent = self.PAUSE

		# Resume request


		# Teardown request
		elif requestCode == self.TEARDOWN and not self.state == self.INIT:
			# Update RTSP sequence number.
			# ...
			self.rtspSeq = self.rtspSeq + 1
			# Write the RTSP request to be sent.
			# request = ...
			request = "TEARDOWN " + "\n" + str(self.rtspSeq)
			self.rtspSocket.send(bytes(request, 'utf-8'))
			print('-'*60 + "\nTEARDOWN request sent to Server...\n" + '-'*60)
			# Keep track of the sent request.
			# self.requestSent = ...
			self.requestSent = self.TEARDOWN

		else:
			return

		# Send the RTSP request using rtspSocket.
		# ...

#		print '\nData sent:\n' + request

	def recvRtspReply(self):
		"""Receive RTSP reply from the server."""
		while True:
			reply = self.rtspSocket.recv(1024)
			if reply:
				self.parseRtspReply(reply.decode("utf-8"))
			# Close the RTSP socket upon requesting Teardown
			if self.requestSent == self.TEARDOWN:
				self.rtspSocket.shutdown(socket.SHUT_RDWR)
				self.rtspSocket.close()
				break

	def parseRtspReply(self, data):
		print("Parsing Received Rtsp data...")

		"""Parse the RTSP reply from the server."""
		lines = data.split('\n')
		seqNum = int(lines[1].split(' ')[1])

		# Process only if the server reply's sequence number is the same as the request's
		if seqNum == self.rtspSeq:
			session = int(lines[2].split(' ')[1])
			# New RTSP session ID
			if self.sessionId == 0:
				self.sessionId = session

			# Process only if the session ID is the same
			if self.sessionId == session:
				if int(lines[0].split(' ')[1]) == 200:
					if self.requestSent == self.SETUP:
						#-------------
						# TO COMPLETE
						#-------------
						# Update RTSP state.
						print("Updating RTSP state...")
						# self.state = ...
						self.state = self.READY
						# Open RTP port.
						#self.openRtpPort()
						print("Setting Up RtpPort for Video Stream")
						self.openRtpPort()

					elif self.requestSent == self.PLAY:
						 self.state = self.PLAYING
						 print('-'*60 + "\nClient is PLAYING...\n" + '-'*60)
					elif self.requestSent == self.PAUSE:
						 self.state = self.READY

						# The play thread exits. A new thread is created on resume.
						 self.playEvent.set()

					elif self.requestSent == self.TEARDOWN:
						# self.state = ...

						# Flag the teardownAcked to close the socket.
						self.teardownAcked = 1

	def openRtpPort(self):
		"""Open RTP socket binded to a specified port."""
		#-------------
		# TO COMPLETE
		#-------------
		# Create a new datagram socket to receive RTP packets from the server
		# self.rtpSocket = ...


		# Set the timeout value of the socket to 0.5sec
		# ...
		self.rtpSocket.settimeout(0.5)
#		try:
			# Bind the socket to the address using the RTP port given by the client user
			# ...
#		except:
#			tkMessageBox.showwarning('Unable to Bind', 'Unable to bind PORT=%d' %self.rtpPort)

		try:
			#self.rtpSocket.connect(self.serverAddr,self.rtpPort)
			self.rtpSocket.bind((self.serverAddr,self.rtpPort))   # WATCH OUT THE ADDRESS FORMAT!!!!!  rtpPort# should be bigger than 1024
			#self.rtpSocket.listen(5)
			print("Bind RtpPort Success")

		except:
			tkinter.messagebox.showwarning('Unable to Bind', 'Unable to bind PORT=%d' %self.rtpPort)


	def handler(self):
		"""Handler on explicitly closing the GUI window."""
		self.exitClient()