class Card(object):
    suit = 0 # 0 - 3: hearts, diamonds, clubs, spades
    rank = 0 # 0 - 12: 2, 3, 4, 5, 6, 7, 8, 9, 10, jack, queen, king, ace
    
    def __init__(self, suit, rank):
        self.suit = suit
        self.rank = rank
        
        
    def __str__(self):
        cardNumber = str(int(self.rank + (self.suit * 13)))
        if int(cardNumber) < 10:
            cardNumber = '0' + cardNumber
        return str(cardNumber)