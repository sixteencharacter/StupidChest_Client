from multiprocessing import Process
import zmq
import config
import time
from messages import MessageFormatter

class Serial2PCProc(Process) : 
    def __init__(self,*args,**kwargs) :
        super(Serial2PCProc,self).__init__(*args,**kwargs)
    def run(self) :
        context = zmq.Context()
        self.discovery_sock = context.socket(zmq.PUB)
        self.discovery_sock.connect(f"{config.HOST}:{config.DISCOVERY_PORT}")
        time.sleep(2)
        self.discovery_sock.send_json(MessageFormatter.parse_module_status("Serial2PC","Up"))
        self.serial2cloud_sock = context.socket(zmq.PAIR)
        self.serial2cloud_sock.bind(f"{config.HOST}:{config.SERIAL2CLOUD_PORT}")
        self.serial2pattern_sock = context.socket(zmq.PAIR)
        self.serial2pattern_sock.bind(f"{config.HOST}:{config.SERIAL2PATTERN_PORT}")
        try :
            while True :
                # TODO : Add Serial to PC logic here
                # This module will read the data sent from the arduino using either pyserial
                # or traditional serial module and send it to the cloud worker to send the data
                # up to the internet

                # ==================================
                time.sleep(1)
        except KeyboardInterrupt :
            pass 