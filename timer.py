from time import time

class Timer(object):
    defaultTime = 0
    timerLeft = 0
    timerStartTime = 0
    
    
    def __init__(self, defaultTime):
        self.defaultTime = defaultTime


    def start(self, fullSeconds = 0):
        if fullSeconds > 0:
            self.timerLeft = fullSeconds
        else:
            self.timerLeft = self.defaultTime
        self.timerStartTime = time()
        
        
    def update(self):
        if self.timerStartTime == 0: # Timer has not started yet
            return False
        self.timerLeft = (self.timerStartTime + self.defaultTime) - time()
        if self.timerLeft <= 0:
            return False
        return True