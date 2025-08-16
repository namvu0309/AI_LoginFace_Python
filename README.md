### 1.3 Chạy migration Laravel
```bash
cd Backend-QNHG
php artisan migrate
```

## Bước 2: Cài đặt Python Dependencies

```bash
cd Face-Detection-with-Name-Recognition-main
python -m pip install -r requirements.txt

```

## Bước 4: Khởi động Services

### Terminal 1: Python Face Service
```bash
cd Face-Detection-with-Name-Recognition-main
python face_api.py

### Terminal 2: Laravel Backend
```bash
cd Backend-QNHG
php artisan serve
```

### Terminal 3: React Frontend
```bash
cd Frontend-QNHG
npm run dev
```

## Bước 5: Test

### 5.1 Kiểm tra Python Service
Truy cập: http://localhost:5000/health

### 5.2 Test Face Authentication
Truy cập: http://localhost:5173/admin/face-auth-test

## Troubleshooting

### Lỗi Database
- Đảm bảo MySQL đang chạy
- Kiểm tra thông tin kết nối trong `.env`
- Chạy `php artisan migrate:fresh` nếu cần

### Lỗi Python Service
- Kiểm tra port 8001 không bị sử dụng
- Đảm bảo tất cả dependencies đã được cài đặt
- Kiểm tra log lỗi trong terminal

### Lỗi Frontend
- Kiểm tra alias path trong `vite.config.js`
- Restart development server sau khi thay đổi config
- Kiểm tra console browser để xem lỗi

## Cấu trúc Files

```
prj-qnhg/
├── Backend-QNHG/           # Laravel Backend
│   ├── app/Http/Controllers/Admin/Auth/FaceAuthController.php
│   ├── routes/admin/auth.php
│   └── database/migrations/2025_01_20_000000_create_admin_faces_table.php
├── Frontend-QNHG/          # React Frontend
│   ├── src/components/admin/auth/
│   │   ├── FaceLogin.jsx
│   │   ├── FaceRegister.jsx
│   │   └── FaceAuthTest.jsx
│   ├── src/services/admin/authService.js
│   ├── src/config/api.js
│   └── vite.config.js
└── face-auth-service/      # Python Face Service
    ├── main.py
    ├── face_utils.py
    ├── database.py
    ├── schemas.py
    ├── requirements.txt
    └── README.md
```

## API Endpoints

### Laravel Routes
- `POST /api/admin/auth/face/login` - Đăng nhập bằng khuôn mặt
- `POST /api/admin/auth/face/register` - Đăng ký khuôn mặt
- `DELETE /api/admin/auth/face/delete/{userId}` - Xóa khuôn mặt
- `GET /api/admin/auth/face/health` - Health check

### Python Service
- `POST /register-face` - Đăng ký khuôn mặt
- `POST /login-face` - Đăng nhập bằng khuôn mặt
- `DELETE /delete-face/{user_id}` - Xóa khuôn mặt
- `GET /health` - Health check

## Lưu ý quan trọng

1. **Database**: Đảm bảo database `qnhg_db` đã được tạo
2. **Ports**: 
   - Laravel: 8000
   - Python Service: 5000
   - React: 5173
3. **Camera**: Cần camera để test chức năng
4. **Model AI**: Lần đầu chạy sẽ tải model FaceNet (có thể mất vài phút)
5. **Environment**: Đảm bảo tất cả environment variables đã được cấu hình

## Test Flow

1. Khởi động tất cả services
2. Truy cập http://localhost:8001/health để kiểm tra Python service
3. Truy cập http://localhost:5173/face-auth-test
4. Click "Kiểm tra Service" để test kết nối
5. Click "Đăng ký khuôn mặt" để đăng ký khuôn mặt cho admin
6. Click "Đăng nhập bằng khuôn mặt" để test đăng nhập
export CENTER_DB_URL="mysql+pymysql://root:@127.0.0.1:3306/center_db"