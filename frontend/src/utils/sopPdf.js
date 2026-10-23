/**
 * Client-side PDF export for standard documents.
 *
 * The document text is interpolated in the browser (see SopDocPage), rasterised
 * with html2canvas and assembled into an A4 PDF with jsPDF. Nothing is sent to
 * the backend — the PDF is produced and downloaded entirely on the client.
 *
 * html2canvas is used rather than jsPDF's text API because jsPDF's built-in
 * fonts have no CJK coverage, and embedding a full Chinese font would bloat the
 * bundle by several megabytes. Rasterising the rendered paper keeps the
 * typography identical to the on-screen preview.
 *
 * Both libraries are loaded lazily: they are only needed when the maker
 * actually exports a document, and they add ~600 kB to the main bundle.
 */

// A4 with a 12mm margin on every side.
const PAGE_W_MM = 210;
const PAGE_H_MM = 297;
const MARGIN_MM = 12;
const CONTENT_W_MM = PAGE_W_MM - MARGIN_MM * 2;
const CONTENT_H_MM = PAGE_H_MM - MARGIN_MM * 2;

/**
 * Build a filesystem-safe filename from a document title.
 */
export function buildPdfFileName(title, serial) {
  const safeTitle = String(title || '标准文书')
    .replace(/[\\/:*?"<>|\s]+/g, '_')
    .slice(0, 60);
  const safeSerial = String(serial || '').replace(/[^\w-]/g, '');
  return safeSerial ? `${safeTitle}_${safeSerial}.pdf` : `${safeTitle}.pdf`;
}

/**
 * Rasterise a DOM node and download it as a multi-page A4 PDF.
 *
 * @param {HTMLElement} element  The paper element holding the document body.
 * @param {string} fileName      Target download filename.
 * @param {object} [options]
 * @param {number} [options.scale=2]  Rasterisation scale (higher = sharper).
 * @returns {Promise<{pages: number, fileName: string}>}
 */
export async function exportElementToPdf(element, fileName, options = {}) {
  if (!element) {
    throw new Error('未找到可导出的文书内容');
  }

  const scale = options.scale ?? 2;

  // Load the PDF toolchain only when an export is actually requested.
  const [{ default: html2canvas }, { jsPDF }] = await Promise.all([
    import('html2canvas'),
    import('jspdf'),
  ]);

  // Render on a white background: the glass surfaces are translucent and would
  // otherwise come out with a transparent (or black) page background.
  const canvas = await html2canvas(element, {
    scale,
    backgroundColor: '#ffffff',
    useCORS: true,
    logging: false,
    windowWidth: element.scrollWidth,
    windowHeight: element.scrollHeight,
  });

  const pdf = new jsPDF({
    orientation: 'portrait',
    unit: 'mm',
    format: 'a4',
    compress: true,
  });

  // The source image is scaled to the printable width; its height in mm then
  // tells us how many A4 pages are needed.
  const imgW = CONTENT_W_MM;
  const imgH = (canvas.height * imgW) / canvas.width;
  const pageCount = Math.max(1, Math.ceil(imgH / CONTENT_H_MM));

  // Pixels of the source image that fit on one page.
  const pxPerMm = canvas.width / imgW;
  const pageHeightPx = CONTENT_H_MM * pxPerMm;

  for (let page = 0; page < pageCount; page += 1) {
    const sourceY = page * pageHeightPx;
    const sourceHeight = Math.min(pageHeightPx, canvas.height - sourceY);
    if (sourceHeight <= 0) break;

    if (page > 0) {
      pdf.addPage();
    }

    // Crop the slice belonging to this page into its own canvas.
    const slice = document.createElement('canvas');
    slice.width = canvas.width;
    slice.height = Math.max(1, Math.round(sourceHeight));
    const ctx = slice.getContext('2d');
    ctx.fillStyle = '#ffffff';
    ctx.fillRect(0, 0, slice.width, slice.height);
    ctx.drawImage(
      canvas,
      0,
      Math.round(sourceY),
      canvas.width,
      slice.height,
      0,
      0,
      canvas.width,
      slice.height
    );

    const sliceData = slice.toDataURL('image/jpeg', 0.92);
    const sliceH = (slice.height * imgW) / slice.width;
    pdf.addImage(sliceData, 'JPEG', MARGIN_MM, MARGIN_MM, imgW, sliceH, undefined, 'FAST');
  }

  // Download the PDF ourselves rather than via pdf.save().
  //
  // Two browser quirks have to be worked around for the file to really land:
  //  1. jsPDF's save() creates a *detached* anchor. Chrome ignores downloads
  //     triggered from an anchor that is not in the document.
  //  2. Chrome resolves the blob URL asynchronously, after the click handler
  //     returns. Revoking the URL too early aborts the download, so the URL is
  //     kept alive well past the click.
  const blob = pdf.output('blob');
  await savePdfToDisk(blob, fileName);

  return { pages: pageCount, fileName, blob };
}

/**
 * Save a PDF blob to the user's disk.
 *
 * Prefers the File System Access API when available: it opens the browser's
 * native "Save as" dialog, so the maker picks the location and the file is
 * written directly. Falls back to a normal browser download otherwise.
 *
 * @param {Blob} blob
 * @param {string} fileName
 * @returns {Promise<{method: 'picker'|'download', fileName: string}>}
 */
export async function savePdfToDisk(blob, fileName) {
  // The picker needs a live user gesture, which is lost across the awaits
  // performed while rendering — so it is only attempted when the caller
  // signals the gesture is still valid.
  if (typeof window.showSaveFilePicker === 'function' && navigator.userActivation?.isActive) {
    try {
      const handle = await window.showSaveFilePicker({
        suggestedName: fileName,
        types: [{
          description: 'PDF 文书',
          accept: { 'application/pdf': ['.pdf'] },
        }],
      });
      const writable = await handle.createWritable();
      await writable.write(blob);
      await writable.close();
      return { method: 'picker', fileName };
    } catch (e) {
      // AbortError means the maker closed the dialog — do not fall back.
      if (e?.name === 'AbortError') {
        return { method: 'cancelled', fileName };
      }
      // Any other failure (e.g. unsupported) falls through to the download path.
    }
  }

  triggerDownload(blob, fileName);
  return { method: 'download', fileName };
}

/**
 * Save a blob to the user's disk via a normal browser download.
 *
 * The anchor is attached to the document before the click is dispatched — a
 * detached anchor is ignored by Chrome and the download silently fails. The
 * object URL is revoked only after a generous delay, because Chrome reads the
 * blob asynchronously and revoking it too early aborts the transfer.
 */
export function triggerDownload(blob, fileName) {
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement('a');
  anchor.href = url;
  anchor.download = fileName;
  anchor.rel = 'noopener';
  anchor.style.display = 'none';

  document.body.appendChild(anchor);
  try {
    anchor.click();
  } finally {
    // Keep the object URL alive long enough for Chrome to consume the blob.
    setTimeout(() => {
      anchor.remove();
      URL.revokeObjectURL(url);
    }, 60_000);
  }
}
