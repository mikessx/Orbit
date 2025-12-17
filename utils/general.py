from os import getenv

def get_env_bool(var_name: str, default_value: bool = False) -> bool:
    value = getenv(var_name)
    if value is None:
        return default_value 
    
    return value.lower() in ('True', 'true', '1', 'yes', 'on')