import socket
import threading
import randomstring #generate
from time import sleep, time
from games import Games
from gamestates import *
from packetsyntax import *
from clients import Clients
from client import Client
from request import Request
import re #regular expression for parsing username
from serversettings import *

milliTime = lambda: int(round(time() * 1000))


class ThreadedServer(object):
	clients = None
	games = None
	
	sock = None
	port = 36936
	
	
	def __init__(self):
		self.clients = Clients()
		self.games = Games()
		self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
		self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
		self.sock.bind(('', self.port))
		print('Port %d: bind successful.' % self.port)


	def listen(self):
		print('Listening for clients.')
		threading.Thread(target = self.mainLoop, args = ()).start()
		self.sock.listen(1)
		while True:
			clientSocket, address = self.sock.accept()
			clientSocket.settimeout(60)
			clientClass = Client(clientSocket, address, "")

			threading.Thread(target = self.listenToClient, args = (clientClass,)).start()

			
	def mainLoop(self):
		while True:
			self.handleMatchmaking()
			sleep(1)


	def handleMatchmaking(self):
		searchers = self.clients.getAllSearching(GM_HOLDEM)
		if len(searchers) > 0:
			print('There is at least one client searching for Texas Hold \'Em!')
			for client in searchers:
				client.sendPacket(SX_SEARCH_OPPONENT, SX_OPPONENT_FOUND)
				client.gameStatus = ST_IN_GAME
			game = self.games.findGame(GM_HOLDEM)
			if game is None:
				threading.Thread(target = self.games.createGame, args = (GM_HOLDEM, searchers)).start()
			else:
				game.addPlayers(searchers)
				
			
	def pingClient(self, clientClass):
		while clientClass.pingThread is not None and not clientClass.isDisconnected():
			pingData = randomstring.generate()
			#print 'Sending a ping: %s' % pingData
			clientClass.lastPingData = pingData.encode('utf-8')
			if not clientClass.sendPacket(SX_PING, b'', pingData):
				self.disconnectClient(clientClass)
				break
			clientClass.lastPingTime = milliTime()
			sleep(PING_DELAY_SECONDS)
				

	def disconnectClient(self, clientClass):
		if clientClass is not None:
			clientClass.disconnect()
			clientClass.pingThread = None
			self.games.playerDisconnect(clientClass)
			self.clients.removeClient(clientClass)


	def listenToClient(self, clientClass):
		size = 256
		while True:
			try:
				message = clientClass.clientHandle.recv(size)
				if message != b'':
					# Received a message
					self.parseMessage(clientClass, message)
					message = None
					if clientClass.pingThread is None:
						clientClass.pingThread = threading.Thread(target = self.pingClient, args = (clientClass,))
						clientClass.pingThread.start()
				else:
					print('Client %s disconnected.' % clientClass.name)
					self.disconnectClient(clientClass)
					return False
			except Exception as e:
				print('Client %s disconnected: %s' % (clientClass.name, e))
				self.disconnectClient(clientClass)
				return False


	def parseMessage(self, clientClass, message):
		#print('Parsing a message: %s' % message)
		while 1:
			if not message or message == b'': # Finished parsing message
				#print('Finished parsing message')
				break
			
			firstByte = bytes([message[0]])
			
			if firstByte == SX_EOR: # End of a request
				#print('End of a request.')
				message = message[1:] # Remove first byte from message
				if self.handleRequest(clientClass) == -1:
					break
				
			elif clientClass.currentRequest.requestType == '':
				#print('Got a header: %s' % firstByte)
				clientClass.currentRequest.requestType = firstByte
				clientClass.currentRequest.requestID += 1
				message = message[1:] # Remove first byte from message
				
			elif clientClass.currentRequest.requestType != '': # Parse the data
				if SX_EOR not in message:
					#print('There is no end in this message')
					clientClass.currentRequest.data += message
					#print('Data now: ' + clientClass.currentRequest.data)
					message = ''
				else:
					#print('There is an end in this message')
					messageSplit = message.split(SX_EOR, 1)
					messageData = messageSplit[0]
					restOfTheMessage = messageSplit[1]
					clientClass.currentRequest.data += messageData
					message = SX_EOR + restOfTheMessage
					#print('Data now: ' + clientClass.currentRequest.data)
					#print('Message now: ' + message)
					

	def handleRequest(self, clientClass):
		print('Received: %s: %s' % (clientClass.currentRequest.requestType, clientClass.currentRequest.data))
		if clientClass.currentRequest.requestID == clientClass.lastHandledRequestID:
			print('Error: Request already handled!')
			return -1
			
		header = b''
		data = ''
		isError = False
			
		if clientClass.currentRequest.requestType == SX_HELLO: # A player connected
			#print('Got a hello!')
			header = SX_HELLO
			
			try:
				name = clientClass.currentRequest.data.decode("utf-8")
			except UnicodeDecodeError as e:
				print('Failed to decode player name: ' + str(e))
				data = SX_ERROR_INVALID_USERNAME
				isError = True
				pass
			
			if not isError:
				# Only allow most of the Latin letters
				# TODO: allow Cyrillic, Greek, Arabic, etc.?
				
				parsedName = " ".join(re.findall("[a-zA-Z0-9\u00C0-\u00F6\u00F8-\u01BF\u01C4-\u024F]+", name))
			
				if len(name) < NAME_LENGTH_MIN:
					print('Name %s is too short!' % name)
					data = SX_ERROR_USERNAME_TOO_SHORT
					isError = True
				elif len(name) > NAME_LENGTH_MAX:
					print('Name %s is too long!' % name)
					data = SX_ERROR_USERNAME_TOO_LONG
					isError = True
				else:
					if name == parsedName:
						clientClass.name = name 
						
						result = self.clients.addClient(clientClass)
						
						if result > 0:
							#print('Name set for client: %s' % clientClass.name)
							data = clientClass.name
						elif result == -1:
							#print('Name %s already exists!' % clientClass.name)
							data = SX_ERROR_NAME_TAKEN
							isError = True
						elif result == -2:
							#print('Client %s is already connected!' % self.address)
							data = SX_ERROR_ALREADY_CONNECTED
							isError = True
					else:
						print('Name %s is not a valid name!' % name)
						data = SX_ERROR_INVALID_USERNAME
						isError = True
				
				
		elif clientClass.currentRequest.requestType == SX_PING: # Ping
			#print('Received a Ping: %s Expected: %s' % (clientClass.currentRequest.data, clientClass.lastPingData))
			header = SX_PING_RESPONSE
			
			if clientClass.lastPingData == clientClass.currentRequest.data:
				clientClass.ping = milliTime() - clientClass.lastPingTime
				#print('Ping is: %d' % clientClass.ping)
				data = str(clientClass.ping)

		elif clientClass.currentRequest.requestType == SX_SEARCH_OPPONENT: # Search opponent
			#print('Received a search for opponent')
			header = SX_SEARCH_OPPONENT
			
			if clientClass.currentRequest.data != GM_NONE:
				if clientClass.gameStatus == ST_IN_GAME or clientClass.gameStatus == ST_PLAYING:
					print('Client %s is searching for a game (%d) but is already in a game.' % (clientClass.name, clientClass.currentGame))
					self.games.playerDisconnect(clientClass)
				clientClass.gameStatus = ST_SEARCHING
				clientClass.currentGame = ord(clientClass.currentRequest.data)
				data = SX_NOW_SEARCHING
				print('Client %s is now searching for a game (%d).' % (clientClass.name, clientClass.currentGame))
				print('Searchers: %d' % len(self.clients.getAllSearching(GM_HOLDEM)))
				
		elif clientClass.currentRequest.requestType == SX_GAME_INFO: # Game data
			#print('Received a game data')
			self.games.deliverGameData(clientClass.currentGameID, clientClass, clientClass.currentRequest.data)
			
		if header != b'' and not clientClass.sendPacket(header, b'', data) or isError:
			self.disconnectClient(clientClass)
			return -1
			
		clientClass.lastHandledRequestID = clientClass.currentRequest.requestID
		clientClass.currentRequest.reset()
		return 1



if __name__ == "__main__":
	ThreadedServer().listen()