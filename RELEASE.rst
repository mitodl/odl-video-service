Release Notes
=============

Version 0.21.1
--------------

- Fix permissions issue with anonymous users and public videos (#635)

Version 0.21.0
--------------

- Update version for mit-moira (#632)
- refactoring CollectionDetail, in preparation for videos pagination
- add videos pagination backend
- restore videofile_set to serializer
- paginator style tweaks
- refactor moira list logic to use moira_client.user_list_membership
- Tweak line ordering
- Additional unit test

Version 0.20.0
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

Version 0.19.1
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

Version 0.19.0
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

Version 0.18.1
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

Version 0.18.0
--------------

- Set collection and video titles
- add num_pages to response
- add start/end indices to collections pagination output

Version 0.17.1
--------------

- Add option to set start time on video
- Use different analytics queries for multiangle/singleangle videos
- Change embed size/styling
- Removes purple theme colors, and fixes spacing issue in sidenav (#544)

Version 0.17.0
--------------

- add &#39;more collections&#39; button to sidebar
- limit sidebar collections
- Collections API pagination
- Make the following CORS-compatible: error views, collections view, TechTV embed view
- video analytics frontend
- update example .env file with new keys

Version 0.16.1
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

Version 0.16.0
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

Version 0.15.2
--------------

- Don&#39;t try to save EncodeJobs on the video admin page
- Switch from celery.get_task_logger() to logging.getLogger() for tasks
- Show the encode job associated with each video in Admin
- Upload to youtube via daily celery task instead of signal
- Play YouTube videos through VideoJS
- Custom selectPlaylist function for videojs

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


