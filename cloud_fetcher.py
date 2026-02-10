# imports
from multiprocessing import Process
import zmq
import config
import time
from messages import MessageFormatter
from aiomqtt import Client
import asyncio
import requests
import json
from dataclasses import dataclass

# logging
# import logging
# logger = logging.Logger(__name__)
# logging.basicConfig(level=logging.DEBUG,filemode="w",filename="run.log")

@dataclass
class RuntimeConfig :
    configuration = None

async def listen_cloud_config(discovery_sock : zmq.SyncSocket,cloud2patt_socket : zmq.SyncSocket) :
    async with Client("localhost") as client:
        await client.subscribe(f"knocklock/v1/devices/{config.DEVICE_ID}/config/#")
        async for msg in client.messages :
            if RuntimeConfig.configuration is not None :
                RuntimeConfig.configuration["desired"]["data"] = json.loads(msg.payload.decode())["data"]
                discovery_sock.send_json(MessageFormatter.parse_log(
                    CloudFetcherProc.__name__,
                    "Config changed to \n{}".format(json.dumps(RuntimeConfig.configuration,indent=4))
                ))
                cloud2patt_socket.send_json(MessageFormatter.parse_config_payload(
                    type="PARAMETERS",
                    payload = RuntimeConfig.configuration["desired"]["data"]
                ))

class CloudFetcherProc(Process) : 
    def __init__(self,*args,**kwargs) :
        super(CloudFetcherProc,self).__init__(*args,**kwargs)
    def run(self) :
        context = zmq.Context()
        self.discovery_sock = context.socket(zmq.PUB)
        self.discovery_sock.connect(f"{config.HOST}:{config.DISCOVERY_PORT}")
        time.sleep(2)
        self.discovery_sock.send_json(MessageFormatter.parse_module_status("CloudFetcher","Up"))
        self.cloud2patt = context.socket(zmq.PAIR)
        self.cloud2patt.bind(f"{config.HOST}:{config.CLOUD2PATT_PORT}")
        RuntimeConfig.configuration = requests.get(f"{config.API_BASE_PATH}/api/v1/devices/{config.DEVICE_ID}/config").json()
        self.discovery_sock.send_json(MessageFormatter.parse_log(
            self.__class__.__name__,
            "Base config retrieved from API: \n{}".format(json.dumps(RuntimeConfig.configuration, indent=4))
        ))
        try:
            asyncio.run(listen_cloud_config(self.discovery_sock,self.cloud2patt))
        except KeyboardInterrupt :
            pass 