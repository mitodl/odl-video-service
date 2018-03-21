Release Notes
=============

Version 0.15.1
--------------

- Made the message posted in slack a bit more verbose for clarity

Version 0.15.0
--------------

- Upgrade to Django 1.11 (#465)
- Import public TechTV collections and set video stream source
- Force login on protected video URL&#39;s but not public video URL&#39;s
- Join BASE_DIR for STATIC_ROOT
- Renamed file to file_name based on feedback
- Added a check to verify that file has not already been synced and if it has to moved it to a &#34;conflict&#34; folder and notify slack
- Import TechTV captions

Version 0.14.1
--------------

- Update django-server-status to version 0.5.0

Version 0.14.0
--------------

- Updated settings and requirements to fix deployment issues

Version 0.13.0
--------------

- Handle nested moira permissions on individual video/collection pages
- Remove validation that moira list is a mailing list but send email notifications only if it is an email list
- TechTV URL&#39;s
- Updated cryptography requirement to fix incompatibility with OpenSSL
- Migration script for TechTV

Version 0.12.0
--------------

- Support for playing MP4 videos in multiple resolutions
- Fix scrolling issues in OVS sidebar (#425)

Version 0.11.0
--------------

- Update the FAQ

Version 0.10.1
--------------

- Refactor video analytics event collection
- Terms of Service page

Version 0.10.0
--------------

- fixed issue with long video titles that do not break (#400)
- Reformat using eslint-config-mitodl (#398)

Version 0.9.0
-------------

- Use unique s3 keys for each subtitle upload

Version 0.8.1
-------------

- bump psycopg to 2.7.3.2 (#389)
- Fix embedded videos
- Fix moira-related issues
- some accessibility changes (#387)

Version 0.8.0
-------------

- Add cloudfront configuration steps

Version 0.7.1
-------------

- Sync settings with cookiecutter (#376)

Version 0.7.0
-------------

- Youtube integration
- Fix subtitle deletion

Version 0.6.0
-------------

- Remove default mit email address (#355)
- Video-specific permission overrides
- 404 for invalid collection/video keys

Version 0.5.0
-------------

- Add FAQ page at /help
- Use application log level for Celery (#340)
- This fixes button style and layout bug (#338)
- Added video delete functionality
- More code review improvements
- Upgrade psycopg to fix error prevent build of web container
- Core review improvements
- Download original video source to Dropbox

Version 0.4.0
-------------

- Update README.rst
- Use yarn install --frozen-lockfile (#321)
- Google analytics for page views and player events
- Moira list validation
- Upgrade node.js and yarn (#318)
- Split CSS into separate file (#317)
- Remove auth endpoints (#315)
- Add templates for 403, 404, 500 views (#310)
- Remove login and registration (#312)
- Custom MoiraException

Version 0.3.0
-------------

- Playback rate control, disable autoplay
- Multi-angle VideoJS
- Fix config of root logger (#300)
- Add no-throw-literal eslint rule (#299)
- Remove default MAILGUN_URL, this should be set in .env instead (#298)
- Add missing return (#296)
- responsive layout fix (#294)
- Fix logging configuration (#293)

Version 0.2.1
-------------

- Fixing previous messy release
- Fixes Firefox layout bug in video cards thumbnails (#288)
- Improved lecture capture default video titles
- Smaller responsive video thumbnails on Collection Details page (#276)

Version 0.2.0
-------------

Version 0.1.0
-------------


