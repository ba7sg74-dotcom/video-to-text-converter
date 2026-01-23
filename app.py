import os
from flask import Flask, request, jsonify
from flask_cors import CORS
import yt_dlp
import whisper

app = Flask(__name__)
CORS(app)

# تحميل نموذج Whisper (النسخة الصغرى لضمان عدم استهلاك الرام)
model = whisper.load_model("tiny")

@app.route('/transcribe', methods=['POST'])
def transcribe_video():
    data = request.json
    video_url = data.get('url')
    
    if not video_url:
        return jsonify({"error": "No URL provided"}), 400

    try:
        # 1. إعدادات تحميل الصوت من الفيديو
        ydl_opts = {
            'format': 'bestaudio/best',
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '192',
            }],
            'outtmpl': 'temp_audio.%(ext)s',
        }

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([video_url])

        # 2. تحويل الصوت إلى نص
        result = model.transcribe("temp_audio.mp3")
        
        # 3. تنظيف الملفات المؤقتة
        if os.path.exists("temp_audio.mp3"):
            os.remove("temp_audio.mp3")

        return jsonify({"text": result['text']})

    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    # هذا السطر ضروري جداً لـ Render
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)