#!/bin/bash
set -eo pipefail

docker build -t mitodl/odl_video_service_web_travis_next -f Dockerfile .

docker push mitodl/odl_video_service_web_travis_next
