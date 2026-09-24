CREATE TABLE IF NOT EXISTS sessions (
 token_hash text PRIMARY KEY, csrf text NOT NULL, expires_at timestamptz NOT NULL
);
CREATE TABLE IF NOT EXISTS jobs (
 id uuid PRIMARY KEY, source_name text NOT NULL, raw_csv text NOT NULL,
 digest text NOT NULL UNIQUE, status text NOT NULL DEFAULT 'queued',
 attempts integer NOT NULL DEFAULT 0, accepted integer NOT NULL DEFAULT 0,
 rejected integer NOT NULL DEFAULT 0, duplicates integer NOT NULL DEFAULT 0,
 error text, created_at timestamptz NOT NULL DEFAULT now(), started_at timestamptz,
 finished_at timestamptz, duration_ms integer
);
CREATE TABLE IF NOT EXISTS readings (
 reading_id text PRIMARY KEY, vehicle_id text NOT NULL, recorded_at timestamptz NOT NULL,
 miles numeric(12,2) NOT NULL CHECK(miles BETWEEN 0 AND 5000),
 fuel_gallons numeric(10,2) NOT NULL CHECK(fuel_gallons BETWEEN 0 AND 500),
 job_id uuid NOT NULL REFERENCES jobs(id), imported_at timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS readings_vehicle_time ON readings(vehicle_id, recorded_at DESC);
CREATE TABLE IF NOT EXISTS rejections (
 id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY, job_id uuid NOT NULL REFERENCES jobs(id),
 row_number integer NOT NULL, reason text NOT NULL, raw_row jsonb NOT NULL
);
CREATE INDEX IF NOT EXISTS rejections_job ON rejections(job_id);
CREATE TABLE IF NOT EXISTS schedule (
 id integer PRIMARY KEY CHECK(id=1), enabled boolean NOT NULL DEFAULT true,
 interval_seconds integer NOT NULL DEFAULT 300, next_run timestamptz NOT NULL DEFAULT now(),
 last_tick timestamptz
);
INSERT INTO schedule(id) VALUES (1) ON CONFLICT DO NOTHING;
