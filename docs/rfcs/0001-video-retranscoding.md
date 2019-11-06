## Video Re-transcoding

#### Abstract
Provide a way to trigger re-transcoding of specified videos, or all videos in a collection, if new presets are needed.


#### Architecture Changes

- Create a flag on Collection and Video: boolean field ‘schedule_retranscode’
- Create a recurring task to look for videos and collections with `schedule_retranscode=True`.
  - check flagged collections first:
     - set `schedule_retranscode=True` for every Video in the Collection, then
     - set `schedule_retranscode=False` on the Collection
  - Trigger a new encode job for each flagged Video.
  - Assign a new video status - ‘Retranscoding’
  - Set `schedule_retranscode=False` on the Video
- Modify the generation of encoding job metadata:
  - a temporary prefix should be added to the output filenames to avoid transcode errors that occur when trying to overwrite existing output from the previous transcode
- Videos being re-transcoded should still be playable (front end needs to accept the new reencoding status as playable)
- Modify the task that checks on video transcode statuses
  - should handle the new Retranscoding status
  - There will now be 2+ encode jobs for the video instead of just 1, the most recent is the one that needs to be checked for progress.
- When a retranscoding is complete:
  - copy output from the temporary S3 subfolder to the correct subfolder, then delete the temporary files
  - Change video status back to complete
- If a retranscoding task fails:
  - Log the error
  - Set video status back to complete (original transcode should still work)

#### Security/Other Considerations

If for some reason the copying of retranscoded S3 files is interrupted or fails partway, the video may be rendered unplayable, since some of the original transcode files will be overwritten.


#### Testing & Rollout
- Upload some new videos into different collections
- Add some new presets or take some away (`ET_PRESET_IDS` in .env file)
- Set `schedule_retranscode=True` on one video, and also on a different collection
- Wait for the new scheduled task to run
- Verify that statuses and flags are updated appropriately and new transcode jobs are started
- While waiting for transcode jobs to complete, verify that the videos can still be played
- Verify that the status check task correctly updates video statuses when retranscodes are complete
- Verify that the videos are playable and that the .m3u8 playlist file contains the new presets