import os

def is_feature_enabled(feature_name: str) -> bool:
    # Feature flags disabled: always enable all features
    return True
