from multiprocessing import Process
import zmq
import config
import time
import json
from messages import MessageFormatter
from dataclasses import dataclass
import numpy as np
import datetime

@dataclass
class PatternConfig :
    pattern_representation = None
    config = None

class PatternCache :
    patt = [1e6] * config.PATTERN_BUFFER_SIZE
    on_timestamp = time.time() * 1000
    currentIdx = 0

def find_pattern_similarity(arr : list) -> float :
    # begin stub ====================
    # if np.random.rand() > 0.7 :
    #     sim = np.random.rand() * 50 + 50
    # else :
    #     sim = 0.3
    return 0
    # end stub
    return sim

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
                    if msg["payload"]["type"] == "PARAMETERS" :
                        PatternConfig.config = msg["payload"]["cfgs"]
                        self.discovery_sock.send_json(MessageFormatter.parse_log(
                            self.__class__.__name__,
                            "Received config: \n{}".format(json.dumps(msg["payload"],indent=4))
                        ))
                    elif msg["payload"]["type"] == "PATTERN" :
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
                    if PatternConfig.config is not None :
                        verdict = msg["payload"]["raw_data"] > PatternConfig.config["threshold"]
                        if verdict :
                            PatternCache.patt[PatternCache.currentIdx] = (time.time() * 1000) - PatternCache.on_timestamp
                            PatternCache.on_timestamp = time.time() * 1000
                            PatternCache.currentIdx = (PatternCache.currentIdx + 1) % config.PATTERN_BUFFER_SIZE
                        if time.time() - PatternCache.on_timestamp > config.IDLE_CUTOFF_PERIOD :
                            PatternCache.patt = [1e6] * config.PATTERN_BUFFER_SIZE
                            PatternCache.currentIdx = 0
                            PatternCache.on_timestamp = time.time() * 1000
            
                    # Run the pattern similarity test
                    simScore = find_pattern_similarity(PatternCache.patt)
                    simVerdict =  simScore > 0.8

                    # Logging to cloud and take action with the serial
                    self.patt2pc2serial.send_json(MessageFormatter.parse_data_transfer(
                        command="unlock" if simVerdict else "lock" # TODO: make this a configurable variable
                    ))

                    self.pattern2cloud.send_json(MessageFormatter.parse_data_transfer(
                        pattern=PatternCache.patt,
                        verdict=simVerdict,
                        timestamp=datetime.datetime.isoformat()
                    ))

                # ==================================
        except KeyboardInterrupt:
            pass