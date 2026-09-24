# Import Desk

Import Desk turns a fleet CSV into checked database records. Its useful part is the handling of mistakes, repeated files, and jobs that stop halfway through.

## Try the main task

Sign in as `demo` and click **Try sample import**. The sample has eight rows: four valid unique readings, one duplicate, and three bad rows. The worker should save four readings, count one duplicate, and show three rejections.

Open the import report. One row has no vehicle ID, one has a bad date, and one has negative miles. Download the original CSV to see exactly what was sent.

Click the sample button again. The app reuses the earlier job because the file has the same content. Fix a rejected row in a new file and upload it to create a new job.

Open **Schedule** to see the worker's last check and next run. The sample feed adds one generated reading every five minutes. You can pause or resume it. It is not a live vehicle service.

## Where the code lives

| Part | File | Job |
| --- | --- | --- |
| Page | `web/src/App.tsx` | Import list, rejection details, saved readings, and schedule |
| API | `app/main.py` | Accepts files, returns reports, and queues retries |
| Import rules | `app/importer.py` | Checks rows and writes accepted records |
| Background work | `app/worker.py` | Checks the schedule and claims queued jobs |
| Database | `app/schema.sql` | Jobs, readings, rejections, sessions, and schedule |
| Sample file | `samples/fleet-readings.csv` | A small file with deliberate mistakes |

## Follow one file

The browser reads a UTF-8 CSV and sends its name and content. The server keeps the raw text and computes a SHA-256 digest. A digest is a fixed value based on the file's contents. Identical contents have the same digest, so a unique database constraint prevents duplicate jobs for the same file.

The API returns quickly after saving a queued job. A separate worker claims it. `FOR UPDATE SKIP LOCKED` means another worker can take a different job without claiming the same row.

The worker marks the job running and records an attempt number. It checks the header before reading data rows. A changed header fails the job rather than quietly putting values into the wrong columns.

For each row, `clean` checks IDs, dates, miles, and fuel. It uses decimal numbers for numeric values so decimal input is handled predictably. Dates need a time zone. IDs must use the allowed characters.

Good rows go into `readings`. Bad rows go into `rejections` with the original row number and a reason. A repeated reading ID with the same values counts as a duplicate. Different values for an existing ID are rejected, and the original record is kept.

## What a transaction protects

All row writes for one job happen in one transaction. A malformed file or database failure rolls back the accepted rows and rejection rows from that attempt. A failed job is then recorded separately.

The worker does not commit each reading one at a time. That avoids a job that appears failed but has saved an unknown fraction of its file.

## Restart and retry

A queued job survives a worker restart because the queue is a database table. A running job older than five minutes can be claimed again. This is a lease: the worker gets a limited time to finish.

Each claim increments the attempt number. Before writing, the worker checks that it still owns that attempt. A worker that wakes up after a newer worker took over cannot overwrite the newer result.

The job row stays locked while results are written. Another worker skips it. Unique reading IDs provide a second layer of protection against duplicate records.

Use **Retry import** after a temporary problem, such as an unavailable database. A file with wrong columns will fail again until you upload a corrected file. Rejected rows are not failed jobs; edit those rows in a new CSV.

## The query measurement

`scripts/benchmark.py` creates a temporary table with 200,000 generated rows. It runs a query for one vehicle's 20 latest readings before and after adding an index on vehicle and time. It runs six measurements for each case and reports the median of the last five.

Read `evidence/query-benchmark.json` for the actual times and query plans. An index gives the database a smaller path to the matching rows. The tradeoff is storage and extra work when new rows are inserted.

This is a local synthetic measurement, not a production fleet result. It does not show that every query benefits from an index.

## Choices and limits

CSV files are limited to 1 MB and 10,000 rows. The page shows the 50 most recent jobs and 25 most recent readings. Raw CSV is stored in PostgreSQL to keep this small project easy to run. Larger systems would usually put source files in object storage.

There is one local demo account. Scheduled imports use a generated sample feed. There is no Azure deployment, live fleet API, Power BI report, email alert, or automatic data-retention job. Those are useful next additions once you can explain the current flow.

## Practice explaining it

Explain why a file digest and a reading ID solve different duplicate problems. Describe what happens if the worker stops after claiming a job. Point to the query that claims work and explain why a browser page is not the scheduler.
