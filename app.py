import streamlit as st
import google.generativeai as genai
import tempfile
import os
import time

# --- 頁面設定 ---
st.set_page_config(page_title="AI 會議記錄", page_icon="🎙️")
st.title("🎙️ AI 會議記錄產生器")

# --- 1. 讀取 API Key ---
try:
    # 嘗試從 Secrets 讀取
    api_key = st.secrets["GOOGLE_API_KEY"]
except:
    # 如果 Secrets 沒設定，提供一個輸入框讓使用者手動輸入 (方便除錯)
    api_key = st.text_input("未偵測到 Secrets，請在此輸入 API Key:", type="password")

if not api_key:
    st.warning("請先設定 API Key 才能使用。")
    st.stop()

# 設定 Gemini
genai.configure(api_key=api_key)

# --- 2. 診斷模式：列出可用模型 (解決您的疑問) ---
with st.expander("🛠️ 點此查看您的 API 支援哪些模型 (除錯用)"):
    if st.button("檢測可用模型"):
        try:
            st.write("正在向 Google 查詢您的權限...")
            available_models = []
            for m in genai.list_models():
                if 'generateContent' in m.supported_generation_methods:
                    available_models.append(m.name)
            st.success(f"您的 API Key 支援以下模型：\n\n" + "\n".join(available_models))
        except Exception as e:
            st.error(f"查詢失敗，可能是 API Key 有誤或套件版本過舊。\n錯誤訊息: {e}")

# --- 3. 主程式 ---
uploaded_file = st.file_uploader("請上傳錄音檔 (mp3, wav, m4a)", type=["mp3", "wav", "m4a", "aac"])

if uploaded_file:
    st.audio(uploaded_file)
    
    if st.button("🚀 開始生成"):
        status = st.status("AI 正在工作中...", expanded=True)
        
        try:
            # 存暫存檔
            status.write("📥 讀取檔案中...")
            suffix = f".{uploaded_file.name.split('.')[-1]}"
            with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
                tmp.write(uploaded_file.getvalue())
                tmp_path = tmp.name

            # 上傳到 Google
            status.write("☁️ 上傳至 Google 雲端...")
            g_file = genai.upload_file(tmp_path)
            
            while g_file.state.name == "PROCESSING":
                time.sleep(2)
                g_file = genai.get_file(g_file.name)
            
            if g_file.state.name == "FAILED":
                raise ValueError("檔案處理失敗")

            # 生成內容
            status.write("🧠 正在生成報告...")
            
            # --- 關鍵修改：這裡指定模型 ---
            # 我們優先使用 Flash，因為它最快且支援音訊
            # 如果您想換模型，改這個字串即可，例如 "models/gemini-1.5-pro"
            model_name = "gemini-1.5-flash" 
            
            model = genai.GenerativeModel(model_name)
            
            prompt = """
            你是一位專業秘書。請根據錄音生成繁體中文會議記錄：
            1. 基本資訊
            2. 關鍵摘要
            3. 詳細討論事項
            4. 待辦事項
            """
            
            response = model.generate_content([g_file, prompt])
            
            status.update(label="✅ 完成！", state="complete", expanded=False)
            st.markdown(response.text)
            
            # 清理
            genai.delete_file(g_file.name)
            os.unlink(tmp_path)
            
        except Exception as e:
            status.update(label="❌ 發生錯誤", state="error")
            st.error(f"錯誤訊息: {e}")
            st.info("提示：如果出現 404 Model not found，請務必更新 requirements.txt 檔案中的版本號。")