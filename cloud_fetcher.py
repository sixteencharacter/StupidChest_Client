import zmq
import json
import time
import config
import asyncio
import requests
from aiomqtt import Client
from dataclasses import dataclass
from multiprocessing import Process
from messages import MessageFormatter

# In memory cache
@dataclass
class RuntimeConfig :
    configuration = None

# Asyncio Task Loop
async def listen_cloud_config(discovery_sock : zmq.SyncSocket,cloud2patt_socket : zmq.SyncSocket) :
    try :
        async with Client(config.MQTT_HOST,timeout=1000) as client:
            while True :
                try :
                # TODO : listen to pattern change from cloud
                    await client.subscribe(f"knocklock/v1/devices/{config.DEVICE_ID}/config/#")
                    async for msg in client.messages :
                        if RuntimeConfig.configuration is not None :
                            print("CONFIG from cloud: {}".format(msg.payload.decode()))
                            RuntimeConfig.configuration["desired"]["data"] = json.loads(msg.payload.decode())["data"]
                            discovery_sock.send_json(MessageFormatter.parse_log(
                                CloudFetcherProc.__name__,
                                "Config changed to \n{}".format(json.dumps(RuntimeConfig.configuration,indent=4))
                            ))
                            cloud2patt_socket.send_json(MessageFormatter.parse_config_payload(
                                type="PARAMETERS",
                                payload = RuntimeConfig.configuration["desired"]["data"]
                            ))
                except Exception as e :
                    print(e)
                    
                await asyncio.sleep(0)
    except KeyboardInterrupt:
        pass # Graceful Shutdown

class CloudFetcherProc(Process) : 
    def __init__(self,*args,**kwargs) :
        super(CloudFetcherProc,self).__init__(*args,**kwargs)
    def run(self) :
        context = zmq.Context()
        self.discovery_sock = context.socket(zmq.PUB)
        self.discovery_sock.connect(f"{config.HOST}:{config.DISCOVERY_PORT}")
        time.sleep(2)
        self.cloud2patt = context.socket(zmq.PAIR)
        self.cloud2patt.bind(f"{config.HOST}:{config.CLOUD2PATT_PORT}")
        try :
            RuntimeConfig.configuration = requests.get(f"{config.API_BASE_PATH}/api/v1/devices/{config.DEVICE_ID}/config").json()
            self.discovery_sock.send_json(MessageFormatter.parse_module_status("CloudFetcher","Up"))
            self.discovery_sock.send_json(MessageFormatter.parse_log(
                self.__class__.__name__,
                "Base config retrieved from API: \n{}".format(json.dumps(RuntimeConfig.configuration, indent=4))
            ))
            try:
                asyncio.run(listen_cloud_config(self.discovery_sock,self.cloud2patt))
            except KeyboardInterrupt :
                pass
        except Exception as e:
            self.discovery_sock.send_json(MessageFormatter.parse_module_status("CloudFetcher","Down"))
            self.discovery_sock.send_json(MessageFormatter.parse_log(
                self.__class__.__name__,
                str(e)
            ))