import streamlit as st
import requests
from bs4 import BeautifulSoup
import google.generativeai as genai
import json

# 1. 網頁基本設定
st.set_page_config(page_title="國藝會求才自動化追蹤器", page_icon="🎨", layout="centered")
st.title("🎨 國藝會求才自動化追蹤器")
st.caption("使用 Streamlit + Google AI Studio (Gemini 2.0 Flash) 自動語意萃取")

# 2. 安全取得 Gemini API Key (相容本地與雲端)
if "GEMINI_API_KEY" in st.secrets:
    api_key = st.secrets["GEMINI_API_KEY"]
else:
    api_key = st.sidebar.text_input("請輸入 Gemini API Key", type="password")

# 3. 核心抓取與分析功能
def fetch_and_analyze():
    if not api_key:
        st.warning("⚠️ 請先在 Streamlit Secrets 設定或在左側輸入 Gemini API Key！")
        return None
    
    url = "https://www.ncafroc.org.tw/recruitment.html"
    
    with st.spinner("🔄 正在擷取國藝會最新網頁文字..."):
        try:
            response = requests.get(url, timeout=10)
            response.encoding = 'utf-8'
            soup = BeautifulSoup(response.text, 'html.parser')
            page_text = soup.get_text(separator="\n", strip=True)
        except Exception as e:
            st.error(f"網頁抓取失敗: {e}")
            return None

    with st.spinner("🧠 Gemini API 正在進行語意分析與結構化萃取..."):
        try:
            # 這是 google-generativeai 套件的標準設定與呼叫方式
            genai.configure(api_key=api_key)
            model = genai.GenerativeModel(model_name="gemini-2.0-flash")
            
            prompt = f"""
            你是一個專業的資料萃取專家。以下是中華民國國家文化藝術基金會（國藝會）求才公告網頁的純文字內容。
            請仔細閱讀，並從中萃取出「最新公告」或「今日公告」的職缺清單。
            
            【嚴格規範】
            1. 必須以純 JSON Array 格式輸出，不要包含 ```json 等 Markdown 標籤。
            2. 每個物件必須包含四個欄位：
               - "date": 職缺公告或更新日期 (格式如: 2026-07-10)
               - "organization": 求才單位名稱
               - "title": 職缺職稱
               - "link": 該職缺的詳細網址 (如果從文字中無法精確取得，請填寫: [https://www.ncafroc.org.tw/recruitment.html](https://www.ncafroc.org.tw/recruitment.html))
            
            【網頁純文字內容】
            {page_text}
            """
            
            response = model.generate_content(prompt)
            clean_text = response.text.strip()
            
            # 預防性清除可能殘留的 markdown 標記
            if clean_text.startswith("```"):
                clean_text = clean_text.split("\n", 1)[1]
            if clean_text.endswith("```"):
                clean_text = clean_text.rsplit("\n", 1)[0]
                
            jobs_data = json.loads(clean_text.strip())
            return jobs_data
        except Exception as e:
            st.error(f"Gemini 分析失敗: {e}")
            if 'response' in locals():
                st.code(response.text) # 印出錯誤時的原始文字方便除錯
            return None

# 4. 網頁 UI 互動介面
if st.button("🚀 立即更新今日職缺", type="primary"):
    data = fetch_and_analyze()
    
    if data:
        st.success(f"🎉 成功找到 {len(data)} 筆近期職缺！")
        
        for index, job in enumerate(data):
            with st.container():
                col1, col2 = st.columns([1, 4])
                with col1:
                    st.info(f"📅 {job.get('date', '未知')}")
                with col2:
                    st.subheader(f"{job.get('organization', '未知')} - {job.get('title', '未知')}")
                    st.markdown(f"[🔗 點此查看詳細求才公告]({job.get('link')})")
                st.divider()
    else:
        st.info("目前沒有抓到職缺，請確認網頁內容或 API Key 是否正確。")
