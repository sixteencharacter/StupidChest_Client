from typing import Literal , Union , Dict
from pydantic import BaseModel

class ModuleStatUpdatePayload(BaseModel) :
    moduleName : str
    status : Literal["Up","Down"]

class SimpleLogPayload(BaseModel) :
    moduleName : str
    content : str

class Patten2UnlockPayload(BaseModel) :
    command : Literal["lock","unlock"]

class PatternModuleConfigMessage(BaseModel) :
    type : Literal["PATTERN","PARAMETERS"]
    cfgs : Dict[str,Union[str,int]]

class StandardizedMessage(BaseModel) :
    type : Literal["MODULE_STATUS_UPDATE","DATA","LOG"]
    payload : Union[ModuleStatUpdatePayload,SimpleLogPayload,Patten2UnlockPayload,PatternModuleConfigMessage]

class MessageFormatter :
    @staticmethod
    def parse_module_status(modName : str , modType : Literal["Up","Down"] = "Up") :
        return StandardizedMessage(type="MODULE_STATUS_UPDATE",payload={
            "moduleName" : modName,
            "status" : modType
        }).model_dump()
    
    @staticmethod
    def parse_data_transfer(command : Literal["lock","unlock"]) :
        return StandardizedMessage(type="DATA",payload={"command":command}).model_dump()
    
    @staticmethod
    def parse_config_payload(type : str,payload : any) :
        return StandardizedMessage(type="DATA",payload={"cfgs" : payload,"type" : type}).model_dump()

    @staticmethod
    def parse_log(modName,context : str) :
        return StandardizedMessage(type="LOG",payload={"moduleName":modName , "content" : context}).model_dump()