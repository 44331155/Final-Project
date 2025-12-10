import httpx
import json
import re
from typing import Dict, List, Tuple, Optional
from datetime import datetime, timedelta, date
from app.config import settings
from .zdbk import login_with_sso_get_jw_cookies, ZdbkLoginError
import html

class TimetableFetchError(Exception):
    pass

def parse_semester_id(semester_id: str) -> Tuple[str, str]:
    parts = semester_id.split("-")
    if len(parts) < 3:
        raise TimetableFetchError(f"无效的学期格式: {semester_id}")
    xnm = parts[0]
    term = parts[-1]
    xqm = "1" if term == "1" else "2"
    return xnm, xqm

def xqm_from_xxq(xxq: str) -> str:
    if not xxq:
        return ""
    if "秋冬" in xxq:
        return "1"  # 教务的学期值（示意）
    if "春夏" in xxq:
        return "2"
    if "秋" in xxq:
        return "1"
    if "夏" in xxq:
        return "2"
    if "春" in xxq:
        return "2"
    if "冬" in xxq:
        return "1"
    return ""

def semester_from_xkkh(xkkh: str) -> str:
    if not xkkh:
        return ""
    m = re.match(r"^\((\d{4}-\d{4}-[12])\)", xkkh)
    return m.group(1) if m else ""

async def fetch_kblist(sso_cookie: str, semester_id: str, strict_filter: bool = True) -> List[Dict]:
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

def compute_date_for_weekday(start_monday: date, week: int, weekday: int) -> date:
    delta_days = (week - 1) * 7 + (weekday - 1)
    return start_monday + timedelta(days=delta_days)

def compute_datetime(semester: str, week: int, weekday: int, period_start: int, period_count: int) -> Tuple[datetime, datetime]:
    """
    根据学期（从 settings.TERM_CONFIGS 取）、周、星期、节次计算具体起止时间。
    依赖：
      - settings.get_term_start_monday(semester)
      - settings.get_term_periods(semester)
    """
    start_monday = settings.get_term_start_monday(semester)
    periods = settings.get_term_periods(semester)
    class_date = compute_date_for_weekday(start_monday, week, weekday)
    # 第 period_start 节的开始时间
    start_t = periods[period_start - 1][0]
    # 连续 period_count 节的结束时间，以最后一节的结束 time 为准
    end_t = periods[period_start + period_count - 2][1]
    return datetime.combine(class_date, start_t), datetime.combine(class_date, end_t)

def parse_kcb_fields(kcb: str) -> dict:
    text = html.unescape(kcb.replace("<br>", "\n"))
    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    course_name = lines[0] if lines else ""
    term_text = ""
    weeks_spec = ""
    period_count: Optional[int] = None
    week_flag: Optional[str] = None
    teachers = ""
    classroom = ""
    extra_date_range = None

    if len(lines) >= 2:
        term_text = lines[1]
        m = re.search(r"\{(.*?)\}", term_text)
        if m:
            inside = m.group(1)
            mw = re.search(r"(第[\d\-，,]+周)", inside)
            if mw:
                weeks_spec = mw.group(1)
            mc = re.search(r"(\d+)节", inside)
            if mc:
                period_count = int(mc.group(1))
            if "单周" in inside:
                week_flag = "单周"
            elif "双周" in inside:
                week_flag = "双周"

    if len(lines) >= 3:
        teachers = lines[2]
    if len(lines) >= 4:
        classroom_line = lines[3]
        md = re.search(r"(\d{4}年\d{2}月\d{2}日\(\d{2}:\d{2}-\d{2}:\d{2}\))", classroom_line)
        if md:
            extra_date_range = md.group(1)
            classroom = classroom_line[:md.start()].strip()
        else:
            classroom = classroom_line.strip()
        classroom = re.sub(r"(zwf)+$", "", classroom).strip()

    return {
        "course_name": course_name,
        "term_text": term_text,
        "weeks_spec": weeks_spec,
        "period_count": period_count,
        "week_flag": week_flag,
        "teachers": teachers,
        "classroom": classroom,
        "extra_date_range": extra_date_range,
    }

def normalize_weeks(weeks_spec: str, week_flag: Optional[str]) -> List[int]:
    if not weeks_spec:
        return []
    s = weeks_spec.replace("第", "").replace("周", "")
    weeks: List[int] = []
    for part in re.split(r"[，,]", s):
        part = part.strip()
        if not part:
            continue
        if "-" in part:
            a, b = part.split("-")
            weeks.extend(range(int(a), int(b) + 1))
        else:
            weeks.append(int(part))
    weeks = sorted(set(weeks))
    if week_flag == "双周":
        weeks = [w for w in weeks if w % 2 == 0]
    if week_flag == "单周":
        weeks = [w for w in weeks if w % 2 == 1]
    return weeks

def seasons_from_xxq(xxq: str) -> List[str]:
    """
    根据 xxq 字段返回季节列表：
    - '秋冬' -> ['秋','冬']
    - '春夏' -> ['春','夏']
    - '秋' -> ['秋']，'冬' -> ['冬']，'春' -> ['春']，'夏' -> ['夏']
    - 其他或为空 -> []（可按需决定是否默认到学期季）
    """
    xxq = xxq or ""
    if "秋冬" in xxq:
        return ["秋", "冬"]
    if "春夏" in xxq:
        return ["春", "夏"]
    for s in ["春", "夏", "秋", "冬"]:
        if s in xxq:
            return [s]
    return []

def parse_kblist_to_occurrences(kb_list: List[Dict]) -> List[Dict]:
    """
    针对当前数据格式：
    - weekday: xqj
    - period_start: djj
    - period_count: 优先 kcb 中的 'N节'，否则回退 skcd
    - season: 来自 xxq（秋冬→两条记录；秋/冬→单条；春夏同理）
    """
    occurrences = []
    for item in kb_list:
        semester = semester_from_xkkh(item.get("xkkh"))
        kcb = item.get("kcb", "") or ""
        fields = parse_kcb_fields(kcb)
        course_name = fields["course_name"]
        teachers = fields["teachers"]
        classroom = fields["classroom"]
        weeks_spec = fields["weeks_spec"]
        week_flag = fields["week_flag"]
        period_count = fields["period_count"]

        if period_count is None:
            try:
                period_count = int(item.get("skcd") or 1)
            except Exception:
                period_count = 1

        try:
            period_start = int(item.get("djj") or 1)
        except Exception:
            period_start = 1

        weekday = int(item.get("xqj") or 1)
        course_code = item.get("xkkh", "")
        single_week = (week_flag == "单周")
        double_week = (week_flag == "双周")
        note = None

        weeks = normalize_weeks(weeks_spec, week_flag)
        season_list = seasons_from_xxq(item.get("xxq", ""))

        # 若 xxq 无法判定季节，可根据需求选择：跳过或赋默认季节
        if not season_list:
            season_list = []  # 保持为空可选择不入库，或设定默认季节

        for w in weeks:
            for season in season_list:
                week_for_date = w + 8 if season in ("冬", "夏") else w
                starts_at, ends_at = compute_datetime(semester, week_for_date, weekday, period_start, period_count)
                occurrences.append({
                    "course_code": course_code,
                    "course_name": course_name,
                    "teacher": teachers,
                    "classroom": classroom,
                    "week": w,
                    "weekday": weekday,
                    "period_start": period_start,
                    "period_count": period_count,
                    "starts_at": starts_at.isoformat(),
                    "ends_at": ends_at.isoformat(),
                    "single_week": single_week,
                    "double_week": double_week,
                    "season": season,
                    "semester": semester,
                    "note": note
                })
    return occurrences