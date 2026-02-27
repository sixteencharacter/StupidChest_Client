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
    pattern_representation = config.DUMMY_PATTERN
    config = None

class PatternCache :
    patt = [1e6] * config.PATTERN_BUFFER_SIZE
    on_timestamp = time.time() * 1000
    currentIdx = 0

def calc_rmse(a,b) :
    rmse = np.sqrt(np.pow(np.array(a) - np.array(b),2).sum() / np.array(b).size)
    return rmse

def find_pattern_similarity() -> float :
    cutoff_delay = 1e6
    filtered_array = [p for p in PatternCache.patt if p < cutoff_delay]
    if len(filtered_array) >= len(PatternConfig.pattern_representation) :
        return calc_rmse(
            filtered_array[:len(PatternConfig.pattern_representation)],
            PatternConfig.pattern_representation
        )
    return np.inf

class PatternRecogProc(Process) : 
    def __init__(self,*args,**kwargs) :
        super(PatternRecogProc,self).__init__(*args,**kwargs)
        self.stub_mode = kwargs["stub_mode"] if "stub_mode" in kwargs else False
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
                # print("current GT is",PatternConfig.pattern_representation)
                socks = dict(self.poller.poll(timeout=500))
                if self.cloud2patt in socks :
                    msg = self.cloud2patt.recv_json()
                    if msg["payload"]["type"] == "PARAMETERS" :
                        PatternConfig.config = msg["payload"]["cfgs"]
                        PatternConfig.pattern_representation = msg["payload"]["cfgs"]["pattern_representation"]
                        self.discovery_sock.send_json(MessageFormatter.parse_log(
                            self.__class__.__name__,
                            "Received config: \n{}".format(json.dumps(msg["payload"],indent=4))
                        ))
                if self.serial2patt in socks :
                    msg = self.serial2patt.recv_json()
                    amp = msg["payload"]["raw_data"]
                    t_now = time.time() * 1000
                    t_diff = t_now - PatternCache.on_timestamp
                    if PatternConfig.config is not None :
                        # print("READ>",msg["payload"]["raw_data"])
                        activation = msg["payload"]["raw_data"] > PatternConfig.config["activation_threshold"]

                        if activation :

                            if t_diff > PatternConfig.config["idle_cutoff_period"] :
                                PatternCache.patt = [1e6] * config.PATTERN_BUFFER_SIZE
                                PatternCache.on_timestamp = t_now
                                PatternCache.patt[0] = 0
                                PatternCache.currentIdx = 1
                            
                            elif PatternCache.currentIdx == 0 :
                                PatternCache.patt[0] = 0
                                PatternCache.on_timestamp = t_now
                                PatternCache.currentIdx = (PatternCache.currentIdx + 1) % config.PATTERN_BUFFER_SIZE

                            else :
                                PatternCache.patt[PatternCache.currentIdx] = t_diff
                                PatternCache.currentIdx = (PatternCache.currentIdx + 1) % config.PATTERN_BUFFER_SIZE
                                PatternCache.on_timestamp = time.time() * 1000
                    
                    # Run the pattern similarity test
                    curr_pattern = PatternCache.patt.copy()
                    simScore = find_pattern_similarity()
                    self.discovery_sock.send_json(MessageFormatter.parse_log(
                        self.__class__.__name__,
                        "RMSE: {}\n".format(simScore)
                    ))
                    if PatternConfig.config is not None :

                        simVerdict =  simScore < PatternConfig.config["predict_threshold"]

                        if simVerdict : 
                            PatternConfig.last_sent_time = time.time() * 1000
                            PatternCache.patt = [1e6] * config.PATTERN_BUFFER_SIZE
                            PatternCache.currentIdx = 0
                            PatternCache.on_timestamp = time.time() * 1000

                        # Logging to cloud and take action with the serial
                        self.patt2pc2serial.send_json(MessageFormatter.parse_data_transfer(
                            command="unlock" if simVerdict else "lock"
                        ))

                        self.pattern2cloud.send_json(MessageFormatter.parse_data_transfer(
                            pattern=curr_pattern,
                            verdict=str(simVerdict),
                            timestamp=datetime.datetime.now().strftime("%m/%d/%Y, %H:%M:%S"),
                            tOffset=int(t_diff),
                            amp=int(amp)
                        ))

                # ==================================
        except KeyboardInterrupt:
            pass