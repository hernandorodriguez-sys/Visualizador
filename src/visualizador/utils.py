from .config import LEADS

def get_current_lead(current_lead_index):
    """Obtiene derivación actual"""
    return LEADS[current_lead_index] if current_lead_index < len(LEADS) else "??"