from multiprocessing import Process
import zmq
import config
import time
from messages import MessageFormatter
import asyncio
import aiomqtt
import json
import datetime

# Async Task Loop
async def upload_data_to_cloud(poller : zmq.Poller , pattern2cloud_sock : zmq.SyncSocket) :
    while True :
        socks = dict(poller.poll(timeout=0.1))
        try :
            async with aiomqtt.Client(config.MQTT_HOST,timeout=100) as client :
                if pattern2cloud_sock in socks :
                    recv_data = pattern2cloud_sock.recv_json()
                    await client.publish(
                        'knocklock/v1/devices/{}/api/knock/result'.format(config.DEVICE_ID),
                        json.dumps({
                            "meta" : {
                                "schema_" : "knock_result/v1",
                                "ts" : datetime.datetime.now().isoformat()
                            },
                            "data" : {
                                "matched" : recv_data["payload"]["verdict"]
                            }
                        }),
                        qos=1
                    )
                    await client.publish(
                        'knocklock/v1/devices/{}/api/logs'.format(config.DEVICE_ID),
                        json.dumps({
                            "meta" : {
                                "schema_" : "logs/v1",
                                "ts" : datetime.datetime.now().isoformat()
                            },
                            "data" : {
                               "level" : "debug",
                               "message" : f"Verdict : {recv_data["payload"]["verdict"]} | {str(recv_data["payload"]["pattern"])}",
                               "module" : "main"
                            }
                        }),
                        qos=1
                    )
                    await client.publish(
                        'knocklock/v1/devices/{}/api/knock/live'.format(config.DEVICE_ID),
                        json.dumps({
                            "meta" : {
                                "schema_" : "knock_live/v1",
                                "ts" : datetime.datetime.now().isoformat()
                            },
                            "data" : {
                                "knocks" : [{
                                    "tOffsetMs" : recv_data["payload"]["tOffset"],
                                    "amp" : recv_data["payload"]["amp"]
                                }]
                            }
                        }),
                        qos=1
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
        self.pattern2cloud = context.socket(zmq.PAIR)
        self.pattern2cloud.connect(f"{config.HOST}:{config.PATTERN2CLOUD_PORT}")
        self.poller = zmq.Poller()
        self.poller.register(self.pattern2cloud , zmq.POLLIN)
        try:
            asyncio.run(upload_data_to_cloud(self.poller,self.pattern2cloud))
        except KeyboardInterrupt :
            pass