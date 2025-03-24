from abc import ABC


class Charger(ABC):
    """
    Abstract base class for chargers. Defines common attributes for all
    charger types.
    """

    type: str
    plug_power: float
    plug_count: int
    price: float


class NoneCharger(Charger):
    """
    Represents a charger with no functionality. Used as a placeholder or
    default option.
    """

    type: str = "none"
    plug_power: float = 0
    plug_count: int = 0
    price: 0


class DynamicCharger(Charger):
    """
    Represents a dynamic charger with high plug count and power. Includes
    cost per km based on external research.
    """

    type: str = "dynamic"
    plug_power: float = 70
    plug_count: int = 9999
    price: float = 2_600_000  # Cost in USD per km


class StaticCharger(Charger):
    """
    Represents a static charger with fixed plug count and power. Includes
    cost per charger based on external research.
    """

    type: str = "default"
    plug_power: float = 150
    plug_count: int = 1
    price: float = 120_000  # Cost in USD per charger
