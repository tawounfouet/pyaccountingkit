from .complete import build_capability_status

# Backward-compatible function name retained for callers from release 0.7.0.
def build_capability_gaps():
    return build_capability_status()
