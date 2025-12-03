import httpx
import re

LOGIN_URL = "https://zjuam.zju.edu.cn/cas/login"
PUBKEY_URL = "https://zjuam.zju.edu.cn/cas/v2/getPubKey"

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36"

def rsa_encrypt_hex_no_padding(password: str, modulus_hex: str, exponent_hex: str) -> str:
    """
    仓库同款原始 RSA：utf8 -> hex -> int，pow(m, e, n) -> hex，左侧补零到 128 位
    """
    pwd_hex = password.encode("utf-8").hex()
    m = int(modulus_hex, 16)
    e = int(exponent_hex, 16)
    p = int(pwd_hex, 16)
    c = pow(p, e, m)  # 原始幂模，无填充
    enc_hex = format(c, "x").zfill(128)  # 与 Dart 版 padLeft(128, '0') 对齐
    return enc_hex

async def get_sso_cookie(username: str, password: str) -> str:
    """
    返回 iPlanetDirectoryPro 的值（服务端内部保存）
    """
    headers = {"User-Agent": UA, "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"}
    async with httpx.AsyncClient(timeout=10, follow_redirects=False, headers=headers) as client:
        # 1) 拿 execution
        r1 = await client.get(LOGIN_URL)
        m = re.search(r'name="execution"\s+value="(.*?)"', r1.text)
        if not m:
            raise Exception("无法获取 execution")
        execution = m.group(1)

        # 2) 取公钥
        r2 = await client.get(PUBKEY_URL)
        pub = r2.json()
        modulus = pub.get("modulus")
        exponent = pub.get("exponent")
        if not modulus or not exponent:
            raise Exception("无法获取 RSA 公钥")

        # 3) 原始 RSA 加密（无填充）
        pwd_enc_hex = rsa_encrypt_hex_no_padding(password, modulus, exponent)

        # 4) 提交登录（表单）
        form = {
            "username": username,
            "password": pwd_enc_hex,
            "execution": execution,
            "_eventId": "submit",
            "rememberMe": "true",
        }
        r3 = await client.post(
            LOGIN_URL,
            data=form,
            headers={
                "User-Agent": UA,
                "Content-Type": "application/x-www-form-urlencoded",
                "Origin": "https://zjuam.zju.edu.cn",
                "Referer": LOGIN_URL,
            },
        )

        # 有的实现把 cookie 写在响应里，有的会更新到 client.cookies
        # 两个地方都找一下
        def find_cookie(jar) -> str | None:
            for c in jar:
                if c.name == "iPlanetDirectoryPro":
                    return c.value
            return None

        cookie_val = find_cookie(r3.cookies.jar) if hasattr(r3.cookies, "jar") else None
        if not cookie_val:
            cookie_val = find_cookie(client.cookies.jar)

        if not cookie_val:
            # 辅助诊断：部分情况下会返回 302，并把 cookie 写在下一跳；也可尝试跟随一次重定向
            # 如果仍拿不到，多半是账号/密码错误或学校引入了额外验证（验证码/二次认证）
            raise Exception("登录失败或未返回 iPlanetDirectoryPro")

        return cookie_val