from __future__ import annotations
import functools
from typing import TypeVar, Callable, ParamSpec
P = ParamSpec("P"); R = TypeVar("R")
def lru_cache(maxsize=128):
    def decorator(func: Callable[P,R]) -> Callable[P,R]:
        c = functools.lru_cache(maxsize=maxsize)(func)
        @functools.wraps(func)
        def w(*a:P.args,**k:P.kwargs): return c(*a,**k)
        w.cache_info=c.cache_info; w.cache_clear=c.cache_clear; return w
    return decorator
def ttl_cache(ttl=60.0,maxsize=128):
    import time
    def d(func:Callable[P,R])->Callable[P,R]:
        cache={}
        @functools.wraps(func)
        def w(*a:P.args,**k:P.kwargs):
            key=functools.make_key(a,k,False); t=time.time()
            if key in cache:
                r,ts=cache[key]
                if t-ts<ttl: return r
            r=func(*a,**k); cache[key]=(r,t)
            if len(cache)>maxsize: del cache[min(cache,key=lambda k:cache[k][1])]
            return r
        w.cache_clear=cache.clear; return w
    return d