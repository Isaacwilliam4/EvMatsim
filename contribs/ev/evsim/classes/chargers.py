from abc import ABC

class Charger(ABC):
    type:str
    plug_power:float
    plug_count:int

class NoneCharger(Charger):
    type:str = "none"
    plug_power:float = 0
    plug_count:int = 0
    
class DynamicCharger(Charger):
    type:str = "dynamic"
    plug_power:float = 70
    plug_count:int = 9999

class StaticCharger(Charger):
    type:str = "default"
    plug_power:float = 100
    plug_count:int = 5