import inspect

from functools import wraps
from typing import Any, Dict, List, Type

import uvicorn
from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.routing import Route
from pydantic import (
    BaseModel,
    conint,
    constr,
)


class PydanticModel(BaseModel):
    uid: conint(gt=10, lt=1000)
    user_name: constr(min_length=2, max_length=4)


class PydanticOtherModel(BaseModel):
    age: conint(gt=1, lt=100)


def params_verify():
    """装饰器"""
    def wrapper(func):
        @wraps(func)
        async def request_param(request: Request, *args, **kwargs):
            # 获取参数
            if request.method == 'GET':
                param_dict: dict = dict(request.query_params)
            else:
                param_dict: dict = await request.json()
            sig: 'inspect.Signature' = inspect.signature(func)
            fun_param_dict: Dict[str, inspect.Parameter] = {
                key: sig.parameters[key]
                for key in sig.parameters
                if sig.parameters[key].annotation != inspect._empty
            }
            return_param: Any = sig.return_annotation
            try:
                func_args: List[BaseModel] = []
                for param in fun_param_dict.values():
                    if param.annotation is Request:
                        continue
                    model: BaseModel = param.annotation(**param_dict)
                    func_args.append(model)
                # 处理响应
                response: Any = await func(request, *func_args, **kwargs)
                if type(response) != return_param:
                    raise ValueError(f'response type != {return_param}')
                if dict is return_param:
                    return JSONResponse(response)
                raise TypeError(f'{type(response)} not support')
            except Exception as e:
                # 这里为了示范,把错误抛出来,这里改为e.json,错误信息会更详细的
                return JSONResponse({'error': str(e)})
        return request_param
    return wrapper


@params_verify()
async def demo_get(request: Request, model: PydanticModel, other_model: PydanticOtherModel) -> dict:
    return_dict = model.dict()
    return_dict.update(other_model.dict())
    return {'result': return_dict}


app = Starlette(
    routes=[
        Route('/api', demo_get, methods=['GET']),
    ]
)


if __name__ == "__main__":
    uvicorn.run(app)
