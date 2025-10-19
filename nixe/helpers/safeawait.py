import inspect
async def safe_await(maybe):
    if inspect.isawaitable(maybe):
        return await maybe
    return maybe
