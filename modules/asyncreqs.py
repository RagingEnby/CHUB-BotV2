import curl_cffi as curl
import constants


_session: curl.AsyncSession | None = None


async def get_session() -> curl.AsyncSession:
    global _session
    if _session is None:
        _session = curl.AsyncSession()
    return _session


async def close():
    if _session is not None:
        await _session.close()


async def get(url: str, *args, **kwargs) -> curl.Response:
    proxy = constants.PROXY if "hypixel.net" in url else None
    impersonate: curl.BrowserTypeLiteral | None = "chrome" if proxy else None
    session = await get_session()
    return await session.get(url, *args, **kwargs, proxy=proxy, impersonate=impersonate)
