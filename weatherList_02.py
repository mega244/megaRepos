import streamlit as st
import requests
from bs4 import BeautifulSoup
import pandas as pd
import re

# スマホの画面幅に完全特化させる設定
st.set_page_config(page_title="八風平の天気比較", layout="centered")

# スマホ表示を美しく見せるためのCSS調整
st.markdown("""
    <style>
    /* 1) タイトルの見切れ対策 */
    .block-container { 
        padding-top: 2rem !important; 
        padding-bottom: 1rem; 
        padding-left: 0.5rem; 
        padding-right: 0.5rem; 
    }

    /* 2) タイトルの改行対策 */
    h1 {
        font-size: 1.5rem !important; 
        line-height: 1.3 !important;
    }

    /* 3) カード型デザインのスタイル */
    .weather-card {
        background-color: #e0f7fa; 
        border-radius: 10px;
        padding: 12px;
        margin-bottom: 15px;
        border: 1px solid #b2ebf2; 
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.05); 
        color: #333333 !important; 
    }
    
    /* カード内の日付ヘッダー */
    .card-header {
        font-weight: bold;
        font-size: 1.1rem;
        border-bottom: 1px solid #b2ebf2;
        padding-bottom: 8px;
        margin-bottom: 8px;
        color: #111111 !important; 
    }
    
    /* 各サイトの天気行 */
    .site-row {
        display: flex;
        align-items: center;
        padding: 6px 0;
        border-bottom: 1px dashed #cccccc; 
        color: #333333 !important; 
    }
    
    /* 一番最後の行だけは下線を消す設定 */
    .site-row:last-child {
        border-bottom: none;
    }

    /* 4) 各要素の横幅を微調整（サイト名を少し狭め、天気を広めに確保） */
    .site-row .site-name {
        width: 25%;      /* サイト名エリア */
        text-align: left;
        font-size: 0.85rem;
    }
    .site-row .site-weather {
        width: 40%;      /* 天気テキストエリア */
        text-align: left;
        font-size: 0.85rem;
    }
    .site-row .site-rain {
        width: 15%;      /* 降水確率エリア */
        text-align: right;
        padding-right: 5px; 
        font-size: 0.85rem;
    }
    .site-row .site-temp {
        width: 20%;      /* 気温エリア */
        text-align: right;
        font-size: 0.85rem;
    }
    </style>
""", unsafe_allow_html=True)

st.title("🌲 八風平 3社天気予報")

# 日付の表記揺れを統一する関数
def normalize_date(date_str):
    if not date_str or date_str == "--":
        return None
    match = re.search(r'(\d+)月(\d+)日(?:\s*\(?(.*?)\)?)?', date_str)
    if match:
        m = int(match.group(1))
        d = int(match.group(2))
        dow = match.group(3) if match.group(3) else ""
        dow = dow.strip()
        return f"{m:02d}月{d:02d}日({dow})" if dow else f"{m:02d}月{d:02d}日"
    return date_str

