// The size the covers looked up on Google Books are fetched at (see
// UpdateBookReview's google_books_util.py), so custom ones match them.
const MAX_COVER_WIDTH = 800;
const MAX_COVER_HEIGHT = 1200;
const JPEG_QUALITY = 0.9;

// Any image the browser can read, as a JPEG no bigger than the above: what
// the API takes for a custom cover. Doing it here means a phone photo or a
// PNG uploads as a small JPEG, well within an API request's size limit.
export async function shrinkCoverToJpeg(file) {
  let bitmap;
  try {
    bitmap = await createImageBitmap(file);
  } catch {
    throw new Error("Couldn't read that image. Try a JPEG, PNG, or WebP.");
  }

  const scale = Math.min(1, MAX_COVER_WIDTH / bitmap.width, MAX_COVER_HEIGHT / bitmap.height);
  const canvas = document.createElement('canvas');
  canvas.width = Math.round(bitmap.width * scale);
  canvas.height = Math.round(bitmap.height * scale);
  const context = canvas.getContext('2d');
  // JPEG has no transparency, which would otherwise come out black.
  context.fillStyle = '#ffffff';
  context.fillRect(0, 0, canvas.width, canvas.height);
  context.drawImage(bitmap, 0, 0, canvas.width, canvas.height);
  bitmap.close();

  return new Promise((resolve, reject) => {
    canvas.toBlob(
      blob => (blob ? resolve(blob) : reject(new Error("Couldn't convert that image."))),
      'image/jpeg',
      JPEG_QUALITY,
    );
  });
}
