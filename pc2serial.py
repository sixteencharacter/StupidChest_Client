from multiprocessing import Process
import zmq
import config
import time
from messages import MessageFormatter
import serial

class PC2SerialProc(Process) : 
    def __init__(self,*args,**kwargs) :
        super(PC2SerialProc,self).__init__()
        self.stub_mode = kwargs["stub_mode"] if "stub_mode" in kwargs else False
    def run(self) :
        context = zmq.Context()
        self.discovery_sock = context.socket(zmq.PUB)
        self.discovery_sock.connect(f"{config.HOST}:{config.DISCOVERY_PORT}")
        time.sleep(2)
        self.pc2serialIn = context.socket(zmq.PAIR)
        self.pc2serialIn.bind(f"{config.HOST}:{config.PC2SERIAL2PATTERN_PORT}")
        try :
            self.serial_conn = None
            if not self.stub_mode :
                self.serial_conn = serial.Serial(config.SERIAL_PORT,baudrate=config.BAUDRATE,timeout=1)
            self.discovery_sock.send_json(MessageFormatter.parse_module_status("PC2Serial","Up"))
            try:
                while True :
                    msg = self.pc2serialIn.recv_json()
                    if msg["payload"]["command"] == "unlock" :
                        if not self.stub_mode :
                            self.serial_conn.write(b'{}\n'.format(config.UNLOCK_COMMAND))
                        self.discovery_sock.send_json(MessageFormatter.parse_log(
                            self.__class__.__name__,
                            "Box unlock signal sent!"
                        ))
                    else :
                        if not self.stub_mode :
                            self.serial_conn.write(b'{}\n'.format(config.LOCK_COMMAND))
                        self.discovery_sock.send_json(MessageFormatter.parse_log(
                            self.__class__.__name__,
                            "Box lock signal sent!"
                        ))                
                    time.sleep(1) 
            except KeyboardInterrupt :
                pass 
            finally :
                if not self.stub_mode :
                    self.serial_conn.close()
        except Exception as e:
            self.discovery_sock.send_json(MessageFormatter.parse_module_status("PC2Serial","Down"))
            time.sleep(2)
            self.discovery_sock.send_json(MessageFormatter.parse_log(
                self.__class__.__name__,
                str(e)
            ))
