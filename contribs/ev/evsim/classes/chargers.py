from abc import ABC

class Charger(ABC):
    type:str
    plug_power:float
    plug_count:int
    price:float

class NoneCharger(Charger):
    type:str = "none"
    plug_power:float = 0
    plug_count:int = 0
    price:0
    
class DynamicCharger(Charger):
    type:str = "dynamic"
    plug_power:float = 70
    plug_count:int = 9999

    # cost in USD per km, pulled from https://www.nature.com/articles/s41467-024-49157-5
    price:2_600_000

class StaticCharger(Charger):
    type:str = "default"
    plug_power:float = 150
    plug_count:int = 5
    # cost in USD per charger, pulled from https://www.nature.com/articles/s41467-024-49157-5
    price:120_000