from multiprocessing import Process
import zmq
import config
import time
from messages import MessageFormatter
import serial

# TODO : add realistic stub mode for the serial broker (read)

class SerialBrokerProc(Process) : 
    def __init__(self,*args,**kwargs) :
        super(SerialBrokerProc,self).__init__(*args,**kwargs)
        self.stub_mode = kwargs["stub_mode"] if "stub_mode" in kwargs else False
    def run(self) :
        context = zmq.Context()
        self.discovery_sock = context.socket(zmq.PUB)
        self.discovery_sock.connect(f"{config.HOST}:{config.DISCOVERY_PORT}")
        time.sleep(2)
        self.discovery_sock.send_json(MessageFormatter.parse_module_status("SerialBroker","Up"))
        self.writeSocket = context.socket(zmq.PAIR)
        self.writeSocket.connect(f"{config.HOST}:{config.SERIAL_W_PORT}")
        self.serial2cloud_sock = context.socket(zmq.PAIR)
        self.serial2cloud_sock.bind(f"{config.HOST}:{config.SERIAL2CLOUD_PORT}")
        self.serial2pattern_sock = context.socket(zmq.PAIR)
        self.serial2pattern_sock.bind(f"{config.HOST}:{config.SERIAL2PATTERN_PORT}")
        self.serial_conn = serial.Serial(config.SERIAL_PORT,baudrate=config.BAUDRATE,timeout=100)
        self.poller = zmq.Poller()
        self.poller.register(self.writeSocket , zmq.POLLIN)
        try:
            while True :
                socks = dict(self.poller.poll(timeout=0.1))
                try :
                    if self.serial_conn.in_waiting > 0 :
                        dat = int(self.serial_conn.readline().decode("utf-8",errors='ignore').rstrip())
                        print(type(dat),dat)
                        self.serial2pattern_sock.send_json(MessageFormatter.parse_data_transfer(raw_data=dat))
                        self.serial2cloud_sock.send_json(MessageFormatter.parse_data_transfer(raw_data=dat))
                    if self.writeSocket in socks :
                        self.serial_conn.write(config.UNLOCK_COMMAND.encode())
                except :
                    pass
                time.sleep(0.1)
        except KeyboardInterrupt :
            pass