from typing import Callable

_PARSER_REGISTRY = {}

def register_parser(pattern: str):
    def decorator(func):
        _PARSER_REGISTRY[pattern] = func
        return func
    return decorator

def get_parser(sheet_name: str) -> Callable:
    import src.sheet_parsers as sheet_parsers
    
    # Try exact match or pattern match from registry
    for pattern, func in _PARSER_REGISTRY.items():
        if pattern == sheet_name or pattern in sheet_name:
            return func
            
    # Fallback to function name conversion
    func_name = "parse_" + "".join(c if c.isalnum() else '_' for c in sheet_name).strip('_')
    func_name = func_name.replace('__', '_')
    if hasattr(sheet_parsers, func_name):
        return getattr(sheet_parsers, func_name)
    
    return None
