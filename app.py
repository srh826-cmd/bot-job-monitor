import streamlit as st
import requests
from bs4 import BeautifulSoup
import google.generativeai as genai
import json

# 1. 網頁基本設定
st.set_page_config(page_title="國藝會求才自動化追蹤器", page_icon="🎨", layout="centered")
st.title("🎨 國藝會求才自動化追蹤器")
st.caption("使用 Streamlit + Google AI Studio (Gemini 2.5 Flash) 精準內頁連結版")

# 2. 安全取得 Gemini API Key (相容本地與雲端)
if "GEMINI_API_KEY" in st.secrets:
    api_key = st.secrets["GEMINI_API_KEY"]
else:
    api_key = st.sidebar.text_input("請輸入 Gemini API Key", type="password")

# 3. 核心抓取與多頁分析功能
def fetch_and_analyze():
    if not api_key:
        st.warning("⚠️ 請先在 Streamlit Secrets 設定或在左側輸入 Gemini API Key！")
        return None
    
    html_snapshot = ""
    
    with st.spinner("🔄 正在巡邏擷取國藝會前 2 頁原始資訊..."):
        try:
            for page in range(1, 3):
                if page == 1:
                    url = "https://www.ncafroc.org.tw/recruitment.html"
                else:
                    url = f"https://www.ncafroc.org.tw/recruitment.html?page={page}"
                
                response = requests.get(url, timeout=10)
                response.encoding = 'utf-8'
                soup = BeautifulSoup(response.text, 'html.parser')
                
                html_snapshot += f"\n--- 第 {page} 頁內容開始 ---\n"
                
                # 這次我們非常聰明，把網頁裡所有的超連結與其文字全部抓出來排好
                # 這樣 Gemini 就能完全看懂哪個職缺名字對應哪個網址
                for a_tag in soup.find_all('a', href=True):
                    text = a_tag.get_text(strip=True)
                    href = a_tag['href']
                    
                    # 只要過濾掉那些無關的聯絡我們、首頁等連結，留下可能跟職缺有關的
                    if text and ("recruitment" in href or "sid=" in href or "html" in href):
                        # 如果是相對網址，自動幫它補上國藝會的前綴
                        if href.startswith("/"):
                            full_url = f"https://www.ncafroc.org.tw{href}"
                        elif href.startswith("http"):
                            full_url = href
                        else:
                            full_url = f"https://www.ncafroc.org.tw/{href}"
                            
                        html_snapshot += f"【名稱/內容】: {text} -> 【詳細內頁網址】: {full_url}\n"
                
                # 順便把整頁的其他純文字也塞進去，輔助 Gemini 看日期與薪資
                html_snapshot += soup.get_text(separator="\n", strip=True)
                html_snapshot += f"\n--- 第 {page} 頁內容結束 ---\n"
                
        except Exception as e:
            st.error(f"網頁抓取失敗: {e}")
            return None

    with st.spinner("🧠 Gemini API 正在翻閱前兩頁並精準對齊職缺內頁網址..."):
        try:
            genai.configure(api_key=api_key)
            model = genai.GenerativeModel(model_name="gemini-2.5-flash")
            
            prompt = f"""
            你是一個專業的網頁資料分析專家。以下是中華民國國家文化藝術基金會（國藝會）求才公告網頁（前兩頁）的對照文字。
            請幫我找出「最新公告」或「今日公告」的所有職缺清單（請忽略重複的職缺）。
            
            【嚴格規範】
            1. 必須以純 JSON Array 格式輸出，不要包含 ```json 等 Markdown 標籤。
            2. 每個物件必須包含四個欄位：
               - "date": 職缺公告或更新日期 (格式如: 2026-07-10)
               - "organization": 求才單位名稱
               - "title": 職缺職稱
               - "link": 請根據文字中的對照關係，找出該職缺對應的精準詳細內容網址（例如含有 recruitment_detail.html 或包含特定識別碼的網址）。如果真的找不到該職缺的獨立內頁網址，才允許填寫: [https://www.ncafroc.org.tw/recruitment.html](https://www.ncafroc.org.tw/recruitment.html)。
            
            【網頁內容與連結對照資料】
            {html_snapshot}
            """
            
            response = model.generate_content(prompt)
            clean_text = response.text.strip()
            
            if clean_text.startswith("```"):
                clean_text = clean_text.split("\n", 1)[1]
            if clean_text.endswith("```"):
                clean_text = clean_text.rsplit("\n", 1)[0]
                
            jobs_data = json.loads(clean_text.strip())
            return jobs_data
        except Exception as e:
            st.error(f"Gemini 分析失敗: {e}")
            if 'response' in locals():
                st.code(response.text)
            return None

# 4. 網頁 UI 互動介面
if st.button("🚀 立即更新今日職缺", type="primary"):
    data = fetch_and_analyze()
    
    if data:
        st.success(f"🎉 成功找到 {len(data)} 筆近期職缺！（已涵蓋前兩頁且自動追蹤詳細內頁）")
        
        for index, job in enumerate(data):
            with st.container():
                col1, col2 = st.columns([1, 4])
                with col1:
                    st.info(f"📅 {job.get('date', '未知')}")
                with col2:
                    st.subheader(f"{job.get('organization', '未知')} - {job.get('title', '未知')}")
                    st.markdown(f"[🔗 點此直接進入該職缺詳細內容頁面]({job.get('link')})")
                st.divider()
    else:
        st.info("目前沒有抓到職缺，請確認網頁內容或 API Key 是否正確。")
