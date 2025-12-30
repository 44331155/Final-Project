## 项目结构
```bash
.
├── README.md
├── app
│   ├── api
│   │   ├── deps.py
│   │   ├── router.py
│   │   ├── routes_auth.py
│   │   ├── routes_calendar.py
│   │   ├── routes_events.py
│   │   ├── routes_system.py
│   │   └── routes_timetable.py
│   ├── config.py
│   ├── main.py
│   ├── models
│   │   └── schemas.py
│   ├── security.py
│   ├── services
│   │   ├── calendar.py
│   │   ├── sso.py
│   │   ├── timetable.py
│   │   └── zdbk.py
│   ├── storage
│   │   ├── db.py
│   │   └── session_store.py
│   └── utils
├── data
│   └── schedule.db
├── requirements.txt

```

### 启动

```bash
cd backend
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

## 路由列表

### auth

POST auth/login 身份认证
```bash
curl -X 'POST' \
  'http://127.0.0.1:8000/api/auth/login' \
  -H 'accept: application/json' \
  -H 'Content-Type: application/json' \
  -d '{
  "username": "string",
  "password": "string"
}'
```
return {"code": 0, "message": "ok", "data": {"token": token, "is_wechat_bound": false}}

POST auth/bind-wechat 绑定微信
```bash
curl -X 'POST' \
  'http://127.0.0.1:8000/api/auth/bind-wechat' \
  -H 'Authorization: Bearer <token>' \
  -H 'Content-Type: application/json' \
  -d '{
  "code": "wx_code"
}'
```
return {"code": 0, "message": "绑定成功"}

POST auth/login-by-wechat 微信免密登录
```bash
curl -X 'POST' \
  'http://127.0.0.1:8000/api/auth/login-by-wechat' \
  -H 'Content-Type: application/json' \
  -d '{
  "code": "wx_code"
}'
```
return {"code": 0, "message": "ok", "data": {"token": token, "is_wechat_bound": true}}

GET auth/me 获取当前用户信息
```bash
curl -X 'GET' \
  'http://127.0.0.1:8000/api/auth/me' \
  -H 'Authorization: Bearer <token>'
```
return {"code": 0, "message": "ok", "data": {"username": "foo", "is_wechat_bound": true}}

POST auth/unbind-wechat 解绑微信
```bash
curl -X 'POST' \
  'http://127.0.0.1:8000/api/auth/unbind-wechat' \
  -H 'Authorization: Bearer <token>' \
  -H 'Content-Type: application/json' \
  -d '{}'
```
return {"code": 0, "message": "ok", "data": {"is_wechat_bound": false}}

### timetable

GET timetable/ 获取课表
```bash
curl -X 'GET' \
    'http://127.0.0.1:8000/api/timetable?semester=2024-2025-2' \
    -H 'Authorization:Bearer <token>'
```

POST timetable/sync 同步课表
```bash
curl -X POST \
    'http://127.0.0.1:8000/api/timetable/sync?semester=2024-2025-2' \
    -H 'Authorization: Bearer <token>'
```

GET timetable/template 获取课程模板
```bash
curl -X 'GET' \
  'http://127.0.0.1:8000/api/timetable/template?semester=2024-2025-1&season_type=1&week_type=single' \
  -H 'Authorization: Bearer <token>'
```

### events

GET events/ 获取事件列表
```bash
curl -X 'GET' \
  'http://127.0.0.1:8000/api/events?start=2025-12-01T00:00:00&end=2025-12-31T23:59:59'  \
  -H 'Authorization: Bearer <token>
```
return {"code": 0, "message": "ok"}

POST events/ 增加事件
```bash
curl -X 'POST' \
  'http://127.0.0.1:8000/api/events' \
  -H 'Authorization: Bearer <token>' \
  -H 'Content-Type: application/json' \
  -d '{
    "title": "play",
    "startTime": "2025-12-01T20:00:00",
    "endTime": "2025-12-01T20:29:59",
    "place": "playground"
  }'
```
return {"code": 0, "message": "ok", "data": events}

GET events/ 查找单个事件
```bash
curl -X 'POST' \
  'http://127.0.0.1:8000/api/events?events_id=ID' \
  -H 'Authorization: Bearer <token>' 
```
return {"code": 0, "message": "ok", "data": event}

DELETE events/{event_id} 删除事件
```bash
curl -X 'POST' \
  'http://127.0.0.1:8000/api/events' \
  -H 'Authorization: Bearer <token>' 
```
return {"code": 0, "message": "ok"}

PUT events/{event_id} 修改事件
```bash
curl -X 'PUT' \
  'http://127.0.0.1:8000/api/events' \
  -H 'Authorization: Bearer <token>' \
  -H 'Content-Type: application/json' \
  -d '{
    "title": "玩",
    "startTime": "2025-12-01T20:00:00",
    "endTime": "2025-12-01T20:29:59",
    "place": "家里"
```
return {"code": 0, "message": "ok"}

### calendar

GET calendar/事件查询
```bash
curl -X 'GET' \
  'http://127.0.0.1:8000/api/calendar?start=STARTTIME&end=ENDTIME'
  -H "Authorization: Bearer <token>"
```
return {"code": 0, "message": "ok", "data": events}

GET calendar/export.ics 导出ICS
```bash
curl -H "Authorization: Bearer <token>" "http://127.0.0.1:8000/api/calendar/export.ics?date_from=2025-03-01&date_to=2025-03-07" -o period.ics
```

## 待完成
