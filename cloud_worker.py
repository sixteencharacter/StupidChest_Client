from multiprocessing import Process
import zmq
import config
import time
from messages import MessageFormatter

class CloudWorkerProc(Process) : 
    def __init__(self,*args,**kwargs) :
        super(CloudWorkerProc,self).__init__(*args,**kwargs)
    def run(self) :
        context = zmq.Context()
        self.discovery_sock = context.socket(zmq.PUB)
        self.discovery_sock.connect(f"{config.HOST}:{config.DISCOVERY_PORT}")
        time.sleep(2)
        self.discovery_sock.send_json(MessageFormatter.parse_module_status("CloudWorker","Up"))
        self.serial2cloud = context.socket(zmq.PAIR)
        self.serial2cloud.connect(f"{config.HOST}:{config.SERIAL2CLOUD_PORT}")
        self.pattern2cloud = context.socket(zmq.PAIR)
        self.pattern2cloud.connect(f"{config.HOST}:{config.PATTERN2CLOUD_PORT}")
        try:
            while True :
                # TODO : Add Cloud worker logic here
                # In this module, we should listen to the MQTT from the server and beware about
                # the config of the application, if there's a change in config, this module
                # must communicate with another module to adapt the config accordingly
                # However, there's also a case where the MQTT failed. In that case we must
                # Create an interval to fetch the config from the cloud.

                # ==================================
                time.sleep(1) 
        except KeyboardInterrupt :
            pass