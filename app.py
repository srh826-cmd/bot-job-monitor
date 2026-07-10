import streamlit as st
import requests
from bs4 import BeautifulSoup
import google.generativeai as genai
import json
from datetime import datetime

# 1. 網頁基本設定
st.set_page_config(page_title="國藝會職缺自動化追蹤器", page_icon="🎨", layout="centered")
st.title("🎨 國藝會職缺自動化追蹤器")
st.caption("使用 Streamlit + Google AI Studio (Gemini 3.1 Flash-Lite 核心) 本週求才表格測試")

# 2. 安全取得 Gemini API Key
if "GEMINI_API_KEY" in st.secrets:
    api_key = st.secrets["GEMINI_API_KEY"]
else:
    api_key = st.sidebar.text_input("請輸入 Gemini API Key", type="password")

# 3. 核心抓取與分析功能 (本週第一頁精簡測試版)
def fetch_and_analyze():
    if not api_key:
        st.warning("⚠️ 請先在 Streamlit Secrets 設定或在左側輸入 Gemini API Key！")
        return None
    
    html_snapshot = ""
    
    with st.spinner("🔄 正在巡邏擷取「本週第一頁」精簡資訊進行測試..."):
        try:
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
                html_snapshot += "\n--- 本週篩選第一頁純文字內容（含薪資資訊） ---\n"
                html_snapshot += soup.get_text(separator="\n", strip=True)
                
        except Exception as e:
            st.error(f"網頁抓取失敗: {e}")
            return None

    if not html_snapshot.strip():
        return []

    with st.spinner("🧠 Gemini 3.1 Flash-Lite 核心正在分析本週職缺與薪資..."):
        try:
            genai.configure(api_key=api_key)
            
            # 💡 大腦鎖定為官方正式支援 3.1 核心之 ID: "gemini-3.1-flash-lite"
            model = genai.GenerativeModel(
                model_name="gemini-3.1-flash-lite",
                generation_config={"response_mime_type": "application/json"}
            )
            
            prompt = f"""
            你是一個專業的網頁資料分析專家。以下是國藝會「本週公告」第一頁的求才對照文字。
            請幫我整理出這一頁包含的所有職缺清單（請嚴格忽略重複的職缺，並依日期由新到舊排序）。
            
            【嚴格規範】
            1. 必須輸出符合 JSON Array 的格式，不要包含 ```json 等 Markdown 標籤。
            2. 每個物件必須包含五個欄位：
               - "date": 職缺公告或更新日期 (請根據網頁實際文字填寫)
               - "organization": 求才單位名稱
               - "title": 職缺職稱
               - "link": 請精準填寫該職缺對應的詳細內頁網址。
               - "salary": 請從純文字中找出該職缺對應的薪資待遇 (例如: 月薪 45,000元 ~、時薪 200元、面議...等，若找不到填寫「依網站公告」)
            
            【本週網頁資料（單頁精簡）】
            {html_snapshot}
            """
            
            response = model.generate_content(prompt)
            jobs_data = json.loads(response.text.strip())
            return jobs_data
        except Exception as e:
            st.error(f"Gemini 分析失敗: {e}")
            return None

# 4. HTML Email 表格報告文字生成功能
def generate_html_email_report(jobs_list):
    if not jobs_list:
        return "<p>本週國藝會無更新職缺，無需發送報告。</p>"
    
    try:
        genai.configure(api_key=api_key)
        # 💡 同步將模型設定為 "gemini-3.1-flash-lite"
        model = genai.GenerativeModel(model_name="gemini-3.1-flash-lite")
        
        current_date = datetime.now().strftime("%Y-%m-%d")
        jobs_json_str = json.dumps(jobs_list, ensure_ascii=False)
        
        email_prompt = f"""
        請根據以下提供的國藝會職缺 JSON 資料，撰寫一份專業、格式工整、適合直接複製貼進 Gmail/Outlook 的 Email 職缺追蹤報告。
        
        【Email 排版要求】
        1. 開頭請嚴格依循此格式（換行請符合以下要求）：
           Dear all ,
           
           以下為 {current_date} 於官網新增之藝文求才與展演櫥窗：
           
           | 藝文求才 |
           
        2. 【極重要字體大小規範】：請確保「| 藝文求才 |」這行字使用一般段落（或使用與內文完全相同的字體大小和粗細，例如標準的 <p> 標籤），絕對不要使用 <h1> 到 <h6> 等會放大字體的網頁標題標籤。
        3. 職缺清單必須繪製成一個標準的 HTML <table> 表格。表格要有邊框、間距與專業外觀。
        4. 表格欄位與樣式規範：
           - 欄位共有三欄：求才單位、職缺名稱、薪資待遇。
           - 標題列（Th）的背景顏色必須是淺灰色（#CCCCCC 或 #D3D3D3），字體加粗，線條要有邊框。
           - 邊框線條必須是細實線（border: 1px solid #000000; border-collapse: collapse;）。
           - 如果同一個「求才單位」有多個職缺，請使用 HTML 的 `rowspan` 屬性將「求才單位」的儲存格合併。
           - 「職缺名稱」必須是帶有超連結的藍色文字，點擊可直接連結到該職缺的 URL。
        5. 結尾留空簽名檔。
        6. 請直接輸出純 HTML 原始碼，絕對不要包含任何 Markdown 標籤（如 ```html），也不要包含 🌟 或 ** 等符號。
        
        【職缺 JSON 資料】
        {jobs_json_str}
        """
        
        response = model.generate_content(email_prompt)
        return response.text.strip()
    except Exception as e:
        return f"HTML 報告生成失敗: {e}"

# 5. 網頁 UI 互動介面
if st.button("🚀 立即更新本週職缺 (商務表格測試)", type="primary"):
    data = fetch_and_analyze()
    
    if data:
        st.success(f"🎉 測試成功！已成功撈回第一頁共 {len(data)} 筆精簡職缺進行表格測試！")
        
        with st.expander("🔍 點此展開「職缺原始清單」以進行資料 Double Check"):
            for index, job in enumerate(data):
                with st.container():
                    col1, col2 = st.columns([1, 4])
                    with col1:
                        st.info(f"📅 {job.get('date', '未知')}")
                    with col2:
                        st.subheader(f"{job.get('organization', '未知')} - {job.get('title', '未知')}")
                        st.markdown(f"💰 薪資: {job.get('salary', '未知')} | [🔗 詳細內容頁面]({job.get('link')})")
                    st.divider()
        
        st.subheader("📋 本週職缺 Email 商務表格報告 (預覽測試)")
        
        html_email_content = generate_html_email_report(data)
        
        # 🌟 乾淨直覺呈現在白色區塊內，再也沒有任何複雜的複製按鈕，滑鼠直接往下反白即可！
        st.markdown(
            f'<div style="border:1px solid #ddd; padding:20px; border-radius:5px; background-color: #ffffff; color: #000000;">'
            f'{html_email_content}'
            f'</div>', 
            unsafe_allow_html=True
        )
        
    else:
        st.info("目前沒有抓到職缺，請確認網頁內容。")
