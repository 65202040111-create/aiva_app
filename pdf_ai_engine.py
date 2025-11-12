import pdfplumber
import google.generativeai as genai
import os
import glob 
from google.generativeai.types import HarmCategory, HarmBlockThreshold

class PdfAIEngine:
    
    def __init__(self, pdf_folder_path: str, api_key: str):
        """
        เริ่มต้น Engine โดยการอ่าน PDF ทั้งหมดในโฟลเดอร์ และตั้งค่า Gemini API
        """
        self.pdf_text = ""
        
        if not os.path.isdir(pdf_folder_path):
            print(f"!!! FATAL ERROR: ไม่พบโฟลเดอร์ PDF ที่: {pdf_folder_path}")
            print("!!! Kiosk จะไม่สามารถตอบคำถามได้")
            self.pdf_text = "เกิดข้อผิดพลาด: ไม่พบโฟลเดอร์ข้อมูล"
        else:
            print(f"กำลังโหลด PDF ทั้งหมดจากโฟลเดอร์ {pdf_folder_path}...")
            self.pdf_text = self._extract_text_from_folder(pdf_folder_path) 
            print(f"ดึงข้อความจาก PDF สำเร็จ รวม {len(self.pdf_text)} ตัวอักษร")
        
        if not api_key:
            print("!!! FATAL ERROR: ไม่ได้ตั้งค่า GEMINI_API_KEY")
        
        try:
            genai.configure(api_key=api_key)
            
            # ตั้งค่าความปลอดภัย
            safety_settings = {
                HarmCategory.HARM_CATEGORY_HATE_SPEECH: HarmBlockThreshold.BLOCK_NONE,
                HarmCategory.HARM_CATEGORY_HARASSMENT: HarmBlockThreshold.BLOCK_NONE,
                HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: HarmBlockThreshold.BLOCK_NONE,
                HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_NONE,
            }

            self.model = genai.GenerativeModel(
                model_name="gemini-2.5-flash-preview-09-2025",
                safety_settings=safety_settings
            )
            
            # ⭐️⭐️⭐️ แก้ไข: ลบกฎที่จำกัดการใช้ความรู้ภายนอก ⭐️⭐️⭐️
            self.system_prompt = f"""
            คุณคือผู้ช่วย AI ของ Kiosk วิทยาลัยเทคนิค
            หน้าที่ของคุณคือตอบคำถาม

            กฎสำคัญ:
            1. ตอบเป็นภาษาไทย
            2. ให้พยายามค้นหาคำตอบจาก "ข้อความในเอกสาร" เป็นลำดับแรก (หากตอบได้)
            3. ⭐️ หากคำตอบไม่มีในเอกสาร ให้ใช้ความรู้ทั่วไปของคุณในการตอบคำถามนั้นๆ ⭐️
            4. ตอบให้กระชับ ชัดเจน และเป็นมิตร
            5. สำคัญมาก: ตอบกลับเป็นข้อความธรรมดาเท่านั้น ห้ามใช้รูปแบบ Markdown, JSON, สัญลักษณ์รายการ เช่น *, -, หรือเครื่องหมาย Backtick (```) ในคำตอบเด็ดขาด

            --- ข้อความในเอกสาร (ใช้เป็นข้อมูลอ้างอิงหลัก) ---
            {self.pdf_text}
            --- สิ้นสุดข้อความในเอกสาร ---
            """
            
            self.convo = self.model.start_chat(history=[
                {'role': 'user', 'parts': [self.system_prompt]},
                {'role': 'model', 'parts': ["ค่ะ ฉันพร้อมแล้วที่จะตอบคำถามของคุณ"]}
            ])
            print("PdfAIEngine เริ่มทำงานและเชื่อมต่อ Gemini API สำเร็จ (อนุญาตให้ใช้ความรู้ทั่วไป)")

        except Exception as e:
            print(f"เกิดปัญหาขณะตั้งค่า Gemini API: {e}")
            self.model = None

    def _extract_text_from_folder(self, folder_path: str) -> str:
        """
        ฟังก์ชันสำหรับดึงข้อความ (Text) ออกจากไฟล์ PDF ทั้งหมดในโฟลเดอร์ที่กำหนด
        """
        text = ""
        pdf_files = glob.glob(os.path.join(folder_path, '*.pdf'))
        
        if not pdf_files:
            print(f"คำเตือน: ไม่พบไฟล์ PDF ในโฟลเดอร์: {folder_path}")
            return "ไม่พบข้อมูลจากไฟล์ PDF ใดๆ"

        for pdf_path in pdf_files:
            try:
                with pdfplumber.open(pdf_path) as pdf:
                    text += f"\n\n--- CONTENT FROM FILE: {os.path.basename(pdf_path)} ---\n\n"
                    for page in pdf.pages:
                        page_text = page.extract_text()
                        if page_text:
                            text += page_text + "\n"
            except Exception as e:
                print(f"เกิดปัญหาในการอ่าน PDF ({os.path.basename(pdf_path)}): {e}")
                continue
                
        return text
    
    def find_answer(self, text: str) -> str:
        """
        ค้นหาคำตอบสำหรับคำถาม (text) โดยใช้ Gemini
        """
        if not self.model:
            return "ขออภัยค่ะ ระบบ AI กำลังมีปัญหา"
            
        print(f"PdfAIEngine: ค้นหาคำตอบสำหรับ '{text}'...")
        
        try:
            self.convo.send_message(text)
            answer = self.convo.last.text
            print(f"Gemini raw response: {answer}")
            
            # การล้างคำตอบ (Cleaning) ที่เราแก้ไขไปก่อนหน้านี้ (ยังคงรักษาไว้)
            cleaned_answer = answer.lstrip('*-# ') 
            cleaned_answer = cleaned_answer.strip('"\'' ) 
            cleaned_answer = cleaned_answer.strip('`' ) 

            print(f"Cleaned answer for TTS: {cleaned_answer}")
            return cleaned_answer

        except Exception as e:
            print(f"เกิดปัญหาในการเรียก Gemini API: {e}")
            return "ขออภัยค่ะ เกิดข้อผิดพลาดในการเชื่อมต่อกับ AI"