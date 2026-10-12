"""用 cartopy 画出矢量文件（.shp）的范围边界"""
import matplotlib.pyplot as plt
import matplotlib
matplotlib.rc('font', family='Microsoft YaHei')  # 支持中文
import cartopy.crs as ccrs
import cartopy.feature as cfeature
import shapefile
from shapely.geometry import shape as shapely_shape

shp_path = r'C:\Users\yuhao\Desktop\新建文件夹\cnmap.shp'
# ============================================

# 读取 shapefile
sf = shapefile.Reader(shp_path)
shapes = sf.shapes()
print(f"共读取 {len(shapes)} 个几何图形")

# 转为 shapely 几何对象
geometries = [shapely_shape(s.__geo_interface__) for s in shapes]

# 创建地图
fig = plt.figure(figsize=(12, 8))
ax = fig.add_subplot(1, 1, 1, projection=ccrs.PlateCarree())

# 添加地理底图
ax.add_feature(cfeature.LAND, facecolor='lightgray')
ax.add_feature(cfeature.OCEAN, facecolor='lightblue')
ax.add_feature(cfeature.COASTLINE, linewidth=0.5)
ax.add_feature(cfeature.BORDERS, linewidth=0.5, linestyle=':')
ax.add_feature(cfeature.LAKES, alpha=0.5)

# 绘制 shapefile 边界
ax.add_geometries(geometries, crs=ccrs.PlateCarree(),
                  facecolor='none', edgecolor='red', linewidth=0.8)

# 自动缩放至数据范围
ax.autoscale_view()

# 网格线
gl = ax.gridlines(draw_labels=True, linestyle='--', alpha=0.3, color='gray')
gl.top_labels = False
gl.right_labels = False

plt.title('Shapefile 范围', fontsize=14)
plt.tight_layout()
plt.show()
