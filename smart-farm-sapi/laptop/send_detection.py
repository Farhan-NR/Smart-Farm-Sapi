"""Dipakai di skrip YOLOv8 laptop. Panggil kirim() saat ada deteksi/anomali."""
import json, requests

VPS_URL = "http://10.33.109.63:8000/api/detections"
API_KEY = "ganti-dengan-kunci-rahasia"

def kirim(camera, cow_id, behavior, confidence, is_anomaly, frame_bgr=None):
    import cv2
    payload = {"camera": camera, "cow_id": cow_id, "behavior": behavior,
               "confidence": round(float(confidence), 3), "is_anomaly": bool(is_anomaly)}
    files = None
    if frame_bgr is not None:
        ok, buf = cv2.imencode(".jpg", frame_bgr, [cv2.IMWRITE_JPEG_QUALITY, 80])
        if ok:
            files = {"photo": ("snap.jpg", buf.tobytes(), "image/jpeg")}
    try:
        r = requests.post(VPS_URL, headers={"X-API-Key": API_KEY},
                          data={"data": json.dumps(payload)}, files=files, timeout=10)
        return r.status_code == 200
    except requests.RequestException as e:
        print("gagal kirim:", e)   # TODO: simpan antrean lokal lalu retry
        return False

if __name__ == "__main__":
    print(kirim("kandang1", "sapi_3", "berdiri", 0.91, False))
