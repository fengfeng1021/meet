import streamlit as st
import google.generativeai as genai
import tempfile
import os
import time

st.set_page_config(page_title="AI 會議記錄", page_icon="🎙️")
st.title("🎙️ AI 會議記錄產生器 (自動偵測版)")

# 1. 讀取 API Key
try:
    api_key = st.secrets["GOOGLE_API_KEY"]
except:
    api_key = st.text_input("請輸入 API Key:", type="password")

if not api_key:
    st.warning("請先設定 API Key。")
    st.stop()

genai.configure(api_key=api_key)

# 2. 【關鍵步驟】自動偵測可用模型
# 這樣我們就不用猜名字了，直接問 Google 系統有哪些模型可用
try:
    available_models = []
    for m in genai.list_models():
        if 'generateContent' in m.supported_generation_methods:
            available_models.append(m.name)
    
    # 簡單的邏輯：優先找 1.5 Flash，沒有就找 1.5 Pro
    # 這裡會自動過濾出真正存在的模型名稱
    target_model = None
    
    # 優先順序清單
    priority_list = ["models/gemini-1.5-flash", "models/gemini-1.5-flash-001", "models/gemini-1.5-flash-latest", "models/gemini-1.5-pro"]
    
    # 1. 先從優先清單找
    for p in priority_list:
        if p in available_models:
            target_model = p
            break
            
    # 2. 如果都沒找到，就用系統回傳的第一個模型
    if not target_model and available_models:
        target_model = available_models[0]
        
    if not target_model:
        st.error("❌ 找不到任何可用模型！可能是 API Key 權限問題或套件過舊。")
        st.write("系統偵測到的清單: ", available_models)
        st.stop()
        
    st.success(f"✅ 自動鎖定模型: `{target_model}`")

except Exception as e:
    st.error(f"偵測模型時發生錯誤: {e}")
    st.info("提示：如果這裡報錯，請確認 requirements.txt 內是否有寫 'google-generativeai>=0.7.2'")
    st.stop()


# 3. 主程式介面
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

            # 上傳
            status.write("☁️ 上傳至 Google 雲端...")
            g_file = genai.upload_file(tmp_path)
            
            while g_file.state.name == "PROCESSING":
                time.sleep(2)
                g_file = genai.get_file(g_file.name)
            
            if g_file.state.name == "FAILED":
                raise ValueError("檔案處理失敗")

            # 生成
            status.write(f"🧠 使用模型 {target_model} 生成報告...")
            
            # 使用剛剛自動偵測到的模型名稱
            model = genai.GenerativeModel(target_model)
            
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
            try:
                genai.delete_file(g_file.name)
                os.unlink(tmp_path)
            except:
                pass
            
        except Exception as e:
            status.update(label="❌ 發生錯誤", state="error")
            st.error(f"錯誤訊息: {e}")