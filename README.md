### 项目结构
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
|:-------|---------|
|   200     |   登录成功             |
|   401     |   未登录或登录失败      |
|   422     |    验证错误            |

### 测试登录教务系统

```bash
curl -X 'GET' \
    'http://127.0.0.1:8000/api/timetable?semester=AIMSEMESTER' \
    -H 'Authorization:Bearer YOURTOKEN'
```
