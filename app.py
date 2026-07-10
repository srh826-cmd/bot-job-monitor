import streamlit as st
import requests
from bs4 import BeautifulSoup
import google.generativeai as genai
import json

# 1. 網頁基本設定
st.set_page_config(page_title="國藝會職缺自動化追蹤器", page_icon="🎨", layout="centered")
st.title("🎨 國藝會職缺自動化追蹤器")
st.caption("使用 Streamlit + Google AI Studio (Gemini 2.5 Flash) 本週單頁報告測試版")

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
            # 💡 測試模式：只抓本週的第一頁網址，並強制加上 .strip() 防禦
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

# 4. Email 報告文字生成功能
def generate_email_report(jobs_list):
    if not jobs_list:
        return "本週國藝會無更新職缺，無需發送報告。"
    
    try:
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel(model_name="gemini-2.5-flash")
        
        # 💡 優化點一：直接在底層資料串接處，換成你指定的實心圓點「・」，並強迫分行！
        jobs_summary = ""
        for index, job in enumerate(jobs_list, 1):
            jobs_summary += f"{index}. {job.get('organization')} - {job.get('title')}\n"
            jobs_summary += f"・日期: {job.get('date')}\n"
            jobs_summary += f"・單位: {job.get('organization')}\n"
            jobs_summary += f"・職稱: {job.get('title')}\n"
            jobs_summary += f"・連結: {job.get('link')}\n\n"
        
        email_prompt = f"""
        請根據以下提供的國藝會職缺清單，撰寫一份專業、格式工整、適合直接複製寄出給主管或團隊的 Email 職缺追蹤報告。
        
        【Email 要求】
        1. 必須包含清晰的「主旨（Subject）」範例（需提及國藝會最新職缺追蹤匯報，並帶有今日日期 2026-07-10）。
        2. 內文開頭需有得體的商務問候語。
        3. 職缺資訊請「嚴格完整保留」我提供給你的「・」實心圓點排版格式，不要自行刪除圓點，也不要加上任何 Markdown 的 ** 粗體星號標籤。
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
if st.button("🚀 立即更新本週職缺 (精簡單頁+雙贏報告測試)", type="primary"):
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
        
        st.subheader("📋 職缺 Email 報告範本 (測試)")
        
        email_content = generate_email_report(data)
        
        # 💡 優化點二：極致的防禦性除錯，把可能漏出來的所有粗體和斜體星號全部瞬間擦乾淨
        clean_email_content = email_content.replace("**", "").replace("*", "").replace("`", "")
        
        # 🌟 1. 點擊連結預覽區
        with st.expander("👀 點此展開「可直接點擊連結」的報告預覽並檢查"):
            st.markdown(email_content)
            
        # 🌟 2. 乾淨純文字複製區（帶有完美的實心圓點排版！）
        st.text_area("📄 乾淨文字複製區 (已自動去除星號 / 點擊框內按 Ctrl+A 即可全選複製)", value=clean_email_content, height=450)
        
    else:
        st.info("目前沒有抓到職缺，請確認網頁內容。")
