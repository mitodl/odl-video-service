web: bin/start-nginx bin/start-pgbouncer-stunnel newrelic-admin run-program uwsgi uwsgi.ini
worker_beat_noscale: celery -A odl_video worker -B
worker_scalable: celery -A odl_video worker
