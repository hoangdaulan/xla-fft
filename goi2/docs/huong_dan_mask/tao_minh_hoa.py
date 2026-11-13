"""Render factual tutorial figures from the real demo and real GUI click handler."""
from pathlib import Path
import sys
import json
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Circle, FancyBboxPatch
from matplotlib.backend_bases import MouseEvent
from PIL import Image
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT))
from frequency_filter.pipeline import prepare,reconstruct,to_uint8,power_spectrum
from frequency_filter.__main__ import edit_mask
OUT=Path(__file__).resolve().parent
plt.rcParams.update({'font.family':'DejaVu Sans','font.size':12,'figure.facecolor':'#f4f7fb','axes.titleweight':'bold'})
a=np.asarray(Image.open(ROOT/'results/demo/noisy.png').convert('L'),dtype=float)
p=prepare(a,padding='none')
s=np.log1p(power_spectrum(p.spectrum))
h=np.ones(a.shape)
# Exercise the same handler as the interactive window, at (column=53,row=47).
original_show=plt.show
capture={}
def simulated_show():
 fig=plt.gcf();ax=fig.axes[0];fig.canvas.draw()
 px,py=ax.transData.transform((53,47))
 event=MouseEvent('button_press_event',fig.canvas,px,py,button=1)
 fig.canvas.callbacks.process('button_press_event',event)
 fig.canvas.draw()
 capture['fig']=fig
plt.show=simulated_show
h=edit_mask(p.spectrum,h,3,'reject')
plt.show=original_show
assert h[47,53]==0 and h[81,75]==0 and h[64,64]==1
result,imaginary=reconstruct(p,h)
plt.close('all')

def save(fig,num):
 fig.savefig(OUT/f'buoc_{num}.png',dpi=145,bbox_inches='tight',facecolor=fig.get_facecolor())
 plt.close(fig)
def title(fig,t,sub):
 fig.suptitle(t,x=.05,ha='left',fontsize=19,color='#162c46',y=.98)
 fig.text(.05,.90,sub,fontsize=11,color='#40566e')
def image(ax,data,t='',vmin=None,vmax=None):
 ax.imshow(data,cmap='gray',vmin=vmin,vmax=vmax);ax.set_title(t,pad=12);ax.axis('off')
def note(ax,text,xy,xytext,color='#06a5ad'):
 ax.annotate(text,xy=xy,xytext=xytext,color=color,fontsize=11,fontweight='bold',
 bbox=dict(boxstyle='round,pad=.4',fc='white',ec=color,alpha=.97),
 arrowprops=dict(arrowstyle='->',color=color,lw=2))
# 1
fig,axs=plt.subplots(1,2,figsize=(10,5));fig.subplots_adjust(top=.79,bottom=.12,wspace=.35)
title(fig,'Bước 1 · Nạp ảnh có nhiễu','Chương trình đọc ảnh mức xám 128 × 128; lệnh demo dùng --padding none.')
image(axs[0],a,'Ảnh đầu vào: noisy.png',0,255)
axs[1].axis('off');axs[1].text(0,.78,'Các vệt sọc chéo lặp lại\nlà nhiễu sin tổng hợp.',fontsize=16,color='#162c46',linespacing=1.6)
axs[1].text(0,.34,'FFT 2D sẽ đưa ảnh này\nsang miền tần số.\nBạn chưa cần click ở bước này.',fontsize=13,color='#40566e',linespacing=1.6)
save(fig,1)
# 2
fig,ax=plt.subplots(figsize=(9,6));fig.subplots_adjust(top=.80,bottom=.08,left=.12,right=.88)
title(fig,'Bước 2 · Đọc phổ Fourier','Phổ công suất lấy log: điểm sáng biểu thị thành phần tần số có năng lượng mạnh.')
image(ax,s,'Phổ đã dịch tâm')
note(ax,'Tâm DC\nGiữ nguyên',(64,64),(82,45),'#d68a00')
note(ax,'Đỉnh nhiễu 1',(53,47),(2,15))
note(ax,'Đỉnh nhiễu 2',(75,81),(2,110))
save(fig,2)
# 3 — same overlay as edit_mask (Reds alpha .3)
fig,ax=plt.subplots(figsize=(9,6));fig.subplots_adjust(top=.80,bottom=.08,left=.12,right=.88)
title(fig,'Bước 3 · Click vào một đỉnh nhiễu','Ví dụ click ở cột 53, hàng 47; tọa độ tần số tương ứng (u,v) = (−17,−11).')
ax.imshow(s,cmap='gray');ax.imshow(np.ones(a.shape),cmap='Reds',alpha=.3,vmin=0,vmax=1);ax.axis('off')
ax.add_patch(Circle((53,47),3,fill=False,color='#10dfec',lw=2))
note(ax,'CLICK TẠI ĐÂY\nBán kính chặn: 3 pixel',(53,47),(0,17))
note(ax,'Không click tâm phổ',(64,64),(77,110),'#e99d23')
save(fig,3)
#4
fig,axs=plt.subplots(1,2,figsize=(11,6));fig.subplots_adjust(top=.79,bottom=.16,wspace=.3)
title(fig,'Bước 4 · Tự thêm vùng chặn đối xứng','Chỉ một click tạo hai vùng chặn. Mask H=0 ở vùng đen; H=1 ở vùng trắng.')
axs[0].imshow(s,cmap='gray');axs[0].imshow(h,cmap='Reds',alpha=.3,vmin=0,vmax=1)
axs[0].set_title('Phổ với lớp mask như giao diện');axs[0].axis('off')
for xy in [(53,47),(75,81)]:axs[0].add_patch(Circle(xy,4,fill=False,color='#15d8e5',lw=2))
image(axs[1],h,'Mask: hai đĩa đen, tâm vẫn trắng',0,1)
fig.text(.08,.065,'Cặp đối xứng giữ tính đối xứng liên hợp → ảnh sau IFFT vẫn là ảnh thực.',fontsize=12,color='#40566e')
save(fig,4)
#5
fig=plt.figure(figsize=(11,5));title(fig,'Bước 5 · Đóng cửa sổ phổ để áp dụng','Đóng cửa sổ chọn mask là tín hiệu hoàn tất lựa chọn; chương trình tiếp tục chạy.')
for x,data,heading in [(.05,s,'Phổ F'),(.37,h,'Mask H'),(.69,result,'Ảnh sau IFFT')]:
 ax=fig.add_axes([x,.24,.24,.48]);image(ax,data,heading)
