import streamlit as st
import pandas as pd
from haversine import haversine
import folium
from folium.plugins import MarkerCluster
from streamlit_folium import st_folium

# --- 전역 CSS 스타일 (카드 디자인 강화) ---
st.markdown("""
<style>
.card {
  border: 1px solid #e0e0e0;
  border-radius: 12px;
  padding: 16px;
            height: 250px;
  margin: 8px;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.05);
  background: linear-gradient(135deg, #f9f9f9 0%, #ffffff 100%);
  transition: transform 0.2s;
}
.card:hover {
  transform: translateY(-4px);
  box-shadow: 0 8px 24px rgba(0, 0, 0, 0.1);
}
.card h3 {
  margin: 0 0 8px;
  color: #2e4a7d;
  font-size: 1.1rem;
}
.card p {
  margin: 4px 0;
  font-size: 0.9rem;
  color: #333;
}
.card a {
  display: inline-block;
  margin-top: 8px;
  text-decoration: none;
  color: #1f77b4;
  font-weight: 500;
}
</style>
""", unsafe_allow_html=True)

# 1) 데이터 로드 함수
@st.cache_data
def load_data(path: str) -> pd.DataFrame:
    df = pd.read_csv(path, encoding='cp949')
    df = df[df['응급실운영여부'] == 1]
    df = df.rename(columns={
        '병원위도': 'lat',
        '병원경도': 'lon',
        '기관명': 'name',
        '주소': 'address',
        '병원분류명': 'type'
    })
    return df[['name','address','type','lat','lon','대표전화1','응급실전화']]

# 2) UI 타이틀 및 설명
st.title("🚑 서울시 응급실 서비스 🚑")

# 3) 데이터 로드
df = load_data("./seoul_emer.csv")

# 4) 사이드바 컨트롤
st.sidebar.markdown("## ⚙️ 설정")
# 위치 입력
# try:
#     from streamlit_javascript import st_javascript
#     js = r''' await new Promise(r => navigator.geolocation.getCurrentPosition(p => r({lat:p.coords.latitude, lon:p.coords.longitude}), e => r(null))) '''
#     loc = st_javascript(js)
#     user_coord = (loc['lat'], loc['lon']) if loc else None
# except ImportError:
#     user_coord = None
# if not user_coord:
st.sidebar.subheader("🚩 내 위치")
lat = st.sidebar.number_input("위도", 37.5665, format="%.6f")
lon = st.sidebar.number_input("경도", 126.9780, format="%.6f")
user_coord = (lat, lon)

st.sidebar.subheader("🗺️ 지도 스타일")
# 필터: 분류
types = st.sidebar.multiselect("응급실 분류", options=df['type'].unique().tolist(), default=df['type'].unique().tolist())
# 반경 슬라이더
radius = st.sidebar.slider("반경 (km)", min_value=1.0, max_value=20.0, value=5.0, step=0.5)
# 타일 선택
tiles = st.sidebar.selectbox("지도 스타일", options=['OpenStreetMap','CartoDB positron'])

# 5) 거리 계산 및 필터링
df['distance'] = df.apply(lambda r: haversine(user_coord,(r.lat,r.lon)), axis=1)
filtered = df[df['distance']<=radius]
filtered = filtered[filtered['type'].isin(types)]

# 6) 반경 내 응급실 통계 차트
st.sidebar.subheader("📊 응급실 분류별 개수")
count_by_type = filtered.groupby('type').size().reset_index(name='count')
chart = st.sidebar.bar_chart(count_by_type.set_index('type'))

# 7) 가장 가까운 3개 응급실
nears = filtered.nsmallest(3,'distance')
st.subheader("🚨 반경 내 가장 가까운 응급실 3개")
cards = st.columns(3)
for idx,row in nears.iterrows():
    i = nears.index.get_loc(idx)
    with cards[i]:
        st.markdown(f"""
        <div class='card'>
          <h3>{row['name']}</h3>
          <p>🚩 {row['address']}</p>
          <p>📏 {row['distance']:.2f} km</p>
          <p>🏷️ {row['type']}</p>
          <a href='https://search.naver.com/search.naver?query={row['name']}' target='_blank'>🔍 네이버 검색</a>
        </div>
        """, unsafe_allow_html=True)

# 8) 상세 정보 테이블 (다운로드 및 스크롤)
st.subheader("📋 상세 응급실 정보")
st.download_button("📥 CSV 다운로드", data=filtered.to_csv(index=False), file_name='filtered_emer.csv')
st.dataframe(filtered[['name','address','type','distance','대표전화1','응급실전화']]
             .rename(columns={'name':'병원 이름','address':'주소','type':'분류','distance':'거리(km)','대표전화1':'대표전화','응급실전화':'응급실전화'}),
             height=300)

# 9) 응급실 위치 지도 (클러스터 + 범례)
st.subheader("📍 응급실 위치 지도")
m = folium.Map(location=user_coord, tiles=tiles, zoom_start=12)
cluster = MarkerCluster().add_to(m)
# 범례
legend_html = '''<div style="position: fixed; bottom: 50px; left: 50px; background: white; padding: 8px; border:1px solid #ccc;">
<strong>분류별 마커 색상</strong><br>
red: 상급종합<br>blue: 종합<br>green: 병원<br>purple: 의원
</div>'''
m.get_root().html.add_child(folium.Element(legend_html))
# 마커 추가
icon_map={'상급종합':'red','종합':'blue','병원':'green','의원':'purple'}
for _,row in filtered.iterrows():
    folium.Marker([row.lat,row.lon],
                  popup=f"{row['name']} ({row['distance']:.2f} km)",
                  icon=folium.Icon(color=icon_map.get(row['type'],'gray'), icon='plus-sign', prefix='glyphicon')
                 ).add_to(cluster)
st_folium(m, width=800, height=500)

# 10) 앱 정보 Footer!
from pandas import Timestamp
uptime = Timestamp.now().strftime('%Y-%m-%d %H:%M:%S')
st.markdown(f"<div style='text-align:center; color:#888;'>🚀 Updated: {uptime}</div>", unsafe_allow_html=True)