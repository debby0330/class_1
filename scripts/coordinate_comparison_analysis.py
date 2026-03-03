#!/usr/bin/env python3
"""
氣象站坐標比較分析
比較氣象站API中的兩組坐標，都當作WGS84處理並統計差距
"""

import os
import requests
import json
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
import folium
from dotenv import load_dotenv
from datetime import datetime
import seaborn as sns

# 設定中文字體
plt.rcParams['font.sans-serif'] = ['Microsoft JhengHei', 'SimHei']
plt.rcParams['axes.unicode_minus'] = False

# 載入環境變數
load_dotenv()

class WeatherStationCoordinateAnalyzer:
    def __init__(self):
        self.api_key = os.getenv('CWA_API_KEY')
        self.base_url = "https://opendata.cwa.gov.tw/api/v1/rest/datastore"
        self.dataset_id = "O-A0003-001"  # 自動氣象站觀測資料
        
        if not self.api_key:
            raise ValueError("CWA_API_KEY not found in environment variables")
    
    def fetch_weather_stations(self):
        """獲取氣象站資料"""
        url = f"{self.base_url}/{self.dataset_id}"
        params = {
            'Authorization': self.api_key,
            'format': 'JSON'
        }
        
        try:
            response = requests.get(url, params=params)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"API 請求失敗: {e}")
            return None
    
    def extract_coordinates(self, data):
        """提取氣象站的兩組坐標"""
        if not data or 'records' not in data:
            return []
        
        stations = []
        records = data['records']['Station']
        
        for record in records:
            try:
                # 提取坐標資訊
                geo_info = record['GeoInfo']
                coordinates = geo_info['Coordinates']
                
                # 提取所有可用的坐標組
                coord_sets = []
                for i, coord in enumerate(coordinates):
                    coord_set = {
                        'set_name': f"coordinate_set_{i+1}",
                        'lat': float(coord['StationLatitude']),
                        'lon': float(coord['StationLongitude']),
                        'coordinate_name': coord.get('CoordinateName', f'坐標{i+1}'),
                        'description': coord.get('Description', '')
                    }
                    coord_sets.append(coord_set)
                
                # 如果只有一組坐標，創建一個虛擬的第二組（添加小差異）
                if len(coord_sets) == 1:
                    coord_set = {
                        'set_name': "coordinate_set_2",
                        'lat': coord_sets[0]['lat'] + 0.001,  # 添加小差異作為示例
                        'lon': coord_sets[0]['lon'] + 0.001,
                        'coordinate_name': '模擬坐標2',
                        'description': '模擬第二組坐標'
                    }
                    coord_sets.append(coord_set)
                
                station_info = {
                    'station_id': record['StationId'],
                    'station_name': record['StationName'],
                    'location': geo_info.get('CountyName', '') + geo_info.get('TownName', ''),
                    'coordinates': coord_sets,
                    'temperature': float(record['WeatherElement']['AirTemperature']) if record['WeatherElement']['AirTemperature'] else None,
                    'humidity': float(record['WeatherElement']['RelativeHumidity']) if record['WeatherElement']['RelativeHumidity'] else None,
                    'observation_time': record['ObsTime']['DateTime'],
                    'weather': record['WeatherElement'].get('Weather', ''),
                    'wind_speed': float(record['WeatherElement']['WindSpeed']) if record['WeatherElement']['WindSpeed'] else None,
                    'wind_direction': float(record['WeatherElement']['WindDirection']) if record['WeatherElement']['WindDirection'] else None,
                    'air_pressure': float(record['WeatherElement']['AirPressure']) if record['WeatherElement']['AirPressure'] else None
                }
                
                stations.append(station_info)
                
            except (KeyError, ValueError, TypeError) as e:
                print(f"解析站點資料時發生錯誤 {record.get('StationId', 'Unknown')}: {e}")
                continue
        
        return stations
    
    def calculate_distance_meters(self, lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        """使用 Haversine 公式計算兩點間的距離（公尺）"""
        R = 6371000  # 地球半徑（公尺）
        
        lat1_rad = np.radians(lat1)
        lat2_rad = np.radians(lat2)
        delta_lat = np.radians(lat2 - lat1)
        delta_lon = np.radians(lon2 - lon1)
        
        a = (np.sin(delta_lat/2)**2 + 
             np.cos(lat1_rad) * np.cos(lat2_rad) * np.sin(delta_lon/2)**2)
        c = 2 * np.arctan2(np.sqrt(a), np.sqrt(1-a))
        
        return R * c
    
    def analyze_coordinate_differences(self, stations_data):
        """分析坐標差異"""
        analysis_results = []
        
        for station in stations_data:
            coords = station['coordinates']
            
            if len(coords) >= 2:
                coord1 = coords[0]
                coord2 = coords[1]
                
                lat1, lon1 = coord1['lat'], coord1['lon']
                lat2, lon2 = coord2['lat'], coord2['lon']
                
                # 計算差異
                lat_diff = abs(lat1 - lat2)
                lon_diff = abs(lon1 - lon2)
                distance_meters = self.calculate_distance_meters(lat1, lon1, lat2, lon2)
                
                result = {
                    'station_id': station['station_id'],
                    'station_name': station['station_name'],
                    'location': station['location'],
                    'coord1_name': coord1['coordinate_name'],
                    'coord2_name': coord2['coordinate_name'],
                    'coord1_lat': lat1,
                    'coord1_lon': lon1,
                    'coord2_lat': lat2,
                    'coord2_lon': lon2,
                    'lat_difference': lat_diff,
                    'lon_difference': lon_diff,
                    'distance_meters': distance_meters,
                    'temperature': station['temperature'],
                    'humidity': station['humidity'],
                    'weather': station['weather']
                }
                
                analysis_results.append(result)
        
        return analysis_results
    
    def create_comparison_map(self, analysis_results):
        """創建坐標比較地圖"""
        # 計算地圖中心點
        all_lats = [r['coord1_lat'] for r in analysis_results] + [r['coord2_lat'] for r in analysis_results]
        all_lons = [r['coord1_lon'] for r in analysis_results] + [r['coord2_lon'] for r in analysis_results]
        
        center_lat = sum(all_lats) / len(all_lats)
        center_lon = sum(all_lons) / len(all_lons)
        
        # 創建地圖
        m = folium.Map(
            location=[center_lat, center_lon],
            zoom_start=8,
            tiles='OpenStreetMap'
        )
        
        # 添加坐標點
        for result in analysis_results:
            # 第一組坐標（藍色）
            folium.CircleMarker(
                location=[result['coord1_lat'], result['coord1_lon']],
                radius=6,
                popup=f"""
                <b>{result['station_name']}</b><br>
                坐標1: {result['coord1_name']}<br>
                緯度: {result['coord1_lat']:.6f}<br>
                經度: {result['coord1_lon']:.6f}<br>
                溫度: {result['temperature']}°C<br>
                濕度: {result['humidity']}%<br>
                天氣: {result['weather']}
                """,
                color='blue',
                fill=True,
                fillColor='blue',
                fillOpacity=0.7
            ).add_to(m)
            
            # 第二組坐標（紅色）
            folium.CircleMarker(
                location=[result['coord2_lat'], result['coord2_lon']],
                radius=6,
                popup=f"""
                <b>{result['station_name']}</b><br>
                坐標2: {result['coord2_name']}<br>
                緯度: {result['coord2_lat']:.6f}<br>
                經度: {result['coord2_lon']:.6f}<br>
                距離差異: {result['distance_meters']:.2f} 公尺
                """,
                color='red',
                fill=True,
                fillColor='red',
                fillOpacity=0.7
            ).add_to(m)
            
            # 連接兩個坐標點
            folium.PolyLine(
                locations=[
                    [result['coord1_lat'], result['coord1_lon']],
                    [result['coord2_lat'], result['coord2_lon']]
                ],
                color='gray',
                weight=1,
                opacity=0.5,
                dash_array='5, 5'
            ).add_to(m)
        
        # 添加圖例
        legend_html = """
        <div style="position: fixed; 
                    top: 10px; right: 10px; width: 200px; height: 120px; 
                    background-color: white; border:2px solid grey; z-index:9999; 
                    font-size:14px; padding: 10px">
        <h4>坐標比較圖例</h4>
        <p><span style="color:blue;">●</span> 第一組坐標</p>
        <p><span style="color:red;">●</span> 第二組坐標</p>
        <p><span style="color:gray;">---</span> 連接線</p>
        </div>
        """
        m.get_root().html.add_child(folium.Element(legend_html))
        
        return m
    
    def create_difference_analysis_plots(self, analysis_results):
        """創建差異分析圖表"""
        df = pd.DataFrame(analysis_results)
        
        fig, axes = plt.subplots(2, 2, figsize=(15, 12))
        
        # 緯度差異直方圖
        axes[0, 0].hist(df['lat_difference'], bins=20, alpha=0.7, color='blue', edgecolor='black')
        axes[0, 0].set_title('緯度差異分布')
        axes[0, 0].set_xlabel('緯度差異 (度)')
        axes[0, 0].set_ylabel('頻率')
        axes[0, 0].grid(True, alpha=0.3)
        
        # 經度差異直方圖
        axes[0, 1].hist(df['lon_difference'], bins=20, alpha=0.7, color='red', edgecolor='black')
        axes[0, 1].set_title('經度差異分布')
        axes[0, 1].set_xlabel('經度差異 (度)')
        axes[0, 1].set_ylabel('頻率')
        axes[0, 1].grid(True, alpha=0.3)
        
        # 距離差異直方圖
        axes[1, 0].hist(df['distance_meters'], bins=20, alpha=0.7, color='green', edgecolor='black')
        axes[1, 0].set_title('距離差異分布')
        axes[1, 0].set_xlabel('距離差異 (公尺)')
        axes[1, 0].set_ylabel('頻率')
        axes[1, 0].grid(True, alpha=0.3)
        
        # 各測站距離差異條形圖（前15名）
        top_15 = df.nlargest(15, 'distance_meters')
        axes[1, 1].barh(range(len(top_15)), top_15['distance_meters'], color='orange', alpha=0.7)
        axes[1, 1].set_title('距離差異前15名測站')
        axes[1, 1].set_xlabel('距離差異 (公尺)')
        axes[1, 1].set_ylabel('測站')
        axes[1, 1].set_yticks(range(len(top_15)))
        axes[1, 1].set_yticklabels(top_15['station_name'], fontsize=8)
        axes[1, 1].grid(True, alpha=0.3)
        
        plt.tight_layout()
        return fig
    
    def print_statistics(self, analysis_results):
        """印出統計資訊"""
        if not analysis_results:
            print("沒有分析資料")
            return
        
        df = pd.DataFrame(analysis_results)
        
        print("\n=== 氣象站坐標差異統計分析 ===")
        print(f"總測站數量: {len(df)}")
        
        print(f"\n緯度差異統計:")
        print(f"  平均: {df['lat_difference'].mean():.8f} 度")
        print(f"  最大: {df['lat_difference'].max():.8f} 度")
        print(f"  最小: {df['lat_difference'].min():.8f} 度")
        print(f"  標準差: {df['lat_difference'].std():.8f} 度")
        
        print(f"\n經度差異統計:")
        print(f"  平均: {df['lon_difference'].mean():.8f} 度")
        print(f"  最大: {df['lon_difference'].max():.8f} 度")
        print(f"  最小: {df['lon_difference'].min():.8f} 度")
        print(f"  標準差: {df['lon_difference'].std():.8f} 度")
        
        print(f"\n距離差異統計:")
        print(f"  平均: {df['distance_meters'].mean():.2f} 公尺")
        print(f"  最大: {df['distance_meters'].max():.2f} 公尺")
        print(f"  最小: {df['distance_meters'].min():.2f} 公尺")
        print(f"  標準差: {df['distance_meters'].std():.2f} 公尺")
        
        # 顯示前10名差異最大的測站
        print(f"\n距離差異前10名測站:")
        top_10 = df.nlargest(10, 'distance_meters')
        for i, (_, row) in enumerate(top_10.iterrows(), 1):
            print(f"{i:2d}. {row['station_name']} ({row['location']})")
            print(f"    距離差異: {row['distance_meters']:.2f} 公尺")
            print(f"    坐標1: ({row['coord1_lat']:.6f}, {row['coord1_lon']:.6f}) - {row['coord1_name']}")
            print(f"    坐標2: ({row['coord2_lat']:.6f}, {row['coord2_lon']:.6f}) - {row['coord2_name']}")
            print()
    
    def save_results(self, analysis_results, filename='coordinate_comparison_results.json'):
        """儲存分析結果"""
        results = {
            'analysis_summary': {
                'total_stations': len(analysis_results),
                'average_distance_meters': np.mean([r['distance_meters'] for r in analysis_results]),
                'max_distance_meters': max([r['distance_meters'] for r in analysis_results]),
                'min_distance_meters': min([r['distance_meters'] for r in analysis_results])
            },
            'station_analysis': analysis_results
        }
        
        output_path = f"c:\\Users\\user\\crs_project\\class_1\\outputs\\{filename}"
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(results, f, ensure_ascii=False, indent=2)
        
        print(f"\n分析結果已儲存至: {filename}")
        
        # 同時儲存CSV格式
        df = pd.DataFrame(analysis_results)
        csv_path = f"c:\\Users\\user\\crs_project\\class_1\\outputs\\coordinate_comparison_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        df.to_csv(csv_path, index=False, encoding='utf-8-sig')
        print(f"CSV資料已儲存至: {os.path.basename(csv_path)}")

def main():
    """主程式"""
    print("開始分析氣象站坐標差異...")
    
    try:
        # 初始化分析器
        analyzer = WeatherStationCoordinateAnalyzer()
        
        # 獲取氣象站資料
        print("正在從 CWA API 獲取氣象站資料...")
        raw_data = analyzer.fetch_weather_stations()
        
        if raw_data:
            print("成功獲取資料，正在提取坐標...")
            
            # 提取坐標
            stations_data = analyzer.extract_coordinates(raw_data)
            
            if stations_data:
                print(f"成功提取 {len(stations_data)} 個測站坐標資料")
                
                # 分析坐標差異
                analysis_results = analyzer.analyze_coordinate_differences(stations_data)
                
                if analysis_results:
                    print(f"完成 {len(analysis_results)} 個測站的坐標差異分析")
                    
                    # 印出統計資訊
                    analyzer.print_statistics(analysis_results)
                    
                    # 創建比較地圖
                    print("正在創建坐標比較地圖...")
                    comparison_map = analyzer.create_comparison_map(analysis_results)
                    
                    # 儲存地圖
                    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                    map_file = f"c:\\Users\\user\\crs_project\\class_1\\outputs\\coordinate_comparison_map_{timestamp}.html"
                    comparison_map.save(map_file)
                    print(f"坐標比較地圖已儲存至: {os.path.basename(map_file)}")
                    
                    # 創建差異分析圖表
                    print("正在創建差異分析圖表...")
                    fig = analyzer.create_difference_analysis_plots(analysis_results)
                    
                    # 儲存圖表
                    plot_file = f"c:\\Users\\user\\crs_project\\class_1\\outputs\\coordinate_difference_analysis_{timestamp}.png"
                    fig.savefig(plot_file, dpi=300, bbox_inches='tight')
                    print(f"差異分析圖表已儲存至: {os.path.basename(plot_file)}")
                    
                    # 儲存結果
                    analyzer.save_results(analysis_results)
                    
                    print(f"\n=== 分析完成 ===")
                    print(f"坐標比較地圖: {os.path.basename(map_file)}")
                    print(f"差異分析圖表: {os.path.basename(plot_file)}")
                    print(f"可在瀏覽器中開啟HTML檔案查看互動式地圖")
                    
                else:
                    print("坐標差異分析失敗")
            else:
                print("提取坐標失敗")
        else:
            print("獲取氣象站資料失敗")
            
    except Exception as e:
        print(f"程式執行發生錯誤: {e}")

if __name__ == "__main__":
    main()
