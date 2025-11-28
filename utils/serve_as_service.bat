\
    @echo off
    REM Simple batch to run uvicorn. Use NSSM or Windows Service in production.
    python -m uvicorn main:app --host 0.0.0.0 --port 8899 --workers 1
