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
      - xqm = 1 学期 -> 3（秋冬），2 学期 -> 12（春夏）
    如有差异请按实际调整。
    """
    parts = semester_id.split("-")
    if len(parts) < 3:
        raise TimetableFetchError(f"无效的学期格式: {semester_id}")
    xnm = parts[0]
    term = parts[-1]
    xqm = "3" if term == "1" else "12"
    return xnm, xqm


def parse_weeks(zcd: str) -> List[int]:
    """
    解析常见周次字符串：如 "1-8周", "1,3,5周", "1-4,6-8周"
    """
    if not zcd:
        return [1]
    s = zcd.replace("周", "").replace(" ", "")
    weeks = set()
    for part in s.split(","):
        if not part:
            continue
        if "-" in part:
            a, b = part.split("-", 1)
            if a.isdigit() and b.isdigit():
                for w in range(int(a), int(b) + 1):
                    weeks.add(w)
        else:
            if part.isdigit():
                weeks.add(int(part))
    return sorted(list(weeks)) or [1]


async def fetch_and_parse_timetable(sso_cookie: str, semester_id: str) -> Dict:
    try:
        jsessionid, route = await login_with_sso_get_jw_cookies(sso_cookie)
    except ZdbkLoginError as e:
        raise TimetableFetchError(f"教务登录失败: {e}")

    xnm, xqm = parse_semester_id(semester_id)

    cookies = {
        "JSESSIONID": jsessionid,
        "route": route
    }
    headers = {
        "Content-Type": "application/x-www-form-urlencoded; charset=utf-8",
        "Referer": "https://zdbk.zju.edu.cn/jwglxt/xtgl/index_initMenu.html",
        "Origin": "https://zdbk.zju.edu.cn",
        "User-Agent": "Mozilla/5.0",
    }
    url = "https://zdbk.zju.edu.cn/jwglxt/kbcx/xskbcx_cxXsKb.html"
    body = f"xnm={xnm}&xqm={xqm}"

    async with httpx.AsyncClient(timeout=15, follow_redirects=False) as client:
        try:
            # 请求课表
            resp = await client.post(url, content=body, cookies=cookies, headers=headers)
            raw = resp.text

            # 从 HTML 中提取 "kbList":[...]
            m = re.search(r'(?<="kbList":)\[(.*?)\](?=,"xh")', raw)
            if not m:
                print("[TT] kbList not found. status:", resp.status_code)
                print("[TT] snippet:", raw[:400].replace("\n", " "))
                raise TimetableFetchError("无法解析课表（kbList 未找到）")

            kb_json = m.group(0)
            kb_list = json.loads(kb_json)

            sessions = []
            courses_map = {}  # code -> name

            for item in kb_list:
                # 兼容字段：优先 kcmc（课程名称），退化到 kcb
                course_name = item.get("kcmc") or item.get("kcb") or ""
                if not course_name:
                    continue
                course_code = item.get("kch") or item.get("kcb") or course_name
                classroom = item.get("cdmc") or item.get("cdjc") or ""
                # 星期：xqj（1-7）
                weekday = int(item.get("xqj") or 1)
                # 节次：jc 可能为 "3-4" 或 "3"
                jc = (item.get("jc") or "1").strip()
                if "-" in jc:
                    a, b = jc.split("-", 1)
                    start_slot = int(a)
                    end_slot = int(b)
                else:
                    start_slot = end_slot = int(jc)
                # 周次：zcd
                weeks = parse_weeks(item.get("zcd") or "")

                courses_map[course_code] = course_name
                sessions.append({
                    "courseCode": course_code,
                    "courseName": course_name,
                    "weekday": weekday,
                    "start_slot": start_slot,
                    "end_slot": end_slot,
                    "classroom": classroom,
                    "weeks": weeks,
                })

            courses = [{"code": code, "name": name} for code, name in courses_map.items()]
            return {"courses": courses, "sessions": sessions}

        except TimetableFetchError:
            raise
        except Exception as e:
            raise TimetableFetchError(f"课表抓取异常: {e}")