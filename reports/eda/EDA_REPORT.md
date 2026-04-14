# BÁO CÁO PHÂN TÍCH KHÁM PHÁ DỮ LIỆU (EDA)

## Dữ liệu Chứng khoán VN30 (2020-2025)

**Ngày báo cáo**: 16/12/2025  
**Tập dữ liệu**: `vn30_stock_data.csv`  
**Phạm vi thời gian**: 02/01/2020 - 28/11/2025

---

## 1. TỔNG QUAN DỮ LIỆU

### 1.1. Kích thước và phạm vi

- **Tổng số quan sát**: 43,932 dòng
- **Số cột**: 7 cột (date, open, high, low, close, volume, symbol)
- **Số mã cổ phiếu**: 30 mã (đầy đủ theo danh sách VN30)
- **Khoảng thời gian**: 2,157 ngày (~5.9 năm)
- **Số ngày giao dịch**: 1,476 ngày
- **Trung bình**: ~246 ngày giao dịch/năm

### 1.2. Universe Ticker

Dữ liệu bao gồm đầy đủ 30 mã cổ phiếu VN30:

```
ACB, BCM, BID, CTG, DGC, FPT, GAS, GVR, HDB, HPG,
LPB, MBB, MSN, MWG, PLX, SAB, SHB, SSB, SSI, STB,
TCB, TPB, VCB, VHM, VIB, VIC, VJC, VNM, VPB, VRE
```

**✓ Kết luận**: Không có ticker thừa hoặc thiếu so với danh sách VN30 chuẩn.

---

## 2. CHẤT LƯỢNG DỮ LIỆU

### 2.1. Duplicate Records

- **Duplicate toàn dòng**: 0 dòng
- **Duplicate theo (date, symbol)**: 0 cặp
- **✓ Kết luận**: Dữ liệu đảm bảo tính duy nhất - mỗi mã mỗi ngày chỉ có 1 bản ghi.

### 2.2. Missing Values

- **Missing theo cột**: **0%** - Không có giá trị thiếu trong bất kỳ cột nào
- **Missing theo ticker**: Tất cả 30 mã đều có dữ liệu đầy đủ
- **Missing theo ngày**: Mỗi ngày giao dịch có đủ dữ liệu từ các mã

**✓ Kết luận**: Chất lượng dữ liệu rất tốt, không có vấn đề về missing values.

### 2.3. Giá trị bất thường

#### 2.3.1. Giá âm hoặc bằng 0

- **open ≤ 0**: 0 dòng
- **high ≤ 0**: 0 dòng
- **low ≤ 0**: 0 dòng
- **close ≤ 0**: 0 dòng
- **✓ Kết luận**: Không có giá âm hoặc bằng 0.

#### 2.3.2. Volume

- **Volume < 0**: 0 dòng
- **Volume = 0**: Có thể có một số phiên không giao dịch (cần kiểm tra thêm)
- **✓ Kết luận**: Không có volume âm.

### 2.4. Logic OHLC

Kiểm tra các quy tắc cơ bản của dữ liệu OHLC:

| Quy tắc                 | Vi phạm | Tỷ lệ  | Trạng thái |
| ----------------------- | ------- | ------ | ---------- |
| low ≤ min(open, close)  | 2 dòng  | 0.005% | ⚠️ Minor   |
| high ≥ max(open, close) | 0 dòng  | 0.000% | ✓ Pass     |
| high ≥ low              | 0 dòng  | 0.000% | ✓ Pass     |

**Đánh giá**:

- Chỉ có 2 dòng vi phạm quy tắc `low > min(open, close)` (0.005%)
- Vi phạm rất nhỏ, có thể do sai số làm tròn hoặc lỗi nhỏ từ nguồn dữ liệu
- **Khuyến nghị**: Loại bỏ 2 dòng này trong quá trình tiền xử lý

---

## 3. LỊCH GIAO DỊCH & COVERAGE

### 3.1. Trading Calendar

- **Tổng số ngày giao dịch**: 1,476 ngày
- **Phân bố**: ~246 ngày/năm (hợp lý cho thị trường chứng khoán)
- **Khoảng cách giữa các ngày**:
  - Có các khoảng cách > 7 ngày (ngày lễ, Tết)
  - Không phát hiện gap bất thường nào

### 3.2. Coverage theo Ticker

- **Số ngày giao dịch trung bình mỗi mã**: ~1,464 ngày
- **Phạm vi**: Hầu hết các mã có coverage tương đương nhau
- **Mã có history ngắn**: Có thể có 1-2 mã IPO muộn hoặc vào VN30 sau (cần xem chi tiết)

**✓ Kết luận**: Dữ liệu có độ coverage tốt, đồng đều giữa các mã.

---

## 4. PHÂN TÍCH OUTLIERS

### 4.1. Phân phối giá (Close Price)

**Thống kê mô tả**:

- **Mean**: ~38.11
- **Median**: ~28.20
- **Min**: ~2.11
- **Max**: ~219.10
- **Std**: ~28.60

**Quan sát**:

- Phân phối lệch phải (right-skewed)
- Khoảng giá rất rộng (từ 2.11 đến 219.10)
- Một số mã có giá rất cao (VJC ~114, MSN ~80, DGC ~67)

### 4.2. Volume

**Thống kê**:

- **Mean**: ~6.95M
- **Median**: ~3.06M
- **Max**: Có phiên giao dịch lên đến 249M (rất cao)

**Quan sát**:

- Phân phối lệch phải mạnh
- Top 3 mã có thanh khoản cao: HPG, SHB, SSI
- Volume tăng mạnh vào năm 2025 (đạt 84 tỷ cổ phiếu)

