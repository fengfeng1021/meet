import streamlit as st
import google.generativeai as genai
import tempfile
import os
import time

# --- 頁面設定 ---
st.set_page_config(page_title="AI 會議記錄", page_icon="🎙️")
st.title("🎙️ AI 會議記錄產生器")

# --- 關鍵修改：從 Secrets 讀取 Key，而不是直接寫死 ---
# 這裡會去抓 Streamlit 後台設定好的密碼
try:
    api_key = st.secrets["GOOGLE_API_KEY"]
except:
    st.error("找不到 API Key！請在 Streamlit Cloud 後台的 Secrets 欄位設定 GOOGLE_API_KEY。")
    st.stop()

# 設定 Gemini
genai.configure(api_key=api_key)

# 上傳檔案介面
uploaded_file = st.file_uploader("請上傳錄音檔 (mp3, wav, m4a)", type=["mp3", "wav", "m4a", "aac"])

if uploaded_file:
    st.audio(uploaded_file)
    
    if st.button("開始生成會議記錄"):
        status = st.status("AI 正在工作中...", expanded=True)
        
        try:
            # 1. 為了上傳給 Google，先存成暫存檔
            status.write("📥 讀取檔案中...")
            suffix = f".{uploaded_file.name.split('.')[-1]}"
            
            with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
                tmp.write(uploaded_file.getvalue())
                tmp_path = tmp.name

            # 2. 上傳到 Gemini
            status.write("☁️ 上傳至 Google 雲端處理...")
            g_file = genai.upload_file(tmp_path)
            
            # 等待處理完成
            while g_file.state.name == "PROCESSING":
                time.sleep(2)
                g_file = genai.get_file(g_file.name)
            
            if g_file.state.name == "FAILED":
                raise ValueError("檔案處理失敗，請確認音訊格式")

            # 3. 呼叫 AI 生成
            status.write("🧠 正在聆聽並撰寫報告...")
            model = genai.GenerativeModel("gemini-1.5-flash")
            
            prompt = """
            你是一位專業秘書。請根據錄音生成繁體中文會議記錄，包含：
            1. 基本資訊 (主題/日期/參與人)
            2. 關鍵摘要 (Executive Summary)
            3. 詳細討論事項 (條列式)
            4. 待辦事項 (Action Items 表格)
            """
            
            response = model.generate_content([g_file, prompt])
            
            status.update(label="✅ 完成！", state="complete", expanded=False)
            
            # 顯示結果
            st.divider()
            st.markdown(response.text)
            
            # 清理暫存檔
            try:
                genai.delete_file(g_file.name)
                os.unlink(tmp_path)
            except:
                pass
            
        except Exception as e:
            status.update(label="❌ 發生錯誤", state="error")
            st.error(f"錯誤訊息: {e}")