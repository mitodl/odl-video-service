// @flow
/* global videojs: true */
import React from "react";

import { makeVideoSubtitleUrl } from "../lib/urls";
import { getHLSEncodedUrl, videojs } from "../lib/video";
import type { Video, VideoSubtitle } from "../flow/videoTypes";
import { FULLSCREEN_API } from "../util/fullscreen_api";
import { CANVASES } from "../constants";
import { sendGAEvent } from "../util/google_analytics";

const gaEvents = ["play", "pause", "seeked", "timeupdate", "fullscreen off", "fullscreen on", "ended"];

const makeConfigForVideo = (video: Video): Object => ({
  autoplay: false,
  controls: true,
  fluid: false,
  playsinline: true,
  html5: {
    nativeTextTracks: false
  },
  playbackRates: [0.50, 0.75, 1.0, 1.25, 1.5, 2.0, 4.0],
  sources: [{
    src: getHLSEncodedUrl(video),
    type: "application/x-mpegURL",
  }]
});

const drawCanvasImage = function(canvas, videoNode, shiftX, shiftY) {
  const x = shiftX ? Math.floor(videoNode.videoWidth / 2) : 0;
  const y = shiftY ? Math.floor(videoNode.videoHeight / 2) : 0;
  const context = canvas.getContext("2d");
  context.drawImage(
    videoNode,
    x, y, Math.floor(videoNode.videoWidth / 2), Math.floor(videoNode.videoHeight / 2),
    0, 0, canvas.width, canvas.height
  );
  setTimeout(drawCanvasImage, 20, canvas, videoNode, shiftX, shiftY);
};

const isFullscreen = function() {
  // $FlowFixMe
  return document[FULLSCREEN_API.fullscreenElement];
};

export default class VideoPlayer extends React.Component {
  props: {
    video: Video,
    selectedCorner: string,
    cornerFunc: (corner: string) => void
  };

  player: Object;
  videoNode: HTMLVideoElement;
  videoContainer: HTMLDivElement;
  cameras: HTMLDivElement;
  percentTracked: Array<number>;

  updateSubtitles() {
    const { video } = this.props;
    if (this.player) {
      // Remove existing tracks for deleted subtitles
      const tracks = this.player.textTracks();
      let subtitleUrls = video.videosubtitle_set.map((subtitle: VideoSubtitle) => (makeVideoSubtitleUrl(subtitle)));
      let trackUrls = [];
      for (let idx = 0; idx < tracks.length; idx++) {
        if (tracks[idx] && !subtitleUrls.includes(tracks[idx].src)) {
          this.player.removeRemoteTextTrack(tracks[idx]);
        } else {
          trackUrls.push(tracks[idx].src);
        }
      }
      // Add tracks for any new subtitles associated with the video
      video.videosubtitle_set.forEach((subtitle: VideoSubtitle) => {
        const subUrl = makeVideoSubtitleUrl(subtitle);
        if (!trackUrls.includes(subUrl)) {
          this.player.addRemoteTextTrack({
            kind: "captions",
            src: subUrl,
            srcLang: subtitle.language,
            label: subtitle.language_name,
          }, true);
        }
        // Add listeners to each track
        let player = this.player;
        for (let idx = 0; idx < this.player.textTracks().length; idx++) {
          if (!trackUrls.includes(tracks[idx].src)) {
            tracks[idx].addEventListener("modechange", function() {
              sendGAEvent(
                "video",
                "modechange",
                `Subtitles for ${this.label} ${this.mode}`, player.currentTime());
            });
          }
        }
      });
    }
  }

  drawCanvas(canvas: HTMLCanvasElement, shiftX: boolean, shiftY: boolean) {
    canvas.width = Math.floor(this.videoNode.offsetWidth / 4) - 2;
    canvas.height = Math.floor(this.videoNode.offsetHeight / 4) - 2;
    if (canvas && this.videoNode) {
      drawCanvasImage(canvas, this.videoNode, shiftX, shiftY);
    }
  }

  configureCameras() {
    if (this.cameras) {
      const canvasElements = this.cameras.getElementsByTagName("canvas");
      Object.keys(CANVASES).forEach(corner => {
        this.drawCanvas(
          // $FlowFixMe - corner does not have to be a number
          canvasElements[corner],
          CANVASES[corner].shiftX,
          CANVASES[corner].shiftY
        );
      });
    }
  }

