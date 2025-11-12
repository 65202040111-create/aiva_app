import os
import io
from flask import Flask, render_template, jsonify, request, send_file
from gtts import gTTS
import time

# --- Mock TTS (สำหรับ Web App) ---
# เราต้องมีตัวแปร .is_speaking ให้ /tts_status ตรวจสอบ
class MockTTS:
    def __init__(self, lang='th'):
        self.is_speaking = False
        self.lang = lang
        print("MockTTS (Web App): Initialized.")

    def generate_speech_audio(self, text):
        """
        สร้างเสียงพูด (gTTS) แต่ส่งกลับเป็น_ข้อมูล_ MP3 (bytes)
        แทนการ_เล่น_เสียงบนเซิร์ฟเวอร์
        """
        self.is_speaking = True
        print(f"MockTTS: Generating audio for '{text}'...")
        try:
            # สร้างไฟล์ MP3 ใน RAM
            tts = gTTS(text=text, lang=self.lang, slow=False)
            mp3_fp = io.BytesIO()
            tts.write_to_fp(mp3_fp)
            mp3_fp.seek(0) # ย้อนกลับไปที่จุดเริ่มต้นของไฟล์
            print("MockTTS: Audio generated.")
            return mp3_fp
        except Exception as e:
            print(f"MockTTS Error: {e}")
            return None
        finally:
            # ⭐️ สำคัญ: เราจะตั้ง is_speaking = False
            # หลังจากที่ไฟล์ถูกส่งไปแล้ว (ใน Flask route)
            # แต่ใน Mock เราจำลองว่ามันเสร็จทันที
            # ใน App จริง, gTTS จะทำงานเร็วกว่าการเล่น
            self.is_speaking = False 

# --- AI Engine (Mock vs Real) ---
try:
    # ⭐️⭐️⭐️ นี่คือส่วนที่สำคัญที่สุด ⭐️⭐️⭐️
    # Render.com จะหาไฟล์นี้เจอ ก็ต่อเมื่อคุณ Push "pdf_ai_engine.py" ขึ้น GitHub
    from pdf_ai_engine import PdfAIEngine
    
    # ดึง API Key จาก Environment Variable ที่เราตั้งใน Render.com
    API_KEY = os.environ.get("GEMINI_API_KEY") 
    PDF_FOLDER_PATH = "data_files" # Render จะดาวน์โหลดโฟลเดอร์นี้มาด้วย
    
    if not API_KEY:
        print("Warning: 'GEMINI_API_KEY' not found in Environment Variables.")
        raise ImportError("Missing API Key")

    if not os.path.exists(PDF_FOLDER_PATH):
        print(f"Warning: PDF folder '{PDF_FOLDER_PATH}' not found. Have you pushed it to GitHub?")
        # แม้จะหาไม่เจอ ก็ยังใช้ AI ได้ แต่อาจจะไม่มีข้อมูล
        
    ai = PdfAIEngine(pdf_folder_path=PDF_FOLDER_PATH, api_key=API_KEY)
    print("✅ Success: Loaded REAL PdfAIEngine.")

except ImportError:
    print("-------------------------------------------------------------------")
    print("⚠️ WARNING: 'pdf_ai_engine.py' not found or API Key missing.")
    print("✅ SOLUTION: Push 'pdf_ai_engine.py' and 'data_files/' to GitHub.")
    print("Switching to MOCK AI ENGINE (ตัวปลอม).")
    print("-------------------------------------------------------------------")
    
    # --- Mock PdfAIEngine (ตัวปลอมสำหรับ Deploy) ---
    class PdfAIEngine:
        def __init__(self, pdf_folder_path, api_key): 
            pass
        def find_answer(self, text):
            print(f"MockPdfAIEngine: Finding answer for '{text}'")
            time.sleep(1) # จำลองการค้นหา
            return f"นี่คือคำตอบจำลองสำหรับ '{text}' (AI จริงยังไม่ได้เชื่อมต่อ)"
    ai = PdfAIEngine(None, None)
    # -------------------------------------------------

# --- Flask App Setup ---
app = Flask(__name__, static_folder='static', template_folder='templates')
tts_service = MockTTS(lang='th') # ใช้ Mock TTS (เวอร์ชัน Web App)

