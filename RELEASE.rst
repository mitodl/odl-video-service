Release Notes
=============

Version 0.57.0
--------------

- accessibility link in the footer (#913)

Version 0.56.0 (Released September 23, 2020)
--------------

- add github templates copied from mitxpro (#789)
- Bump elliptic from 6.4.0 to 6.5.3 (#905)
- Make collection autocomplete field for video (#909)
- Added openssl to pass tests
- Delete NotificationEmail (#877)
- Bumped to latest django-server-status

Version 0.55.0 (Released August 19, 2020)
--------------

- More JS upgrades (#903)

Version 0.54.1 (Released July 15, 2020)
--------------

- Update dependencies (#900)

Version 0.54.0 (Released July 13, 2020)
--------------

- Bump forwarded from 0.1.0 to 0.1.2 (#848)
- Bump jquery from 3.4.1 to 3.5.0 (#886)
- Bump httplib2 from 0.17.2 to 0.18.0 (#895)
- Bump django from 2.2.10 to 2.2.13 (#896)
- Add url links to video/collection admin (#898)

Version 0.53.3 (Released May 07, 2020)
--------------

- New error message for 403 (#870)
- pin ddt (#893)
- Add permissions just for logged in users (#889)

Version 0.53.2 (Released May 06, 2020)
--------------

- With log file specified, force logger to write to file (#888)

Version 0.53.1 (Released May 05, 2020)
--------------

- Add ODL_VIDEO_LOG_FILE to app.json (#885)
- Add optional logging to file, not stdio (#883)
- Email templates (#873)

Version 0.53.0 (Released April 30, 2020)
--------------

- Pre-commit checks (#876)

Version 0.52.0 (Released April 24, 2020)
--------------

- Fix TechTV embed URLs (#879)
- Add structured logging with structlog
- Fix signal test

Version 0.51.2 (Released April 23, 2020)
--------------

- Rename a couple UWSGI environment variables, remove redundant if-env blocks (#871)

Version 0.51.1 (Released April 17, 2020)
--------------

- Remove py-call-osafterfork uWSGI setting (#867)

Version 0.51.0 (Released April 16, 2020)
--------------

- Use sentry sdk instead of raven (#869)

Version 0.50.0 (Released April 01, 2020)
--------------

- Add videojs-annotation-comments plugin and put it behind a feature flag (#864)
- Add keyboard control to video player (#856)
- Fix video source switch failover (#858)
- Enabled multiple edX endpoints for posting HLS videos
- Force non-native HLS playback to fix quality selector in Edge, Safari (#860)

Version 0.49.2 (Released March 31, 2020)
--------------

- Include paramters in login redirects (#850)
- fix typos in terms of service (#851)
- Hide private videos (#840)
- Add uWSGI settings (#847)

Version 0.49.1 (Released March 25, 2020)
--------------

- add youtube tos and google privacy policy links (#845)
- Collection of security updates in 1 PR (#831)
- Removed 'public' option for videos in front end
- Enabled edX course ID editing for collections

Version 0.49.0 (Released March 24, 2020)
--------------

- Sharing a youtube video link with start time (#832)
- Get tox to run and pass (#839)
- Fix the play button and video controls for  Youtube videos (#822)
- Fix heroku build (#829)
- Update postgres & python, fix Moira list api URL pattern (#825)

Version 0.48.0 (Released January 29, 2020)
--------------

- Update Video.js to v7 (#817)

Version 0.47.0 (Released December 18, 2019)
--------------

- continue m3u8 reorder task if s3_object_key is not found on s3
- m3u8 reorder task

Version 0.46.0 (Released December 02, 2019)
--------------

- Upgraded redis
- Updated Celery to 4.3.0

Version 0.45.0 (Released November 15, 2019)
--------------

- Support for retranscoding videos (#792)

Version 0.44.0 (Released November 07, 2019)
--------------

- Change prefix_id to a TextField (#790)

Version 0.43.1 (Released August 28, 2019)
--------------

- Upgraded version of django-server-status

Version 0.43.0 (Released August 26, 2019)
--------------

- Added runtime.txt to specify python version

Version 0.42.0 (Released August 22, 2019)
--------------

- Remove -e flags from requirements.in (#776)
- Remove -e flags in requirements.txt (#775)
- Upgrade Django to 2.1.11 (#770)

Version 0.41.1 (Released August 12, 2019)
--------------

- Changed edX auto-add to use edxval library endpoints

Version 0.41.0 (Released August 07, 2019)
--------------

- Added request to auto-add HLS videos to edX when appropriate

Version 0.40.0 (Released June 26, 2019)
--------------

- Update hijack version (#760)

Version 0.39.1 (Released June 26, 2019)
--------------

- Add cloudfront url to ShareVideoDialog (#755)

Version 0.39.0 (Released June 20, 2019)
--------------

- Upgrade css-loader (#756)

Version 0.38.0 (Released June 04, 2019)
--------------

- Update dependencies
- Update procfile
- Fix 500 error in video admin (#749)

Version 0.37.0 (Released April 22, 2019)
--------------

- Upgrading urllib3 version (#736)

Version 0.36.0 (Released April 01, 2019)
--------------

- bump docker to use stretch (#746)
- email validation updated
- test update to meet coverage
- util test added
- fix tests
- test added for views
- test updated
- test added for permissions
- fix quality
- views added for moira list and users

Version 0.35.0 (Released March 20, 2019)
--------------

- fix embded video not playing

Version 0.34.1 (Released January 11, 2019)
--------------

- Download videos directly from cloudfront (#734)

Version 0.34.0 (Released January 11, 2019)
--------------

- Filter out bad analytics data (#731)
- Handle bad video duration values for the analytics chart (#730)
- Add Video.custom_order field, reorder imports (#727)

Version 0.33.0 (Released November 05, 2018)
--------------

- Upgrade requests
- Fix lint tests (#721)
- Update pylint, astroid, and related packages (#716)
- Change no-videos message for anonymous (#719)

Version 0.32.0 (Released October 22, 2018)
--------------

- Enable anonymous access to collection pages (#709)

Version 0.31.1 (Released October 12, 2018)
--------------

- Added default sorting to created_at descending (#711)
- Lecture Capture: move unrecognized videos into an admin-only collection (#710)

Version 0.31.0 (Released October 10, 2018)
--------------

- Fix video start time in Safari (#705)
- Updated requirements.in based on feedback
- Updated package versions in requirements.txt file that have reported vulnerabilities

Version 0.30.0 (Released October 01, 2018)
--------------

- Added server status end-point for checking application certificate (#704)
- remove target from mailto links in faq (#699)
- Run Youtube upload task every hour (#703)
- Pin docker image versions (#693)

Version 0.29.1 (Released September 06, 2018)
--------------

- Configure raven.js (#688)

Version 0.29.0 (Released September 06, 2018)
--------------

- Remove IS_OSX now that Docker for Mac is used by everyone (#687)

Version 0.28.0 (Released September 05, 2018)
--------------

- Fix formatting with fmt
- Formatting of javascript with fmt (#682)
- Updated contact information in FAQ (#686)
- Remove IS_OSX variable (#675)

Version 0.27.0 (Released August 29, 2018)
--------------

- Clear collection errors from state after form submission (#681)
- Increase moira retrieval limit to 100K (#679)
- Add a missing TechTV route to urls.py (#678)

Version 0.26.0 (Released August 13, 2018)
--------------

- Removed extra LECTURE_CAPTURE_USER string (#672)

Version 0.25.1 (Released July 30, 2018)
--------------

- Fix issue with the Youtube play icon on mobile devices (#670)

Version 0.25.0 (Released July 26, 2018)
--------------

- Add version to django-shibboleth-remoteuser to force upgrade (#666)

Version 0.24.1 (Released July 24, 2018)
--------------

- Added select2 to Moira list selection dropdown (#663)
- Release date for 0.24.0

Version 0.24.0 (Released July 13, 2018)
--------------

- Add search admin site (#661)
- Pinned Dockerfile to python to 3.6.4

Version 0.23.1 (Released June 14, 2018)
--------------

- Add sentry handler to root and django logger configurations (#649)

Version 0.23.0 (Released June 11, 2018)
--------------

- Increase the max_length of Video.source_url (#644)

Version 0.22.0 (Released May 30, 2018)
--------------

- Public video download links (#642)

Version 0.21.2 (Released May 22, 2018)
--------------

- Exclude &#39;Cloudfront&#39; stream_source videos from Youtube upload task (#638)

Version 0.21.1 (Released May 21, 2018)
--------------

- Fix permissions issue with anonymous users and public videos (#635)

Version 0.21.0 (Released May 21, 2018)
--------------

- Update version for mit-moira (#632)
- refactoring CollectionDetail, in preparation for videos pagination
- add videos pagination backend
- restore videofile_set to serializer
- paginator style tweaks
- refactor moira list logic to use moira_client.user_list_membership
- Tweak line ordering
- Additional unit test

Version 0.20.0 (Released May 09, 2018)
--------------

- Fix login redirect (#621)
- update error message for 404
- Don&#39;t require login for 404 collection URLs (#609)
- Bring back the login view and make it the default LOGIN_URL (#616)
- add collection_key to SimpleVideoSerializer
- ignore transcode exceptions for deleted videos
- change &#39;Only me&#39; =&gt; &#39;Only owner&#39;, to clarify permissions behavior
- pass analytics overlay into video player for better sizing
- refresh collections in drawer after editing collection
- remove collections button from drawer, linkify drawer header
- analytics style tweaks
- add django-hijack for user masquerading
- add close button to analytics overlay
- Decouple watch bucket uploads from collection titles (#602)
- add active style for icons

Version 0.19.1 (Released May 03, 2018)
--------------

- add status messages to embed page
- add timestamps to models
- Per-user moira list cache (#587)
- add delete subtitles modal dialog
- add video count to collection items in drawer
- center play button in VideoPlayer
- Switch `fluid` property of VideoJS to true when switching from Youtube playback to Cloudfront if embedded (#594)
- &#39;Digital Learning&#39; =&gt; &#39;Open Learning&#39; in footer
- Add status to SimpleVideoSerializer
- anonymize terms-of-service page
- send debug emails to support for certain notification emails
- add toast messages for collection created/updated
- add contact us link to footer, fix email address var in error messages
- add toast message for subtitle deletion
- add toast message for uploading subtitles
- hides logout button when there is logged in user

Version 0.19.0 (Released May 01, 2018)
--------------

- one more check for empty dimensions/padding in analytics chart
- adding toast message to EditVideoFormDialog
- anonymize help page
- add error message for collection page
- add additional empty check when rendering analytics chart
- Simplified video serializer for collection page (#572)
- Adjust Youtube video dimensions
- adding toast message
- update notification email to include collection title
- add error message for collections page
- analytics dialog =&gt; analytics overlay

Version 0.18.1 (Released April 26, 2018)
--------------

- Make TTV collection name display on admin page for TTV video
- Remove forbidden characters from title/description before uploading to Youtube
- move create collection button (#561)
- revert &#39;-e&#39; changes for requirements, no need for &#39;-e&#39; w/ bug fix from pip 10.0.1
- revert &#39;-e&#39; changes for requirements, no need for &#39;-e&#39; w/ bug fix from pip 10.0.1
- remove defunct fn
- change playlist selector to select highest available active playlist
- revert .travis.yml change
- lower default collections page size to 50
- fix pip string for pip 10 (which tox force installs &gt;:( )
- test/format updates
- initial work on quality selector button
- scss lint fixup
- fix pip string for pip 10 (which tox force installs &gt;:( )
- change travis install to build instead of run
- Revert &#34;travis bump&#34;
- travis bump
- add flow checks
- fleshing out paginator tests
- updating withPagedCollections hoc tests
- adding tests for loading state to collection list page
- update api to use pagination parameters
- updating pagination actions
- updating paginations reducer tests
- tweak pagination styling
- adding start of paginator to collectionlistpage
- adding paginator handlers/styling
- combining collectionlistpage w/ hoc withPagedCollections
- add add actioncreator for set current page
- adding initial state for currentPage, adding handler for set_current_page
- add paging parameters to api getCollections call
- fleshing out hoc for paged collections
- fleshing out actions/reducers for pagination
- fleshing out collections pagination

Version 0.18.0 (Released April 23, 2018)
--------------

- Set collection and video titles
- add num_pages to response
- add start/end indices to collections pagination output

Version 0.17.1 (Released April 12, 2018)
--------------

- Add option to set start time on video
- Use different analytics queries for multiangle/singleangle videos
- Change embed size/styling
- Removes purple theme colors, and fixes spacing issue in sidenav (#544)

Version 0.17.0 (Released April 11, 2018)
--------------

- add &#39;more collections&#39; button to sidebar
- limit sidebar collections
- Collections API pagination
- Make the following CORS-compatible: error views, collections view, TechTV embed view
- video analytics frontend
- update example .env file with new keys

Version 0.16.1 (Released April 06, 2018)
--------------

- fix text field regressions from mdc upgrade
- Use redbeat to schedule tasks
- add YouTubeVideo model admin features
- Make videos full width (#514)
- Add backend handling for video analytics queries.
- Return a Youtube ID only if the status is processed
- Make video title required when editing
- Upload transcoded video to YouTube if original not available
- Make sure title and description both have no html tags and are truncated to within Youtube limitations on upload
- update @material components modules and add rmwc
- Make TechTV URLs work with or without slugs
- Stream videofiles from S3 to Youtube
- Make `ENABLE_VIDEO_PERMISSIONS` affect front-end video edit form only

Version 0.16.0 (Released April 02, 2018)
--------------

- add .pytest-cache to .gitignore
- if YoutubeVideo status not found, mark as failed
- &#39;let&#39; =&gt; &#39;const&#39;
- fix &#39;bail&#39; flag conditional
- fix yarn version
- enzyme =&gt; enzyme3
- Add {&#39;pipeline&#39;: &#39;odl-video-service-&lt;environment&gt;&#39;} to &#39;UserMetadata&#39; to ElasticTranscoder job
- add bail option
- Corrextly assign attributes to VideoSubtitles imported from TechTV
- Fixes a layout issue with squeezed icons (#491)

Version 0.15.2 (Released March 23, 2018)
--------------

- Don&#39;t try to save EncodeJobs on the video admin page
- Switch from celery.get_task_logger() to logging.getLogger() for tasks
- Show the encode job associated with each video in Admin
- Upload to youtube via daily celery task instead of signal
- Play YouTube videos through VideoJS
- Custom selectPlaylist function for videojs

Version 0.15.1 (Released March 21, 2018)
--------------

- Made the message posted in slack a bit more verbose for clarity

Version 0.15.0 (Released March 19, 2018)
--------------

- Upgrade to Django 1.11 (#465)
- Import public TechTV collections and set video stream source
- Force login on protected video URL&#39;s but not public video URL&#39;s
- Join BASE_DIR for STATIC_ROOT
- Renamed file to file_name based on feedback
- Added a check to verify that file has not already been synced and if it has to moved it to a &#34;conflict&#34; folder and notify slack
- Import TechTV captions

Version 0.14.1 (Released March 02, 2018)
--------------

- Update django-server-status to version 0.5.0

Version 0.14.0 (Released February 27, 2018)
--------------

- Updated settings and requirements to fix deployment issues

Version 0.13.0 (Released February 22, 2018)
--------------

- Handle nested moira permissions on individual video/collection pages
- Remove validation that moira list is a mailing list but send email notifications only if it is an email list
- TechTV URL&#39;s
- Updated cryptography requirement to fix incompatibility with OpenSSL
- Migration script for TechTV

Version 0.12.0 (Released February 01, 2018)
--------------

- Support for playing MP4 videos in multiple resolutions
- Fix scrolling issues in OVS sidebar (#425)

Version 0.11.0 (Released January 23, 2018)
--------------

- Update the FAQ

Version 0.10.1 (Released January 19, 2018)
--------------

- Refactor video analytics event collection
- Terms of Service page

Version 0.10.0 (Released January 16, 2018)
--------------

- fixed issue with long video titles that do not break (#400)
- Reformat using eslint-config-mitodl (#398)

Version 0.9.0 (Released January 08, 2018)
-------------

- Use unique s3 keys for each subtitle upload

Version 0.8.1 (Released December 28, 2017)
-------------

- bump psycopg to 2.7.3.2 (#389)
- Fix embedded videos
- Fix moira-related issues
- some accessibility changes (#387)

Version 0.8.0 (Released December 21, 2017)
-------------

- Add cloudfront configuration steps

Version 0.7.1 (Released November 30, 2017)
-------------

- Sync settings with cookiecutter (#376)

Version 0.7.0 (Released November 29, 2017)
-------------

- Youtube integration
- Fix subtitle deletion

Version 0.6.0 (Released November 17, 2017)
-------------

- Remove default mit email address (#355)
- Video-specific permission overrides
- 404 for invalid collection/video keys

Version 0.5.0 (Released November 08, 2017)
-------------

- Add FAQ page at /help
- Use application log level for Celery (#340)
- This fixes button style and layout bug (#338)
- Added video delete functionality
- More code review improvements
- Upgrade psycopg to fix error prevent build of web container
- Core review improvements
- Download original video source to Dropbox

Version 0.4.0 (Released October 26, 2017)
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

Version 0.3.0 (Released October 11, 2017)
-------------

- Playback rate control, disable autoplay
- Multi-angle VideoJS
- Fix config of root logger (#300)
- Add no-throw-literal eslint rule (#299)
- Remove default MAILGUN_URL, this should be set in .env instead (#298)
- Add missing return (#296)
- responsive layout fix (#294)
- Fix logging configuration (#293)

Version 0.2.1 (Released October 03, 2017)
-------------

- Fixing previous messy release
- Fixes Firefox layout bug in video cards thumbnails (#288)
- Improved lecture capture default video titles
- Smaller responsive video thumbnails on Collection Details page (#276)

Version 0.2.0 (Released September 25, 2017)
-------------

Version 0.1.0 (Released July 27, 2017)
-------------


