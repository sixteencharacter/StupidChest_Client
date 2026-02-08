from multiprocessing import Process
import zmq
import config
import time
from messages import MessageFormatter

class PC2SerialProc(Process) : 
    def __init__(self,*args,**kwargs) :
        super(PC2SerialProc,self).__init__(*args,**kwargs)
    def run(self) :
        context = zmq.Context()
        self.discovery_sock = context.socket(zmq.PUB)
        self.discovery_sock.connect(f"{config.HOST}:{config.DISCOVERY_PORT}")
        time.sleep(2)
        self.discovery_sock.send_json(MessageFormatter.parse_module_status("PC2Serial","Up"))
        self.pc2serialIn = context.socket(zmq.PAIR)
        self.pc2serialIn.bind(f"{config.HOST}:{config.PC2SERIAL2PATTERN_PORT}")
        try:
            while True :
                # TODO : Add PC to Serial logic here
                # this module is responsible for notifying the arduino for a close / open signal
                # this module will listen for the signal from the pattern recognition module and
                # act as a router of the command to the arduino. You may implement this feature
                # with either pyserial or just standard serial module
                
                # PAIR socket testing
                # dat = self.pc2serialIn.recv_json()
                # print(dat)
                
                # ==================================
                time.sleep(1) 
        except KeyboardInterrupt :
            pass 