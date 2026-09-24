# Verification notes

The first local verification ran on September 24, 2026 with Windows, Java 21, Python 3.12, PostgreSQL 17.11, and pgvector 0.8.6. Across the three apps, 57 tests passed. This total includes 32 HTTP/database checks and 25 Python unit checks. It is a shared-suite total, not a per-app count.

The apps built successfully, and all three databases passed a dump/restore check. The original local Docker engine could not start, so the first checks used native PostgreSQL. Each standalone repo now has its own Docker workflow. GitHub Actions is the source for current container builds and the exact test count for this repo.

The screenshots show the real local app with fictional records. They document visible behavior, not an outside usability study or production traffic. Public backend hosting is not set up. No paid model call has been tested.
