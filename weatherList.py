import streamlit as st
import requests
from bs4 import BeautifulSoup
import pandas as pd
import re

# スマホの画面幅に完全特化させる設定
st.set_page_config(page_title="那須塩原の天気比較", layout="centered")

# スマホ表示を美しく見せるためのCSS調整
st.markdown("""
    <style>
    /* 1) タイトルの見切れ対策: 上部の余白(padding-top)を増やして上に隠れないようにする */
    .block-container { 
        padding-top: 3rem !important; 
        padding-bottom: 1rem; 
        padding-left: 0.5rem; 
        padding-right: 0.5rem; 
    }

    /* 2) タイトルの改行対策: スマホ向けにフォントサイズを小さくし、強制的に1行に収める */
    h1 {
        font-size: 1.5rem !important; 
        line-height: 1.3 !important;
        white-space: nowrap !important;
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

    /* 4) 各要素の横幅を固定して縦ラインを綺麗に揃える設定 */
    .site-row .site-name {
        width: 30%;      /* サイト名エリア */
        text-align: left;
    }
    .site-row .site-weather {
        width: 35%;      /* 天気テキストエリア */
        text-align: left;
    }
    .site-row .site-rain {
        width: 15%;      /* 降水確率エリア */
        text-align: right;
        padding-right: 5px; 
    }
    .site-row .site-temp {
        width: 20%;      /* 気温エリア */
        text-align: right;
    }
    </style>
""", unsafe_allow_html=True)

st.title("🌲 那須塩原 3社天気予報")

# --- 1. tenki.jp のスクレイピング関数 ---
def get_tenki_jp_week():
    url = "https://tenki.jp/forecast/3/12/4120/9213/10days.html"
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
    
    res = requests.get(url, headers=headers)
    soup = BeautifulSoup(res.text, 'html.parser')
    
    lines = [line.strip() for line in soup.get_text().splitlines() if line.strip()]
    forecast_list = []
    
    i = 0
    while i < len(lines):
        if re.match(r'^\d{2}月\d{2}日\(.\)$', lines[i]):
            date_text = lines[i]
            if i + 3 < len(lines):
                weather_text = lines[i+1]
                temp_text = lines[i+2]
                rain_text = lines[i+3]
                
                if "℃" in temp_text:
                    temps = temp_text.split("℃")
                    if len(temps) >= 2:
                        temp_text = f"{temps[0]}℃ / {temps[1]}℃"
                if "%" in rain_text:
                    rain_text = rain_text.split("%")[0] + "%"
                
                if not any(d["日付"] == date_text for d in forecast_list):
                    forecast_list.append({
                        "日付": date_text,
                        "天気 (tenki)": weather_text,
                        "確率 (tenki)": rain_text,
                        "気温 (tenki)": temp_text
                    })
                i += 3
        i += 1
    return forecast_list

# --- 2. Yahoo!天気 のスクレイピング関数 ---
def get_yahoo_weather_week():
    url = "https://weather.yahoo.co.jp/weather/9/4120/9213.html"
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
    
    res = requests.get(url, headers=headers)
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
                date_key = f"{m:02d}月{d:02d}日({dow})"
                
                weather_val = "--"
                temps_today = []
                
                for sub_idx in range(idx + 2, idx + 60):
                    if sub_idx >= len(lines): break
                    if lines[sub_idx] == "天気" and sub_idx + 5 < len(lines):
                        weather_val = lines[sub_idx + 5]
                    if "気温" in lines[sub_idx]:
                        for t_offset in range(1, 9):
                            t_val = lines[sub_idx + t_offset]
                            if t_val.isdigit():
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
                date_key = f"{m:02d}月{d:02d}日({dow})"
                
                weather_val = "--"
                temps_tomorrow = []
                
                for sub_idx in range(idx + 2, idx + 60):
                    if sub_idx >= len(lines): break
                    if lines[sub_idx] == "天気" and sub_idx + 5 < len(lines):
                        weather_val = lines[sub_idx + 5]
                    if "気温" in lines[sub_idx]:
                        for t_offset in range(1, 9):
                            t_val = lines[sub_idx + t_offset]
                            if t_val.isdigit():
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
                        dates.append(f"{m:02d}月{d:02d}日{w}")
                    i += 1
            elif mode == "weather":
                if len(line) <= 6 and not line.startswith("(") and line not in ["A","B","C","D","E"]:
                    weathers.append(line)
            elif mode == "temp":
                if line.isdigit():
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

