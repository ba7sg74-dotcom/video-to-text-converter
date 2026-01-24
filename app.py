from flask import Flask, request, jsonify, send_file
import yt_dlp
import whisper
import os
import tempfile
from pathlib import Path
import uuid

app = Flask(__name__)

# تحميل نموذج Whisper (يتم تحميله مرة واحدة عند التشغيل)
model = whisper.load_model("base")  # يمكن تغيير إلى "small", "medium", "large"

@app.route('/')
def home():
    return jsonify({"status": "YouTube Video to Text Converter API"})

@app.route('/process', methods=['POST'])
def process_video():
    data = request.json
    url = data.get('url')
    
    if not url:
        return jsonify({"error": "No URL provided"}), 400
    
    try:
        # إنشاء مجلد مؤقت
        temp_dir = tempfile.mkdtemp()
        video_id = str(uuid.uuid4())[:8]
        
        # خيارات yt-dlp
        ydl_opts = {
            'format': 'bestaudio/best',
            'outtmpl': os.path.join(temp_dir, f'{video_id}.%(ext)s'),
            'quiet': True,
            'no_warnings': True,
        }
        
        # تحميل الفيديو/الصوت
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            downloaded_file = ydl.prepare_filename(info)
            
            # إذا كان الملف يحتوي على امتداد غير دقيق
            actual_files = list(Path(temp_dir).glob(f"{video_id}.*"))
            if actual_files:
                audio_file = str(actual_files[0])
            else:
                return jsonify({"error": "Failed to download file"}), 500
        
        # تحويل الصوت إلى نص
        result = model.transcribe(audio_file)
        transcript = result["text"]
        
        # تنظيف الملفات المؤقتة
        for file in Path(temp_dir).glob("*"):
            file.unlink()
        os.rmdir(temp_dir)
        
        return jsonify({
            "success": True,
            "title": info.get('title', 'Unknown'),
            "transcript": transcript,
            "video_id": video_id
        })
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/download-audio', methods=['POST'])
def download_audio_only():
    """لتحميل الصوت فقط بدون تحويل إلى نص"""
    data = request.json
    url = data.get('url')
    
    if not url:
        return jsonify({"error": "No URL provided"}), 400
    
    try:
        temp_dir = tempfile.mkdtemp()
        video_id = str(uuid.uuid4())[:8]
        
        ydl_opts = {
            'format': 'bestaudio/best',
            'outtmpl': os.path.join(temp_dir, f'{video_id}.mp3'),
            'quiet': True,
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '192',
            }],
        }
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            audio_file = os.path.join(temp_dir, f'{video_id}.mp3')
            
            if os.path.exists(audio_file):
                return send_file(audio_file, as_attachment=True, download_name=f"{video_id}.mp3")
            else:
                return jsonify({"error": "Failed to create audio file"}), 500
                
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)