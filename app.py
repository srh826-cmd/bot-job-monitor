import streamlit as st
import requests
from bs4 import BeautifulSoup
import google.generativeai as genai
import json

# 1. 網頁基本設定
st.set_page_config(page_title="國藝會求才自動化追蹤器", page_icon="🎨", layout="centered")
st.title("🎨 國藝會求才自動化追蹤器")
st.caption("使用 Streamlit + Google AI Studio (Gemini 2.5 Flash) 本週單頁精簡報告測試版")

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
    
    html_snapshot = ""
    
    with st.spinner("🔄 正在巡邏擷取「本週第一頁」精簡資訊進行測試..."):
        try:
            # 💡 精簡優化：只抓 page=0 (第一頁的 12 筆職缺)
            url = "https://www.ncafroc.org.tw/recruitment?page=0&organizationId=&salaryType=&salaryRange=&organizationName=&publishTime=WEEK".strip()
            
            headers = {
                "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            }
            
            response = requests.get(url, headers=headers, timeout=10)
            response.encoding = 'utf-8'
            soup = BeautifulSoup(response.text, 'html.parser')
            
            has_links = False
            
            for a_tag in soup.find_all('a', href=True):
                text = a_tag.get_text(strip=True)
                href = a_tag['href']
                
                if text and ("recruitment" in href or "sid=" in href or "html" in href):
                    has_links = True
                    if href.startswith("/"):
                        full_url = f"https://www.ncafroc.org.tw{href}"
                    elif href.startswith("http"):
                        full_url = href
                    else:
                        full_url = f"https://www.ncafroc.org.tw/{href}"
                        
                    html_snapshot += f"【名稱/內容】: {text} -> 【詳細內頁網址】: {full_url}\n"
            
            if has_links:
                html_snapshot += "\n--- 本週篩選第一頁純文字內容 ---\n"
                html_snapshot += soup.get_text(separator="\n", strip=True)
                
        except Exception as e:
            st.error(f"網頁抓取失敗: {e}")
            return None

    if not html_snapshot.strip():
        return []

    with st.spinner("🧠 Gemini API 正在以最省配額模式分析第一頁職缺..."):
        try:
            genai.configure(api_key=api_key)
            
            model = genai.GenerativeModel(
                model_name="gemini-2.5-flash",
                generation_config={"response_mime_type": "application/json"}
            )
            
            prompt = f"""
            你是一個專業的網頁資料分析專家。以下是國藝會「本週公告」第一頁的求才對照文字。
            請幫我整理出這一頁包含的所有職缺清單（請嚴格忽略重複的職缺，並依日期由新到舊排序）。
            
            【嚴格規範】
            1. 必須輸出符合 JSON Array 的格式，不要包含 ```json 等 Markdown 標籤。
            2. 每個物件必須包含四個欄位：
               - "date": 職缺公告或更新日期 (請根據網頁實際文字填寫，格式如: 2026-07-10)
               - "organization": 求才單位名稱
               - "title": 職缺職稱
               - "link": 請精準填寫該職缺對應的詳細內頁網址。
            
            【本週網頁資料（單頁精簡）】
            {html_snapshot}
            """
            
            response = model.generate_content(prompt)
            jobs_data = json.loads(response.text.strip())
            return jobs_data
        except Exception as e:
            st.error(f"Gemini 分析失敗: {e}")
            return None

# 4. Email 報告文字生成功能 (輕量化)
def generate_email_report(jobs_list):
    if not jobs_list:
        return "本週國藝會無更新職缺，無需發送報告。"
    
    try:
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel(model_name="gemini-2.5-flash")
        
        jobs_summary = ""
        for job in jobs_list:
            jobs_summary += f"- 日期: {job.get('date')} | 單位: {job.get('organization')} | 職稱: {job.get('title')}\n  詳細網址: {job.get('link')}\n\n"
        
        email_prompt = f"""
        請根據以下提供的國藝會職缺清單，撰寫一份專業、格式工整、適合直接複製寄出給主管或團隊的 Email 職缺追蹤報告。
        
        【Email 要求】
        1. 必須包含清晰的「主旨（Subject）」範例（需提及國藝會最新職缺追蹤匯報，並帶有今日日期 2026-07-10）。
        2. 內文開頭需有得體的商務問候語。
        3. 請將職缺資訊用工整的條列式、或純文字表格排版，方便閱讀。每一筆職缺都必須附上其對應的詳細內容網址連結。
        4. 結尾需有專業的簽名檔格式留空。
        5. 不要包含任何網頁代碼或額外的 Markdown 解釋，輸出必須是純文字的 Email 範本。
        
        【職缺資料】
        {jobs_summary}
        """
        
        response = model.generate_content(email_prompt)
        return response.text.strip()
    except Exception as e:
        return f"Email 報告生成失敗: {e}"

# 5. 網頁 UI 互動介面
if st.button("🚀 立即更新本週職缺 (精簡單頁+報告測試)", type="primary"):
    data = fetch_and_analyze()
    
    if data:
        st.success(f"🎉 測試成功！已成功撈回第一頁共 {len(data)} 筆精簡職缺！")
        
        # 顯示網頁卡片 UI
        for index, job in enumerate(data):
            with st.container():
                col1, col2 = st.columns([1, 4])
                with col1:
                    st.info(f"📅 {job.get('date', '未知')}")
                with col2:
                    st.subheader(f"{job.get('organization', '未知')} - {job.get('title', '未知')}")
                    st.markdown(f"[🔗 點此直接進入該職缺詳細內容頁面]({job.get('link')})")
                st.divider()
        
        # 自動生成 Email 報告區塊
        st.subheader("📋 職缺 Email 報告範本 (精簡測試)")
        st.info("💡 提示：點擊右側的「Copy」按鈕即可一鍵複製，直接貼進信箱寄出！")
        
        email_content = generate_email_report(data)
        st.code(email_content, language="text")
        
    else:
        st.info("目前沒有抓到職缺，請確認網頁內容。")
