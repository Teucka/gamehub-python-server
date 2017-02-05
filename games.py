import threading
from game import TexasHoldEmGame
from gamestates import *

class Games(object):
    games = []
    nextGameID = 0
    
    
    def createGame(self, gameType, playerClients):
        print('Creating a new game.')
        if gameType == GM_HOLDEM:
            game = TexasHoldEmGame(self.nextGameID)
        game.addPlayers(playerClients)
        self.games.append(game)
        threading.Thread(target = game.startGame,args = ()).start()
        self.nextGameID += 1
        
        
    def findGame(self, gameType):
        bestNumOfPlayers = -1
        bestGame = None
        for g in self.games:
            if g.gameType == GM_HOLDEM:
                numOfPlayers = len(g.players)
                if numOfPlayers > bestNumOfPlayers and numOfPlayers < g.maxPlayers:
                    bestGame = g
                    bestNumOfPlayers = numOfPlayers
        return bestGame
        
        
    def deliverGameData(self, gameID, clientClass, data):
        for g in self.games:
            if g.gameID == gameID:
                g.handleData(clientClass, data)
                break
            
            
    def closeGame(self, game):
        game.gameState = GMST_ENDED
        for p in game.getAllPlayers():
            p.currentGameID = -1
            p.currentGame = GM_NONE
            p.gameStatus = ST_IDLE
        self.games.remove(game)
            
            
    def playerDisconnect(self, clientClass):
        if clientClass.currentGameID != -1:
            for g in self.games:
                if g.gameID == clientClass.currentGameID:
                    g.handleDisconnect(clientClass)
                    if g.currentlyInGame() == 0:
                        print('Not enough players. Closing the game.')
                        self.closeGame(g)
                    break