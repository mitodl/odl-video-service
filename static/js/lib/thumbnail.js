// @flow

// edX rejects video images outside these limits; keep in sync with odl_video/constants.py
export const THUMBNAIL_MIN_WIDTH = 640
export const THUMBNAIL_MIN_HEIGHT = 360
const THUMBNAIL_ASPECT_RATIO = 16 / 9
const THUMBNAIL_ASPECT_RATIO_ERROR_MARGIN = 0.1

export const THUMBNAIL_REQUIREMENTS = `16:9, at least ${THUMBNAIL_MIN_WIDTH}x${THUMBNAIL_MIN_HEIGHT}`

export const getThumbnailDimensionError = (
  width: number,
  height: number
): ?string => {
  const tooSmall = width < THUMBNAIL_MIN_WIDTH || height < THUMBNAIL_MIN_HEIGHT
  const aspectRatioDelta = Math.abs(width / height - THUMBNAIL_ASPECT_RATIO)
  if (tooSmall || aspectRatioDelta > THUMBNAIL_ASPECT_RATIO_ERROR_MARGIN) {
    return `Thumbnails must be 16:9 and at least ${THUMBNAIL_MIN_WIDTH}x${THUMBNAIL_MIN_HEIGHT} pixels. This image is ${width}x${height}.`
  }
  return null
}

const isSixteenByNine = (width: number, height: number): boolean =>
  Math.abs(width / height - THUMBNAIL_ASPECT_RATIO) <=
  THUMBNAIL_ASPECT_RATIO_ERROR_MARGIN

// A note for a thumbnail that is already stored but that edX will show adjusted, or null
export const getExistingThumbnailNote = (
  width: number,
  height: number
): ?string => {
  if (!isSixteenByNine(width, height)) {
    return `This thumbnail is ${width}x${height}, not 16:9, so edX courses show it with black bars. Replace it with a 16:9 image to fill the frame.`
  }
  if (width < THUMBNAIL_MIN_WIDTH || height < THUMBNAIL_MIN_HEIGHT) {
    return `This thumbnail is ${width}x${height}, smaller than ${THUMBNAIL_MIN_WIDTH}x${THUMBNAIL_MIN_HEIGHT}, so edX courses show it enlarged. Replace it with a larger 16:9 image.`
  }
  return null
}

export const getImageDimensions = (
  file: File
): Promise<{ width: number, height: number }> =>
  new Promise((resolve, reject) => {
    const url = URL.createObjectURL(file)
    const image = new Image()
    image.onload = () => {
      URL.revokeObjectURL(url)
      resolve({ width: image.naturalWidth, height: image.naturalHeight })
    }
    image.onerror = () => {
      URL.revokeObjectURL(url)
      reject(new Error("Could not read this image."))
    }
    image.src = url
  })
