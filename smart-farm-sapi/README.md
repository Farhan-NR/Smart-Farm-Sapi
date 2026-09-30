# Setup Backend Monitoring Sapi

## Alur
CCTV Tapo --RTSP (LAN)--> MediaMTX laptop --RTSP push--> MediaMTX VPS --WebRTC--> Dashboard (VPS)
Laptop (YOLOv8) --POST JSON+foto--> FastAPI VPS --> SQLite + foto --> Telegram (jika anomali)

## 1. SSH ke VPS (cukup SSH saja, tidak perlu GUI)
    ssh ghaniy@10.33.109.63      # wajib VPN/WiFi UGM
    passwd                        # GANTI password sekarang
    sudo apt update && sudo apt install -y python3-venv ffmpeg ufw

## 2. MediaMTX di VPS
    # unduh rilis linux_amd64 dari github.com/bluenviron/mediamtx/releases
    tar xzf mediamtx_*_linux_amd64.tar.gz && cp vps/mediamtx.yml ./mediamtx.yml
    ./mediamtx        # coba dulu; nanti jadikan systemd service

## 3. Backend FastAPI di VPS
    cd vps && python3 -m venv .venv && . .venv/bin/activate
    pip install -r requirements.txt
    export API_KEY="kunci-rahasia" VPS_HOST=10.33.109.63
    export TELEGRAM_BOT_TOKEN="..." TELEGRAM_CHAT_ID="..."   # opsional
    uvicorn main:app --host 0.0.0.0 --port 8000
    # Dashboard: http://10.33.109.63:8000

## 4. Firewall VPS
    sudo ufw allow 22/tcp && sudo ufw allow 8000/tcp
    sudo ufw allow 8554/tcp && sudo ufw allow 8889/tcp && sudo ufw allow 8189/udp
    sudo ufw allow 8888/tcp && sudo ufw enable

## 5. Laptop
    # jalankan mediamtx dengan laptop/mediamtx.yml (isi IP/akun Tapo + password publish)
    # test kirim data: python laptop/send_detection.py

## Catatan
- Tes cepat: curl -H "X-API-Key: kunci" -F 'data={"camera":"k1","cow_id":"sapi_3","behavior":"berdiri","confidence":0.9,"is_anomaly":true}' -F photo=@foto.jpg http://10.33.109.63:8000/api/detections
- WebRTC lewat VPN kadang butuh `webrtcAdditionalHosts: [10.33.109.63]` di mediamtx.yml VPS.
- Jika Telegram diblokir dari jaringan kampus, kirim notifikasi dari laptop saja.
- Data sedikit -> SQLite cukup; ganti ke PostgreSQL bila perlu multi-user.
