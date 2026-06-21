# LapoAnalytics - Laptop Price Comparison Analytics

LapoAnalytics là project crawl và phân tích giá laptop từ nhiều website bán lẻ, hiện hỗ trợ:

- Phong Vũ
- GearVN
- CellphoneS

Project có 3 phần chính:

1. **Crawler**: lấy dữ liệu laptop theo hãng.
2. **Database PostgreSQL**: lưu raw data, bảng so sánh giá, user và sản phẩm yêu thích.
3. **FastAPI Web App**: trang chủ, danh sách sản phẩm, dashboard sản phẩm, login/register và favorites.

---

## 1. Cấu trúc thư mục

```text
.
├── app/
│   ├── crawlers/
│   │   ├── cellphones.py
│   │   ├── gearvn.py
│   │   └── phongvu.py
│   │
│   ├── pipeline/
│   │   ├── merge_daily.py
│   │   └── run_daily.py
│   │
│   ├── db/
│   │   ├── database.py
│   │   └── schema.sql
│   │
│   └── web/
│       ├── web_app.py
│       ├── templates/
│       └── static/
│
├── data/
│   └── output/
│
├── docs/
│   └── webdesign/
│
├── web_app.py
├── run_daily.py
├── database.py
├── requirements.txt
├── .env.example
└── README.md
```

Các file `web_app.py`, `run_daily.py`, `database.py` ở thư mục gốc là wrapper để chạy lệnh dễ hơn.

---

## 2. Yêu cầu trước khi chạy

Cần cài:

- Python
- PostgreSQL
- Git, nếu muốn quản lý bằng Git

Project đang dùng virtual environment trong thư mục:

```text
.venv
```

Nếu chưa có `.venv`, tạo bằng:

```powershell
python -m venv .venv
```

Kích hoạt môi trường ảo:

```powershell
.\.venv\Scripts\activate
```

Sau khi kích hoạt thành công, terminal thường sẽ hiện tiền tố dạng:

```text
(.venv)
```

Khi đã thấy `(.venv)`, bạn có thể dùng lệnh ngắn:

```powershell
python ...
```

Thay vì phải ghi đầy đủ:

```powershell
.\.venv\Scripts\python.exe ...
```

Trong README này, mỗi lệnh quan trọng sẽ có:

- **Lệnh ngắn**: dùng khi `.venv` đã được kích hoạt.
- **Lệnh đầy đủ**: dùng khi chưa kích hoạt `.venv` hoặc muốn chắc chắn chạy đúng Python trong project.

Cài thư viện:

Nếu đã kích hoạt `.venv`:

```powershell
python -m pip install -r requirements.txt
```

Nếu chưa kích hoạt `.venv`:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

---

## 3. Cấu hình PostgreSQL

### 3.1 Tạo database

Mở SQL Shell `psql`, đăng nhập bằng user `postgres`, rồi chạy:

```sql
CREATE DATABASE laptop_prices;
```

### 3.2 Tạo user cho app

Ví dụ dùng password:

```text
LaptopApp@123
```

Chạy:

```sql
CREATE USER laptop_app WITH PASSWORD 'LaptopApp@123';
GRANT ALL PRIVILEGES ON DATABASE laptop_prices TO laptop_app;
```

Chuyển sang database mới:

```sql
\c laptop_prices
```

Cấp quyền schema:

```sql
GRANT ALL ON SCHEMA public TO laptop_app;
```

---

## 4. Tạo file `.env`

Copy file mẫu:

```powershell
Copy-Item .env.example .env
```

Mở `.env` và kiểm tra nội dung:

```env
DATABASE_URL=postgresql://laptop_app:LaptopApp%40123@localhost:5432/laptop_prices
```

Lưu ý:

- Nếu password là `LaptopApp@123`, trong URL phải viết `@` thành `%40`.
- Nếu bạn dùng password khác, hãy sửa lại trong `.env`.

Ví dụ:

```env
DATABASE_URL=postgresql://laptop_app:MAT_KHAU_CUA_BAN@localhost:5432/laptop_prices
```

---

## 5. Kiểm tra kết nối database

Chạy:

Nếu đã kích hoạt `.venv`:

```powershell
python .\database.py test
```

Nếu chưa kích hoạt `.venv`:

```powershell
.\.venv\Scripts\python.exe .\database.py test
```

Nếu thành công sẽ thấy dạng:

```text
Database: laptop_prices
User: laptop_app
Version: PostgreSQL ...
```

---

## 6. Tạo bảng trong database

Chạy:

Nếu đã kích hoạt `.venv`:

```powershell
python .\database.py init
```

Nếu chưa kích hoạt `.venv`:

```powershell
.\.venv\Scripts\python.exe .\database.py init
```

Lệnh này tạo các bảng:

- `crawl_runs`
- `raw_products`
- `daily_price_comparisons`
- `app_users`
- `favorite_products`

---

## 7. Import dữ liệu CSV hiện có vào database

Nếu đã có file CSV trong `D:/Data/raw` và `D:/Data/processed`, chạy:

Nếu đã kích hoạt `.venv`:

```powershell
python .\database.py import-existing
```

Nếu chưa kích hoạt `.venv`:

```powershell
.\.venv\Scripts\python.exe .\database.py import-existing
```

Lệnh này sẽ import dữ liệu mới nhất hiện có vào PostgreSQL.

---

## 8. Chạy crawler hằng ngày

Chạy:

Nếu đã kích hoạt `.venv`:

```powershell
python .\run_daily.py
```

Nếu chưa kích hoạt `.venv`:

```powershell
.\.venv\Scripts\python.exe .\run_daily.py
```

