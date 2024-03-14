import sys

def debugger_is_active() -> bool:
    """Check if the debugger is currently active"""
    return hasattr(sys, "gettrace") and sys.gettrace() is not None