# --- 1. tenki.jp の新パース処理 ---
def get_tenki_jp_week():
    url = "https://tenki.jp/forecast/3/13/4210/10211/10days.html"
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"}
    
    try:
        res = requests.get(url, headers=headers, timeout=10)
        res.encoding = 'utf-8'
        soup = BeautifulSoup(res.text, 'html.parser')
        
        forecast_list = []
        current_month = pd.Timestamp.now().month
        
        # class='forecast' を持つdivブロックをすべて解析
        forecast_divs = soup.find_all("div", class_="forecast")
        
        for div in forecast_divs:
            # 日付部分の抽出 (例: "16日(木)")
            day_elem = div.find(class_=re.compile("day|date"))
            if not day_elem:
                continue
            day_text = day_elem.get_text(strip=True)
            day_match = re.search(r'(\d+)日\((.*?)\)', day_text)
            if not day_match:
                continue
            
            d = int(day_match.group(1))
            dow = day_match.group(2)
            date_key = normalize_date(f"{current_month:02d}月{d:02d}日({dow})")
            
            # 天気の抽出
            weather_elem = div.find(class_=re.compile("weather|telop"))
            weather_text = "--"
            if weather_elem:
                img = weather_elem.find("img")
                weather_text = img.get("alt", weather_elem.get_text(strip=True)) if img else weather_elem.get_text(strip=True)
            
            # 気温の抽出 (最高/最低)
            temp_elem = div.find(class_=re.compile("temp|temperature"))
            temp_text = "--℃ / --℃"
            if temp_elem:
                # 数値（マイナス対応）をすべて抽出
                temp_vals = re.findall(r'[-+]?\d+', temp_elem.get_text())
                if len(temp_vals) >= 2:
                    temp_text = f"{temp_vals[0]}℃ / {temp_vals[1]}℃"
            
            # 降水確率の抽出
            rain_elem = div.find(class_=re.compile("precip|prob"))
            rain_text = "--%"
            if rain_elem:
                rain_val = "".join(filter(str.isdigit, rain_elem.get_text()))
                if rain_val:
                    rain_text = f"{rain_val}%"
                    
            forecast_list.append({
                "日付": date_key,
                "天気 (tenki)": weather_text.strip(),
                "確率 (tenki)": rain_text,
                "気温 (tenki)": temp_text
            })
            
        return forecast_list
    except Exception as e:
        st.warning(f"tenki.jp の取得でエラーが発生しました: {e}")
        return []

