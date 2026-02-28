from multiprocessing import Process
import zmq
import config
import time
from messages import MessageFormatter
from dataclasses import dataclass

@dataclass
class SerialConfig:
    last_sent_time  = time.time() * 1000


class PC2SerialProc(Process) : 
    def __init__(self,*args,**kwargs) :
        super(PC2SerialProc,self).__init__()
    def run(self) :
        context = zmq.Context()
        self.discovery_sock = context.socket(zmq.PUB)
        self.discovery_sock.connect(f"{config.HOST}:{config.DISCOVERY_PORT}")
        time.sleep(2)
        self.pc2serialIn = context.socket(zmq.PAIR)
        self.pc2serialIn.bind(f"{config.HOST}:{config.PC2SERIAL2PATTERN_PORT}")
        self.writeSocket = context.socket(zmq.PAIR)
        self.writeSocket.bind(f"{config.HOST}:{config.SERIAL_W_PORT}")
        try :
            self.discovery_sock.send_json(MessageFormatter.parse_module_status("PC2Serial","Up"))
            try:
                while True :
                    msg = self.pc2serialIn.recv_json()
                    if msg["payload"]["command"] == "unlock" :
                        if time.time() * 1000 - SerialConfig.last_sent_time > 5000 :
                            self.writeSocket.send_json(MessageFormatter.parse_data_transfer(command="unlock"))
                            self.discovery_sock.send_json(MessageFormatter.parse_log(
                                self.__class__.__name__,
                                "Box unlock signal sent!"
                            ))                
                            SerialConfig.last_sent_time = time.time() * 1000
                    time.sleep(0.5) 
            except KeyboardInterrupt :
                pass 
            except Exception as e :
                print(str(e))
        except Exception as e:
            self.discovery_sock.send_json(MessageFormatter.parse_module_status("PC2Serial","Down"))
            time.sleep(2)
            self.discovery_sock.send_json(MessageFormatter.parse_log(
                self.__class__.__name__,
                str(e)
            ))
