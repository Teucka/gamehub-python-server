from packetsyntax import *
from games import *


class Clients(object):
    clients = []
    
    def containsName(self, name):
        if self.clients == None:
            return False
        for client in self.clients:
            if client.name == name:
                return True
        return False
    
    
    def containsHandle(self, handle):
        if self.clients == None:
            return False
        for c in self.clients:
            if c.clientHandle == handle:
                return True
        return False
    
    
    def addClient(self, client):
        if self.containsName(client.name):
            return -1
        if self.containsHandle(client.clientHandle):
            return -2
        self.clients.append(client)
        return 1
    
    
    def removeClient(self, client):
        client.clientHandle.close()
        if client in self.clients:
            self.clients.remove(client)
            print('Removed a client from clients. Clients still connected: %d' % len(self.clients))
            
            
    def getAllSearching(self, gameType):
        players = []
        for c in self.clients:
            if c.gameStatus == ST_SEARCHING and c.currentGame == gameType:
                players.append(c)
        return players
    
