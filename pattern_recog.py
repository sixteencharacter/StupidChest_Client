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

def calc_sliding_window(a,b) :
    # assume array a is longer than b
    min_rmse = np.inf
    if a.size > 0 and b.size > 0 :
        mu_a , sigma_a = a.mean() , a.var()
        mu_b , sigma_b = b.mean() , b.var()
        a = (a - mu_a) / sigma_a
        b = (b - mu_b) / sigma_b
        for i in range(a.size - b.size) :
            curr_rmse = np.sqrt(np.pow(a[i:i+b.size] - b,2).sum() / b.size)
            min_rmse = min(min_rmse,curr_rmse)
    return min_rmse

def find_pattern_similarity(arr : list) -> float :
    cutoff_delay = 1e6
    if PatternConfig.pattern_representation is not None :
        gt_arr = np.array(PatternConfig.pattern_representation)
        inp_arr = np.array([a for a in arr if a != cutoff_delay])
        if gt_arr.size > inp_arr.size :
            return calc_sliding_window(gt_arr,inp_arr)
        else :
            return calc_sliding_window(inp_arr,gt_arr)

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
                    if PatternConfig.config is not None :
                        verdict = msg["payload"]["raw_data"] > PatternConfig.config["activation_threshold"]
                        # print(verdict)
                        if verdict :
                            PatternCache.patt[PatternCache.currentIdx] = (time.time() * 1000) - PatternCache.on_timestamp
                            PatternCache.on_timestamp = time.time() * 1000
                            PatternCache.currentIdx = (PatternCache.currentIdx + 1) % config.PATTERN_BUFFER_SIZE
                        elif time.time() - PatternCache.on_timestamp > config.IDLE_CUTOFF_PERIOD :
                            PatternCache.patt = [1e6] * config.PATTERN_BUFFER_SIZE
                            PatternCache.currentIdx = 0
                            PatternCache.on_timestamp = time.time() * 1000
            
                    # Run the pattern similarity test
                    simScore = find_pattern_similarity(PatternCache.patt)
                    self.discovery_sock.send_json(MessageFormatter.parse_log(
                        self.__class__.__name__,
                        "RMSE: {}\n".format(simScore)
                    ))
                    if PatternConfig.config is not None :

                        simVerdict =  simScore < PatternConfig.config["predict_threshold"]
                        # print("Sim verdict: ",simVerdict)

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
                            pattern=PatternCache.patt,
                            verdict=str(simVerdict),
                            timestamp=datetime.datetime.now().strftime("%m/%d/%Y, %H:%M:%S")
                        ))

                # ==================================
        except KeyboardInterrupt:
            pass