from multiprocessing import Process
import zmq
import config
import time
from messages import MessageFormatter

class PatternRecogProc(Process) : 
    def __init__(self,*args,**kwargs) :
        super(PatternRecogProc,self).__init__(*args,**kwargs)
    def run(self) :
        context = zmq.Context()
        self.discovery_sock = context.socket(zmq.PUB)
        self.discovery_sock.connect(f"{config.HOST}:{config.DISCOVERY_PORT}")
        time.sleep(2)
        self.discovery_sock.send_json(MessageFormatter.parse_module_status("PatternRecognition","Up"))
        self.patt2pc2serial = context.socket(zmq.PAIR)
        self.patt2pc2serial.connect(f"{config.HOST}:{config.PC2SERIAL2PATTERN_PORT}")
        self.serial2patt = context.socket(zmq.PAIR)
        self.serial2patt.connect(f"{config.HOST}:{config.SERIAL2PATTERN_PORT}")
        try :
            while True :
                # TODO : Add Pattern recognition logic here
                # In this module , we must store the local system config from the pipe exposed from
                # the config fetcher module and calculate the similarity of the data using the mean
                # square error or any relevant comparision
                
                # PAIR socket testing
                # self.patt2pc2serial.send_json(MessageFormatter.parse_data_transfer("lock"))
                
                # ==================================
                time.sleep(1) 
        except KeyboardInterrupt:
            pass