# digital-id-management-dashboard-e45cba16

## Digital ID Backend/API Container

This is the backend for the Digital ID Management Dashboard. It exposes a FastAPI REST API for all data and authentication flows.
See also the `interfaces/openapi.json` for the API schema.

### Environment Variables Required

To configure connection to *your* PostgreSQL instance, these must be set (by .env file, docker env, or shell):

```
POSTGRES_URL=<host>        # Host, e.g. localhost
POSTGRES_USER=<username>   # e.g. appuser
POSTGRES_PASSWORD=<pw>     # Password for user
POSTGRES_DB=<database>     # e.g. myapp
POSTGRES_PORT=<port>       # e.g. 5000 (default 5432)
```

You may also set (for security):

```
JWT_SECRET=your-secret-string
```

#### Example `.env`

```
POSTGRES_URL=localhost
POSTGRES_USER=appuser
POSTGRES_PASSWORD=dbuser123
POSTGRES_DB=myapp
POSTGRES_PORT=5000
JWT_SECRET=myverysecretstring
```

### Database Setup

This backend expects to connect to a PostgreSQL instance initialized with the correct user/database.
A sample connection string might be:
```
postgresql://appuser:dbuser123@localhost:5000/myapp
```
(see `../digital_id_database/db_connection.txt`)

Check and initialize the database using the provided SQL schema or startup script in the `digital_id_database` container.

### Running

To start the backend server (pick up .env automatically if present):
```
uvicorn src.api.main:app --reload --host 0.0.0.0 --port 3001
```
or (if you want to run as a script for local/dev/preview environments):
```
python src/api/main.py
```
(This ensures FastAPI will bind to port 3001, which is required for preview and container launch success.)

### REST API Endpoints

- API documentation and OpenAPI/Swagger can be found at `http://localhost:3001/docs` (when backend is running).
- All endpoints are under `/api/`
- Require a valid JWT token (get via `/api/token`).

See `interfaces/openapi.json` for the list of endpoints.

### Communication With Frontend

The frontend should point API requests (via `REACT_APP_API_URL`) to this backend’s HTTP URL, e.g.:
```
REACT_APP_API_URL=http://localhost:3001/api
```
(see frontend README for details).
