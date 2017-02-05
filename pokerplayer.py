from gamestates import *

class PokerPlayer(object):
    clientClass = None
    cards = []
    chips = 100
    totalBet = 0
    inSidePot = False
    
    currentRound = 0
    allIn = False
    folded = False
    waitForBigBlind = False
    
    chair = -1
        
    def __init__(self, clientClass):
        self.reset()
        self.clientClass = clientClass
        self.chips = 100
        
        
    def reset(self):
        self.cards = []
        self.totalBet = 0
        self.inSidePot = False
        self.currentRound = 0
        self.allIn = False
        self.folded = False

        
    def getName(self):
        if self.clientClass is not None:
            return self.clientClass.name
        return None
    
    
    def addCard(self, card):
        self.cards.append(card)
    
    
    def takeChips(self, amount):
        chipsTook = 0
        if self.chips <= amount:
            chipsTook = self.chips
            self.chips = 0
            self.allIn = True
            print('Player %s goes all in!' % self.clientClass.name)
        else:
            chipsTook = amount
            self.chips -= amount
            
        self.totalBet += chipsTook
            
        return chipsTook
        
        
    def sitOut(self):
        self.clientClass.gameStatus = ST_IN_GAME
        print('Player %s is sitting out (%d)!' % (self.clientClass.name, self.clientClass.gameStatus))
        
        
    def sitIn(self):
        self.clientClass.gameStatus = ST_PLAYING
        print('Player %s is sitting in (%d)!' % (self.clientClass.name, self.clientClass.gameStatus))
        
    
    def getCardsStr(self):
        string = ''
        for card in self.cards:
            string += str(card)
        return string