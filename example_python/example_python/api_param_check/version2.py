import ast
from functools import wraps
from typing import Any, Callable, Dict, List, Optional, Type, Union


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
        _type: Type,
        default: Any = MISS_OBJECT,
        max_length: Optional[int] = None,
        max_value: Optional[int] = None,
        min_value: Optional[int] = None,
    ):
        self._type: Type = _type
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

    def __set__(self, instance: 'object()', value: Union[str, Any]):
        # 写入数据
        if value is MISS_OBJECT:
            # 如果是空数据,且没设置默认值,则抛错
            if self._default is not MISS_OBJECT:
                value = self._default
            else:
                raise ValueError('value must not empty')

        if value is not None:
            # 类型转换
            if type(value) != self._type:
                value = ast.literal_eval(value)
                value = self._type(value)

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

    def __delete__(self, instance):
        del self._dict[instance]


class Model:
    def __init__(self):
        """这里把类属性的值设置到field_dict"""
        self.field_list: List[str] = []
        for key in self.__dir__():
            # 屏蔽自带方法,或其他私有方法
            if key.startswith('_'):
                continue
            if key in self.__dict__:
                continue
            try:
                getattr(self, key)
            except CustomValueError:
                # 还没初始化数据,所以会抛出CustpmValueError错误
                self.field_list.append(key)

    def to_dict(self) -> Dict[str, Any]:
        """把{参数}={类型}转为dict"""
        return {
            key: getattr(self, key)
            for key in self.field_list
        }


class CustomModel(Model):
    uid = Field(int, min_value=10, max_value=100)
    timestamp = Field(int, default=None)
    user_info = Field(dict, default=None)
    user_name = Field(str, max_length=4)


def params_verify(model: Type[Model]):
    """装饰器"""
    def wrapper(func: Callable):
        @wraps(func)
        async def request_param(request: Request, *args, **kwargs):
            # 获取参数, 这里只做简单演示, 只获取url和json请求的数据
            param_dict: dict = dict(request.query_params)
            if request.method == "POST":
                param_dict.update(await request.json())
            instance_model: Model = model()
            try:
                for key in instance_model.field_list:
                    value = param_dict.get(key, MISS_OBJECT)
                    setattr(instance_model, key, value)
                # 把model设置到request.stat里面,方便调用
                request.state.model = instance_model
                # 处理响应
                return await func(request, *args, **kwargs)
            except Exception as e:
                # 这里为了示范,把错误抛出来
                return JSONResponse({'error': str(e)})
        return request_param
    return wrapper


@params_verify(CustomModel)
async def demo_post(request):
    # 适配修改
    return JSONResponse({'result': request.state.model.to_dict()})


@params_verify(CustomModel)
async def demo_get(request):
    # 适配修改
    return JSONResponse({'result': request.state.model.to_dict()})


app = Starlette(
    routes=[
        Route('/api', demo_post, methods=['POST']),
        Route('/api', demo_get, methods=['GET']),
    ]
)


if __name__ == "__main__":
    uvicorn.run(app)
