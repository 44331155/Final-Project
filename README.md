### 项目结构
```bash
.
├── README.md
├── app
│   ├── api
│   │   ├── deps.py
│   │   ├── router.py
│   │   ├── routes_auth.py
│   │   ├── routes_calendar.py
│   │   ├── routes_events.py
│   │   └── routes_timetable.py
│   ├── config.py
│   ├── main.py
│   ├── models
│   │   └── schemas.py
│   ├── services
│   │   ├── sso.py
│   │   ├── timetable.py
│   │   └── zdbk.py
│   ├── storage
│   │   ├── db.py
│   │   └── session_store.py
│   └── utils
├── requirements.txt
└── tests

```

### 启动

```bash
cd backend
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```
打开 http://127.0.0.1:8000/docs 查看 Swagger

#### 测试身份认证

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
返回如下表
|   代码    |   描述       |
|-------|:---------|
|   200     |   登录成功             |
|   401     |   未登录或登录失败      |
|   422     |    验证错误            |

### 获得课表数据

```bash
curl -X 'GET' \
    'http://127.0.0.1:8000/api/timetable?semester=2024-2025-2' \
    -H 'Authorization:Bearer <token>'
```

### 获取课表并存入数据库

```bash
curl -X POST \
    'http://127.0.0.1:8000/api/timetable/sync?semester=2024-2025-2' \
    -H 'Authorization: Bearer <token>'
```

### 事件查询

```bash
curl -X GET "http://127.0.0.1:8000/api/calendar/events?date_from=2025-03-01&date_to=2025-03-07" -H "Authorization: Bearer <token>"
```

### 导出ICS

```bash
curl -H "Authorization: Bearer <token>" "http://127.0.0.1:8000/api/calendar/export.ics?date_from=2025-03-01&date_to=2025-03-07" -o period.ics
```

## 待完成

制作一张表仅存放课程数据，不存储日期