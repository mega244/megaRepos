import streamlit as st
import requests
from bs4 import BeautifulSoup
import pandas as pd
import re

# スマホ画面用の基本設定
st.set_page_config(page_title="那須塩原の天気比較", layout="centered")

st.markdown("""
    <style>
    .block-container { padding-top: 2rem; }
    </style>
""", unsafe_allow_html=True)

st.subheader("🌲 那須塩原市 週間天気予報比較")
st.write("各サイトの週間予報を1つのリストにまとめて比較します。")

# --- tenki.jpの週間予報スクレイピング関数（テキスト並び順 解析版） ---
def get_tenki_jp_week():
    url = "https://tenki.jp/forecast/3/12/4120/9213/10days.html"
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
    
    res = requests.get(url, headers=headers)
    soup = BeautifulSoup(res.text, 'html.parser')
    
    # ページ内のテキストを、改行ごとに区切った綺麗なリストにする
    lines = [line.strip() for line in soup.get_text().splitlines() if line.strip()]
    
    forecast_list = []
    
    # データを上から順番に見ていく
    i = 0
    while i < len(lines):
        # 「07月13日(月)」のような日付のパターンを探す
        if re.match(r'^\d{2}月\d{2}日\(.\)$', lines[i]):
            date_text = lines[i]
            
            # 安全のため、残りの要素数が足りているかチェックしながら直後のデータを回収
            if i + 3 < len(lines):
                weather_text = lines[i+1] # 次の行が天気（例: 曇）
                temp_text = lines[i+2]    # その次の行が気温（例: 26℃22℃）
                rain_text = lines[i+3]    # その次の行が降水確率（例: 20%）
                
                # 気温の見栄えを良くする（例: "26℃22℃" -> "26℃ / 22℃"）
                if "℃" in temp_text:
                    # 最高気温と最低気温に分割して「 / 」で繋ぐ
                    temps = temp_text.split("℃")
                    if len(temps) >= 2:
                        temp_text = f"{temps[0]}℃ / {temps[1]}℃"
                
                # 降水確率のゴミ取り（"20% 0mm" のように降水量も巻き込んでいたら%までにする）
                if "%" in rain_text:
                    rain_text = rain_text.split("%")[0] + "%"
                
                # 重複していなければリストに追加
                if not any(d["日付"] == date_text for d in forecast_list):
                    forecast_list.append({
                        "日付": date_text,
                        "天気 (tenki.jp)": weather_text,
                        "確率 (tenki.jp)": rain_text,
                        "気温 (tenki.jp)": temp_text
                    })
                
                i += 3 # 読み進めた分、インデックスをスキップ
        i += 1

    return forecast_list

# --- 画面のメイン処理 ---
if st.button("🔄 各サイトから週間予報を取得してリスト化", use_container_width=True):
    with st.spinner("データを解析中..."):
        try:
            tenki_data = get_tenki_jp_week()
            
            if tenki_data:
                df = pd.DataFrame(tenki_data)
                st.success("tenki.jpの週間予報データの抽出に成功しました！")
                st.dataframe(df, use_container_width=True, hide_index=True)
                st.info("💡 最終的には、この表の右側に『Yahoo!の結果』や『ウェザーニュースの結果』のカラムが合体して、横並びで比較できるようになります！")
            else:
                st.error("テーブルの構造がうまく解析できませんでした。URLや構造が変更された可能性があります。")
                
        except Exception as e:
            st.error(f"エラーが発生しました: {e}")