# --- 2. Yahoo!天気 のスクレイピング関数 ---
def get_yahoo_weather_week():
    url = "https://weather.yahoo.co.jp/weather/jp/10/4210/10211.html"
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"}
    
    try:
        res = requests.get(url, headers=headers, timeout=10)
        soup = BeautifulSoup(res.text, 'html.parser')
        lines = [line.strip() for line in soup.get_text().splitlines() if line.strip()]
        
        yahoo_list = []
        umbrella_today = "--%"
        umbrella_tomorrow = "--%"
        
        for idx, line in enumerate(lines):
            if line == "今日明日の指数情報":
                sub_lines = lines[idx:idx+100]
                umbrella_vals = []
                for sub_line in sub_lines:
                    if "傘指数" in sub_line:
                        val = "".join(filter(str.isdigit, sub_line))
                        if val:
                            umbrella_vals.append(f"{val}%")
                if len(umbrella_vals) >= 1:
                    umbrella_today = umbrella_vals[0]
                if len(umbrella_vals) >= 2:
                    umbrella_tomorrow = umbrella_vals[1]
                break

        today_data = None
        tomorrow_data = None
        
        for idx, line in enumerate(lines):
            if line == "今日の天気" and idx + 1 < len(lines):
                date_line = lines[idx+1]
                match = re.search(r'(\d+)月(\d+)日\((.+)\)', date_line)
                if match:
                    m, d, dow = int(match.group(1)), int(match.group(2)), match.group(3)
                    date_key = normalize_date(f"{m:02d}月{d:02d}日({dow})")
                    weather_val = "--"
                    temps_today = []
                    
                    for sub_idx in range(idx + 2, idx + 60):
                        if sub_idx >= len(lines): break
                        if lines[sub_idx] == "天気" and sub_idx + 5 < len(lines):
                            weather_val = lines[sub_idx + 5]
                        if "気温" in lines[sub_idx]:
                            for t_offset in range(1, 9):
                                t_val = lines[sub_idx + t_offset]
                                if t_val.replace('-', '').isdigit():
                                    temps_today.append(int(t_val))
                    
                    high_val = max(temps_today) if temps_today else "--"
                    low_val = min(temps_today) if temps_today else "--"
                    
                    today_data = {
                        "日付": date_key,
                        "天気 (Yahoo)": weather_val if weather_val != "--" else "曇り",
                        "確率 (Yahoo)": umbrella_today,
                        "気温 (Yahoo)": f"{high_val}℃ / {low_val}℃"
                    }
                    
            if line == "明日の天気" and idx + 1 < len(lines):
                date_line = lines[idx+1]
                match = re.search(r'(\d+)月(\d+)日\((.+)\)', date_line)
                if match:
                    m, d, dow = int(match.group(1)), int(match.group(2)), match.group(3)
                    date_key = normalize_date(f"{m:02d}月{d:02d}日({dow})")
                    weather_val = "--"
                    temps_tomorrow = []
                    
                    for sub_idx in range(idx + 2, idx + 60):
                        if sub_idx >= len(lines): break
                        if lines[sub_idx] == "天気" and sub_idx + 5 < len(lines):
                            weather_val = lines[sub_idx + 5]
                        if "気温" in lines[sub_idx]:
                            for t_offset in range(1, 9):
                                t_val = lines[sub_idx + t_offset]
                                if t_val.replace('-', '').isdigit():
                                    temps_tomorrow.append(int(t_val))
                    
                    high_val = max(temps_tomorrow) if temps_tomorrow else "--"
                    low_val = min(temps_tomorrow) if temps_tomorrow else "--"
                    
                    tomorrow_data = {
                        "日付": date_key,
                        "天気 (Yahoo)": weather_val if weather_val != "--" else "曇り",
                        "確率 (Yahoo)": umbrella_tomorrow,
                        "気温 (Yahoo)": f"{high_val}℃ / {low_val}℃"
                    }

        start_idx = -1
        for idx, line in enumerate(lines):
            if "週間天気" in line:
                start_idx = idx
                break
                
        if start_idx != -1:
            sub_lines = lines[start_idx:]
            dates = []
            weathers = []
            temps = []
            rains = []
            
            mode = None
            i = 0
            while i < len(sub_lines):
                line = sub_lines[i]
                if line == "日付":
                    mode = "date"
                    i += 1
                    continue
                elif line == "天気":
                    mode = "weather"
                    i += 1
                    continue
                elif "気温" in line:
                    mode = "temp"
                    i += 1
                    continue
                elif "降水確率" in line:
                    mode = "rain"
                    i += 1
                    continue
                elif "今日明日の指数情報" in line or "エリアの情報" in line:
                    break
                    
                if mode == "date":
                    if "月" in line and "日" in line and i + 1 < len(sub_lines) and sub_lines[i+1].startswith("("):
                        match = re.search(r'(\d+)月(\d+)日', line)
                        if match:
                            m = int(match.group(1))
                            d = int(match.group(2))
                            w = sub_lines[i+1]
                            dates.append(normalize_date(f"{m:02d}月{d:02d}日{w}"))
                        i += 1
                elif mode == "weather":
                    if len(line) <= 6 and not line.startswith("(") and line not in ["A","B","C","D","E"]:
                        weathers.append(line)
                elif mode == "temp":
                    if line.replace('-', '').isdigit():
                        temps.append(line)
                elif mode == "rain":
                    if line.isdigit() or line == "--":
                        rains.append(f"{line}%" if line.isdigit() else "--%")
                i += 1

            paired_temps = []
            for k in range(0, len(temps), 2):
                if k + 1 < len(temps):
                    paired_temps.append(f"{temps[k]}℃ / {temps[k+1]}℃")

            min_len = min(len(dates), len(weathers), len(paired_temps), len(rains))
            for idx in range(min_len):
                yahoo_list.append({
                    "日付": dates[idx],
                    "天気 (Yahoo)": weathers[idx],
                    "確率 (Yahoo)": rains[idx],
                    "気温 (Yahoo)": paired_temps[idx]
                })

        final_list = []
        if today_data:
            final_list.append(today_data)
        if tomorrow_data:
            final_list.append(tomorrow_data)
            
        for item in yahoo_list:
            if not any(d["日付"] == item["日付"] for d in final_list):
                final_list.append(item)
                
        return final_list
    except Exception as e:
        st.warning(f"Yahoo!天気の取得でエラーが発生しました: {e}")
        return []

