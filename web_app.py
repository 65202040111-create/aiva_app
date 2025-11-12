import os 
from flask import Flask, render_template, jsonify, request, send_file
import threading
from concurrent.futures import ThreadPoolExecutor
import time
import io # ⭐️ สำคัญ: สำหรับสร้างไฟล์ใน RAM

# --- TTS Engine (ย้าย gTTS มาที่นี่) ---
try:
    from gtts import gTTS
    print("Success: Loaded gTTS.")
except ImportError:
    print("Error: gTTS module not found. Please run 'pip install gTTS'")
    # สร้าง Mock gTTS เพื่อให้โค้ดส่วนอื่นทำงานได้ (แต่จะไม่มีเสียง)
    class gTTS:
        def __init__(self, text, lang, slow): pass
        def write_to_fp(self, fp):
            print(f"MockgTTS: Pretending to write '{text}' to RAM")
            pass

# --- Mock HumanDetector (ไม่ถูกใช้งานในโมเดลนี้) ---
# ... (ส่วนนี้ไม่ถูกเรียกใช้ใน Web App) ...

# --- Mock PdfAIEngine (ยังใช้เหมือนเดิม) ---
try:
    from pdf_ai_engine import PdfAIEngine
except ImportError:
    print("Warning: 'pdf_ai_engine' module not found. Using Mock PdfAIEngine.")
    class PdfAIEngine:
        def __init__(self, pdf_folder_path, api_key): 
            print("MockPdfAIEngine: Initialized.")
            if not api_key:
                print("MockPdfAIEngine: Warning! API Key is missing.")
            if not os.path.exists(pdf_folder_path):
                print(f"MockPdfAIEngine: Warning! PDF folder not found at {pdf_folder_path}")
            
        def find_answer(self, text):
            print(f"MockPdfAIEngine: Finding answer for '{text}'")
            time.sleep(1) # จำลองการค้นหา
            return f"นี่คือคำตอบจำลองสำหรับ '{text}' จาก PDF ที่เรามีข้อมูลทั้งหมด"

# --- Flask App Setup ---

app = Flask(__name__, static_folder='static', template_folder='templates')

# ⭐️ ตั้งค่าสำหรับ Engine ⭐️
API_KEY = "AIzaSyCt0ggPjQq117AVDtL18t7gXYVB8cni7PE" # 📌 เปลี่ยนเป็น API Key จริงของคุณ
PDF_FOLDER_PATH = "data_files" 

# ⭐️ สร้างโฟลเดอร์ถ้ายังไม่มี ⭐️
if not os.path.exists(PDF_FOLDER_PATH):
    os.makedirs(PDF_FOLDER_PATH)
    print(f"สร้างโฟลเดอร์ {PDF_FOLDER_PATH} แล้ว กรุณานำไฟล์ PDF ทั้งหมดมาใส่ในโฟลเดอร์นี้")

# Instantiate modules
print("Starting AI Engine...")
ai = PdfAIEngine(pdf_folder_path=PDF_FOLDER_PATH, api_key=API_KEY)
# (เราไม่สร้าง STT/TTS instance ที่นี่)

# --- Helper Function for TTS Generation ---

def generate_tts_audio(text):
    """
    สร้างไฟล์เสียง MP3 จากข้อความ และเก็บไว้ใน RAM (BytesIO)
    """
    try:
        print(f"TTS Gen: Generating audio for: {text[:30]}...")
        audio_fp = io.BytesIO()
        tts = gTTS(text=text, lang='th', slow=False)
        tts.write_to_fp(audio_fp)
        audio_fp.seek(0) # ย้าย cursor กลับไปที่จุดเริ่มต้นของไฟล์
        print("TTS Gen: Audio generated in RAM.")
        return audio_fp
    except Exception as e:
        print(f"Error generating TTS audio: {e}")
        return None

# --- Web App Endpoints ---

@app.route("/")
def index():
    # ⭐️ เราจะ render template ใหม่
    return render_template("aiva_web_portal.html")

@app.route("/get_answer_audio", methods=["POST"])
def get_answer_audio():
    """
    Endpoint หลัก: รับ Text -> ค้นหาคำตอบ -> สร้าง MP3 -> ส่ง MP3 กลับไป
    """
    try:
        data = request.json
        text = data.get("question")

        if not text:
            return jsonify({"error": "ไม่ได้ส่งคำถามมา"}), 400
        
        # 1. ค้นหาคำตอบ (ยังเหมือนเดิม)
        answer_text = ai.find_answer(text)
        
        # 2. สร้างไฟล์เสียง MP3 ใน RAM
        audio_file_in_ram = generate_tts_audio(answer_text)
        
        if audio_file_in_ram is None:
            return jsonify({"error": "ไม่สามารถสร้างไฟล์เสียงได้"}), 500
            
        # 3. ส่งไฟล์เสียงกลับไปที่ Client
        print("Sending MP3 file to client...")
        return send_file(
            audio_file_in_ram,
            mimetype='audio/mpeg',
            as_attachment=False, #
            download_name='answer.mp3' # ชื่อไฟล์ (เผื่อ user อยาก save)
        )

    except Exception as e:
        print(f"Error in /get_answer_audio: {e}")
        return jsonify({"error": str(e)}), 500

# (Endpoint อื่นๆ เช่น /listen, /speak_answer, /stop_tts, /tts_status ไม่จำเป็นแล้ว
# เพราะ Client (JS) เป็นคนจัดการการฟัง และการเล่นเสียงเองทั้งหมด)

if __name__ == "__main__":
    print("Flask Web App (Option 2) running...")
    # ⭐️ หมายเหตุ: debug=False สำคัญมากเมื่อรันจริง
    app.run(host="0.0.0.0", port=5000, debug=False)