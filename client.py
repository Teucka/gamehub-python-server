from packetsyntax import *
from gamestates import *
from request import *
import socket #error
import struct

class Client(object):
    clientHandle = None
        
    # Connection information
    pingThread = None
    ping = 999
    lastPingData = b''
    lastPingTime = 0
    address = None
    currentRequest = None
    lastHandledRequestID = -1
    disconnected = False
    
    # Identification details
    name = ''
    
    # Game related information
    currentGame = GM_NONE
    currentGameID = -1
    gameStatus = ST_IDLE


    def __init__(self, clientHandle, address, name):
        print('%s connected on port %d' % (address[0], address[1]))
        self.clientHandle = clientHandle
        self.address = address
        self.name = name
        self.currentRequest = Request()
        
        
    def sendPacket(self, headerByte1, headerByte2 = b'', dataString = ''):
        if self.isDisconnected():
            return False
        
        dataToSend = b''
        dataBytes = b''
        
        try:
            if type(dataString) is str:
                dataBytes = dataString.encode('utf-8')
            elif type(dataString) is bytes:
                dataBytes = dataString
            else:
                dataBytes = str(dataString).encode('utf-8')
        except UnicodeEncodeError as e:
            print('Failed to encode sendPacket data: ' + str(e))
            return True
            
        dataToSend = headerByte1 + headerByte2 + dataBytes + SX_EOR
            
        if self.clientHandle is not None:
            try:
                print('Sending: %s' % dataToSend.decode('utf-8'))
            except UnicodeDecodeError as e:
                print('Sending data.')
                pass
                
            try:
                sent = self.clientHandle.send(dataToSend)
                if sent == 0:
                    print('Can\'t send data to client.')
                    return False
            except Exception as e:
                print('Can\'t send data to client: %s' % e)
                return False
        return True
    
    
    def disconnect(self):
        self.disconnected = True
        
        
    def isDisconnected(self):
        return self.disconnected