# --- 3. ウェザーニュース の新リスト構造パース処理 ---
def get_weathernews_week():
    url = "https://weathernews.jp/onebox/tenki/gunma/10211/"
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"}
    
    try:
        res = requests.get(url, headers=headers, timeout=10)
        soup = BeautifulSoup(res.text, 'html.parser')
        
        wn_list = []
        current_month = pd.Timestamp.now().month
        
        # クラス名に 'wxweek_content' を含み、かつ 'past'（過去の実績）を含まないリストを取得
        items = soup.find_all("ul", class_=lambda x: x and "wxweek_content" in x and "past" not in x)
        
        for item in items:
            lis = item.find_all("li")
            if len(lis) < 5:
                continue
            
            # 日付（li[0]）: 例「16 | (木)」や「16 | 木」
            day_val = lis[0].get_text(" ", strip=True)
            day_match = re.search(r'(\d+)\s*\(?(.*?)\)?$', day_val)
            if not day_match:
                continue
            
            d = int(day_match.group(1))
            dow = day_match.group(2).replace("(", "").replace(")", "").strip()
            date_key = normalize_date(f"{current_month:02d}月{d:02d}日({dow})")
            
            # 天気（li[1]）: テキストまたは画像 alt 
            weather_txt = lis[1].get_text(strip=True)
            img = lis[1].find("img")
            if img:
                weather_txt = img.get("alt", img.get("title", weather_txt))
                
            # 最高気温（li[2]）, 最低気温（li[3]）
            high_temp = lis[2].get_text(strip=True).replace("℃", "").strip()
            low_temp = lis[3].get_text(strip=True).replace("℃", "").strip()
            
            # 降水確率（li[4]）
            rain_val = "".join(filter(str.isdigit, lis[4].get_text()))
            rain_prob = f"{rain_val}%" if rain_val else "0%" # 空の場合は0%
            
            wn_list.append({
                "日付": date_key,
                "天気 (WNews)": weather_txt if weather_txt else "曇り",
                "確率 (WNews)": rain_prob,
                "気温 (WNews)": f"{high_temp}℃ / {low_temp}℃"
            })
            
        return wn_list
    except Exception as e:
        st.warning(f"ウェザーニュースの取得でエラーが発生しました: {e}")
        return []

# --- アプリ起動時にデータをロード ---
if 'weather_df' not in st.session_state:
    st.session_state.weather_df = None

if st.button("🔄 最新の天気予報を取得", use_container_width=True) or st.session_state.weather_df is None:
    with st.spinner("3大気象サイトからデータを解析中..."):
        try:
            # 3サイト個別に取得
            tenki_data = get_tenki_jp_week()
            yahoo_data = get_yahoo_weather_week()
            wn_data = get_weathernews_week()
            
            # 取得できたデータだけでマージ処理
            dfs = []
            if tenki_data:
                dfs.append(pd.DataFrame(tenki_data))
            if yahoo_data:
                dfs.append(pd.DataFrame(yahoo_data))
            if wn_data:
                dfs.append(pd.DataFrame(wn_data))
            
            if dfs:
                df_merged = dfs[0]
                for next_df in dfs[1:]:
                    df_merged = pd.merge(df_merged, next_df, on="日付", how="outer")
                
                # 足りない項目は -- で埋めて日付順にソート
                df_merged = df_merged.fillna("--").sort_values(by="日付")
                st.session_state.weather_df = df_merged
            else:
                st.error("すべての天気サイトからのデータ取得に失敗しました。時間をおいて再度お試しください。")
                
        except Exception as e:
            st.error(f"システムエラーが発生しました: {e}")

# --- 📱 モバイルUI表示セクション ---
df_display = st.session_state.weather_df

