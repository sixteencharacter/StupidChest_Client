#!/usr/bin/env python

import zmq
import config 
from serial2pc import Serial2PCProc
from pc2serial import PC2SerialProc
from pattern_recog import PatternRecogProc
from cloud_fetcher import CloudFetcherProc
from cloud_worker import CloudWorkerProc
from typing import List
from multiprocessing import Process
from halo import Halo
from time import sleep
from typing import Tuple
import termcolor

processes : List[Process] = []
moduleStatuses = dict()

def setup_subscriber() -> Tuple[zmq.Context,zmq.SyncSocket] :
    context = zmq.Context()
    subscriber = context.socket(zmq.SUB)
    subscriber.setsockopt_string(zmq.SUBSCRIBE, "")
    subscriber.bind(f"{config.HOST}:{config.DISCOVERY_PORT}")
    return context , subscriber

def start_processes() :
    global processes
    processes.append(Serial2PCProc()) # dev mode
    processes.append(PC2SerialProc()) # dev mode
    # processes.append(Serial2PCProc())
    # processes.append(PC2SerialProc())
    processes.append(PatternRecogProc())
    processes.append(CloudWorkerProc())
    processes.append(CloudFetcherProc())
    for p in processes :
        p.start()

def cleanup_processes() :
    global processes
    for p in processes :
        if p.is_alive :
            p.terminate()

if __name__ == "__main__" :
    context , main_subscriber = setup_subscriber()
    start_processes()
    try :
        # Startup stage
        with Halo(text="Starting up modules",color="cyan",spinner="dots") as ht :
            while len(moduleStatuses) < len(processes) :
                content = main_subscriber.recv_json()
                if content["type"] == "MODULE_STATUS_UPDATE" :
                    moduleStatuses[content["payload"]["moduleName"]] = content["payload"]["status"]
                    ht.text = "Module Loaded [{}/{}]".format(len(moduleStatuses),len(processes))
            ht.spinner = None
        print("✔ All module Loaded successfully")
        for mod in moduleStatuses :
            cmap = "light_green" if moduleStatuses[mod] == "Up" else "light_red"
            print(termcolor.colored(f"[ {moduleStatuses[mod]} ]",cmap) + f" {mod} module")
        # Logging stage
        while True :
            msg = main_subscriber.recv_json()
            if msg["type"] == "LOG" :
                print(f"[{msg["payload"]["moduleName"]}] {msg["payload"]["content"]}")
    except KeyboardInterrupt:
        main_subscriber.close()
        cleanup_processes()
        context.term()