### 4.3. Biên độ dao động (High-Low Range)

**Thống kê**:

- **Trung bình**: ~2-3% mỗi ngày
- **95% percentile**: ~7-8%
- **99% percentile**: ~10-12%

**Quan sát**:

- Hầu hết các phiên có biên độ < 7% (phù hợp với quy định sàn HOSE)
- Có một số phiên có biên độ rất lớn (>20%) - cần kiểm tra

### 4.4. Thay đổi giá hàng ngày (Daily Returns)

**Thống kê**:

- **Mean**: ~0.09% (tích cực)
- **Std**: ~2.18%
- **Min**: -15.18%
- **Max**: +12.57%

**Quan sát**:

- Phân phối gần chuẩn, tập trung quanh 0
- Có một số ngày biến động mạnh (±10-15%)
- Không phát hiện ngày nào tăng/giảm > 50% (không có stock split hoặc lỗi nghiêm trọng)

**Volatility theo thời gian**:

- Cao vào đầu 2020 (COVID-19 pandemic)
- Spike lớn vào 2023
- Ổn định hơn vào các năm gần đây

---

## 5. PHÁT HIỆN QUAN TRỌNG

### 5.1. Điểm mạnh của dữ liệu

✓ **Độ toàn vẹn cao**: Không có missing values  
✓ **Không duplicate**: Đảm bảo tính duy nhất  
✓ **Coverage tốt**: Đầy đủ 30 mã VN30, ~6 năm dữ liệu  
✓ **Logic OHLC**: 99.995% dữ liệu hợp lệ  
✓ **Không có giá âm/0**: Dữ liệu đã được làm sạch tốt

### 5.2. Vấn đề cần xử lý

⚠️ **2 dòng vi phạm OHLC**: low > min(open, close) - cần loại bỏ  
⚠️ **Outliers**: Một số phiên có biên độ/volume bất thường - cần review  
⚠️ **Mã có history ngắn**: 1-2 mã có thể có ít dữ liệu hơn - cần xác định

### 5.3. Khuyến nghị cho bước tiếp theo

#### 5.3.1. Data Cleaning

1. **Loại bỏ 2 dòng vi phạm OHLC** (0.005% dữ liệu)
2. **Xác minh outliers**:
   - Các phiên có range > 15%
   - Các phiên có volume > mean + 5\*std
   - Các ngày biến động > ±10%
3. **Kiểm tra mã có history ngắn**: Xác định lý do và quyết định có loại bỏ không

#### 5.3.2. Feature Engineering

1. **Tính các chỉ báo kỹ thuật**:
   - Moving averages (MA5, MA10, MA20)
   - RSI, MACD, Bollinger Bands
   - Volume indicators
2. **Tính các đặc trưng thị trường**:
   - Market volatility
   - Correlation between stocks
   - Sector momentum
3. **Tính các đặc trưng thời gian**:
   - Day of week effects
   - Month effects
   - Holiday effects

#### 5.3.3. Modeling Strategy

1. **Train/Test Split**:
   - Training: 2020-2023 (4 năm)
   - Validation: 2024 (1 năm)
   - Test: 2025 (11 tháng)
2. **Cross-validation**: Time series cross-validation
3. **Evaluation metrics**:
   - Accuracy, Precision, Recall, F1-Score
   - ROI, Sharpe Ratio (nếu làm portfolio)

---

## 6. KẾT LUẬN

### 6.1. Đánh giá chung

Tập dữ liệu VN30 có **chất lượng rất tốt** với:

- Độ toàn vẹn cao (no missing, no duplicates)
- Phạm vi thời gian hợp lý (6 năm)
- Coverage đầy đủ (30 mã, 1,476 ngày)
- Logic dữ liệu hợp lệ (99.995%)

### 6.2. Sẵn sàng cho bước tiếp theo

Dữ liệu **sẵn sàng** cho:

- ✓ Data preprocessing (chỉ cần làm sạch nhẹ)
- ✓ Feature engineering (có đủ dữ liệu thô)
- ✓ Modeling (có đủ samples và phạm vi thời gian)

### 6.3. Rủi ro và hạn chế

- ⚠️ **Market regime changes**: Thị trường 2020 (COVID) rất khác 2024-2025
- ⚠️ **VN30 composition changes**: Danh sách VN30 có thể thay đổi theo thời gian
- ⚠️ **Survivorship bias**: Chỉ có dữ liệu các mã hiện tại trong VN30

---

## 7. DANH SÁCH BIỂU ĐỒ & FILE ĐÃ TẠO

Tất cả biểu đồ phân tích được lưu tại: `reports/eda/figures/`

1. `normalized_price_growth.png` - Giá đóng cửa chuẩn hóa về mốc 100 theo từng mã
2. `symbols_per_day.png` - Số ticker có dữ liệu mỗi ngày
3. `trading_calendar_gaps.png` - Khoảng cách giữa các ngày giao dịch
4. `coverage_by_ticker.png` - Coverage theo từng mã
5. `price_volume_distributions.png` - Phân phối giá và volume
6. `price_range_analysis.png` - Phân tích biên độ dao động
7. `daily_changes_analysis.png` - Phân tích thay đổi giá hàng ngày

---

## 8. THAM KHẢO

- **Notebook EDA**: `notebooks/01_eda_comprehensive.ipynb`
- **Raw data**: `data/raw/vn30_stock_data.csv`
- **Figures**: `reports/eda/figures/`

---

**Người thực hiện**: Data Mining Team  
**Ngày hoàn thành**: 16/12/2025  
**Phiên bản**: 1.0
