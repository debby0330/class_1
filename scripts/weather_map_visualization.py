#!/usr/bin/env python3
"""
氣象站地圖視覺化腳本
使用 folium 在地圖上標示測站位置，依氣溫進行分色顯示
"""

import pandas as pd
import folium
from folium.plugins import HeatMap
import branca.colormap as cm
import os
from datetime import datetime

class WeatherMapVisualizer:
    def __init__(self):
        self.temperature_colors = {
            'cold': '#0000FF',      # 藍色 - 氣溫 < 20°C
            'normal': '#00FF00',    # 綠色 - 20°C ≤ 氣溫 ≤ 28°C  
            'hot': '#FFA500'        # 橘色 - 氣溫 > 28°C
        }
    
    def get_temperature_color(self, temperature):
        """根據氣溫回傳對應顏色"""
        if temperature is None:
            return '#808080'  # 灰色 - 無資料
        
        if temperature < 20:
            return self.temperature_colors['cold']
        elif temperature <= 28:
            return self.temperature_colors['normal']
        else:
            return self.temperature_colors['hot']
    
    def create_popup_content(self, station_data):
        """建立彈出視窗內容"""
        temp = station_data['temperature']
        humidity = station_data['humidity']
        weather = station_data['weather']
        wind_speed = station_data['wind_speed']
        wind_direction = station_data['wind_direction']
        air_pressure = station_data['air_pressure']
        obs_time = station_data['observation_time']
        
        # 格式化觀測時間
        try:
            formatted_time = pd.to_datetime(obs_time).strftime('%Y-%m-%d %H:%M')
        except:
            formatted_time = obs_time
        
        popup_html = f"""
        <div style="font-family: Arial, sans-serif; width: 250px;">
            <h4 style="margin: 0 0 10px 0; color: #333;">{station_data['station_name']}</h4>
            <p style="margin: 5px 0;"><strong>地點:</strong> {station_data['location']}</p>
            <p style="margin: 5px 0;"><strong>溫度:</strong> <span style="font-size: 16px; font-weight: bold; color: {self.get_temperature_color(temp)};">{temp}°C</span></p>
            <p style="margin: 5px 0;"><strong>濕度:</strong> {humidity}%</p>
            <p style="margin: 5px 0;"><strong>天氣:</strong> {weather}</p>
            <p style="margin: 5px 0;"><strong>風速:</strong> {wind_speed} m/s</p>
            <p style="margin: 5px 0;"><strong>風向:</strong> {wind_direction}°</p>
            <p style="margin: 5px 0;"><strong>氣壓:</strong> {air_pressure} hPa</p>
            <p style="margin: 5px 0; font-size: 12px; color: #666;"><strong>觀測時間:</strong> {formatted_time}</p>
        </div>
        """
        
        return popup_html
    
    def create_weather_map(self, csv_file, output_file=None):
        """建立氣象地圖"""
        # 讀取 CSV 資料
        try:
            df = pd.read_csv(csv_file)
            print(f"成功讀取 {len(df)} 筆測站資料")
        except Exception as e:
            print(f"讀取 CSV 檔案失敗: {e}")
            return None
        
        # 過濾有效座標資料
        valid_df = df.dropna(subset=['latitude', 'longitude'])
        print(f"有效座標資料: {len(valid_df)} 筆")
        
        if len(valid_df) == 0:
            print("沒有有效的座標資料")
            return None
        
        # 計算地圖中心點（台灣中心）
        center_lat = valid_df['latitude'].mean()
        center_lon = valid_df['longitude'].mean()
        
        # 建立地圖
        m = folium.Map(
            location=[center_lat, center_lon],
            zoom_start=7,
            tiles='OpenStreetMap'
        )
        
        # 加入溫度色階圖例
        colormap = cm.LinearColormap(
            colors=['#0000FF', '#00FF00', '#FFA500'],
            vmin=0,
            vmax=35,
            caption='氣溫 (°C)'
        )
        colormap.add_to(m)
        
        # 統計資料
        temp_stats = {
            'cold': 0,
            'normal': 0, 
            'hot': 0,
            'no_data': 0
        }
        
        # 為每個測站加入標記
        for idx, row in valid_df.iterrows():
            temp = row['temperature']
            
            # 判斷溫度範圍
            if pd.isna(temp):
                color = '#808080'  # 灰色
                temp_stats['no_data'] += 1
            elif temp < 20:
                color = self.temperature_colors['cold']
                temp_stats['cold'] += 1
            elif temp <= 28:
                color = self.temperature_colors['normal']
                temp_stats['normal'] += 1
            else:
                color = self.temperature_colors['hot']
                temp_stats['hot'] += 1
            
            # 建立自定義圖標
            icon = folium.CircleMarker(
                location=[row['latitude'], row['longitude']],
                radius=8,
                popup=folium.Popup(self.create_popup_content(row), max_width=300),
                color='black',
                weight=1,
                fillColor=color,
                fillOpacity=0.8
            )
            
            icon.add_to(m)
        
        # 加入統計資訊
        stats_html = f"""
        <div style="position: fixed; 
                    bottom: 50px; left: 50px; width: 200px; height: 120px; 
                    background-color: white; border:2px solid grey; z-index:9999; 
                    font-size:14px; padding: 10px">
        <h4 style="margin: 0 0 10px 0;">氣溫分佈統計</h4>
        <p style="margin: 5px 0;"><span style="color: #0000FF;">●</span> 低溫 (&lt;20°C): {temp_stats['cold']}</p>
        <p style="margin: 5px 0;"><span style="color: #00FF00;">●</span> 適中 (20-28°C): {temp_stats['normal']}</p>
        <p style="margin: 5px 0;"><span style="color: #FFA500;">●</span> 高溫 (&gt;28°C): {temp_stats['hot']}</p>
        <p style="margin: 5px 0;"><span style="color: #808080;">●</span> 無資料: {temp_stats['no_data']}</p>
        </div>
        """
        
        m.get_root().html.add_child(folium.Element(stats_html))
        
        # 儲存地圖
        if output_file is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_file = f"c:\\Users\\user\\crs_project\\class_1\\outputs\\weather_map_{timestamp}.html"
        
        m.save(output_file)
        print(f"地圖已儲存至: {output_file}")
        
        # 顯示統計資訊
        print(f"\n=== 氣溫分佈統計 ===")
        print(f"低溫測站 (<20°C): {temp_stats['cold']}")
        print(f"適中測站 (20-28°C): {temp_stats['normal']}")
        print(f"高溫測站 (>28°C): {temp_stats['hot']}")
        print(f"無資料測站: {temp_stats['no_data']}")
        
        return output_file
    
    def create_heatmap(self, csv_file, output_file=None):
        """建立溫度熱力圖"""
        try:
            df = pd.read_csv(csv_file)
            print(f"成功讀取 {len(df)} 筆測站資料")
        except Exception as e:
            print(f"讀取 CSV 檔案失敗: {e}")
            return None
        
        # 過濾有效溫度和座標資料
        valid_df = df.dropna(subset=['latitude', 'longitude', 'temperature'])
        print(f"有效溫度資料: {len(valid_df)} 筆")
        
        if len(valid_df) == 0:
            print("沒有有效的溫度資料")
            return None
        
        # 計算地圖中心點
        center_lat = valid_df['latitude'].mean()
        center_lon = valid_df['longitude'].mean()
        
        # 建立地圖
        m = folium.Map(
            location=[center_lat, center_lon],
            zoom_start=7,
            tiles='OpenStreetMap'
        )
        
        # 準備熱力圖資料
        heat_data = [[row['latitude'], row['longitude'], row['temperature']] 
                    for idx, row in valid_df.iterrows()]
        
        # 加入熱力圖
        HeatMap(
            heat_data,
            min_opacity=0.4,
            radius=15,
            blur=10,
            gradient={0.0: 'blue', 0.3: 'cyan', 0.5: 'lime', 0.7: 'yellow', 1.0: 'red'}
        ).add_to(m)
        
        # 儲存熱力圖
        if output_file is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_file = f"c:\\Users\\user\\crs_project\\class_1\\outputs\\weather_heatmap_{timestamp}.html"
        
        m.save(output_file)
        print(f"熱力圖已儲存至: {output_file}")
        
        return output_file

