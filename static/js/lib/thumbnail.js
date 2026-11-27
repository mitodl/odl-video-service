// @flow
/* global SETTINGS: false */

// edX rejects video images outside these limits; the server sends them in SETTINGS
const minSize = () =>
  `${SETTINGS.thumbnail_min_width}x${SETTINGS.thumbnail_min_height}`

const isTooSmall = (width: number, height: number): boolean =>
  width < SETTINGS.thumbnail_min_width || height < SETTINGS.thumbnail_min_height

const isSixteenByNine = (width: number, height: number): boolean =>
  Math.abs(width / height - SETTINGS.thumbnail_aspect_ratio) <=
  SETTINGS.thumbnail_aspect_ratio_error_margin

export const getThumbnailRequirements = (): string =>
  `16:9, at least ${minSize()}`

export const getThumbnailDimensionError = (
  width: number,
  height: number
): ?string => {
  if (isTooSmall(width, height) || !isSixteenByNine(width, height)) {
    return `Thumbnails must be 16:9 and at least ${minSize()} pixels. This image is ${width}x${height}.`
  }
  return null
}

// A note for a thumbnail that is already stored but that edX will show adjusted, or null
export const getExistingThumbnailNote = (
  width: number,
  height: number
): ?string => {
  if (!isSixteenByNine(width, height)) {
    return `This thumbnail is ${width}x${height}, not 16:9, so edX courses show it with black bars. Replace it with a 16:9 image to fill the frame.`
  }
  if (isTooSmall(width, height)) {
    return `This thumbnail is ${width}x${height}, smaller than ${minSize()}, so edX courses show it enlarged. Replace it with a larger 16:9 image.`
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
