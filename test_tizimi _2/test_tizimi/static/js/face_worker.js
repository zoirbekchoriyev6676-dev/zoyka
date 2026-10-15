// face_worker.js — Offscreen canvas & lightweight face detection worker
// Ushbu worker asosiy UI thread (savollar, tugmalar) qotib qolmasligi uchun alohida oqimda ishlaydi.

let detector = null;
let isBusy = false;

// Agar brauzerda Shape Detection API (FaceDetector) mavjud bo'lsa
if ("FaceDetector" in self) {
  try {
    detector = new self.FaceDetector({ fastMode: true, maxDetectedFaces: 5 });
  } catch (e) {
    detector = null;
  }
}

self.onmessage = async (e) => {
  const { type, imageBitmap } = e.data;
  if (type !== "DETECT_FACES") return;

  if (isBusy) {
    if (imageBitmap && imageBitmap.close) imageBitmap.close();
    return;
  }

  isBusy = true;
  try {
    let faceCount = 0;

    if (detector) {
      try {
        const faces = await detector.detect(imageBitmap);
        faceCount = faces.length;
      } catch (err) {
        faceCount = estimateFacesFallback(imageBitmap);
      }
    } else {
      faceCount = estimateFacesFallback(imageBitmap);
    }

    self.postMessage({
      type: "FACE_RESULT",
      faceCount: faceCount,
      timestamp: Date.now()
    });
  } catch (err) {
    self.postMessage({
      type: "FACE_ERROR",
      error: err.message
    });
  } finally {
    if (imageBitmap && imageBitmap.close) imageBitmap.close();
    isBusy = false;
  }
};

/**
 * Fallback: agar apparat darajasidagi FaceDetector qo'llab-quvvatlanmasa,
 * 320x240 pikseldagi kadr yorug'ligi va yuz tusi (skin-tone pixel distribution) tahlili
 * orqali kadrda inson bor-yo'qligini tekshiradi (CPU sarfi minimal < 2ms).
 */
function estimateFacesFallback(bitmap) {
  const width = bitmap.width;
  const height = bitmap.height;

  const canvas = new OffscreenCanvas(width, height);
  const ctx = canvas.getContext("2d", { willReadFrequently: true });
  ctx.drawImage(bitmap, 0, 0, width, height);

  const imgData = ctx.getImageData(0, 0, width, height);
  const data = imgData.data;

  let skinPixels = 0;
  let totalSampled = 0;

  // Har 4-pikselni tanlab (sampling) o'ta tez tahlil qilamiz
  for (let i = 0; i < data.length; i += 16) {
    const r = data[i];
    const g = data[i + 1];
    const b = data[i + 2];
    totalSampled++;

    // Universal inson terisi rang diapazoni (RGB skin-tone filter)
    if (r > 70 && g > 40 && b > 20 && (r - g) > 10 && r > b) {
      skinPixels++;
    }
  }

  const skinRatio = skinPixels / (totalSampled || 1);

  // Markaziy zonada yetarli darajada yuz/teri aniqlansa: 1 ta yuz
  if (skinRatio >= 0.12) {
    // Agar butun kadrni bir nechta katta maydon to'ldirsa
    if (skinRatio > 0.65) {
      return 2; // ehtimoliy bir nechta yuz
    }
    return 1;
  }
  return 0; // Yuz ko'rinmadi
}
