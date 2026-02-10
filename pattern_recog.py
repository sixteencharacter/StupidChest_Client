from multiprocessing import Process
import zmq
import config
import time
import json
from messages import MessageFormatter
from dataclasses import dataclass

@dataclass
class PatternConfig :
    pattern_representation = None
    config = None

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
        self.pattern2cloud = context.socket(zmq.PAIR)
        self.pattern2cloud.bind(f"{config.HOST}:{config.PATTERN2CLOUD_PORT}")
        self.cloud2patt = context.socket(zmq.PAIR)
        self.cloud2patt.connect(f"{config.HOST}:{config.CLOUD2PATT_PORT}")
        self.poller = zmq.Poller()
        self.poller.register(self.serial2patt,zmq.POLLIN)
        self.poller.register(self.cloud2patt,zmq.POLLIN)
        try :
            while True :
                # In this module , we must store the local system config from the pipe exposed from
                # the config fetcher module and calculate the similarity of the data using the mean
                # square error or any relevant comparision
                
                socks = dict(self.poller.poll(timeout=500))
                if self.cloud2patt in socks :
                    msg = self.cloud2patt.recv_json()
                    if msg.type == "PARAMETERS" :
                        PatternConfig.config = msg["payload"]["cfgs"]
                        self.discovery_sock.send_json(MessageFormatter.parse_log(
                            self.__class__.__name__,
                            "Received config: \n{}".format(json.dumps(msg["payload"],indent=4))
                        ))
                    elif msg.type == "PATTERN" :
                        PatternConfig.pattern_representation = msg["payload"]["cfgs"]
                        self.discovery_sock.send_json(MessageFormatter.parse_log(
                            self.__class__.__name__,
                            "Received pattern config: \n{}".format(json.dumps(msg["payload"],indent=4))
                        ))
                if self.serial2patt in socks :
                    msg = self.serial2patt.recv_json()
                    # TODO : add the preprocessing logic to the pattern recognition module 
                    # (also the cache of the signal) after the signal is processed , the module
                    # will run the pattern processing and if the unlock attemp is created this
                    # module will contact with other modules to deliver the unlock command to
                    # the box and the access log to the cloud

                # ==================================
        except KeyboardInterrupt:
            pass