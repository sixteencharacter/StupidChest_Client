from multiprocessing import Process
import zmq
import config
import time
from messages import MessageFormatter
import serial
import numpy as np

# TODO : add realistic stub mode for the serial broker (read)

class SerialBrokerProc(Process) : 
    def __init__(self,*args,**kwargs) :
        super(SerialBrokerProc,self).__init__(*args)
        self.useMockMode = True if kwargs.get("useMockMode") else False
    def run(self) :
        context = zmq.Context()
        self.discovery_sock = context.socket(zmq.PUB)
        self.discovery_sock.connect(f"{config.HOST}:{config.DISCOVERY_PORT}")
        time.sleep(2)
        self.discovery_sock.send_json(MessageFormatter.parse_module_status("SerialBroker","Up"))
        self.writeSocket = context.socket(zmq.PAIR)
        self.writeSocket.connect(f"{config.HOST}:{config.SERIAL_W_PORT}")
        self.serial2pattern_sock = context.socket(zmq.PAIR)
        self.serial2pattern_sock.bind(f"{config.HOST}:{config.SERIAL2PATTERN_PORT}")
        if not self.useMockMode :
            self.serial_conn = serial.Serial(config.SERIAL_PORT,baudrate=config.BAUDRATE,timeout=100)
        self.poller = zmq.Poller()
        self.poller.register(self.writeSocket , zmq.POLLIN)
        try:
            while True :
                socks = dict(self.poller.poll(timeout=0.1))
                try :
                    
                    if hasattr(self,'serial_conn') and self.serial_conn.in_waiting > 0  :
                        dat = int(self.serial_conn.readline().decode("utf-8",errors='ignore').rstrip())
                        self.serial2pattern_sock.send_json(MessageFormatter.parse_data_transfer(raw_data=dat))
                    else :
                        if np.random.random() < 0.05 : time.sleep(5)
                        dat = int(np.random.choice(np.arange(1,1024),size=1)[0])
                        print(dat)
                        if dat > 300 :
                            self.serial2pattern_sock.send_json(MessageFormatter.parse_data_transfer(raw_data=dat))
                    
                    if self.writeSocket in socks :
                        self.writeSocket.recv()
                        if hasattr(self,'serial_conn') :
                            self.serial_conn.write(config.UNLOCK_COMMAND.encode())
                            self.serial_conn.reset_output_buffer()
                except Exception as e:
                    print(e)
                time.sleep(0.1)
        except KeyboardInterrupt :
            pass