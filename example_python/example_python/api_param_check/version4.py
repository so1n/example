import ast
import inspect

from functools import wraps
from typing import Any, Callable, Dict, Optional, Tuple, Type, Union, _GenericAlias

import uvicorn
from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.routing import Route


class CustomValueError(ValueError):
    """异常"""
    pass


MISS_OBJECT: 'object()' = object()  # 用于判空且非None


class Field:
    def __init__(
        self,
        default: Any = MISS_OBJECT,
        max_length: Optional[int] = None,
        max_value: Optional[int] = None,
        min_value: Optional[int] = None,
    ):
        self._default: Any = default
        self._max_length: Optional[int] = max_length
        self._max: Optional[int] = max_value
        self._min: Optional[int] = min_value
        self._dict: Dict[str, Any] = {}

    def __get__(self, instance: 'object()', owner: Type) -> Any:
        # 获取数据
        try:
            value = self._dict[instance]
        except Exception as e:
            raise CustomValueError('value must not empty') from e
        return value

    def __set__(self, instance: 'object()', value_tuple: Tuple[Any, Union[Type, _GenericAlias]]):
        # 写入数据
        value, key_type = value_tuple
        if value is MISS_OBJECT:
            # 如果是空数据,且没设置默认值,则抛错
            if self._default is not MISS_OBJECT:
                value = self._default
            else:
                raise ValueError('value must not empty')
        if value is not None:
            # 类型转换
            value = self.type_handle(value, key_type)
            if isinstance(value, str) or isinstance(value, list) or isinstance(value, tuple):
                # 限制字符,list串长度
                if self._max_length and len(value) > self._max_length:
                    raise ValueError(f'value length:{len(value)} > {self._max_length}')
            elif isinstance(value, int) or isinstance(value, float):
                # 限制数字范围
                if self._max is not None and value > self._max:
                    value = self._max
                elif self._min is not None and value < self._min:
                    value = self._min
        self._dict[instance] = value

    def __delete__(self, instance: 'object()'):
        del self._dict[instance]
    
    def type_handle(self, value: Any, key_type: Union[Type, _GenericAlias]) -> Any:
        """兼容TyepHint和python基础类型转换的handle
        目前只支持typing的Union,Option和所有Python的基础类型
        """
        if hasattr(key_type, '__origin__') and key_type.__origin__ is Union:
            # get typing.type from Union
            key_type = key_type.__args__
        if not isinstance(value, key_type):
            try:
                if isinstance(key_type, tuple):
                    for i in key_type:
                        try:
                            value = self._python_type_conversion(i, value)
                            break
                        except TypeError:
                            value = None
                    else:
                        raise TypeError
                else:
                    value = self._python_type_conversion(key_type, value)
            except Exception:
                raise TypeError(f"The type should be {key_type}")
        return value

    @staticmethod
    def _python_type_conversion(key_type: Type, value: str) -> Any:
        """Python基础类型转换"""
        value = ast.literal_eval(value)
        if type(value) == key_type:
            return value
        try:
            return key_type(value)
        except Exception:
            raise TypeError(f"Value type:{type(value)} is not {key_type}")


class Model:
    def __init__(self):
        """这里把类属性的值设置到field_dict"""
        self.field_dict = {}
        # 这里调用的是self.__annotations__,里面存着类属性的key, type
        for key in self.__annotations__:
            # 屏蔽自带方法,或其他私有方法
            if key.startswith('_'):
                continue
            if key in self.__dict__:
                continue
            try:
                getattr(self, key)
            except CustomValueError:
                # 还没初始化数据,所以会抛出CustpmValueError错误
                self.field_dict[key] = self.__annotations__[key]
                
    def to_dict(self):
        """把{参数}={类型}转为dict"""
        return {
            key: getattr(self, key)
            for key in self.field_dict
        }


class CustomModel(Model):
    uid: Union[str, int] = Field(min_value=10, max_value=100)
    timestamp: int = Field(default=None)
    user_info: dict = Field(default=None)
    user_name: str = Field(max_length=4)


class CustomOtherModel(Model):
    age: int = Field(min_value=1, max_value=100)


def params_verify():
    """装饰器"""
    def wrapper(func: Callable):
        @wraps(func)
        async def request_param(request: Request, *args, **kwargs):
            # 获取参数, 这里只做简单演示, 只获取url和json请求的数据
            param_dict: dict = dict(request.query_params)
            if request.method == "POST":
                param_dict.update(await request.json())
            sig: 'inspect.Signature' = inspect.signature(func)
            fun_param_dict: Dict[str, inspect.Parameter] = {
                key: sig.parameters[key]
                for key in sig.parameters
                if sig.parameters[key].annotation != inspect._empty
            }
            return_param: Type = sig.return_annotation
            try:
                # 对参数进行转换,并返回给函数
                func_args = []
                for param in fun_param_dict.values():
                    model: Model = param.annotation()
                    for key, key_type in model.field_dict.items():
                        value: Any = param_dict.get(key, MISS_OBJECT)
                        setattr(model, key, (value, key_type))
                    func_args.append(model)
                # 处理响应
                response = await func(request, *func_args, **kwargs)
                # 响应检查
                if type(response) != return_param:
                    raise ValueError(f'response type != {return_param}')
                if dict is return_param:
                    return JSONResponse(response)
                raise TypeError(f'{type(response)} not support')
            except Exception as e:
                # 这里为了示范,把错误抛出来
                return JSONResponse({'error': str(e)})
        return request_param
    return wrapper


# 装饰器移除了参数, 改为从函数参数传入
@params_verify()
async def demo_get(request, model: CustomModel, other_model: CustomOtherModel) -> dict:
    return_dict = model.to_dict()
    return_dict.update(other_model.to_dict())
    return {'result': return_dict}


app = Starlette(
    routes=[
        Route('/api', demo_get, methods=['GET']),
    ]
)


if __name__ == "__main__":
    uvicorn.run(app)
