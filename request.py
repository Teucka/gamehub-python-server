class Request(object):
    requestID = 0
    requestType = ''
    length = -1
    rawLength = ''
    data = b''


    def Request(self):
        self.reset


    def reset(self):
        #self.requestID = 0
        self.requestType = ''
        self.length = -1
        self.rawLength = ''
        self.data = b''