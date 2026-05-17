web:                         → Process type (web server)
gunicorn                     → Production WSGI server
app:app                      → Run "app" object from "app.py"
--bind 0.0.0.0:$PORT         → Listen on Railway port
--workers 2                  → 2 worker processes
--threads 4                  → 4 threads per worker
--timeout 120                → 120 sec timeout (for AI requests)
--access-logfile -           → Log to stdout
--error-logfile -            → Errors to stdout