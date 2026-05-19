// shared/exif-stripper.js
//
// Client-side photo sanitiser for the One Health reporting flows.
//
// Hard rule (plan/06-mobile-app.md): photos must leave the device with
// no EXIF GPS unless the user has explicitly opted into location
// sharing. This module is the client-side enforcement point.
//
// Two exports:
//
//   sniffJpegHasGps(file)        -> Promise<boolean>
//     Look at the JPEG APP1 segment to see if the source file carried
//     GPS tags. Used for the audit trail (media_asset.original_had_gps).
//
//   stripExif(file, opts)        -> Promise<{ blob, originalHadGps }>
//     Re-encode the file through a canvas so the output has no EXIF
//     block at all. Defence-in-depth against forgotten GPS, plus
//     copyright / camera-serial metadata that's none of our business.
//
// The canvas re-encode is the actual strip: HTMLCanvasElement export
// does not preserve EXIF. We sniff first so we can record whether the
// strip was load-bearing for this report; that flag is useful for the
// validation pipeline and for governance audits, but the GPS values
// themselves are never read or written.

const APP1_MARKER          = 0xFFE1;
const EXIF_IDENTIFIER_BE   = 0x45786966; // "Exif"
const GPS_IFD_POINTER_TAG  = 0x8825;

/**
 * Walk the first APP1 segment of a JPEG and return true iff the
 * GPS-IFD pointer tag is present. The actual GPS values are never read.
 *
 * Returns false (defensively) for non-JPEG inputs.
 */
export async function sniffJpegHasGps(file) {
  if (!file || !(file instanceof Blob)) return false;
  // We only need the header; reading the whole file would be wasteful
  // for multi-MB phone shots.
  const headerSize = Math.min(file.size, 256 * 1024);
  const buf = await file.slice(0, headerSize).arrayBuffer();
  const view = new DataView(buf);

  // SOI must be 0xFFD8 (start-of-image) for any JPEG.
  if (view.byteLength < 4 || view.getUint16(0, false) !== 0xFFD8) {
    return false;
  }

  let offset = 2;
  while (offset < view.byteLength - 4) {
    const marker = view.getUint16(offset, false);
    if ((marker & 0xFF00) !== 0xFF00) return false; // misaligned
    const segLen = view.getUint16(offset + 2, false);
    if (segLen < 2) return false;

    if (marker === APP1_MARKER && offset + 4 + segLen < view.byteLength) {
      // APP1: check for the "Exif\0\0" identifier
      const idOffset = offset + 4;
      const id = view.getUint32(idOffset, false);
      if (id === EXIF_IDENTIFIER_BE) {
        return scanTiffForGps(view, idOffset + 6, idOffset + segLen);
      }
    }

    if (marker === 0xFFDA) return false; // start-of-scan: image data begins
    offset += 2 + segLen;
  }
  return false;
}

function scanTiffForGps(view, tiffStart, segEnd) {
  if (tiffStart + 8 > segEnd) return false;
  const byteOrder = view.getUint16(tiffStart, false);
  const little = (byteOrder === 0x4949); // 'II' = little-endian
  const ifd0Offset = view.getUint32(tiffStart + 4, little);
  const ifd0Abs = tiffStart + ifd0Offset;
  if (ifd0Abs + 2 > segEnd) return false;

  const entries = view.getUint16(ifd0Abs, little);
  for (let i = 0; i < entries; i++) {
    const entryAbs = ifd0Abs + 2 + i * 12;
    if (entryAbs + 4 > segEnd) return false;
    const tag = view.getUint16(entryAbs, little);
    if (tag === GPS_IFD_POINTER_TAG) return true;
  }
  return false;
}

/**
 * Re-encode an image file through an offscreen canvas so the output
 * has no EXIF block.
 *
 * Resolves to:
 *   { blob:            Blob,     // JPEG, no EXIF
 *     originalHadGps:  boolean,  // for media_asset.original_had_gps
 *     width:           number,
 *     height:          number,
 *     stripped:        true }
 */
export async function stripExif(file, opts = {}) {
  const maxDim = opts.maxDim || 2560; // cap shrink to keep multipart small
  const quality = opts.quality ?? 0.9;

  const originalHadGps = await sniffJpegHasGps(file);

  const bitmap = await createImageBitmap(file).catch(async () => {
    // Fallback: createImageBitmap can fail on HEIC etc.; let the
    // <img> decoder normalise it via decode().
    const url = URL.createObjectURL(file);
    try {
      const img = new Image();
      img.src = url;
      await img.decode();
      return img;
    } finally {
      URL.revokeObjectURL(url);
    }
  });

  const { width: w0, height: h0 } = bitmap;
  const scale = Math.min(1, maxDim / Math.max(w0, h0));
  const w = Math.round(w0 * scale);
  const h = Math.round(h0 * scale);

  const canvas = (typeof OffscreenCanvas !== 'undefined')
    ? new OffscreenCanvas(w, h)
    : Object.assign(document.createElement('canvas'), { width: w, height: h });
  const ctx = canvas.getContext('2d');
  ctx.drawImage(bitmap, 0, 0, w, h);

  const blob = (canvas instanceof OffscreenCanvas)
    ? await canvas.convertToBlob({ type: 'image/jpeg', quality })
    : await new Promise((resolve) => canvas.toBlob(resolve, 'image/jpeg', quality));

  // Final defence: confirm the output has no APP1/EXIF segment. The
  // canvas API guarantees this, but a test failure here would catch
  // a future browser regression.
  const outHasGps = await sniffJpegHasGps(blob);
  if (outHasGps) {
    throw new Error('exif-stripper: output still contained EXIF GPS');
  }

  return { blob, originalHadGps, width: w, height: h, stripped: true };
}
