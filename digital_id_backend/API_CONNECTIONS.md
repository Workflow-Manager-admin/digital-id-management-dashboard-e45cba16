# API & Internal Communication Points: Digital ID Management Dashboard

This document describes the environment variables, API base URLs, and component linkage for bringing up the platform end-to-end.

---

## 1. Database (PostgreSQL)
- **Required by:** Backend
- **Connection details:**
  - POSTGRES_URL=localhost
  - POSTGRES_USER=appuser
  - POSTGRES_PASSWORD=dbuser123
  - POSTGRES_DB=myapp
  - POSTGRES_PORT=5000
- **Sample connection string:**  
  `postgresql://appuser:dbuser123@localhost:5000/myapp`
- **Bootstrap:**  
  Run `startup.sh` or execute the schema in `schema.sql`.

---

## 2. Backend API (FastAPI)
- **Required by:** Frontend
- **API base URL:**  
  `http://localhost:8000/api`
- **.env location:**  
  Place env file in `digital_id_backend/`
- **Security / Auth:**  
  JWT tokens returned from `/api/token`, required as `Authorization: Bearer <token>` for secured endpoints.
- **OpenAPI Docs:**  
  [http://localhost:8000/docs](http://localhost:8000/docs)

---

## 3. Frontend (React)
- **Env var for backend connection:**  
  `REACT_APP_API_URL=http://localhost:8000/api` (for local dev)
- **.env location:**  
  Place in `digital_id_frontend/`
- **How it works:**  
  All API calls are made using this base (see `src/api.js`).
- **Fallback:**  
  If unset, attempts to use `/api`, assuming dev or proxy config.

---

## 4. API Paths (Key Endpoints)
- `POST   /api/token`           — login for admin/superadmin (JWT token)
- `POST   /api/invite`          — (superadmin) send invitation to admin
- `POST   /api/register`        — register from invitation (admin)
- `GET    /api/users/me`        — current user profile
- `GET    /api/admins/`         — list admins (superadmin only)
- `GET/POST/PUT/DELETE /api/holders/` — manage holders
- `GET/POST /api/numbers/`      — manage unique numbers
- `POST   /api/holders/{holder_id}/numbers/{number_id}/link`    — link number
- `POST   /api/holders/{holder_id}/numbers/{number_id}/unlink`  — unlink number
- `GET    /api/history/`        — view linkage/unlinkage history

---

## 5. Connection Sequence (dev/test/local):

1. **Launch PostgreSQL:**
    - Start the database via `startup.sh` (or Docker) with above POSTGRES_* vars.

2. **Launch Backend:**
    - Ensure backend's `.env` is configured as above.
    - Start with:
      ```
      uvicorn src.api.main:app --reload
      ```
3. **Launch Frontend:**
   - Ensure frontend `.env` is set with correct `REACT_APP_API_URL`.
   - Start with:
     ```
     npm install
     npm start
     ```
   - App loads at [http://localhost:3000](http://localhost:3000).

*All flows (admin invite/accept, login, CRUD, link/unlink, and history viewing) should work via the above setup.*

---
## 6. Host/Port Mapping (Defaults)
- PostgreSQL: `localhost:5000`
- Backend (FastAPI): `localhost:8000`
- Frontend (React): `localhost:3000`

---
## 7. Troubleshooting Quick Checklist
- Confirm all `.env` files are present and correct before startup.
- DB must be initialized before backend runs.
- Backend must run before frontend for proper API communication.
- Use browser devtools to examine failed requests—check for CORS or 4xx/5xx errors if flows break.
