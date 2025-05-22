import streamlit as st
import pandas as pd
import os
from math import radians, sin, cos, sqrt, atan2
import folium
from folium.plugins import MarkerCluster
from streamlit_folium import st_folium

# --- 전역 CSS 스타일 (카드 디자인) ---
st.markdown("""
<style>
.card {
  border: 1px solid #e0e0e0;
  border-radius: 12px;
  padding: 16px;
  margin: 8px;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.05);
  background: linear-gradient(135deg, #f9f9f9 0%, #ffffff 100%);
  transition: transform 0.2s;
}
.card:hover {
  transform: translateY(-4px);
  box-shadow: 0 8px 24px rgba(0, 0, 0, 0.1);
}
.card h3 { margin: 0 0 8px; color: #2e4a7d; font-size: 1.1rem; }
.card p { margin: 4px 0; font-size: 0.9rem; color: #333; }
.card a { display: inline-block; margin-top: 8px; text-decoration: none; color: #1f77b4; font-weight: 500; }
</style>
""", unsafe_allow_html=True)

# Haversine 함수 정의
def haversine(coord1, coord2):
    lat1, lon1 = coord1
    lat2, lon2 = coord2
    lat1, lon1, lat2, lon2 = map(radians, [lat1, lon1, lat2, lon2])
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    a = sin(dlat/2)**2 + cos(lat1)*cos(lat2)*sin(dlon/2)**2
    c = 2 * atan2(sqrt(a), sqrt(1-a))
    return 6371 * c  # km

# 1) 데이터 로드 함수
@st.cache_data
def load_data(path: str) -> pd.DataFrame:
    # 앱 디렉터리 기준 절대경로로 변환
    base_dir = os.path.dirname(__file__)
    full_path = os.path.join(base_dir, path)
    df = pd.read_csv(full_path, encoding='cp949')
    df = df[df['응급실운영여부'] == 1]
    df = df.rename(columns={
        '병원위도':'lat', '병원경도':'lon',
        '기관명':'name', '주소':'address', '병원분류명':'type'
    })
    return df[['name','address','type','lat','lon','대표전화1','응급실전화']]

# 2) UI 타이틀 및 WebApp 소개
st.title("🚑 서울시 응급실 서비스 🚑")

# 3) 데이터 로드
df = load_data("seoul_emer.csv")

# 4) 사이드바 설정
st.sidebar.header("⚙️ 설정")
lat = st.sidebar.number_input("위도", value=37.5665, format="%.6f")
lon = st.sidebar.number_input("경도", value=126.9780, format="%.6f")
user_coord = (lat, lon)
types = st.sidebar.multiselect(
    "응급실 분류", options=df['type'].unique(), default=list(df['type'].unique())
)
radius = st.sidebar.slider("반경 (km)", 1.0, 20.0, 5.0, 0.5)
tiles = st.sidebar.selectbox("지도 스타일", ['OpenStreetMap','CartoDB positron'])

# 5) 거리 계산 및 필터링
df['distance'] = df.apply(lambda r: haversine(user_coord, (r.lat, r.lon)), axis=1)
filtered = df[(df['distance'] <= radius) & (df['type'].isin(types))]

# 6) 통계 차트
st.sidebar.subheader("📊 응급실 분류별 개수")
count_by_type = filtered.groupby('type').size().reset_index(name='count')
st.sidebar.bar_chart(count_by_type.set_index('type'))

# 7) 카드형 최근접 3개
st.subheader("🚨 반경 내 가장 가까운 3개 응급실")
nears = filtered.nsmallest(3, 'distance').reset_index(drop=True)
cards = st.columns(3)
for i, row in nears.iterrows():
    with cards[i]:
        st.markdown(f"""
        <div class='card'>
          <h3>{row['name']}</h3>
          <p>📍 {row['address']}</p>
          <p>📏 {row['distance']:.2f} km</p>
          <p>🏷️ {row['type']}</p>
          <a href='https://search.naver.com/search.naver?query={row['name']}' target='_blank'>🔍 네이버 검색</a>
        </div>
        """, unsafe_allow_html=True)

# 8) 상세 정보 테이블
st.subheader("📋 상세 응급실 정보")
st.download_button(
    "📥 CSV 다운로드", filtered.to_csv(index=False), file_name='filtered_emer.csv'
)
disp = filtered.rename(columns={
    'name':'병원 이름', 'address':'주소', 'type':'분류',
    'distance':'거리(km)', '대표전화1':'대표전화', '응급실전화':'응급실전화'
})
st.dataframe(
    disp[['병원 이름','주소','분류','거리(km)','대표전화','응급실전화']], height=300
)

# 9) 클러스터 지도 및 범례
st.subheader("📍 응급실 위치 지도")
m = folium.Map(location=user_coord, tiles=tiles, zoom_start=12)
cluster = MarkerCluster().add_to(m)
legend = folium.Element(
    '<div style="position: fixed; bottom: 50px; left: 50px; '
    'background: white; padding: 8px; border:1px solid #ccc; font-size:0.85rem;">'
    '<strong>분류 색상</strong><br>red: 상급종합<br>blue: 종합<br>green: 병원<br>purple: 의원</div>'
)
m.get_root().html.add_child(legend)
icon_map = {'상급종합':'red','종합':'blue','병원':'green','의원':'purple'}
for _, row in filtered.iterrows():
    folium.Marker(
        [row.lat, row.lon],
        popup=f"{row['name']} ({row['distance']:.2f} km)",
        icon=folium.Icon(color=icon_map.get(row['type'], 'gray'), prefix='glyphicon', icon='plus-sign')
    ).add_to(cluster)
st_folium(m, width=800, height=500)

# 10) Footer
from pandas import Timestamp
uptime = Timestamp.now().strftime('%Y-%m-%d %H:%M:%S')
st.markdown(
    f"<div style='text-align:center; color:#888;'>🚀 Updated: {uptime}</div>",
    unsafe_allow_html=True
)
