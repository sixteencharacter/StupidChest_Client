from multiprocessing import Process
import zmq
import config
import time
from messages import MessageFormatter
import serial
import numpy as np
import traceback
class Serial2PCProc(Process) : 
    def __init__(self,*args,**kwargs) :
        super(Serial2PCProc,self).__init__()
        self.stub_mode = kwargs["stub_mode"] if "stub_mode" in kwargs else False
    def run(self) :
        context = zmq.Context()
        self.discovery_sock = context.socket(zmq.PUB)
        self.discovery_sock.connect(f"{config.HOST}:{config.DISCOVERY_PORT}")
        time.sleep(2)
        self.serial2cloud_sock = context.socket(zmq.PAIR)
        self.serial2cloud_sock.bind(f"{config.HOST}:{config.SERIAL2CLOUD_PORT}")
        self.serial2pattern_sock = context.socket(zmq.PAIR)
        self.serial2pattern_sock.bind(f"{config.HOST}:{config.SERIAL2PATTERN_PORT}")
        try :
            self.serial_conn = None
            if not self.stub_mode :
                self.serial_conn = serial.Serial(config.SERIAL_PORT,baudrate=config.BAUDRATE,timeout=1)
            self.discovery_sock.send_json(MessageFormatter.parse_module_status("Serial2PC","Up"))
            try :
                while True :
                    if self.stub_mode or self.serial_conn.in_waiting > 0 :
                        dat = None
                        if self.stub_mode :
                            dat = int(np.random.random() * 1024)
                        else :
                            print(dat)
                            dat = int(self.serial_conn.readline().decode('utf8').rstip())
                        self.serial2pattern_sock.send_json(MessageFormatter.parse_data_transfer(raw_data=dat))
                        self.serial2cloud_sock.send_json(MessageFormatter.parse_data_transfer(raw_data=dat))
                    time.sleep(0.1)
            except KeyboardInterrupt :
                pass
            except Exception as e :
                print(str(e))
            finally :
                if not self.stub_mode :
                    self.serial_conn.close()
        except Exception as e:
            self.discovery_sock.send_json(MessageFormatter.parse_module_status("Serial2PC","Down"))
            time.sleep(2)
            self.discovery_sock.send_json(MessageFormatter.parse_log(
                self.__class__.__name__,
                str(e)
            ))