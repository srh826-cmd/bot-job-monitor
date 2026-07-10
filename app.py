import streamlit as st
import requests
from bs4 import BeautifulSoup
import google.generativeai as genai
import json

# 1. 網頁基本設定
st.set_page_config(page_title="國藝會求才自動化追蹤器", page_icon="🎨", layout="centered")
st.title("🎨 國藝會求才自動化追蹤器")
st.caption("使用 Streamlit + Google AI Studio (Gemini 2.5 Flash) 本週雙頁測試版")

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
    
    with st.spinner("🔄 正在巡邏擷取「本週前兩頁」的求才資訊進行測試..."):
        try:
            # 💡 巡邏 page=0 和 page=1 (前兩頁)
            for page_num in range(0, 2):
                url = f"https://www.ncafroc.org.tw/recruitment?page={page_num}&organizationId=&salaryType=&salaryRange=&organizationName=&publishTime=WEEK"
                url = url.strip()
                headers = {
                    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
                }
                
                response = requests.get(url, headers=headers, timeout=10)
                response.encoding = 'utf-8'
                soup = BeautifulSoup(response.text, 'html.parser')
                
                has_links = False
                
                # 抓取該分頁裡所有的超連結與其文字
                for a_tag in soup.find_all('a', href=True):
                    text = a_tag.get_text(strip=True)
                    href = a_tag['href']
                    
                    if text and ("recruitment" in href or "sid=" in href or "html" in href):
                        has_links = True
                        if href.startswith("/"):
                            full_url = f"[https://www.ncafroc.org.tw](https://www.ncafroc.org.tw){href}"
                        elif href.startswith("http"):
                            full_url = href
                        else:
                            full_url = f"[https://www.ncafroc.org.tw/](https://www.ncafroc.org.tw/){href}"
                            
                        html_snapshot += f"【名稱/內容】: {text} -> 【詳細內頁網址】: {full_url}\n"
                
                # 如果這頁有抓到東西，才把純文字也黏上去
                if has_links:
                    html_snapshot += f"\n--- 本週篩選第 {page_num + 1} 頁純文字內容 ---\n"
                    html_snapshot += soup.get_text(separator="\n", strip=True)
                
        except Exception as e:
            st.error(f"網頁抓取失敗: {e}")
            return None

    if not html_snapshot.strip():
        return []

    with st.spinner("🧠 Gemini 2.5 Flash 正在合併雙頁職缺並精準對齊連結..."):
        try:
            genai.configure(api_key=api_key)
            
            # 💡 修正一：強制 Gemini 2.5 結構化輸出純 JSON，避免解析錯誤
            model = genai.GenerativeModel(
                model_name="gemini-2.5-flash",
                generation_config={"response_mime_type": "application/json"}
            )
            
            # 💡 修正二：將 Prompt 修改為整理「本週」職缺，避免非今天的職缺被過濾掉
            prompt = f"""
            你是一個專業的網頁資料分析專家。以下是國藝會「本週公告」前兩頁的求才對照文字。
            請幫我整理出這兩頁包含的所有職缺清單（請嚴格忽略重複的職缺，並依日期由新到舊排序）。
            
            【嚴格規範】
            1. 必須輸出符合 JSON Array 的格式，不要包含 ```json 等 Markdown 標籤。
            2. 每個物件必須包含四個欄位：
               - "date": 職缺公告或更新日期 (格式如: 2026-07-10)
               - "organization": 求才單位名稱
               - "title": 職缺職稱
               - "link": 請精準填寫該職缺對應的詳細內頁網址。
            
            【本週最新網頁資料（前兩頁合併）】
            {html_snapshot}
            """
            
            response = model.generate_content(prompt)
            jobs_data = json.loads(response.text.strip())
            return jobs_data
        except Exception as e:
            st.error(f"Gemini 分析失敗: {e}")
            if 'response' in locals():
                st.code(response.text)
            return None

# 4. 網頁 UI 互動介面
if st.button("🚀 立即更新本週職缺 (精準雙頁測試)", type="primary"):
    data = fetch_and_analyze()
    
    if data:
        st.success(f"🎉 測試成功！已完美合併前兩頁，共撈回 {len(data)} 筆本週公告職缺！")
        
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
        st.info("目前沒有抓到本週職缺，請確認網頁內容。")
