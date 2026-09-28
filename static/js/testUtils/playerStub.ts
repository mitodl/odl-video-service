import type { SinonSandbox, SinonStub } from "sinon"

/*
 * A stand-in for a video.js player, shared by VideoPlayer_test.js and
 * video_player_controller_test.js -- the component test needs it because
 * `videojs()` is stubbed to return it, the controller test because the
 * controller is handed a player it never constructs.
 *
 * The text-track methods are real implementations over a plain `tracks`
 * array rather than stubs, so updateSubtitles' add/remove bookkeeping is
 * observable. Everything else is a sinon stub on the caller's sandbox, so
 * `sandbox.restore()` in the test's afterEach cleans up.
 */
type StubTrack = {
  src: string
  addEventListener?: (...args: any[]) => void
}

export const makePlayerStub = (sandbox: SinonSandbox) => {
  const player = {
    el_: {
      style:         {},
      dispatchEvent: sandbox.stub()
    },
    tracks:        [] as Array<StubTrack>,
    on:            sandbox.stub(),
    tech_:         {},
    // RTL unmounts after every test, so VideoPlayer's componentWillUnmount --
    // which the Enzyme tests never reached -- disposes the player for real.
    dispose:       sandbox.stub(),
    width:         sandbox.stub(),
    height:        sandbox.stub(),
    currentTime:   () => 630.5,
    duration:      () => 2400.0,
    videoWidth:    () => 640,
    videoHeight:   () => 360,
    currentWidth:  () => 1280,
    currentHeight: () => 720,
    textTracks:    function() {
      return this.tracks
    },
    removeRemoteTextTrack: function(track: StubTrack) {
      this.tracks.splice(this.tracks.indexOf(track), 1)
    },
    addRemoteTextTrack: function(track: StubTrack) {
      this.tracks.push({ src: track.src, addEventListener: sandbox.stub() })
    }
  }
  // video.js returns the player from these for chaining. They are assigned
  // after the literal because they close over `player` itself, so the object
  // is widened here rather than at the literal.
  const chained = player as typeof player & {
    reset: SinonStub
    src: SinonStub
    fluid: SinonStub
  }
  chained.reset = sandbox.stub().returns(player)
  chained.src = sandbox.stub().returns(player)
  chained.fluid = sandbox.stub().returns(player)
  return chained
}