@app.route("/")
def index():
    # ⭐️ เปลี่ยนไปใช้ Template ตัวใหม่ของคุณ
    return render_template("aiva_web_portal.html") 

def get_answer_and_audio(text):
    """
    ฟังก์ชันช่วย: ค้นหาคำตอบและสร้างไฟล์เสียง MP3
    """
    try:
        # 1. ค้นหาคำตอบ (จาก AI จริง หรือ Mock)
        answer = ai.find_answer(text)
        
        # 2. สร้างเสียงพูด (จาก gTTS)
        # เราจะไม่ใช้ MockTTS.generate_speech_audio ที่นี่
        # เพราะเราต้องการให้ gTTS ทำงานจริง
        
        print(f"gTTS: Generating audio for '{answer}'...")
        tts_service.is_speaking = True # ⭐️ บอกว่ากำลังจะเริ่มพูด
        tts = gTTS(text=answer, lang='th', slow=False)
        mp3_fp = io.BytesIO()
        tts.write_to_fp(mp3_fp)
        mp3_fp.seek(0)
        print("gTTS: Audio generated.")
        
        return answer, mp3_fp
        
    except Exception as e:
        print(f"Error in get_answer_and_audio: {e}")
        return "เกิดข้อผิดพลาด", None
    finally:
        # ⭐️ สำคัญ: ตั้งค่า is_speaking = False
        # เราย้ายไปตั้งใน @app.route("/.../callback")
        # เพื่อให้แน่ใจว่ามันถูกตั้งหลังจากไฟล์ถูกส่งไปแล้ว
        pass 

@app.route("/listen", methods=["POST"])
def listen():
    """
    รับ Text จาก Web Speech API (ไม่ใช่เสียง)
    ค้นหาคำตอบ, สร้าง MP3, และส่งไฟล์ MP3 กลับไป
    """
    try:
        data = request.json
        text = data.get("text")
        if not text:
            return jsonify({"ok": False, "answer": "ไม่ได้ยินคำถาม"}), 400

        print(f"Received text from client: {text}")
        answer, audio_file = get_answer_and_audio(text)

        if audio_file:
            return send_file(
                audio_file, 
                mimetype="audio/mpeg",
                as_attachment=False,
                # ⭐️ ส่งคำตอบ (Text) กลับไปใน Header
                headers={
                    "X-Answer-Text": answer,
                    "X-Question-Text": text
                }
            )
        else:
             return jsonify({"ok": False, "answer": "สร้างเสียงไม่สำเร็จ"}), 500

    except Exception as e:
        print(f"Error in /listen: {e}")
        return jsonify({"ok": False, "answer": "เกิดข้อผิดพลาดในเซิร์ฟเวอร์"}), 500

@app.route("/speak_answer", methods=["POST"])
def speak_answer():
    """
    รับคำถาม (ปุ่ม) ค้นหาคำตอบ, สร้าง MP3, และส่งไฟล์ MP3 กลับไป
    """
    try:
        data = request.json
        question = data.get("question")
        if not question:
            return jsonify({"ok": False, "answer": "ไม่ได้ส่งคำถามมา"}), 400

        print(f"Received button press: {question}")
        answer, audio_file = get_answer_and_audio(question)

        if audio_file:
            return send_file(
                audio_file, 
                mimetype="audio/mpeg",
                as_attachment=False,
                headers={
                    "X-Answer-Text": answer,
                    "X-Question-Text": question
                }
            )
        else:
             return jsonify({"ok": False, "answer": "สร้างเสียงไม่สำเร็จ"}), 500

    except Exception as e:
        print(f"Error in /speak_answer: {e}")
        return jsonify({"ok": False, "answer": "เกิดข้อผิดพลาดในเซิร์ฟเวอร์"}), 500

@app.route("/tts_finished_callback", methods=["POST"])
def tts_finished_callback():

    tts_service.is_speaking = False
    # print("Callback received: TTS is no longer speaking.")
    return jsonify({"ok": True})

@app.route("/stop_tts", methods=["POST"])
def stop_tts():

    print("Stop command received from client.")
    tts_service.is_speaking = False 
    return jsonify({"ok": True, "status": "TTS status reset."})

@app.route("/tts_status")
def tts_status():

    return jsonify({"is_speaking": tts_service.is_speaking})


if __name__ == "__main__":

    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=True)