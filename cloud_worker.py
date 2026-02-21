from multiprocessing import Process
import zmq
import config
import time
from messages import MessageFormatter
import asyncio
import aiomqtt
import json

async def upload_data_to_cloud(poller : zmq.Poller , pattern2cloud_sock : zmq.SyncSocket , serial2cloud_sock : zmq.SyncSocket) :
    print("hit the first loop")
    while True :
        socks = dict(poller.poll(timeout=0.5))
        try :
            async with aiomqtt.Client(config.MQTT_HOST,timeout=1000) as client :
                if pattern2cloud_sock in socks :
                    recv_data = pattern2cloud_sock.recv_json()
                    await client.publish(
                        'knocklock/v1/devices/{}/knock/result'.format(config.DEVICE_ID),
                        json.dumps(recv_data["payload"]["verdict"]),
                        qos=2
                    )
                    await client.publish(
                        'knocklock/v1/devices/{}/knock/logs'.format(config.DEVICE_ID),
                        json.dumps(recv_data),
                        qos=2
                    )

                if serial2cloud_sock in socks :
                    await client.publish(
                        'knocklock/v1/devices/{}/knock/live'.format(config.DEVICE_ID),
                        json.dumps(serial2cloud_sock.recv_json()["payload"]["raw_data"]),
                        qos=2
                    )
        except Exception as e :
            print(e)
        time.sleep(0.1) 

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
        self.poller = zmq.Poller()
        self.poller.register(self.pattern2cloud , zmq.POLLIN)
        self.poller.register(self.serial2cloud,zmq.POLLIN)
        try:
            asyncio.run(upload_data_to_cloud(self.poller,self.pattern2cloud , self.serial2cloud))
        except KeyboardInterrupt :
            pass