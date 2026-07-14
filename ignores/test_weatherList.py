import streamlit as st
import random  # 本来はここにスクレイピングの関数をインポートします

# スマホ画面用の基本設定
st.set_page_config(page_title="那須塩原の天気", layout="centered")

# カスタムCSSで余白を限界まで削り、スマホ1画面に収める
st.markdown("""
    <style>
    .block-container { padding-top: 1rem; padding-bottom: 0rem; }
    div[data-testid="stMetric"] { background-color: #f0f2f6; padding: 10px; border-radius: 10px; }
    </style>
""", unsafe_allow_html=True)

st.subheader("🌲 那須塩原市 天気予報比較")

# 1. スマホからのトリガー（ボタン）
if st.button("🔄 各サイトから最新の予報を取得", use_container_width=True):
    with st.spinner("スクレイピング中..."):
        # ーーー ここで各サイトのURLからスクレイピングを実行するイメージ ーーー
        # 例： data_wn = scrape_weathernews() ...
        
        # 画面確認用のダミーデータ
        weather_data = {
            "ウェザーニュース": {"icon": "☁️", "condition": "くもり", "temp": "30℃ / 22℃", "rain": "30%"},
            "tenki.jp": {"icon": "☔️", "condition": "くもり時々雨", "temp": "30℃ / 22℃", "rain": "90%"},
            "Yahoo!天気": {"icon": "☁️", "condition": "曇り", "temp": "32℃ / 22℃", "rain": "20%"}
        }

    # 2. スマホに収めるための3カラム（横並び）表示
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.markdown("**W.News**")
        d = weather_data["ウェザーニュース"]
        st.metric(label=f"{d['icon']} {d['condition']}", value=d['rain'], delta=d['temp'], delta_color="off")
        
    with col2:
        st.markdown("**tenki.jp**")
        d = weather_data["tenki.jp"]
        st.metric(label=f"{d['icon']} {d['condition']}", value=d['rain'], delta=d['temp'], delta_color="off")
        
    with col3:
        st.markdown("**Yahoo!**")
        d = weather_data["Yahoo!天気"]
        st.metric(label=f"{d['icon']} {d['condition']}", value=d['rain'], delta=d['temp'], delta_color="off")
        
    st.caption("最終更新: たった今取得")
else:
    st.info("上のボタンをタップすると予報を比較します。")