fig.text(.315,.47,'×',fontsize=30,color='#0b939d');fig.text(.63,.47,'→',fontsize=30,color='#0b939d')
fig.text(.07,.09,'Bên trong chương trình: G = H × F  →  dịch phổ về vị trí ban đầu  →  IFFT.',fontsize=12,color='#40566e')
save(fig,5)
#6
fig,axs=plt.subplots(1,4,figsize=(13,5));fig.subplots_adjust(top=.76,bottom=.23,wspace=.18)
title(fig,'Bước 6 · So sánh kết quả ở cửa sổ tiếp theo','Có --show thì xuất hiện bốn ô theo đúng thứ tự bên dưới.')
for ax,data,heading in zip(axs,[a,s,h,result],['Input · Ảnh vào','Log power · Phổ','Transfer H · Mask','Output · Sau lọc']):image(ax,data,heading)
fig.text(.06,.105,'So sánh Input và Output: sọc giảm rõ trong demo; kiểm tra thêm chi tiết ảnh khi dùng ảnh thật.',fontsize=12,color='#40566e')
fig.text(.06,.045,'Log power ở đây là phổ ảnh đầu vào, không phải phổ đã lọc.',fontsize=11,color='#40566e')
save(fig,6)
#7
fig=plt.figure(figsize=(11,5));title(fig,'Bước 7 · Xem các file đã lưu','Thư mục đích theo lệnh ví dụ: goi2/results/mask_hand/')
ax=fig.add_axes([.05,.12,.9,.68]);ax.axis('off')
rows=[('filtered.png','Ảnh kết quả: mở để xem hoặc tính metric'),('mask.png','Mask trắng/đen: xem những vùng đã chặn'),('mask.npy','Mask số thực: nạp lại để dùng đúng cấu hình'),('spectrum.png','Ảnh phổ log: xem vị trí đỉnh tần số'),('config.json','Ghi lại tham số, kích thước và sai số phần ảo')]
for i,(name,meaning) in enumerate(rows):
 y=.91-i*.18
 ax.add_patch(FancyBboxPatch((0,y-.11),1,.14,boxstyle='round,pad=.01',facecolor='white',edgecolor='#d9e3ef'))
 ax.text(.025,y-.045,name,fontfamily='DejaVu Sans Mono',fontsize=13,color='#007d89',va='center')
 ax.text(.31,y-.045,meaning,fontsize=12,color='#243e59',va='center')
save(fig,7)
np.save(OUT/'mask_minh_hoa.npy',h)
Image.fromarray(to_uint8(result)).save(OUT/'ket_qua_click.png')
(OUT/'kiem_chung.json').write_text(json.dumps({'click_col_row':[53,47],'frequency_u_v':[-17,-11],
 'conjugate_col_row':[75,81],'radius':3,'imaginary_residual':imaginary,
 'method':'Actual edit_mask MouseEvent handler; illustrative figures, not OS screenshots'},indent=2))
print('Rendered 7 figures; real click handler checked.')
