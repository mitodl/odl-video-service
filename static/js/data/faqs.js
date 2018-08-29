// @flow
/* global SETTINGS:false */
/* eslint-disable max-len */
import React from "react"

export const sectionFAQs = {
  "General Questions": {
    "What is OVS?": (
      <div>
        OVS is a web site for video hosting and distribution. It was built to
        host MIT videos that cannot be hosted on other platforms (like YouTube
        or Vimeo).
      </div>
    ),
    "What kinds of videos does OVS host?": (
      <ul>
        <li>Video lecture capture, using a custom multi-angle player</li>
        <li>
          Videos used for residential teaching at MIT. Usually the permission to
          view these videos is limited to the students in a specific class.
        </li>
        <li>
          Videos uses for worldwide teaching that need to be viewed in regions
          where YouTube is blocked
        </li>
        <li>Videos that used to be hosted on techtv.mit.edu</li>
      </ul>
    )
  },
  "Automated Video Lecture Capture": {
    "What is Automated Video Lecture Capture?": (
      <div>
        <div>
          Some rooms on campus at MIT have been configured to automatically
          record lectures using multiple cameras. Currently these rooms include
          2-131, 2-190, 6-120 and 34-101. Recording requests should be sent to{" "}
          <a
            href={`mailto:${SETTINGS.support_email_address}`}
            target="_blank"
            rel="noopener noreferrer"
          >
            {SETTINGS.support_email_address}
          </a>
        </div>
        <div>
          When viewing the videos recording in these rooms, viewers can select
          which camera or presentation source they prefer. This avoids the need
          for a an active camera operator who pans or switches between the
          instructor, chalkboard, computer display, etc.
        </div>
      </div>
    ),
    "How can I have my lectures recorded?": (
      <div>
        Automated lecture capture is currently available in rooms 2-131, 2-190,
        6-120 and 34-101. You can request that your lectures be recorded by
        sending an email to{" "}
        <a
          href={`mailto:${SETTINGS.support_email_address}`}
          target="_blank"
          rel="noopener noreferrer"
        >
          {SETTINGS.support_email_address}
        </a>
      </div>
    ),
    "How long does it take for the lecture capture videos to become available?": (
      <div>
        Videos recorded by the lecture capture systems in the classroom are
        automatically uploaded to the course collection overnight. Collection
        owners will receive an email notification with a link to each lecture
        when it is done being processed.
      </div>
    )
  },
  "Uploading Video and Managing Collections": {
    "Who can host videos on OVS?": (
      <ul>
        <li>Anyone in the MIT community can host videos on OVS.</li>
        <li>
          To request permission to upload your own videos, contact:{" "}
          <a
            href={`mailto:${SETTINGS.support_email_address}`}
            target="_blank"
            rel="noopener noreferrer"
          >
            {SETTINGS.support_email_address}
          </a>
        </li>
      </ul>
    ),
    "Why should I use Dropbox to upload videos on OVS?": (
      <div>
        <div>
          Dropbox can act as a repository for your video, giving you a safe
          place for storage so that your content does not get lost in the event
          of a failure of the OVS system. We strongly recommend that you keep
          your content on Dropbox as a backup in case you need to upload your
          videos elsewhere.
        </div>
        <div>
          You can request a free MIT Dropbox account from IS&T at{" "}
          <a
            href="https://dropbox.mit.edu/"
            target="_blank"
            rel="noopener noreferrer"
          >
            https://dropbox.mit.edu/
          </a>
        </div>
      </div>
    ),
    "Can I move all my YouTube videos to OVS?": (
      <div>
        <div>
          For public videos, Youtube is still the best location for people to
          view your content.
        </div>
        <div>
          If you have content that needs to be accessed by people in countries
          where Youtube is blocked, please contact{" "}
          <a href="mailto:odl-video-support@mit.edu">
            odl-video-support@mit.edu
          </a>{" "}
          for assistance.
        </div>
      </div>
    ),
    "Who has permission to view my videos?": (
      <div>
        <div>
          Course content is restricted to Stellar course access lists, or
          department email lists. In order to view the videos in a secured
          collection, the viewer must be on one of the access lists. In
          addition, collection administrators can add custom Moira lists for
          group access to videos.
        </div>
        <div>
          You can find out more about creating and managing Moira lists at{" "}
          <a
            href="https://ist.mit.edu/email-lists"
            target="_blank"
            rel="noopener noreferrer"
          >
            https://ist.mit.edu/email-lists
          </a>.
        </div>
      </div>
    ),
    "What if I want to give access to partner universities?": (
      <div>
        Non-MIT individuals can access content if they have a{" "}
        <a
          href="http://kb.mit.edu/confluence/display/istcontrib/Creating+a+Touchstone+Collaboration+Account"
          target="_blank"
          rel="noopener noreferrer"
        >
          Touchstone Collaboration
        </a>{" "}
        account and are on a Moira list.
      </div>
    ),
    "I would like my videos to be public.  How can I set my recordings to public?": (
      <div>
        If you would like your videos to be public, you can change the settings
        under the settings controls. Please note that a public setting will also
        post the videos to Youtube and that captions will be required to post
        public videos to conform would accessibility guidelines for public
        content.
      </div>
    ),
    "How long will it take for my video to be ready?": (
      <div>
        <div>
          If you uploaded from Dropbox, your video will be made available as
          soon as it has finished processing. The website will send you an email
          when your video is ready.
        </div>
        <div>
          If you do not see your video after 2 hours check your junk folder for
          the email notification. If you are sure you didn’t receive the email,
          please contact{" "}
          <a href="mailto:odl-video-support@mit.edu">
            odl-video-support@mit.edu
          </a>{" "}
          for assistance.
        </div>
      </div>
    )
  },
  Accessibility: {
    "Does OVS support captions and subtitles?": (
      <div>
        <div>
          Yes. Collection admins can upload WebVTT (.vtt) files format for
          subtitles) for their videos. You can find out more about WebVTT at{" "}
          <a
            href="https://w3c.github.io/webvtt/"
            target="_blank"
            rel="noopener noreferrer"
          >
            https://w3c.github.io/webvtt/
          </a>.
        </div>
        <div>
          Once uploaded, you should see the captions when you play your video
          and turn on the CC on the video toolbar.
        </div>
      </div>
    ),
    "How do I create captions?": (
      <div>
        There are several services online that you can use to upload your videos
        and create captions. You can use a service such as{" "}
        <a
          href="http://www.3playmedia.com"
          target="_blank"
          rel="noopener noreferrer"
        >
          PlayMedia
        </a>,{" "}
        <a href="http://www.rev.com" target="_blank" rel="noopener noreferrer">
          Rev
        </a>, or you can try some free services:{" "}
        <a
          href="http://www.amara.org"
          target="_blank"
          rel="noopener noreferrer"
        >
          Amara.org
        </a>{" "}
        and{" "}
        <a
          href="http://www.dotsub.com"
          target="_blank"
          rel="noopener noreferrer"
        >
          DotSub.com
        </a>. Make sure you request a WebVTT file, which you can then upload on
        your video page.
      </div>
    ),
    "I have a question that isn't on the FAQ": (
      <div>
        Please contact{" "}
        <a href="mailto:odl-video-support@mit.edu">odl-video-support@mit.edu</a>
      </div>
    )
  }
}