Pipeline sẽ làm các bước:

1. Crawl Phong Vũ.
2. Crawl GearVN.
3. Crawl CellphoneS.
4. Lưu raw CSV.
5. Merge dữ liệu so sánh giá.
6. Ghi dữ liệu vào PostgreSQL.
7. Gửi thông báo kết quả qua Telegram nếu đã cấu hình `TELEGRAM_BOT_TOKEN` và `TELEGRAM_CHAT_ID`.

---

## 9. Mở web app

Chạy server:

Nếu đã kích hoạt `.venv`:

```powershell
python -m uvicorn web_app:app --reload
```

Nếu chưa kích hoạt `.venv`:

```powershell
.\.venv\Scripts\python.exe -m uvicorn web_app:app --reload
```

Sau đó mở trình duyệt:

```text
http://127.0.0.1:8000
```

Các trang chính:

```text
/             Trang chủ
/products     Danh sách sản phẩm
/dashboard    Dashboard sản phẩm
/login        Đăng nhập
/register     Tạo tài khoản
/favorites    Sản phẩm yêu thích
```

Ví dụ:

```text
http://127.0.0.1:8000/products
```

Khi bấm vào một sản phẩm trong trang listing, web sẽ mở dashboard riêng cho sản phẩm đó.

---

## 10. Tính năng hiện có trên web

### Trang chủ

- Giới thiệu LapoAnalytics.
- Search sản phẩm.
- Hiển thị một số sản phẩm theo hãng.

### Danh sách sản phẩm

- Xem toàn bộ sản phẩm.
- Tìm kiếm theo tên/model.
- Lọc theo hãng.
- Bấm sản phẩm để mở dashboard.
- Bấm `Theo dõi / Yêu thích` để lưu sản phẩm.

### Dashboard sản phẩm

- Hiển thị thông tin model.
- So sánh giá giữa Phong Vũ, GearVN, CellphoneS.
- Nếu website không có giá, hiển thị:

```text
Không kinh doanh
```

- Website không kinh doanh sẽ không click được.
- Có chat tư vấn sản phẩm.

### Tài khoản

- Register.
- Login.
- Lưu sản phẩm yêu thích.
- Xem danh sách favorites.

---

## 11. Lưu ý về dữ liệu

Hiện project chủ yếu có dữ liệu:

- tên sản phẩm
- brand
- giá bán
- giá gốc
- url
- source
- thời gian crawl
- model key

Một số website có thêm:

- stock
- available

Nhưng dữ liệu cấu hình chi tiết như CPU/RAM/SSD/GPU chưa đầy đủ 100%. Vì vậy chat tư vấn chỉ suy luận từ tên sản phẩm nếu có thông tin trong tên, và sẽ không tự bịa thông số.

---

## 12. Một số lỗi thường gặp

### Lỗi password PostgreSQL

Nếu thấy:

```text
password authentication failed for user "laptop_app"
```

Hãy kiểm tra lại file `.env`.

Nếu muốn reset password:

```sql
ALTER USER laptop_app WITH PASSWORD 'LaptopApp@123';
```

### Web trắng hoặc CSS không cập nhật

Bấm:

```text
Ctrl + F5
```

để hard refresh trình duyệt.

### Không thấy dữ liệu trên web

Chạy lần lượt:

Nếu đã kích hoạt `.venv`:

```powershell
python .\database.py test
python .\database.py init
python .\database.py import-existing
```

Nếu chưa kích hoạt `.venv`:

```powershell
.\.venv\Scripts\python.exe .\database.py test
.\.venv\Scripts\python.exe .\database.py init
.\.venv\Scripts\python.exe .\database.py import-existing
```

Sau đó chạy lại web.

### Port 8000 đang bị dùng

Chạy bằng port khác:

Nếu đã kích hoạt `.venv`:

```powershell
python -m uvicorn web_app:app --reload --port 8001
```

Nếu chưa kích hoạt `.venv`:

```powershell
.\.venv\Scripts\python.exe -m uvicorn web_app:app --reload --port 8001
```

Mở:

```text
http://127.0.0.1:8001
```

---

## 13. Các lệnh hay dùng

### Chạy web

Nếu đã kích hoạt `.venv`:

```powershell
python -m uvicorn web_app:app --reload
```

Nếu chưa kích hoạt `.venv`:

```powershell
.\.venv\Scripts\python.exe -m uvicorn web_app:app --reload
```

### Test database

Nếu đã kích hoạt `.venv`:

```powershell
python .\database.py test
```

Nếu chưa kích hoạt `.venv`:

```powershell
.\.venv\Scripts\python.exe .\database.py test
```

### Tạo bảng

Nếu đã kích hoạt `.venv`:

```powershell
python .\database.py init
```

Nếu chưa kích hoạt `.venv`:

```powershell
.\.venv\Scripts\python.exe .\database.py init
```

### Import CSV hiện có

Nếu đã kích hoạt `.venv`:

```powershell
python .\database.py import-existing
```

Nếu chưa kích hoạt `.venv`:

```powershell
.\.venv\Scripts\python.exe .\database.py import-existing
```

### Chạy crawl hằng ngày

Nếu đã kích hoạt `.venv`:

```powershell
python .\run_daily.py
```

Nếu chưa kích hoạt `.venv`:

```powershell
.\.venv\Scripts\python.exe .\run_daily.py
```

---

## 14. Ghi chú Git

Không commit các file/thư mục sau:

```text
.env
.venv/
__pycache__/
data/output/
```

File `.env.example` được commit để người khác biết cần cấu hình gì.
