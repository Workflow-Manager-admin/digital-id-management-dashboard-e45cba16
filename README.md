# digital-id-management-dashboard-e45cba16

## Digital ID Backend/API Container

This is the backend for the Digital ID Management Dashboard. It exposes a FastAPI REST API for all data and authentication flows.
See also the `interfaces/openapi.json` for the API schema.

### Environment Variables Required

To configure connection to *your* MySQL instance, these must be set (by .env file, docker env, or shell):

```
MYSQL_URL=<host>           # Host, e.g. localhost
MYSQL_USER=<username>      # e.g. appuser
MYSQL_PASSWORD=<pw>        # Password for user
MYSQL_DB=<database>        # e.g. myapp
MYSQL_PORT=<port>          # e.g. 3306
```

You may also set (for security):

```
JWT_SECRET=your-secret-string
```

#### Example `.env`

```
MYSQL_URL=localhost
MYSQL_USER=appuser
MYSQL_PASSWORD=dbuser123
MYSQL_DB=myapp
MYSQL_PORT=3306
JWT_SECRET=myverysecretstring
```

### Database Setup

This backend expects to connect to a MySQL instance initialized with the correct user/database/schema.
A sample connection string might be:
```
mysql+pymysql://appuser:dbuser123@localhost:3306/myapp
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
