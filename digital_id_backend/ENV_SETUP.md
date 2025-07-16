# Digital ID Management Dashboard – Environment & API Integration Quickstart

This describes the critical setup for **API/backend/database** connectivity and environment variable handling, covering all containers:

---

## [1] Database (MySQL) – digital_id_database

Set (in shell/.env):
```
MYSQL_URL=localhost
MYSQL_USER=appuser
MYSQL_PASSWORD=dbuser123
MYSQL_DB=myapp
MYSQL_PORT=3306
```
Sample connection string (see `db_connection.txt` in database container):
```
mysql+pymysql://appuser:dbuser123@localhost:3306/myapp
```
The database must be initialized with users/tables as in the provided schema.

---

## [2] Backend API (FastAPI) – digital_id_backend

The backend loads DB connection settings from environment variables (`MYSQL_*`) as shown above.
It can pick these up from a `.env` file in the backend directory.

**Basic backend .env example:**
```
MYSQL_URL=localhost
MYSQL_USER=appuser
MYSQL_PASSWORD=dbuser123
MYSQL_DB=myapp
MYSQL_PORT=3306
JWT_SECRET=something-random-for-jwt
```

---

## [3] Frontend (React) – digital_id_frontend

The frontend sends REST requests to the backend.

Set in a `.env` in the frontend folder:
```
REACT_APP_API_URL=http://localhost:3001/api
```
If not set, it defaults to `/api` (which works for relative APIs if hosted behind a reverse proxy).

**Summary Table:**
| Component | Required Env/Config                | Example Value                        |
|-----------|-----------------------------------|--------------------------------------|
| Database  | POSTGRES_*                        | See above                            |
| Backend   | POSTGRES_*, (JWT_SECRET)          | See above                            |
| Frontend  | REACT_APP_API_URL                 | http://localhost:3001/api            |

---

## [4] End-to-end API/DB Troubleshooting

- Ensure backend `.env` or system environment matches DB configuration.
- Frontend `.env` should match backend root URL.
- Test each API endpoint from the frontend in dev mode, and the backend using Swagger docs at `/docs` or `/redoc`.

---

## [5] Additional Notes

- All API security (JWT tokens) and most API paths are under `/api/...`.
- Change environment values as needed for cloud, Docker, or prod.

---

*All containers/tools should reference this file to help new developers bring up the stack quickly and correctly!*

