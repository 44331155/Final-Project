import httpx
import json
import re
from typing import Dict, List, Tuple
from .zdbk import login_with_sso_get_jw_cookies, ZdbkLoginError

class TimetableFetchError(Exception):
    pass

def parse_semester_id(semester_id: str) -> Tuple[str, str]:
    """
    将 2024-2025-1 映射为 (xnm, xqm)
    默认规则：
      - xnm = 起始年（例：2024）
      - xqm = 1 学期 -> （秋冬），2 学期 -> （春夏）
    """
    parts = semester_id.split("-")
    if len(parts) < 3:
        raise TimetableFetchError(f"无效的学期格式: {semester_id}")
    xnm = parts[0]
    term = parts[-1]
    xqm = "1" if term == "1" else "2"
    return xnm, xqm

def xqm_from_xxq(xxq: str) -> str:
    """
    将中文学期标识映射为 xqm：
      - 秋冬 -> 1
      - 春夏 -> 2
    """
    if not xxq:
        return ""
    if "秋冬" in xxq:
        return "1"
    if "春夏" in xxq:
        return "2"
    return ""

def semester_from_xkkh(xkkh: str) -> str:
    """
    从 xkkh 抽取学期标识，例如：
      "(2025-2026-1)-BME3001M-0020237-1" -> "2025-2026-1"
    """
    if not xkkh:
        return ""
    m = re.match(r"^\((\d{4}-\d{4}-[12])\)", xkkh)
    return m.group(1) if m else ""

async def fetch_kblist(sso_cookie: str, semester_id: str, strict_filter: bool = True) -> List[Dict]:
    """
    直接返回原始 kbList 数组。
    strict_filter=True：按 xkkh/xxq 过滤为目标学期；False：原样返回不筛选。
    """
    try:
        jsessionid, route = await login_with_sso_get_jw_cookies(sso_cookie)
    except ZdbkLoginError as e:
        raise TimetableFetchError(f"教务登录失败: {e}")

    xnm, xqm = parse_semester_id(semester_id)
    cookies = {"JSESSIONID": jsessionid, "route": route}
    headers = {
        "Content-Type": "application/x-www-form-urlencoded; charset=utf-8",
        "Referer": "https://zdbk.zju.edu.cn/jwglxt/xtgl/index_initMenu.html",
        "Origin": "https://zdbk.zju.edu.cn",
        "User-Agent": "Mozilla/5.0",
    }
    url = "https://zdbk.zju.edu.cn/jwglxt/kbcx/xskbcx_cxXsKb.html"
    body = f"xnm={xnm}&xqm={xqm}"

    async with httpx.AsyncClient(timeout=15, follow_redirects=False) as client:
        resp = await client.post(url, content=body, cookies=cookies, headers=headers)
        raw = resp.text

        m = re.search(r'(?<="kbList":)\[(.*?)\](?=,"xh")', raw)
        if not m:
            print("[TT] kbList not found. status:", resp.status_code)
            print("[TT] snippet:", raw[:800].replace("\n", " "))
            raise TimetableFetchError("无法解析课表（kbList 未找到）")

        kb_list = json.loads(m.group(0))

        if not strict_filter:
            return kb_list

        # 严格筛选到目标学期
        filtered = []
        for e in kb_list:
            entry_sem_id = semester_from_xkkh(e.get("xkkh", ""))
            if entry_sem_id and entry_sem_id != semester_id:
                continue
            entry_xqm = xqm_from_xxq(e.get("xxq", ""))
            if entry_xqm and entry_xqm != xqm:
                continue
            filtered.append(e)
        return filtered