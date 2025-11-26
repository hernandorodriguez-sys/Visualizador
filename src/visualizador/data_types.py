from typing import NamedTuple

class ADCData(NamedTuple):
    """Data structure for ADC readings"""
    timestamp: int
    voltage: float
    source: str  # 'esp32' or 'arduino'
    metadata: dict = None  # Additional data like lead changes, energies, etc.