# --- 3. ウェザーニュース のスクレイピング関数 ---
def get_weathernews_week():
    url = "https://weathernews.jp/onebox/tenki/tochigi/09213/week.html?tab=4"
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
    
    res = requests.get(url, headers=headers)
    soup = BeautifulSoup(res.text, 'html.parser')
    lines = [line.strip() for line in soup.get_text().splitlines() if line.strip()]
    
    wn_list = []
    current_month = pd.Timestamp.now().month
    
    today_weather = "晴れ"
    tomorrow_weather = "晴れ"
    for idx, line in enumerate(lines):
        if line == "今日の天気" and idx + 2 < len(lines):
            today_weather = lines[idx+2]
        if line == "明日の天気" and idx + 2 < len(lines):
            tomorrow_weather = lines[idx+2]
            
    table_start_idx = -1
    for idx, line in enumerate(lines):
        if line == "日" and idx + 4 < len(lines) and lines[idx+1] == "天気" and lines[idx+2] == "最高":
            table_start_idx = idx + 5
            break
            
    if table_start_idx != -1:
        sub_lines = lines[table_start_idx:]
        i = 0
        while i < len(sub_lines):
            if sub_lines[i].isdigit() and i + 1 < len(sub_lines):
                dow_match = re.match(r'^[\(（](.)[\)）]$', sub_lines[i+1])
                if dow_match:
                    day = int(sub_lines[i])
                    dow = dow_match.group(1)
                    date_key = f"{current_month:02d}月{day:02d}日({dow})"
                    
                    cursor = i + 2
                    if cursor < len(sub_lines) and sub_lines[cursor] in ["A", "B", "C", "D", "E"]:
                        cursor += 1
                        
                    if cursor + 2 < len(sub_lines):
                        temp_high = sub_lines[cursor]
                        temp_low = sub_lines[cursor + 1]
                        rain_prob = sub_lines[cursor + 2]
                        
                        day_weather = "曇時々晴"
                        if day == pd.Timestamp.now().day:
                            day_weather = today_weather
                        elif day == (pd.Timestamp.now() + pd.Timedelta(days=1)).day:
                            day_weather = tomorrow_weather
                        else:
                            prob_num = "".join(filter(str.isdigit, rain_prob))
                            if prob_num:
                                val = int(prob_num)
                                if val >= 60:
                                    day_weather = "雨"
                                elif val >= 40:
                                    day_weather = "曇一時雨"
                                else:
                                    day_weather = "晴時々曇"
                        
                        if rain_prob.isdigit():
                            rain_prob = f"{rain_prob}%"
                            
                        wn_list.append({
                            "日付": date_key,
                            "天気 (WNews)": day_weather,
                            "確率 (WNews)": rain_prob,
                            "気温 (WNews)": f"{temp_high} / {temp_low}" if "℃" in temp_high else f"{temp_high}℃ / {temp_low}℃"
                        })
                        
                    i = cursor + 3
                    continue
            i += 1
            
    return wn_list

# --- アプリ起動時にデータをロード ---
if 'weather_df' not in st.session_state:
    st.session_state.weather_df = None

if st.button("🔄 最新の天気予報を取得", use_container_width=True) or st.session_state.weather_df is None:
    with st.spinner("3大気象サイトからデータを解析中..."):
        try:
            tenki_data = get_tenki_jp_week()
            yahoo_data = get_yahoo_weather_week()
            wn_data = get_weathernews_week()
            
            if tenki_data:
                df = pd.DataFrame(tenki_data)
                if yahoo_data:
                    df = pd.merge(df, pd.DataFrame(yahoo_data), on="日付", how="left")
                if wn_data:
                    df = pd.merge(df, pd.DataFrame(wn_data), on="日付", how="left")
                
                df = df.fillna("--").sort_values(by="日付")
                st.session_state.weather_df = df
            else:
                st.error("データの取得に失敗しました。")
        except Exception as e:
            st.error(f"エラー: {e}")

# --- 📱 モバイルUI表示セクション ---
df_merged = st.session_state.weather_df

if df_merged is not None:
    # 2つの視点（タブ）を用意
    tab_card, tab_table = st.tabs(["📱 スマホカード表示", "📊 項目別・横並び比較"])
    
    # ------------------
    # 1. スマホカード表示
    # ------------------
    with tab_card:
        st.caption("日付ごとに3社の予報をコンパクトに並べています。スクロールで簡単に比較できます。")
        
        for _, row in df_merged.iterrows():
            # 曜日に応じた日付ヘッダーの色分け
            date_str = row["日付"]
            if "(土)" in date_str:
                header_style = "color: #64B5F6;"
            elif "(日)" in date_str:
                header_style = "color: #EF5350;"
            else:
                header_style = ""
                
            # ★【修正点】ここから下のHTML表示のインデントを下げ、forループの内部に入れました
            st.markdown(f"""
            <div class="weather-card">
                <div class="card-header" style="{header_style}">{row['日付']}</div>
                <!-- tenki.jp -->
                <div class="site-row">
                    <span class="site-name">🇯🇵 tenki.jp</span>
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
        st.caption("見たい情報だけを3社でスマートに横並び比較できます。横スクロールが不要です！")
        
        sub_tab_rain, sub_tab_temp, sub_tab_weather = st.tabs(["☔️ 降水確率", "🌡️ 最高/最低気温", "☁️ 天気マーク"])
        
        # 降水確率の横並び表
        with sub_tab_rain:
            df_rain = df_merged[["日付", "確率 (tenki)", "確率 (Yahoo)", "確率 (WNews)"]].copy()
            df_rain.columns = ["日付", "tenki.jp", "Yahoo!", "ウェザー"]
            st.dataframe(df_rain, use_container_width=True, hide_index=True)
            
        # 気温の横並び表
        with sub_tab_temp:
            df_temp = df_merged[["日付", "気温 (tenki)", "気温 (Yahoo)", "気温 (WNews)"]].copy()
            df_temp.columns = ["日付", "tenki.jp", "Yahoo!", "ウェザー"]
            # 表示を少しスリムにするため、文字の"℃"を削る
            for col in ["tenki.jp", "Yahoo!", "ウェザー"]:
                df_temp[col] = df_temp[col].str.replace("℃", "")
            st.dataframe(df_temp, use_container_width=True, hide_index=True)
            
        # 天気テキストの横並び表
        with sub_tab_weather:
            df_weather = df_merged[["日付", "天気 (tenki)", "天気 (Yahoo)", "天気 (WNews)"]].copy()
            df_weather.columns = ["日付", "tenki.jp", "Yahoo!", "ウェザー"]
            st.dataframe(df_weather, use_container_width=True, hide_index=True)