import os

def is_feature_enabled(feature_name: str) -> bool:
    return os.getenv(f"FEATURE_{feature_name.upper()}", "false").lower() == "true"
