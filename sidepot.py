class SidePot(object):
    potNumber = 0
    potPerPlayer = 0
    totalPot = 0
    playersInPot = []
    
    def __init__(self, potNumber, potPerPlayer, totalPot, playersInPot):
        self.potNumber = potNumber
        self.potPerPlayer = potPerPlayer
        self.totalPot = totalPot
        self.playersInPot = playersInPot