  cropVideo = () => {
    const { selectedCorner } = this.props;
    const shiftX = CANVASES[selectedCorner].shiftX;
    const shiftY = CANVASES[selectedCorner].shiftY;
    const transformProps = ["transform", "WebkitTransform", "MozTransform", "msTransform", "OTransform"];

    const prop = transformProps.find(property => this.player.el_.style[property] !== undefined) || transformProps[0];
    const aspectRatio = (this.player.videoWidth() / this.player.videoHeight());
    let videoWidth = Math.min(
      parseInt(window.getComputedStyle(this.videoNode).maxHeight) * aspectRatio,
      window.innerWidth,
      screen.width
    );
    if (isNaN(videoWidth) || isFullscreen()) {
      videoWidth = Math.min(window.innerWidth, screen.width);
    }
    const canvasWidth = Math.floor(videoWidth / 4);
    videoWidth = Math.floor(videoWidth - (canvasWidth - (canvasWidth / aspectRatio / 3)));
    this.videoContainer.style.maxWidth = `${videoWidth}px`;
    // $FlowFixMe videoContainer.parentElement is not going to be null
    this.videoContainer.parentElement.style.width = `${videoWidth + canvasWidth}px`;
    const left = Math.round(this.player.currentWidth() / (shiftX ? -2 : 2));
    const top = Math.round(this.player.currentHeight() / (shiftY ? -2 : 2));
    this.videoNode.style.left = `${left}px`;
    this.videoNode.style.top = `${top}px`;
    // $FlowFixMe prop does not have to be a number
    this.videoNode.style[prop] = "scale(2)";
    this.configureCameras();

  }

  toggleFullscreen = () => {
    let fullscreen = isFullscreen();
    if (fullscreen) {
      // $FlowFixMe
      document[FULLSCREEN_API.exitFullscreen]();
    } else {
      // $FlowFixMe videoContainer.parentElement is not going to be null
      this.videoContainer.parentElement[FULLSCREEN_API.requestFullscreen]();
    }
    this.player.el_.dispatchEvent(new Event(`fullscreen ${fullscreen ? "off" : "on"}`));
  }

  sendEvent = (action: string, label: string) => {
    if (action === "timeupdate") {
      // Track percentage played in increments of 10
      const currentTime = this.player.currentTime();
      const duration = this.player.duration();
      const percentPlayed = currentTime / duration * 100;
      const percentRoundTen = percentPlayed - (percentPlayed % 10);
      if (!this.percentTracked.includes(percentRoundTen)) {
        sendGAEvent("video", action, "percentPlayed", percentRoundTen);
        this.percentTracked.push(percentRoundTen);
      }
    } else {
      sendGAEvent("video", action, label, this.player.currentTime());
    }
  }

 createEventHandler = (action: string, label: string) => {
   const sendEvent = this.sendEvent;
   this.player.on(action, function() {
     sendEvent(action, label);
   });
 }

 componentDidMount() {
   const { video } = this.props;
   const cropVideo = this.cropVideo;
   const createEventHandler = this.createEventHandler;
   const toggleFullscreen = this.toggleFullscreen;
   if (video.multiangle) {
     videojs.getComponent("FullscreenToggle").prototype.handleClick = toggleFullscreen;
   }
   this.percentTracked = [];
   this.player = videojs(
     this.videoNode, makeConfigForVideo(video), function onPlayerReady() {
       this.enableTouchActivity();
       if (video.multiangle) {
         this.on("loadeddata", cropVideo);
         this.on(FULLSCREEN_API.fullscreenchange, cropVideo);
         window.addEventListener("resize", cropVideo);
       }
       this.on("loadeddata", function() {
         gaEvents.forEach((event: string) => {
           createEventHandler(event, event);
         });
       });
     });
   this.updateSubtitles();
 }

 componentDidUpdate() {
   this.updateSubtitles();
 }

  // destroy player on unmount
 componentWillUnmount() {
   if (this.player) {
     this.player.dispose();
   }
 }

  clickCamera = async (corner: string) => {
    const { cornerFunc } = this.props;
    if (cornerFunc) {
      sendGAEvent("video", 'changeCameraView', corner, this.player.currentTime());
      await cornerFunc(corner);
      this.cropVideo();
    }
  }

  render() {
    const { video, selectedCorner } = this.props;
    return (
      <div className="fullwidth-band">
        <div className="video-odl-center">
          <div
            className={`video-odl-medium ${video.multiangle ? "video-odl-multiangle" : ""}`}
            ref={node => this.videoContainer = node}>
            <div data-vjs-player>
              <video
                ref={node => this.videoNode = node}
                className="video-js vjs-default-skin"
                crossOrigin="anonymous"
                controls
              />
            </div>
          </div>
          {video.multiangle &&
          <div ref={node => this.cameras = node} className="camera-bar">
            {Object.keys(CANVASES).map(corner => (
              <div key={corner}>
                <canvas id={corner} key={corner}
                  onClick={this.clickCamera.bind(this, corner)}
                  className={`camera-box ${corner === selectedCorner ? "camera-box-selected" : ""}`}
                />
              </div>)
            )}
          </div>
          }
        </div>
      </div>
    );
  }
}
