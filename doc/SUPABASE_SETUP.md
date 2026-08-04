# Supabase Setup Guide — AIGalileoArena

Complete walkthrough: create project → connect app → migrate schema → migrate data.

---

## 1. Create a Supabase Project

1. Go to [supabase.com/dashboard](https://supabase.com/dashboard) and sign in (or create an account).
2. Click **New Project**.
3. Fill in:
   - **Organization**: pick or create one
   - **Project name**: e.g. `galileo-arena`
   - **Database password**: generate a strong one — **save it somewhere safe** (you'll need it for connection strings)
   - **Region**: pick the closest to you (e.g. `eu-central-1` for Europe)
4. Click **Create new project** and wait ~2 minutes for provisioning.

---

## 2. Collect Connection Strings

Go to **Project Settings → Database** (left sidebar → gear icon → Database).

Open your Supabase project dashboard (make sure you’re inside the project, not the org overview).

Click Connect in the top header bar.

In the modal/panel, go to Connection string (or “Database connection”) and set:

Type: URI

You’ll see the three URIs:

Direct connection

Session pooler (port 5432)

Transaction pooler (port 6543)

You need **three** connection strings. Supabase shows them under **Connection String → URI**.

### 2a. Session Pooler (for app + migrations)

- Tab: **Connection Pooling** → Mode: **Session**
- Port: `5432`
- Host: `aws-0-<region>.pooler.supabase.com`
- Format:
  ```
  postgresql://postgres.<project-ref>:<password>@aws-0-<region>.pooler.supabase.com:5432/postgres

  postgresql://postgres.mjdixgwduzzsdrjhttxw:[YOUR-PASSWORD]@aws-1-eu-west-1.pooler.supabase.com:5432/postgres

  ```
- **Used for**: app runtime, Alembic migrations, CI/CD
- **Why**: supports prepared statements, works on IPv4 + IPv6

### 2b. Direct Connection (optional — admin only)

- Tab: **Connection Info** (not pooled)
- Port: `5432`
- Host: `db.<project-ref>.supabase.co`
- Format:
  ```
  postgresql://postgres.<project-ref>:<password>@db.<project-ref>.supabase.co:5432/postgres
  ```
- **Used for**: manual `psql` sessions, `pg_dump`/`pg_restore`
- **Caveat**: IPv6 by default — only use where IPv6 is confirmed

### 2c. Transaction Pooler (NOT recommended for this app)

- Port: `6543` — does NOT support prepared statements
- Only needed for serverless/autoscaling. Ignore for now.

---

## 3. Create a Dedicated App User

Don't run the app as `postgres` superuser. Create a least-privilege role.

1. Go to **SQL Editor** in the Supabase dashboard (left sidebar).
2. Run:

```sql
-- 1. Create the role
CREATE ROLE app_user WITH LOGIN PASSWORD 'REPLACE_WITH_STRONG_PASSWORD';

-- 2. Grant connect + schema usage
GRANT CONNECT ON DATABASE postgres TO app_user;
GRANT USAGE ON SCHEMA public TO app_user;

-- 3. Grant DML on all current tables
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO app_user;

-- 4. Grant DML on future tables too
ALTER DEFAULT PRIVILEGES IN SCHEMA public
  GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO app_user;

-- 5. Grant sequence usage (for autoincrement columns)
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO app_user;
ALTER DEFAULT PRIVILEGES IN SCHEMA public
  GRANT USAGE, SELECT ON SEQUENCES TO app_user;
```

> **Note**: Run the `ALTER DEFAULT PRIVILEGES` statements again after running Alembic migrations, since the tables are created by `postgres`, not `app_user`.

3. Build the `app_user` connection string for the Session Pooler:
   ```
   postgresql://app_user.<project-ref>:REPLACE_WITH_STRONG_PASSWORD@aws-0-<region>.pooler.supabase.com:5432/postgres
   ```

---

## 4. Configure Environment Variables

Edit `backend/.env`:

```ini
# -----------------------------------------------
# Database — Supabase
# -----------------------------------------------

# App runtime (app_user, Session pooler)
DATABASE_URL=postgresql+asyncpg://app_user.<project-ref>:<password>@aws-0-<region>.pooler.supabase.com:5432/postgres

# Migrations / admin (postgres role, Session pooler)
DATABASE_URL_MIGRATIONS=postgresql+asyncpg://postgres.<project-ref>:<password>@aws-0-<region>.pooler.supabase.com:5432/postgres

# Require SSL for runtime connections (must be true for Supabase)
DATABASE_REQUIRE_SSL=true
```

Replace `<project-ref>`, `<password>`, and `<region>` with your actual values from Step 2.

> **Important**: Keep the `postgresql+asyncpg://` prefix — it tells SQLAlchemy to use the `asyncpg` driver.
>
> **Note**: `DATABASE_REQUIRE_SSL=true` is required — without it the runtime engine connects without SSL even though Alembic's `env.py` hardcodes `ssl: require`.

---

## 5. Run Alembic Migrations (Create Tables on Supabase)

> **Note**: `alembic.ini` still contains the old local URL (`postgresql+asyncpg://galileo:...@localhost`). This is harmless — `alembic/env.py` overrides it with `settings.database_url_migrations` at runtime. You can leave it as-is or blank it out to avoid confusion.

```bash
cd backend
.venv\Scripts\activate

# This creates all 13 tables + indexes on Supabase
alembic upgrade head
```

Expected output:
```
INFO  [alembic.runtime.migration] Running upgrade  -> 001, initial schema
INFO  [alembic.runtime.migration] Running upgrade 001 -> 002, add phase round to messages
...
INFO  [alembic.runtime.migration] Running upgrade 007 -> 008, debate usage
```

**If you get an SSL error**: make sure you're using the Session pooler URL (not Direct) and that `alembic/env.py` has `connect_args={"ssl": "require"}` (already applied in the code changes).

### Re-grant privileges to `app_user`

After Alembic creates the tables (owned by `postgres`), re-run the grants in the SQL Editor:

```sql
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO app_user;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO app_user;
```

---

## 6. Verify App Connects to Supabase

```bash
cd backend
uvicorn app.main:app --reload
```

✅ Check for: no connection errors in terminal output  
✅ Open `http://localhost:8000/docs` → try `GET /datasets` → should return `[]` (empty, no data yet)

---

## 7. Migrate Existing Data from Local PostgreSQL

> **Prerequisite**: `pg_dump`, `pg_restore`, and `psql` CLI tools must be available on your PATH. If you only have PostgreSQL running inside Docker (no local install), either install the [PostgreSQL client tools](https://www.postgresql.org/download/) or run the commands from inside the container with `docker exec`.

### 7a. Stop writes (freeze local DB)

Stop the backend if it's currently running against the local DB.

### 7b. Export data from local Docker PostgreSQL

Make sure your local Docker PostgreSQL is running:
```bash
docker compose up postgres -d
```

Dump data only (schema is handled by Alembic). Since PostgreSQL runs in Docker, use `docker exec`:

```powershell
# Runs pg_dump inside the container; output redirected to local file
docker exec galileo-pg pg_dump -h localhost -U galileo -d galileo_arena --data-only --column-inserts --format=plain > galileo_data.sql
```

### 7c. Import into Supabase

Since `psql` is also inside Docker, pipe the local SQL file into the container:

```powershell
Get-Content galileo_data.sql | docker exec -i galileo-pg psql "postgresql://postgres.<project-ref>:<password>@db.<project-ref>.supabase.co:5432/postgres?sslmode=require"
```

```powershell
Get-Content galileo_data.sql | docker exec -i galileo-pg psql "postgresql://postgres.mjdixgwduzzsdrjhttxw:X^38rsRS!270Z5Ehjy9bbKy2*@aws-1-eu-west-1.pooler.supabase.com:5432/postgres?sslmode=require"
```

> You'll be prompted for the password (the one from Step 1).
>
> **IPv4 networks**: The Direct connection host (`db.<project-ref>.supabase.co`) resolves to IPv6. If you're on an IPv4-only network, use the Session Pooler host (`aws-0-<region>.pooler.supabase.com`) instead.

### 7d. Fix sequences after restore

Auto-increment sequences may be out of sync. Run in the Supabase **SQL Editor**:

```sql
SELECT setval(pg_get_serial_sequence('dataset_cases', 'id'),      COALESCE(MAX(id), 1)) FROM dataset_cases;
SELECT setval(pg_get_serial_sequence('run_case_status', 'id'),     COALESCE(MAX(id), 1)) FROM run_case_status;
SELECT setval(pg_get_serial_sequence('run_messages', 'id'),        COALESCE(MAX(id), 1)) FROM run_messages;
SELECT setval(pg_get_serial_sequence('run_results', 'id'),         COALESCE(MAX(id), 1)) FROM run_results;
SELECT setval(pg_get_serial_sequence('run_events', 'id'),          COALESCE(MAX(id), 1)) FROM run_events;
SELECT setval(pg_get_serial_sequence('cached_result_sets', 'id'),  COALESCE(MAX(id), 1)) FROM cached_result_sets;
```

### 7e. Verify data

Run in SQL Editor:
```sql
SELECT 'datasets' AS t, COUNT(*) FROM datasets
UNION ALL SELECT 'dataset_cases',    COUNT(*) FROM dataset_cases
UNION ALL SELECT 'runs',             COUNT(*) FROM runs
UNION ALL SELECT 'run_results',      COUNT(*) FROM run_results
UNION ALL SELECT 'run_messages',     COUNT(*) FROM run_messages
UNION ALL SELECT 'llm_model',        COUNT(*) FROM llm_model
UNION ALL SELECT 'galileo_eval_run', COUNT(*) FROM galileo_eval_run;
```

Compare counts against local DB to confirm all data transferred.

---

## 8. Final Verification

1. Start backend: `uvicorn app.main:app --reload`
2. Start frontend: `cd frontend && npm run dev`
3. Open the app → verify:
   - Start page loads with datasets
   - Graphs page renders charts
   - Can run an evaluation → new data appears in Supabase Table Editor
4. Check **Supabase Logs → Postgres** for any query errors.

---

## 9. Row Level Security (RLS)

Supabase enables RLS by default on tables created via its dashboard. Since our tables are created by **Alembic**, RLS is **not** enabled — which is correct for a single-tenant backend-to-DB setup. If you later need multi-tenant or direct-from-browser access via Supabase client libraries, enable RLS and add policies per table.

---

## 10. Cleanup

```bash
# Stop local Docker PostgreSQL
docker compose down

# (Optional) Remove the Docker volume
docker volume rm aigalileoarena_pgdata
```

The local postgres service in `docker-compose.yml` is commented out but preserved for offline development fallback.

---

## Quick Reference

| What | Value |
|---|---|
| Supabase Dashboard | https://supabase.com/dashboard |
| Project Settings → Database | Connection strings live here |
| SQL Editor | Run SQL directly on the DB |
| Table Editor | Browse/verify data visually |
| Logs → Postgres | Monitor query errors |
| App user | `app_user` (least-privilege) |
| Admin user | `postgres` (migrations only) |
| App connection | Session pooler, port `5432` |
| Migrations connection | Session pooler, port `5432` |
