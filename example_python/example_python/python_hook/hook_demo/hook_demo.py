import importlib
import sys
from functools import wraps
from typing import cast, Any, Callable, Optional
from types import ModuleType


def func_wrapper(func: Callable):
    @wraps(func)
    def wrapper(*args, **kwargs) -> Any:
        start: float = time.time()
        result: Any = func(*args, **kwargs)
        end: float = time.time()
        print(f"speed time:{end - start}")
        return result
    return cast(Callable, wrapper)


class MetaPathFinder:

    @staticmethod
    def find_module(fullname: str, path: Optional[str] = None) -> Optional["MetaPathLoader"]:
        print(f'find module:{fullname}')
        if fullname == 'time':
            return MetaPathLoader()
        else:
            return None


class MetaPathLoader:

    @staticmethod
    def load_module(fullname: str) -> ModuleType:
        print(f'load module:{fullname}')
        if fullname in sys.modules:
            return sys.modules[fullname]
        # 防止递归调用
        finder: "MetaPathFinder" = sys.meta_path.pop(0)
        # 导入 module
        module: ModuleType = importlib.import_module(fullname)
        module.sleep = func_wrapper(module.sleep)
        sys.meta_path.insert(0, finder)
        return module


sys.meta_path.insert(0, MetaPathFinder())


if __name__ == '__main__':
    import datetime
    import time
    time.sleep(1)