def main():
    """主程式"""
    # 查找最新的 CSV 檔案
    output_dir = "c:\\Users\\user\\crs_project\\class_1\\outputs"
    csv_files = [f for f in os.listdir(output_dir) if f.startswith('weather_stations_') and f.endswith('.csv')]
    
    if not csv_files:
        print("找不到氣象站 CSV 資料檔，請先執行 cwa_weather_api.py")
        return
    
    # 使用最新的檔案
    latest_csv = max(csv_files, key=lambda x: os.path.getmtime(os.path.join(output_dir, x)))
    csv_path = os.path.join(output_dir, latest_csv)
    print(f"使用資料檔案: {csv_path}")
    
    # 建立視覺化器
    visualizer = WeatherMapVisualizer()
    
    # 建立氣象地圖
    print("\n正在建立氣象地圖...")
    map_file = visualizer.create_weather_map(csv_path)
    
    # 建立熱力圖
    print("\n正在建立溫度熱力圖...")
    heatmap_file = visualizer.create_heatmap(csv_path)
    
    if map_file and heatmap_file:
        print(f"\n=== 地圖檔案 ===")
        print(f"氣象地圖: {map_file}")
        print(f"溫度熱力圖: {heatmap_file}")
        print("\n可以在瀏覽器中開啟 HTML 檔案查看地圖")

if __name__ == "__main__":
    main()
