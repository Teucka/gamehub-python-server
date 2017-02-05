from card import Card

HAND_RANK_STRAIGHT_FLUSH = 1
HAND_RANK_FOUR_OF_A_KIND = 2
HAND_RANK_FULL_HOUSE = 3
HAND_RANK_FLUSH = 4
HAND_RANK_STRAIGHT = 5
HAND_RANK_THREE_OF_A_KIND = 6
HAND_RANK_TWO_PAIRS = 7
HAND_RANK_PAIR = 8
HAND_RANK_HIGH_CARD = 9
HAND_RANK_NOT_KNOWN = 10


class Hand(object):
    cards = []
    bestHand = None
    bestHandRank = HAND_RANK_NOT_KNOWN

    straightFlush = None
    fourOfAKind = None
    fullHouse = None
    flush = None # Can contain more than five cards
    straight = None
    threeOfAKind = None
    twoPairs = []
    pairs = []
    
    def __init__(self, cards):
        if len(cards) < 2 or len(cards) > 7:
            raise Exception('Hand() must consist of two to seven cards! Given: %d' % len(cards))
        self.cards = cards
        self.sortCardsByRank()
    
        
    def sortCardsByRank(self):
        if self.cards is None:
            return
        for i in range (0, len(self.cards)):
            maxRankIndex = i
            for j in range (i+1, len(self.cards)):
                if self.cards[j].rank > self.cards[maxRankIndex].rank:
                    maxRankIndex = j
                    
            temp = self.cards[i]
            self.cards[i] = self.cards[maxRankIndex]
            self.cards[maxRankIndex] = temp
        
        
    def getCardByRank(self, cards, rank):
        if cards is None:
            return None
        for c in cards:
            if c.rank == rank:
                return c
        return None
        
        
    def getStraight(self, cards):
        cardsTotal = len(cards)
        if cardsTotal < 5:
            #print 'Has no straight (1).'
            return None
        
        maxRank = cards[0].rank
        minRank = cards[-1].rank
        
        if maxRank - minRank < 4:
            #print 'Has no straight (2).'
            return None
        
        straightCards = []
        
        if maxRank == 12: # Handle ace as the lowest rank card
            card = self.getCardByRank(cards, 12)
            if card is not None:
                straightCards.append(card)
                #print 'Added ace: %d' % card.rank
                for y in range(0, cardsTotal - 1):
                    #print 'Checking for rank: %d' % y
                    card = self.getCardByRank(cards, y)
                    if card is not None:
                        straightCards.append(card)
                        #print 'Added: %d' % card.rank
                    else:
                        break
                    
            if len(straightCards) == 5:
                return straightCards
                
            straightCards = []
            #print '-----'
        
        for x in range(minRank, maxRank - 3):
            for y in range(0, cardsTotal):
                #print 'Checking for rank: %d' % (maxRank - y - (x - minRank))
                card = self.getCardByRank(cards, maxRank - y - (x - minRank))
                if card is not None:
                    straightCards.append(card)
                    if len(straightCards) == 5:
                        return straightCards
                    #print 'Added: %d' % card.rank
                else:
                    break

            if len(straightCards) == 5:
                return straightCards
                
            straightCards = []
            #print '-----'
        
        #print 'Has %d straights.' % len(straights)
        return None
        
        
    def calculateFlushes(self):
        hearts = []
        diamonds = []
        clubs = []
        spades = []
        self.flush = None
        
        for c in self.cards:
            if c.suit == 0:
                hearts.append(c)
            elif c.suit == 1:
                diamonds.append(c)
            elif c.suit == 2:
                clubs.append(c)
            elif c.suit == 3:
                spades.append(c)
        
        if len(hearts) > 4:
            self.flush = hearts
                
        elif len(diamonds) > 4:
            self.flush = diamonds
                
        elif len(clubs) > 4:
            self.flush = clubs
                
        elif len(spades) > 4:
            self.flush = spades
            
        
    def getFourOfAKind(self):
        if len(self.cards) < 4:
            return None
        cards = []
        for i in range(0, len(self.cards) - 3):
            if self.cards[i].rank == self.cards[i+1].rank and self.cards[i].rank == self.cards[i+2].rank and self.cards[i].rank == self.cards[i+3].rank:
                cards.append(self.cards[i])
                cards.append(self.cards[i+1])
                cards.append(self.cards[i+2])
                cards.append(self.cards[i+3])
                highestCard = self.highestCardNotInCards(cards)
                if highestCard is not None:
                    cards.append(highestCard)
                return cards
        return None
        
    # Must have called getThreeOfAKind() and calculatePairs() before calling this!
    def getFullHouse(self):
        if len(self.cards) < 5:
            return None
        if self.threeOfAKind is not None and len(self.pairs) > 1:
            cards = []
            cards.extend(self.threeOfAKind)
            cards.append(self.pairs[0])
            cards.append(self.pairs[1])
            return cards
        else:
            return None
        
        
    def getThreeOfAKind(self):
        if len(self.cards) < 3:
            return None
        cards = []
        for i in range(0, len(self.cards) - 2):
            if self.cards[i].rank == self.cards[i+1].rank and self.cards[i].rank == self.cards[i+2].rank:
                cards.append(self.cards[i])
                cards.append(self.cards[i+1])
                cards.append(self.cards[i+2])
                return cards
        return None
    
        
    def calculatePairs(self):
        self.pairs = []
        for i in range(0, len(self.cards) - 1):
            if self.cards[i].rank == self.cards[i+1].rank:
                # Do not count cards of which there are three and do not allow three pairs
                if (self.threeOfAKind is None or self.cards[i] not in self.threeOfAKind) and len(self.pairs) < 4:
                    self.pairs.append(self.cards[i])
                    self.pairs.append(self.cards[i+1])
                    #print 'Added card to pairs: %d of %d' % (self.cards[i].rank, self.cards[i].suit)
                    #print 'Added card to pairs: %d of %d' % (self.cards[i+1].rank, self.cards[i+1].suit)
                    i = i+1
            
        
    def highestCardNotInCards(self, cards):
        for c in self.cards:
            if c not in cards:
                return c
        return None
        
        
    def highestCardsNotInCards(self, cards):
        highestCards = []

        for c in self.cards:
            if c not in cards:
                highestCards.append(c)
                if len(cards) + len(highestCards) == 5:
                    return highestCards
        return None
        
        
    def getBestHand(self):
        self.calculateFlushes()
        self.straight = self.getStraight(self.cards)
        
        if self.flush is not None:
            self.straightFlush = self.getStraight(self.flush)
            
            if self.straightFlush is not None:
                print('Straight flush!')
                self.bestHand = self.straightFlush
                self.bestHandRank = HAND_RANK_STRAIGHT_FLUSH
                return self.bestHand

        self.fourOfAKind = self.getFourOfAKind()
        if self.fourOfAKind is not None:
            print('Four of a kind!')
            self.bestHand = self.fourOfAKind
            self.bestHandRank = HAND_RANK_FOUR_OF_A_KIND
            return self.bestHand
        
        self.threeOfAKind = self.getThreeOfAKind()
        self.calculatePairs()
        self.fullHouse = self.getFullHouse()
        if self.fullHouse is not None:
            print('Full house!')
            self.bestHand = self.fullHouse
            self.bestHandRank = HAND_RANK_FULL_HOUSE
            return self.bestHand
            
        if self.flush is not None:
            print('Flush!')
            self.bestHand = self.flush[:5]
            self.bestHandRank = HAND_RANK_FLUSH
            return self.bestHand
        
        if self.straight is not None:
            print('Straight!')
            self.bestHand = self.straight
            self.bestHandRank = HAND_RANK_STRAIGHT
            return self.bestHand
        
        if self.threeOfAKind is not None:
            print('Three of a kind!')
            highestCards = self.highestCardsNotInCards(self.threeOfAKind)
            if highestCards is not None:
                self.threeOfAKind.extend(highestCards)
            self.bestHand = self.threeOfAKind
            self.bestHandRank = HAND_RANK_THREE_OF_A_KIND
            return self.bestHand
        
        if len(self.pairs) > 3:
            print('Two pairs!')
            self.twoPairs = []
            self.twoPairs.append(self.pairs[0])
            self.twoPairs.append(self.pairs[1])
            self.twoPairs.append(self.pairs[2])
            self.twoPairs.append(self.pairs[3])
            highestCard = self.highestCardNotInCards(self.twoPairs)
            if highestCard is not None:
                self.twoPairs.append(highestCard)
            self.bestHand = self.twoPairs
            self.bestHandRank = HAND_RANK_TWO_PAIRS
            return self.bestHand
        
        if len(self.pairs) == 2:
            print('A pair!')
            highestCards = self.highestCardsNotInCards(self.pairs)
            if highestCards is not None:
                self.pairs.extend(highestCards)
            self.bestHand = self.pairs
            self.bestHandRank = HAND_RANK_PAIR
            return self.bestHand
        
        self.bestHand = self.highestCardsNotInCards([])
        self.bestHandRank = HAND_RANK_HIGH_CARD
        return self.bestHand
    
    
    def compareToHand(self, hand):
        if not hand.bestHand or hand.bestHandRank == HAND_RANK_NOT_KNOWN:
            hand.getBestHand()
        if not self.bestHand or self.bestHandRank == HAND_RANK_NOT_KNOWN:
            self.getBestHand()
        
        print('Hand1:')
        for i in range (0, len(self.bestHand)):
            print('      %d of %d' % (self.bestHand[i].rank, self.bestHand[i].suit))
            
        print('Hand2:')
        for i in range (0, len(hand.bestHand)):
            print('      %d of %d' % (hand.bestHand[i].rank, hand.bestHand[i].suit))
        
        if self.bestHandRank < hand.bestHandRank:
            return -1
        elif self.bestHandRank > hand.bestHandRank:
            return 1
        else:
            return self.compareHighCards(hand)
        
        
    def compareHighCards(self, hand):
        for i in range(0, min(len(self.bestHand), len(hand.bestHand))):
            if self.bestHand[i].rank > hand.bestHand[i].rank:
                return -1
            elif self.bestHand[i].rank < hand.bestHand[i].rank:
                return 1
            print('Cards are of the same rank!')
        return 0
    