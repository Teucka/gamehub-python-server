from math import floor
from random import shuffle
from gamestates import *
from packetsyntax import *
from time import sleep, time
from hand import Hand
from card import Card
from pokerplayer import PokerPlayer
from timer import Timer
from sidepot import SidePot
from serversettings import *

class TexasHoldEmGame(object):
    gameID = -1
    gameType = GM_HOLDEM
    gameState = GMST_START
    
    players = []
    maxPlayers = 2
    spectatingPlayers = []
    lastAddedPlayer = None
    
    deck = []
    cardsOnTable = []
    
    defaultSmallBlind = 10
    smallBlindAmount = defaultSmallBlind
    bigBlindAmount = smallBlindAmount * 2
    dealerPlayerChair = -1
    smallBlindPlayerChair = -1
    bigBlindPlayerChair = -1
    dealerPlayer = None
    smallBlindPlayer = None
    bigBlindPlayer = None
    
    sidePots = []
    pot = 0
    roundMinBet = 0
    
    currentPlayerTurn = None
    lastPlayerTurn = None
    currentRound = 0
    lastRound = -1
    
    showedAllCards = False
    
    # Timers
    foldTimer = None
    foldTimerSeconds = 15 # How many seconds each turn lasts
    waitTimer = None
    waitTimerSeconds = 2 # How many seconds the server has to wait between showing new cards
    
    
    def __init__(self, gameID):
        self.gameID = gameID
        self.gameState = GMST_START
        self.players = []
        self.spectatingPlayers = []
        self.foldTimer = Timer(self.foldTimerSeconds)
        self.waitTimer = Timer(self.waitTimerSeconds)
        print('Created game with ID: %d' % self.gameID)
    
    
    def addPlayers(self, clientClasses):
        for c in clientClasses:
            self.addPlayer(c)
    
    
    def addPlayer(self, clientClass):
        clientClass.currentGameID = self.gameID
        clientClass.gameStatus = ST_IN_GAME
        
        player = PokerPlayer(clientClass)
        self.spectatingPlayers.append(player)
        self.announcePlayersChips([player], player) # Tell the player how many chips the player has
        self.announcePlayers(player) # Tell the player who is sitting at the table
        self.announcePlayersChips(self.players, player) # Tell the player how many chips sitting players have
        self.announcePlayersCardCounts(self.players, player) # Tell the player how many cards the sitting players have
        self.announceButtons(player) # Tell the player who is the dealer, the small blind and the big blind
        self.announceTurn(True, player) # Tell the player whose turn it is currently and how much time he has left to think
        
        
    def removePlayer(self, player):
        if player in self.players:
            self.players.remove(player)
            
            
    def removeSpectator(self, player):
        if player in self.spectatingPlayers:
            self.spectatingPlayers.remove(player)
            
            
    def findPlayer(self, clientClass):
        for p in self.getAllPlayers():
            if p.clientClass is clientClass:
                return p
        return None
        
        
    def getAllPlayers(self):
        return self.players + self.spectatingPlayers
        
        
    def sendToAll(self, headerByte, dataString = ''):
        for p in self.getAllPlayers():
            self.sendToPlayer(p, headerByte, dataString)
            
    
    def sendToAllBut(self, clientClassNotIncluded, headerByte, dataString = ''):
        for p in self.getAllPlayers():
            if p.clientClass is not clientClassNotIncluded:
                self.sendToPlayer(p, headerByte, dataString)
                
                
    def sendToPlayer(self, player, headerByte, dataString = '', disconnectOnFail = True):
        if player.clientClass.isDisconnected():
            return
        if not player.clientClass.sendPacket(SX_GAME_INFO, headerByte, dataString):
            print('Failed to send a packet to player %s.' % player.getName())
            self.handleDisconnect(player.clientClass)
        
        
    def handleDisconnect(self, clientClass):
        player = self.findPlayer(clientClass)
        if player is not None:
            print('Player %s disconnected from the game.' % player.getName())
            self.endGameForPlayer(player)
            self.sendToAllBut(clientClass, SX_GAME_DISCONNECT, player.getName())
            self.removePlayer(player)
            self.removeSpectator(player)
        
        
    def addSittingPlayer(self, player):
        # Remove player from spectators
        if player in self.spectatingPlayers:
            self.spectatingPlayers.remove(player)
            
        # Assign a free chair for the player
        chair = 0
        freeChair = False
        while not freeChair:
            freeChair = True
            for p in self.players:
                if p.chair == chair:
                    freeChair = False
                    chair += 1
                    break
        player.chair = chair
        
        # If there were at least two other players before the player, the player has to pay a big blind (when he gets to play)
        if len(self.players) > 1:
            player.waitForBigBlind = True
        
        # Add the player to active players
        self.players.append(player)
        
        # Change the player's status to ST_PLAYING
        player.sitIn()

        # Tell everyone there is a new player sitting at the table
        playersData = player.getName() + SXSTR_EOO + str(player.chair)
        self.sendToAll(SX_GAME_PLAYER_CHAIR, playersData)
        
        # Tell everyone how many chips this player has
        self.announcePlayersChips([player])
        
        
    def removeSittingPlayer(self, player):
        if player not in self.players:
            return
        
        # Change the player's status to ST_IN_GAME
        player.sitOut()

        # Tell everyone the player is no longer sitting at the table
        self.sendToAll(SX_GAME_PLAYER_SIT_OUT, player.getName())
        
        # Remove the player from active players and make the player a spectator
        self.removePlayer(player)
        self.spectatingPlayers.append(player)
            
        
    def endGameForPlayer(self, player):
        if player.clientClass.gameStatus == ST_PLAYING:
            if self.currentPlayerTurn is player:
                self.checkCallRaiseBetFold(player, 0, True)
            
            self.removeSittingPlayer(player)
        
        
    def handleData(self, clientClass, data):
        player = self.findPlayer(clientClass)
        if player is None:
            return
        
        dataByte = bytes([data[0]])
        
        if dataByte == SX_GAME_READY_TO_START:
            if len(self.players) >= self.maxPlayers:
                self.sendToPlayer(player, SX_GAME_TABLE_FULL)
            elif player not in self.players:
                if player.chips > 0:
                    print('Player %s now sits at the table.' % player.getName())
                else:
                    print('Player %s wants to sit at the table but does not have enough chips.' % player.getName())
                    player.chips = 100
                self.addSittingPlayer(player)
            
        elif dataByte == SX_GAME_BET:
            self.checkCallRaiseBetFold(player, int(data[1:]))
            
        elif dataByte == SX_GAME_FOLD:
            self.checkCallRaiseBetFold(player, 0, True)
            
        elif dataByte == SX_GAME_PLAYER_SIT_OUT:
            self.endGameForPlayer(player)
            
        elif dataByte == SX_GAME_CHAT_MESSAGE:
            self.sendChatMessage(player, data[1:])
            
        
    def sendChatMessage(self, sendingPlayer, message):
        try:
            decodedMessage = sendingPlayer.clientClass.currentRequest.data.decode("utf-8")
        except UnicodeDecodeError as e:
            print('Failed to decode a chat message from player %s: ' % (sendingPlayer.getName(), str(e)))
            return
        
        # Remove and replace newlines
        decodedMessage = decodedMessage.replace("\r", "")
        decodedMessage = decodedMessage.replace("\n", " ")
        
        decodedMessage = decodedMessage[:CHAT_MESSAGE_MAX_LENGTH]
        self.sendToAll(SX_GAME_CHAT_MESSAGE, sendingPlayer.getName() + SXSTR_EOO + decodedMessage)
        
        
    def checkCallRaiseBetFold(self, player, amount, fold = False):
        print('Player %s is trying to check, call, raise, bet or fold.' % player.getName())
        if self.currentPlayerTurn is not None:
            print('Current player turn: %s' % self.currentPlayerTurn.getName())
        else:
            print('But it is no one\'s turn!')
            return
        
        if self.currentPlayerTurn is player:
            messageAction = SX_GAME_BET
            if fold:
                print('Player %s folded.' % player.getName())
                player.folded = True
                messageAction = SX_GAME_FOLD
            else:
                if amount == 0:
                    if self.roundMinBet == player.totalBet:
                        print('Player %s is checking.' % player.getName())
                    else:
                        amount = self.roundMinBet - player.totalBet
                        if amount < player.chips:
                            print('Player %s is calling [%d].' % (player.getName(), amount))
                        else:
                            print('Player %s is going all in with a call [%d].' % (player.getName(), amount))
                else:
                    self.currentRound += 1
                    minBetRaiseAmount = (self.roundMinBet - player.totalBet) + self.bigBlindAmount
                    if amount < minBetRaiseAmount:
                        # Can't bet/raise less than the big blind amount unless the player is going All In
                        amount = min(minBetRaiseAmount, player.chips)
                        
                    if self.roundMinBet == player.totalBet:
                        if amount < player.chips:
                            print('Player %s is betting [%d].' % (player.getName(), amount))
                        else:
                            print('Player %s is going all in with a bet [%d].' % (player.getName(), amount))
                    else:
                        if amount < player.chips:
                            print('Player %s is raising [%d].' % (player.getName(), amount))
                        else:
                            print('Player %s is going all in with a raise [%d].' % (player.getName(), amount))

                self.pot += player.takeChips(amount)
                if self.roundMinBet < player.totalBet:
                    self.roundMinBet = player.totalBet
                    
            player.currentRound = self.currentRound
            self.sendToAll(messageAction, player.getName() + SXSTR_EOO + str(amount))
            self.handleTurn()

                        
    def everyoneHasPlayed(self):
        if len(self.players) < 2:
            print('Not enough players!')
            return -1
        
        allPlayed = True
        for p in self.players:
            if self.playerCanPlayThisTurn(p):
                #print 'Player %s has not played yet.' % p.getName()
                allPlayed = False
                break
                
        if not allPlayed:
            return 0
        
        print('All players have played.')
        return 1
                        
        
    def currentlyInGame(self):
        return len(self.getAllPlayers())
        
        
    def shuffleDeck(self):
        self.deck = []
        for x in range(0, 51):
            suit = floor(x / 13)
            rank = x % 13
            card = Card(suit, rank)
            self.deck.append(card)
        shuffle(self.deck)
        print('Deck shuffled.')
        
        
    def dealCardsToTable(self, number):
        print('Dealing cards to the table.')
        for x in range(0, number):
            print('Dealt %d of %d to the table.' % (self.deck[0].rank, self.deck[0].suit))
            self.cardsOnTable.append(self.deck[0])
            self.deck.pop(0)
        
        cardString = ""
        
        for c in self.cardsOnTable:
            cardString += str(c)
            cardString += SXSTR_EOO
        cardString = cardString[:-1] # Remove last unnecessary SXSTR_EOO
        self.sendToAll(SX_GAME_DEAL_TABLE, cardString)

        
    def dealCardsToPlayers(self, number):
        print('Dealing cards to players.')
        playingPlayers = self.getPlayingPlayers()
        for x in range(0, number):
            for p in playingPlayers:
                print('Dealt %d of %d to %s.' % (self.deck[0].rank, self.deck[0].suit, p.getName()))
                p.addCard(self.deck[0])
                self.deck.pop(0)
                
        for p in playingPlayers:
            cardString = ""
            for c in p.cards:
                cardString += str(c)
                cardString += SXSTR_EOO
            cardString = cardString[:-1] # Remove last unnecessary SXSTR_EOO
            self.sendToPlayer(p, SX_GAME_DEAL_HAND, cardString)
            
        self.announcePlayersCardCounts(self.players)
        
        
    def startGame(self):
        print('Waiting for players to be ready.')
        self.gameLoop()
        print('gameLoop() ended.')
        
        
    def resetPlayers(self):
        for p in self.players:
            p.reset()
        
        
    def checkChips(self):
        for p in self.players:
            if p.chips == 0:
                self.endGameForPlayer(p)
        
        
    def getNextPlayerFrom(self, player, allowSame = False):
        if player is None:
            return None
        
        nextChair = player.chair
        for x in range(0, self.maxPlayers):
            if nextChair == (self.maxPlayers - 1):
                nextChair = 0
            else:
                nextChair += 1
                
            for p in self.players:
                if p.chair == nextChair and (allowSame or p.chair != player.chair) and self.playerCanPlayThisTurn(p):
                    return p
                
        return None
    
    
    def getNextChairFrom(self, chair, bigBlind = False):
        if chair < 0:
            chair = 0
        
        nextChair = chair
        for x in range(0, self.maxPlayers):
            if nextChair >= (self.maxPlayers - 1):
                nextChair = 0
            else:
                nextChair += 1
                
            if bigBlind and nextChair == self.dealerPlayer.chair:
                # Dealer can never also be the big blind
                print('Dealer can never also be the big blind!')
                continue
                
            for p in self.players:
                if p.chair == nextChair and p.chair != chair and (bigBlind or not p.waitForBigBlind):
                    print('Original chair: %d found chair: %d' % (chair, nextChair))
                    return p
                
        return None
        
        
    def playerCanPlayThisTurn(self, player):
        if not player.allIn and not player.folded and player.currentRound < self.currentRound and not player.waitForBigBlind:
            return True
        return False
        
        
    def moveButtons(self):
        playersTotal = len(self.players)
        
        for p in self.players:
            print('Player: %s. Chair: %d.' % (p.getName(), p.chair))
        
        if self.dealerPlayerChair == -1:
            # The very first player sitting at the table gets to be the dealer
            self.dealerPlayer = self.players[0]
            
            if playersTotal > 2:
                # The ones following the dealer get to be the small and big blinds, respectively
                self.smallBlindPlayer = self.players[1]
                self.bigBlindPlayer = self.players[2]
                
            else:
                # In two-player matches the dealer is also the small blind
                self.smallBlindPlayer = self.players[0]
                self.bigBlindPlayer = self.players[1]
                
        else:
            if playersTotal > 2:
                if self.dealerPlayer is not self.smallBlindPlayer:
                    print('A')
                    # The dealer button always moves to the next chair unless the player sitting on that chair only just joined
                    self.dealerPlayer = self.getNextChairFrom(self.dealerPlayerChair)
                    # Small blind player is the next one from dealer
                    self.smallBlindPlayer = self.getNextChairFrom(self.dealerPlayer.chair)
                    # Big blind player is the next one from small blind
                    self.bigBlindPlayer = self.getNextChairFrom(self.smallBlindPlayer.chair, True)
                    
                else:
                    print('B')
                    # The dealer is also the small blind; this means it used to be a two-player match but no longer is
                    # Make the old big blind the small blind while the dealer stays the same and make that new player the big blind
                    self.smallBlindPlayer = self.getNextChairFrom(self.dealerPlayerChair)
                    self.bigBlindPlayer = self.getNextChairFrom(self.smallBlindPlayer.chair, True)
                    
            else:
                # Move the dealer button to the next chair and also make that player the small blind
                # The other player is then the big blind
                print('C')
                self.dealerPlayer = self.getNextChairFrom(self.dealerPlayerChair)
                self.smallBlindPlayer = self.dealerPlayer
                self.bigBlindPlayer = self.getNextChairFrom(self.smallBlindPlayer.chair, True)
        
        # Save the chair number in case the player leaves the table during a hand
        self.dealerPlayerChair = self.dealerPlayer.chair
        self.smallBlindPlayerChair = self.smallBlindPlayer.chair
        self.bigBlindPlayerChair = self.bigBlindPlayer.chair
        
        print('D player\'s chair: %d' % self.dealerPlayer.chair)
        print('SB player\'s chair: %d' % self.smallBlindPlayer.chair)
        print('BB player\'s chair: %d' % self.bigBlindPlayer.chair)
        
        
    def takeBlinds(self):
        smallBlind = self.smallBlindPlayer.takeChips(self.smallBlindAmount)
        print('Taking a small blind of %d from %s.' % (smallBlind, self.smallBlindPlayer.getName()))
        self.pot += smallBlind
        
        blindsData = self.smallBlindPlayer.getName()
        blindsData += SXSTR_EOO
        blindsData += str(self.smallBlindAmount)
        
        # Allow every new player sitting ahead of the big blind but before the dealer to play
        # Also collect big blinds from them and from the big blind player
        bigBlindPlayers = [p for p in self.players if (p.waitForBigBlind or p is self.bigBlindPlayer)]
        print('bigBlindPlayers length: %d.' % len(bigBlindPlayers))
        newChair = self.bigBlindPlayer.chair
        for x in range(0, self.maxPlayers):
            for p in bigBlindPlayers:
                print('Checking %s (%d).' % (p.getName(), p.chair))
                if p.chair == newChair and (p.waitForBigBlind or p is self.bigBlindPlayer):
                    p.waitForBigBlind = False
                    bigBlindPlayers.remove(p)
                    bigBlind = p.takeChips(self.bigBlindAmount)
                    if p is not self.bigBlindPlayer:
                        print('New player %s is sitting on %d and therefore is between %d and %d and can now play!' % (p.getName(), p.chair, self.bigBlindPlayer.chair, self.dealerPlayer.chair))
                    print('Taking a big blind of %d from %s.' % (bigBlind, p.getName()))
                    self.pot += bigBlind
                    
                    blindsData += SXSTR_EOO
                    blindsData += p.getName()
                    blindsData += SXSTR_EOO
                    blindsData += str(self.bigBlindAmount)
                    
            if newChair == (self.maxPlayers - 1):
                newChair = 0
            else:
                newChair += 1
                
            if newChair == self.dealerPlayer.chair:
                break
        
        # Tell everyone about the posted blinds
        self.sendToAll(SX_GAME_BLINDS, blindsData)
        
        self.roundMinBet = self.bigBlindAmount


    def cleanTable(self): # Next hand
        print('Cleaning the table!')
        self.cardsOnTable = []
        
        self.smallBlindAmount = self.defaultSmallBlind
        self.bigBlindAmount = self.smallBlindAmount * 2
        
        self.sidePots = []
        self.pot = 0
        self.roundMinBet = 0
        
        self.currentPlayerTurn = None
        self.lastPlayerTurn = None
        self.currentRound = 0
        self.lastRound = -1
        
        self.showedAllCards = False
        
        self.foldTimerSeconds = 15


    def nextRound(self, firstRound = False):
        print('nextRound() Called!')
        
        self.currentPlayerTurn = None
        self.currentRound += 1
        
        self.handleTurn()


    def announceTurn(self, force = True, toPlayer = None):
        if self.currentPlayerTurn is not None:
            if force or not self.foldTimer.update():
                if toPlayer is not None:
                    self.sendToPlayer(player, SX_GAME_PLAYER_TURN, self.currentPlayerTurn.getName() + SXSTR_EOO + str(int(round(self.foldTimer.timerLeft))))
                else:
                    self.sendToAll(SX_GAME_PLAYER_TURN, self.currentPlayerTurn.getName() + SXSTR_EOO + str(int(round(self.foldTimer.timerLeft))))


    def nextTurn(self):
        if self.currentPlayerTurn is not None:
            self.currentPlayerTurn = self.getNextPlayerFrom(self.currentPlayerTurn)
        else:
            self.currentPlayerTurn = self.getNextPlayerFrom(self.bigBlindPlayer, True)


    def handleTurn(self):
        print('handleTurn() Called!')
        newTurn = False
        
        if self.currentPlayerTurn is None or not self.playerCanPlayThisTurn(self.currentPlayerTurn):
            self.nextTurn()
            newTurn = True
        
        if self.currentPlayerTurn is not None:
            playersThatCanPlay = [p for p in self.players if (p is not self.currentPlayerTurn and not p.allIn and not p.folded and not p.waitForBigBlind)]
                
            if len(playersThatCanPlay) == 0:
                print('We have gone All In or everyone else has gone All In!')
                print('Player %s totalBet %d roundMinBet %d' % (self.currentPlayerTurn.getName(), self.currentPlayerTurn.totalBet, self.roundMinBet))
                if self.currentPlayerTurn.totalBet < self.roundMinBet:
                    print('Player %s can only make a call.' % self.currentPlayerTurn.getName())
                else:
                    print('Auto-checking for player %s.' % self.currentPlayerTurn.getName())
                    self.currentPlayerTurn.allIn = True
                    self.currentPlayerTurn = None
                    return
                
            if newTurn:
                self.foldTimer.start()
                self.announceTurn()
                print('Player %s\'s turn!' % self.currentPlayerTurn.getName())
            else:
                self.announceTurn(False)


    def announcePlayersCardCounts(self, players, toPlayer = None):
        if len(self.players) == 0:
            return

        cardsData = ''
        for p in players:
            cardsData += p.getName()
            cardsData += SXSTR_EOO
            cardsData += str(len(p.cards))
            cardsData += SXSTR_EOO
        cardsData = cardsData[:-1]
        
        if toPlayer is None:
            self.sendToAll(SX_GAME_PLAYER_CARD_COUNT, cardsData)
        else:
            self.sendToPlayer(toPlayer, SX_GAME_PLAYER_CARD_COUNT, cardsData)
            

    def announcePlayersChips(self, players, toPlayer = None):
        if len(self.players) == 0:
            return
        
        chipsData = ''
        for p in players:
            chipsData += p.getName()
            chipsData += SXSTR_EOO
            chipsData += str(p.chips)
            chipsData += SXSTR_EOO
        chipsData = chipsData[:-1]
        
        chipsInPotData = ''
        for p in players:
            chipsInPotData += p.getName()
            chipsInPotData += SXSTR_EOO
            chipsInPotData += str(p.totalBet)
            chipsInPotData += SXSTR_EOO
        chipsInPotData = chipsInPotData[:-1]
        
        if toPlayer is None:
            self.sendToAll(SX_GAME_PLAYER_CHIPS, chipsData)
            self.sendToAll(SX_GAME_PLAYER_CHIPS_IN_POT, chipsInPotData)
        else:
            self.sendToPlayer(toPlayer, SX_GAME_PLAYER_CHIPS, chipsData)
            self.sendToPlayer(toPlayer, SX_GAME_PLAYER_CHIPS_IN_POT, chipsInPotData)


    def announcePlayers(self, toPlayer = None):
        if len(self.players) == 0:
            return
        
        playersData = ''
        for p in self.players:
            playersData += p.getName()
            playersData += SXSTR_EOO
            playersData += str(p.chair)
            playersData += SXSTR_EOO
        playersData = playersData[:-1]

        if toPlayer is None:
            self.sendToAll(SX_GAME_PLAYER_CHAIR, playersData)
        else:
            self.sendToPlayer(toPlayer, SX_GAME_PLAYER_CHAIR, playersData)
            
        
    def announceButtons(self, toPlayer = None):
        buttonsData = ''
        buttonsData += str(self.dealerPlayerChair)
        buttonsData += SXSTR_EOO
        buttonsData += str(self.smallBlindPlayerChair)
        buttonsData += SXSTR_EOO
        buttonsData += str(self.bigBlindPlayerChair)

        if toPlayer is None:
            self.sendToAll(SX_GAME_BUTTONS_CHAIRS, buttonsData)
        else:
            self.sendToPlayer(toPlayer, SX_GAME_BUTTONS_CHAIRS, buttonsData)
            
        
    def dealFlop(self):
        if self.showedAllCards:
            self.wait()
        self.dealCardsToTable(3)
        
        
    def dealTurn(self):
        if self.showedAllCards:
            self.wait()
        self.dealCardsToTable(1)
        
        
    def dealRiver(self):
        if self.showedAllCards:
            self.wait()
        self.dealCardsToTable(1)

        
    # Return the player with the losing hand
    # In case of a tie, return a None
    def comparePlayerHands(self, player1, player2):
        print('Comparing hands of player %s and player %s.' % (player1.getName(), player2.getName()))
        player1Hand = Hand(player1.cards + self.cardsOnTable)
        player2Hand = Hand(player2.cards + self.cardsOnTable)
        
        comparison = player1Hand.compareToHand(player2Hand)
        
        if comparison == -1:
            return player2
        elif comparison == 1:
            return player1
        else:
            return None
        
        
    def endHand(self, prematureEnding = False):
        print('Hand ended!')
        playersNotHandled = [p for p in self.getPlayingPlayers()]
        
        if not prematureEnding:
            self.showAllCards()
            
        self.sendToAll(SX_GAME_HAND_ENDED)
        
        while self.pot > 0:
            winners = [p for p in playersNotHandled]
            
            for p1 in playersNotHandled:
                if p1 in winners:
                    for p2 in playersNotHandled:
                        if p1 is not p2 and p1 in winners and p2 in winners:
                            losingPlayer = self.comparePlayerHands(p1, p2)
                            if losingPlayer is not None:
                                print('Removing %s from winners.' % losingPlayer.getName())
                                winners.remove(losingPlayer)
            pot = self.pot
            sidePot = None
            
            for s in self.sidePots:
                print('Looping side pot.')
                for p in winners:
                    print('Looping winners %s.' % p.getName())
                    if p in s.playersInPot:
                        print('Winner %s is in side pot %d.' % (p.getName(), s.potNumber))
                        pot = s.totalPot
                        sidePot = s
                        if p.totalBet == s.potPerPlayer:
                            print('Removing %s from playersNotHandled.' % p.getName())
                            playersNotHandled.remove(p)
            
            if sidePot is not None:
                print('Removing side pot!')
                self.sidePots.remove(sidePot)
                print('Winners (%d) of side pot %d (%d):' % (len(winners), sidePot.potNumber, pot))
            else:
                print('Winners (%d) of pot (%d):' % (len(winners), pot))
            
            winningAmount = int(floor(pot / len(winners)))
            for p in winners:
                p.chips += winningAmount
                print('    %s wins %d.' % (p.getName(), winningAmount))
                # Tell players who won and how much
                self.sendToAll(SX_GAME_POT, p.getName() + SXSTR_EOO + str(winningAmount))
            self.pot -= pot
            print('Pot left: %d.' % self.pot)
            
        sleep(5)
        self.gameState = GMST_CHECK_CHIPS
        
        
    def calculateSidePots(self):
        sortedPlayers = [p for p in self.players]
        
        for i in range (0, len(sortedPlayers)):
            minBetIndex = i
            for j in range (i+1, len(sortedPlayers)):
                if sortedPlayers[j].totalBet < sortedPlayers[minBetIndex].totalBet:
                    minBetIndex = j
                    
            temp = sortedPlayers[i]
            sortedPlayers[i] = sortedPlayers[minBetIndex]
            sortedPlayers[minBetIndex] = temp
        
        for p in sortedPlayers:
            if p.allIn and p.totalBet < self.roundMinBet and not p.inSidePot:
                self.createSidePot(sortedPlayers, p.totalBet)
        
        
    def createSidePot(self, sortedPlayers, totalBetAmount):
        sidePotPlayers = []
        totalPot = 0
        sidePotNumber = (len(self.sidePots) + 1)
        print('Creating a side pot %d with the size of %d!' % (sidePotNumber, totalBetAmount))
        for p in sortedPlayers:
            if not p.inSidePot:
                totalPot += totalBetAmount
            if p.totalBet == totalBetAmount:
                print('Player %s added to the side pot!' % p.getName())
                sidePotPlayers.append(p)
                p.inSidePot = True
                
        sidePot = SidePot(sidePotNumber, totalBetAmount, totalPot, sidePotPlayers)
        self.sidePots.append(sidePot)


    # Sitting players that are still competing for the pot
    def getPlayingPlayers(self):
        playingPlayers = [p for p in self.players if (not p.folded and not p.waitForBigBlind)]
    
        return playingPlayers
    
    
    def canPlayersPlay(self):
        playersThatCanPlay = [p for p in self.players if (not p.allIn and not p.folded and not p.waitForBigBlind)]
            
        if len(playersThatCanPlay) > 0:
            return True
        return False
    
    
    def showAllCards(self):
        if not self.showedAllCards:
            self.showedAllCards = True
            for p in self.getPlayingPlayers():
                self.sendToAllBut(p.clientClass, SX_GAME_PLAYER_HAND, p.getName() + SXSTR_EOO + str(p.cards[0]) + SXSTR_EOO + str(p.cards[1]))


    def handleAutoFold(self):
        if self.currentPlayerTurn is not None:
            if not self.foldTimer.update():
                self.endGameForPlayer(self.currentPlayerTurn)
    
    
    def wait(self, fullSeconds = 0):
        self.waitTimer.start(fullSeconds)


    def gameLoop(self):
        while True:
            if self.gameState == GMST_ENDED:
                print('Closing game thread.')
                break
            
            if self.gameState == GMST_START:
                if len(self.players) > 1:
                    print('We have enough players. Starting the game.')
                    self.gameState = GMST_CHECK_CHIPS
                    
            if self.gameState == GMST_CHECK_CHIPS:
                self.resetPlayers()
                self.announcePlayersChips(self.players)
                self.cleanTable()
                self.checkChips()
                
                if len(self.players) > 1:
                    self.gameState = GMST_DEAL_CARDS
                else:
                    print('Not enough players with enough chips.')
                    self.gameState = GMST_START
                    self.sendToAll(SX_GAME_NOT_ENOUGH_PLAYERS)
                    
            if self.gameState == GMST_DEAL_CARDS:
                self.announcePlayers()
                self.shuffleDeck()
                self.moveButtons()
                self.announceButtons()
                self.takeBlinds()
                self.nextRound(True)
                self.dealCardsToPlayers(2)
                self.gameState = GMST_BET
                
            if self.gameState == GMST_BET:
                self.handleAutoFold() # Did the timer run out for the current player
                
                if len(self.players) < 2 or len(self.getPlayingPlayers()) < 2:
                    # Not enough players: end the hand
                    self.gameState = GMST_END_HAND_PREMATURE
                else:
                    canPlay = self.canPlayersPlay() # No plays can be made if too many players have gone All In
                    
                    if canPlay:
                        playersHavePlayed = self.everyoneHasPlayed()
                        if playersHavePlayed != 1: # Not everyone has played on this round yet
                            self.announceTurn(False)
                    elif not self.showedAllCards:
                        print('Showing all cards!')
                        self.showAllCards()
                        
                    if (not canPlay or playersHavePlayed == 1) and not self.waitTimer.update(): # No plays can be made on this round
                        if len(self.cardsOnTable) < 5:
                            self.nextRound()
                        self.calculateSidePots()
                        if len(self.cardsOnTable) == 0:
                            self.dealFlop()
                        elif len(self.cardsOnTable) == 3:
                            self.dealTurn()
                        elif len(self.cardsOnTable) == 4:
                            self.dealRiver()
                        else:
                            self.gameState = GMST_END_HAND
                            
                    elif playersHavePlayed == -1:
                        self.gameState = GMST_END_HAND_PREMATURE
                        
            if self.gameState == GMST_END_HAND:
                self.endHand()
            elif self.gameState == GMST_END_HAND_PREMATURE:
                self.endHand(True)
                
            sleep(0.05)
            
        print('Game thread closed.')