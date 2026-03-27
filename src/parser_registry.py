from typing import Callable

_PARSER_REGISTRY = {}

def register_parser(pattern: str):
    def decorator(func):
        _PARSER_REGISTRY[pattern] = func
        return func
    return decorator

def get_parser(sheet_name: str) -> Callable:
    import src.sheet_parsers as sheet_parsers
    
    # 1) 精确匹配优先
    if sheet_name in _PARSER_REGISTRY:
        return _PARSER_REGISTRY[sheet_name]

    # 2) 包含匹配：按 pattern 长度从长到短排序，确保更具体的 pattern 优先命中
    #    例如 "备份P SF乱评" 应先于 "乱评" 被匹配
    for pattern, func in sorted(_PARSER_REGISTRY.items(), key=lambda x: len(x[0]), reverse=True):
        if pattern in sheet_name:
            return func
            
    # 3) Fallback: 按函数名转换查找
    func_name = "parse_" + "".join(c if c.isalnum() else '_' for c in sheet_name).strip('_')
    func_name = func_name.replace('__', '_')
    if hasattr(sheet_parsers, func_name):
        return getattr(sheet_parsers, func_name)
    
    return None
