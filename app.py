from flask import Flask, render_template, request, jsonify, send_file
from flask_cors import CORS
import os
import tempfile
import yt_dlp
import whisper
import warnings
warnings.filterwarnings("ignore")

app = Flask(__name__, static_folder='.', static_url_path='')
CORS(app)

# تكوين yt-dlp
ydl_opts = {
    'format': 'bestaudio/best',
    'quiet': True,
    'no_warnings': True,
    'extract_flat': False,
}

# تحميل نموذج Whisper (سيتم تحميله عند أول طلب)
model = None

def load_whisper_model():
    """تحميل نموذج Whisper مرة واحدة"""
    global model
    if model is None:
        print("جاري تحميل نموذج Whisper...")
        model = whisper.load_model("base")
        print("تم تحميل النموذج بنجاح!")
    return model

def download_audio(url):
    """تحميل الصوت من فيديو YouTube"""
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            audio_file = ydl.prepare_filename(info)
            
            # التأكد من أن الملف موجود
            if not os.path.exists(audio_file):
                # محاولة الحصول على امتداد مختلف
                for ext in ['.webm', '.m4a', '.mp3']:
                    alt_file = audio_file.rsplit('.', 1)[0] + ext
                    if os.path.exists(alt_file):
                        audio_file = alt_file
                        break
            
            return audio_file, info
    except Exception as e:
        raise Exception(f"خطأ في تحميل الفيديو: {str(e)}")

def transcribe_audio(audio_path, language='ar'):
    """تحويل الصوت إلى نص"""
    try:
        model = load_whisper_model()
        
        # استخدام Whisper للتحويل
        result = model.transcribe(
            audio_path,
            language=language if language != 'auto' else None,
            task='transcribe',
            fp16=False  # مهم للخوادم بدون GPU
        )
        
        return result['text']
    except Exception as e:
        raise Exception(f"خطأ في تحويل الصوت: {str(e)}")

@app.route('/')
def index():
    """الصفحة الرئيسية"""
    return app.send_static_file('index.html')

@app.route('/api/health', methods=['GET'])
def health_check():
    """فحص حالة السيرفر"""
    return jsonify({
        'status': 'online',
        'service': 'Video to Text Converter',
        'version': '1.0.0',
        'whisper_model': 'base'
    })

@app.route('/api/transcribe', methods=['POST'])
def transcribe():
    """واجهة API لتحويل الفيديو إلى نص"""
    try:
        data = request.json
        video_url = data.get('videoUrl')
        language = data.get('language', 'ar')
        
        if not video_url:
            return jsonify({'error': 'الرجاء تقديم رابط الفيديو'}), 400
        
        print(f"معالجة الفيديو: {video_url}")
        
        # 1. تحميل الفيديو
        print("جاري تحميل الفيديو...")
        audio_file, video_info = download_audio(video_url)
        print(f"تم التحميل: {audio_file}")
        
        # 2. تحويل الصوت إلى نص
        print("جاري تحويل الصوت إلى نص...")
        transcription = transcribe_audio(audio_file, language)
        print("تم التحويل بنجاح!")
        
        # 3. تنظيف الملف المؤقت
        if os.path.exists(audio_file):
            os.remove(audio_file)
        
        # 4. إرجاع النتيجة
        return jsonify({
            'success': True,
            'title': video_info.get('title', 'فيديو'),
            'duration': video_info.get('duration', 0),
            'transcription': transcription,
            'wordCount': len(transcription.split()),
            'language': language,
            'source': video_url,
            'processed_by': 'Render.com'
        })
        
    except Exception as e:
        print(f"حدث خطأ: {str(e)}")
        return jsonify({
            'error': str(e),
            'note': 'قد يكون الخطأ بسبب: 1- رابط غير صحيح 2- الفيديو طويل جداً 3- مشكلة في السيرفر'
        }), 500

@app.route('/api/demo', methods=['GET'])
def demo_transcription():
    """نص تجريبي للاختبار"""
    return jsonify({
        'success': True,
        'title': 'فيديو تجريبي',
        'duration': 150,
        'transcription': '''هذا نص تجريبي من محول الفيديو إلى نص.

التطبيق يعمل على سيرفر Render.com المجاني ويستخدم:
1. Flask لخدمة الواجهة
2. yt-dlp لتحميل الفيديوهات
3. Whisper AI من OpenAI لتحويل الصوت

للاستخدام الفعلي، أرسل طلب POST إلى /api/transcribe مع رابط الفيديو.''',
        'wordCount': 65,
        'language': 'ar',
        'source': 'https://youtube.com/watch?v=demo'
    })

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=True)
