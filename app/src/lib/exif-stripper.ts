/**
 * Client-side photo sanitiser for the One Health reporting flows.
 *
 * Hard rule (plan/06-mobile-app.md): photos must leave the device
 * with no EXIF GPS unless the user has explicitly opted into location
 * sharing on their profile. This module is the client-side
 * enforcement point; the server runs the same check as
 * defence-in-depth.
 *
 * Canvas re-encode does the actual strip — HTMLCanvasElement /
 * OffscreenCanvas exports never preserve EXIF. We sniff the input
 * first so the audit trail (`originalHadGps`) can record whether the
 * strip was load-bearing for this report.
 */

const APP1_MARKER = 0xffe1;
const EXIF_IDENTIFIER_BE = 0x45786966; // "Exif"
const GPS_IFD_POINTER_TAG = 0x8825;

export interface StripResult {
  blob: Blob;
  originalHadGps: boolean;
  width: number;
  height: number;
  stripped: true;
}

export interface StripOpts {
  /** Largest dimension after resize. Defaults to 2560 px. */
  maxDim?: number;
  /** JPEG quality (0–1). Defaults to 0.9. */
  quality?: number;
}

/**
 * Walk the first APP1 segment of a JPEG and return true iff a
 * GPS-IFD pointer tag is present. We only read the tag presence,
 * never the GPS values themselves.
 */
export async function sniffJpegHasGps(file: Blob): Promise<boolean> {
  if (!(file instanceof Blob)) return false;
  const headerSize = Math.min(file.size, 256 * 1024);
  const buf = await file.slice(0, headerSize).arrayBuffer();
  const view = new DataView(buf);

  if (view.byteLength < 4 || view.getUint16(0, false) !== 0xffd8) return false;

  let offset = 2;
  while (offset < view.byteLength - 4) {
    const marker = view.getUint16(offset, false);
    if ((marker & 0xff00) !== 0xff00) return false;
    const segLen = view.getUint16(offset + 2, false);
    if (segLen < 2) return false;

    if (marker === APP1_MARKER && offset + 4 + segLen < view.byteLength) {
      const idOffset = offset + 4;
      const id = view.getUint32(idOffset, false);
      if (id === EXIF_IDENTIFIER_BE) {
        return scanTiffForGps(view, idOffset + 6, idOffset + segLen);
      }
    }

    if (marker === 0xffda) return false; // start-of-scan
    offset += 2 + segLen;
  }
  return false;
}

function scanTiffForGps(
  view: DataView,
  tiffStart: number,
  segEnd: number
): boolean {
  if (tiffStart + 8 > segEnd) return false;
  const byteOrder = view.getUint16(tiffStart, false);
  const little = byteOrder === 0x4949;
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
 * Re-encode an image file through a canvas so the output carries no
 * EXIF block. Returns the stripped JPEG plus whether the original
 * had GPS tags (for the media_asset audit trail).
 */
export async function stripExif(
  file: Blob,
  opts: StripOpts = {}
): Promise<StripResult> {
  const maxDim = opts.maxDim ?? 2560;
  const quality = opts.quality ?? 0.9;

  const originalHadGps = await sniffJpegHasGps(file);

  const source = await loadDecodable(file);
  const { width: w0, height: h0 } = source;
  const scale = Math.min(1, maxDim / Math.max(w0, h0));
  const w = Math.round(w0 * scale);
  const h = Math.round(h0 * scale);

  const canvas =
    typeof OffscreenCanvas !== 'undefined'
      ? new OffscreenCanvas(w, h)
      : Object.assign(document.createElement('canvas'), {
          width: w,
          height: h,
        });

  const ctx = (canvas as HTMLCanvasElement | OffscreenCanvas).getContext('2d');
  if (!ctx) throw new Error('exif-stripper: 2d context unavailable');
  (ctx as CanvasRenderingContext2D).drawImage(source as CanvasImageSource, 0, 0, w, h);

  const blob =
    canvas instanceof OffscreenCanvas
      ? await canvas.convertToBlob({ type: 'image/jpeg', quality })
      : await new Promise<Blob>((resolve, reject) =>
          (canvas as HTMLCanvasElement).toBlob(
            (b) => (b ? resolve(b) : reject(new Error('toBlob returned null'))),
            'image/jpeg',
            quality
          )
        );

  const outHasGps = await sniffJpegHasGps(blob);
  if (outHasGps) {
    throw new Error('exif-stripper: output still contained EXIF GPS');
  }

  return { blob, originalHadGps, width: w, height: h, stripped: true };
}

async function loadDecodable(file: Blob): Promise<ImageBitmap | HTMLImageElement> {
  try {
    return await createImageBitmap(file);
  } catch {
    // HEIC, AVIF, and a few other formats may not decode via
    // createImageBitmap on all browsers. Fall through to <img>.
    const url = URL.createObjectURL(file);
    try {
      const img = new Image();
      img.src = url;
      await img.decode();
      return img;
    } finally {
      URL.revokeObjectURL(url);
    }
  }
}
