Release Notes
=============

Version 0.2.1
-------------

- Fixes Firefox layout bug in video cards thumbnails (#288)
- Improved lecture capture default video titles
- Smaller responsive video thumbnails on Collection Details page (#276)
- Release 0.2.0
- Send emails to admin moira lists
- Fixed bug with unusable scrollbars after saving a dialog form
- Very minor tweaks (#268)
- Subtitles for videos
- Responsive styles for widescreen layout of collection page (#263)
- Added message for collections with no videos added yet
- Revert &#34;Fixed bug with redirect destination after touchstone login&#34;
- Fixes Safari Layout bug on Collection Details page (#255)
- Fixed bug with redirect destination after touchstone login
- Set logout redirect
- Expanded collections list to include view-enabled collections
- A few more style tweaks to OVS (#247)
- Removed unused forms (#246)
- Video counts on collection list page
- Added max height and inner scroll bar to dialog body
- Add dialog for creating a new collection (#240)
- Improved upload UI
- More styling fixes (#234)
- Remove owner from serializers, other code cleanup (#237)
- Sort collections by reverse creation date
- Fix scrollbar bug with dialogs
- Enabled video share button on collection detail page
- Enabled video edit button on collection detail page
- more UI tweaks (#214)
- Fix endless loop on forbidden collection pages
- Added collection edit dialog form
- Changed default mailgun_url to video.odl.mit.edu domain instead of micromasters as this service has its own mailgun domain
- Styling the side-drawer (#197)
- Merge pull request #193 from mitodl/mb/sandwich2
- footer styles (#194)
- OVS style changes (#191)
- Sandwich menu content
- Created React pages for collection list and detail
- Let read-only users see the collection detail page
- Increased the thumbnail size to 600x338
- Fix height of the USwitch player iframe
- Working share button
- style changes to video details page (#162)
- Restrict collection creation to staff users or superusers.
- Moira list permissions
- Indentation error
- Tweaked regular expression after testing on classroom machine
- Added some logic to parse output of s3 sync command and get the file names that have been uploaded and then use that list to move those specific files to the synced folder. Also added an entry in the settings file to point to the s3_sync_results_file
- Implemented video detail page display
- Reformatted paths for synced and done folders
- Added function to move files that have been uploaded to S3 to a local folder on the host. Also added that folder to the settings file
- Use environmental variables as x509 keys
- Added email notifications on Video change of status
- Added try/except block for reading config file
- Monitor and process video files in an S3 watch bucket
- Changes based on feedback
- PEP8 compliance changes, feedback from Giovanni, and removed an un-needed setting in the ini file
- Enable JS tests for travis (#131)
- Add collectstatic step (#133)
- Standardize docker-compose.yml
- Changes based on feedback and removed AWS CLI install since script would need to be run as admin and we want to avoid doing that
- Fixed bug with multiangle
- Changes based on feedback
- Fixed some small problems in the UI
- Fixed a typo and some spacing
- Automatically upload videos from specified folder to s3 bucket - Issue#100 - https://github.com/mitodl/odl-video-service/issues/100 Added two files, s3_sync and a setting ini file.
- Adding scripts for the pre-post compile
- Added Collections and refactored UI flow
- Update USwitch component
- Reformat JSON
- Update presets
- Hide the logo in the middle of the video that appears when not playing.
- Removed scriptjs
- Fixed and added tests
- Put USwitch player in an iframe, fix mosaic window, code review improvements
- Fix tests
- USwitch player for multiangle videos
- Introduced mandatory settings
- Video statuses restricted to a list
- - Updated AWS transcoder presets JSON to reflect LectureCapture settings     - Tweaked the createpresets management command to output `ET_PRESET_IDS=[list of generated preset ids]

Version 0.2.0
-------------

Version 0.1.0
-------------


