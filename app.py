import streamlit as st
import requests
from bs4 import BeautifulSoup
import google.generativeai as genai
import json

# 1. 網頁基本設定
st.set_page_config(page_title="國藝會求才自動化追蹤器", page_icon="🎨", layout="centered")
st.title("🎨 國藝會求才自動化追蹤器")
st.caption("使用 Streamlit + Google AI Studio (Gemini 2.5 Flash) 精準連結優化版")

# 2. 安全取得 Gemini API Key (相容本地與雲端)
if "GEMINI_API_KEY" in st.secrets:
    api_key = st.secrets["GEMINI_API_KEY"]
else:
    api_key = st.sidebar.text_input("請輸入 Gemini API Key", type="password")

# 3. 核心抓取與精準連結分析功能
def fetch_and_analyze():
    if not api_key:
        st.warning("⚠️ 請先在 Streamlit Secrets 設定或在左側輸入 Gemini API Key！")
        return None
    
    formatted_job_list = ""
    
    with st.spinner("🔄 正在巡邏擷取國藝會前 2 頁求才清單與詳細連結..."):
        try:
            for page in range(1, 3):
                if page == 1:
                    url = "https://www.ncafroc.org.tw/recruitment.html"
                else:
                    url = f"https://www.ncafroc.org.tw/recruitment.html?page={page}"
                
                response = requests.get(url, timeout=10)
                response.encoding = 'utf-8'
                soup = BeautifulSoup(response.text, 'html.parser')
                
                # 國藝會職缺表格通常在 table 裡，我們精準抓取每一筆職缺的區塊
                # 這裡透過傳統過濾，把職缺名稱、求才單位與對應的絕對網址先綁定好
                job_items = soup.find_all('tr') # 抓取表格的每一列
                
                for item in job_items:
                    # 尋找內含的連結
                    link_tag = item.find('a')
                    if link_tag and 'recruitment-content.html' in link_tag.get('href', ''):
                        title = link_tag.get_text(strip=True)
                        relative_url = link_tag.get('href')
                        # 拼湊成絕對網址
                        full_url = f"https://www.ncafroc.org.tw/{relative_url}"
                        
                        # 抓取同列中的時間、單位或薪資等文字來輔助
                        row_text = item.get_text(separator=" | ", strip=True)
                        
                        # 把這一筆結構化的資訊塞進字串，準備給 Gemini 做日期與語意篩選
                        formatted_job_list += f"職缺摘要資訊: {row_text}  --> 詳細內容網址: {full_url}\n"
                        
        except Exception as e:
            st.error(f"網頁抓取或連結解析失敗: {e}")
            return None

    if not formatted_job_list:
        st.info("網頁表格解析未抓到資料，請確認網頁架構。")
        return None

    with st.spinner("🧠 Gemini API 正在篩選今日最新職缺..."):
        try:
            genai.configure(api_key=api_key)
            model = genai.GenerativeModel(model_name="gemini-1.5-flash-latest")
            
            prompt = f"""
            你是一個專業的資料萃取專家。以下是已經預先處理過、包含詳細連結網址的國藝會求才清單文字。
            請仔細閱讀，並從中過濾篩選出「最新公告」或「今日公告」的職缺清單（請忽略重複的職缺）。
            
            【嚴格規範】
            1. 必須以純 JSON Array 格式輸出，不要包含 ```json 等 Markdown 標籤。
            2. 每個物件必須包含四個欄位：
               - "date": 職缺公告或更新日期 (格式如: 2026-07-10)
               - "organization": 求才單位名稱
               - "title": 職缺職稱
               - "link": 必須精準填寫該職缺對應的「詳細內容網址」（即文字中 --> 後面的完整網址）
            
            【帶連結的預處理清單內容】
            {formatted_job_list}
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
        st.success(f"🎉 成功找到 {len(data)} 筆近期職缺！（已完美綁定內頁詳細連結）")
        
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