if df_display is not None and not df_display.empty:
    # 存在しないカラムがある場合のデフォルト値を補完
    cols_to_ensure = {
        "天気 (tenki)": "--", "確率 (tenki)": "--%", "気温 (tenki)": "--℃ / --℃",
        "天気 (Yahoo)": "--", "確率 (Yahoo)": "--%", "気温 (Yahoo)": "--℃ / --℃",
        "天気 (WNews)": "--", "確率 (WNews)": "--%", "気温 (WNews)": "--℃ / --℃"
    }
    for col, default in cols_to_ensure.items():
        if col not in df_display.columns:
            df_display[col] = default

    tab_card, tab_table = st.tabs(["📱 スマホカード表示", "📊 項目別・横並び比較"])
    
    # ------------------
    # 1. スマホカード表示
    # ------------------
    with tab_card:
        st.caption("日付ごとに3社の予報をコンパクトに並べています。スクロールで簡単に比較できます。")
        
        for _, row in df_display.iterrows():
            date_str = row["日付"]
            if "(土)" in date_str:
                header_style = "color: #2196F3; font-weight: bold;"
            elif "(日)" in date_str or "(祝)" in date_str:
                header_style = "color: #F44336; font-weight: bold;"
            else:
                header_style = ""
                
            st.markdown(f"""
            <div class="weather-card">
                <div class="card-header" style="{header_style}">{row['日付']}</div>
                <!-- tenki.jp -->
                <div class="site-row">
                    <span class="site-name">🇯🇵 tenki</span>
                    <span class="site-weather">{row['天気 (tenki)']}</span>
                    <span class="site-rain">{row['確率 (tenki)']}</span>
                    <span class="site-temp">{row['気温 (tenki)'].replace('℃', '')}</span>
                </div>
                <!-- Yahoo! -->
                <div class="site-row">
                    <span class="site-name">🔴 Yahoo!</span>
                    <span class="site-weather">{row['天気 (Yahoo)']}</span>
                    <span class="site-rain">{row['確率 (Yahoo)']}</span>
                    <span class="site-temp">{row['気温 (Yahoo)'].replace('℃', '')}</span>
                </div>
                <!-- WNews -->
                <div class="site-row">
                    <span class="site-name">🔵 WNews</span>
                    <span class="site-weather">{row['天気 (WNews)']}</span>
                    <span class="site-rain">{row['確率 (WNews)']}</span>
                    <span class="site-temp">{row['気温 (WNews)'].replace('℃', '')}</span>
                </div>
            </div>
            """, unsafe_allow_html=True)

    # ------------------
    # 2. 項目別・横並び比較
    # ------------------
    with tab_table:
        st.caption("見たい情報だけを3社でスマートに横並び比較できます。")
        
        sub_tab_rain, sub_tab_temp, sub_tab_weather = st.tabs(["☔️ 降水確率", "🌡️ 最高/最低気温", "☁️ 天気マーク"])
        
        with sub_tab_rain:
            df_rain = df_display[["日付", "確率 (tenki)", "確率 (Yahoo)", "確率 (WNews)"]].copy()
            df_rain.columns = ["日付", "tenki.jp", "Yahoo!", "ウェザー"]
            st.dataframe(df_rain, use_container_width=True, hide_index=True)
            
        with sub_tab_temp:
            df_temp = df_display[["日付", "気温 (tenki)", "気温 (Yahoo)", "気温 (WNews)"]].copy()
            df_temp.columns = ["日付", "tenki.jp", "Yahoo!", "ウェザー"]
            for col in ["tenki.jp", "Yahoo!", "ウェザー"]:
                df_temp[col] = df_temp[col].astype(str).str.replace("℃", "")
            st.dataframe(df_temp, use_container_width=True, hide_index=True)
            
        with sub_tab_weather:
            df_weather = df_display[["日付", "天気 (tenki)", "天気 (Yahoo)", "天気 (WNews)"]].copy()
            df_weather.columns = ["日付", "tenki.jp", "Yahoo!", "ウェザー"]
            st.dataframe(df_weather, use_container_width=True, hide_index=True)