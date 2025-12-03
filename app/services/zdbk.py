import httpx
from typing import Tuple

class ZdbkLoginError(Exception):
    pass

CAS_SERVICE = "https%3A%2F%2Fzdbk.zju.edu.cn%2Fjwglxt%2Fxtgl%2Flogin_ssologin.html"
CAS_LOGIN_WITH_SERVICE = f"https://zjuam.zju.edu.cn/cas/login?service={CAS_SERVICE}"
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36"


async def login_with_sso_get_jw_cookies(sso_cookie: str) -> Tuple[str, str]:
    """
    用统一认证 iPlanetDirectoryPro 获取教务系统会话：
    返回 (JSESSIONID for /jwglxt, route)
    """
    headers = {
        "User-Agent": UA,
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Referer": CAS_LOGIN_WITH_SERVICE,
    }
    cookies = {
        # 显式随请求携带 SSO
        "iPlanetDirectoryPro": sso_cookie
    }

    async with httpx.AsyncClient(timeout=12, follow_redirects=False, headers=headers) as client:
        # 第一步：访问 CAS 带 service 的登录入口
        r1 = await client.get(CAS_LOGIN_WITH_SERVICE, cookies=cookies)
        loc = r1.headers.get("location")
        if not loc:
            # 打印辅助信息便于排查
            snippet = (r1.text or "")[:200].replace("\n", " ")
            print("[ZDBK] CAS no location, status:", r1.status_code, "| body:", snippet)
            raise ZdbkLoginError("CAS 跳转未返回 location（可能 SSO 无效或已过期）")
        if loc.startswith("http://"):
            loc = loc.replace("http://", "https://", 1)

        # 第二步：请求跳转地址（教务域），从响应 cookies 获取 JSESSIONID(/jwglxt) 与 route
        r2 = await client.get(loc, cookies=cookies, follow_redirects=False)

        jsessionid = None
        route = None
        for c in r2.cookies.jar:
            if c.name == "JSESSIONID" and c.path == "/jwglxt":
                jsessionid = c.value
            if c.name == "route":
                route = c.value

        if not jsessionid:
            print("[ZDBK] set-cookie:", r2.headers.get("set-cookie"))
            raise ZdbkLoginError("无法获取 JSESSIONID（/jwglxt）")
        if not route:
            print("[ZDBK] set-cookie:", r2.headers.get("set-cookie"))
            raise ZdbkLoginError("无法获取 route")

        return jsessionid, route