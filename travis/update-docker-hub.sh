#!/bin/bash
set -eo pipefail

docker build -t mitodl/odl_video_service_web_travis_next -f Dockerfile .
docker build -t mitodl/odl_video_service_watch_travis -f travis/Dockerfile-travis-watch-build .

docker push mitodl/odl_video_service_web_travis_next
docker push mitodl/odl_video_service_watch_travis
