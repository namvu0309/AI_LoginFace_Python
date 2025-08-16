from flask import Flask, request, jsonify
from flask_cors import CORS
import cv2
import numpy as np
import os
import base64
from PIL import Image
import io
import mysql.connector
from datetime import datetime
import json

app = Flask(__name__)
CORS(app)

# Cấu hình database
DB_CONFIG = {
    'host': 'localhost',
    'user': 'root',
    'password': '',
    'database': 'qnhg-app'
}

# Khởi tạo face detector và recognizer
face_detector = cv2.CascadeClassifier('haarcascade_frontalface_default.xml')
recognizer = cv2.face.LBPHFaceRecognizer_create()

class FaceRecognitionAPI:
    def __init__(self):
        self.dataset_path = 'dataset'
        self.trainer_path = 'trainer'
        self.model_path = 'trainer/trainer.yml'
        
        # Tạo thư mục nếu chưa có
        os.makedirs(self.dataset_path, exist_ok=True)
        os.makedirs(self.trainer_path, exist_ok=True)
    
    def get_db_connection(self):
        """Kết nối database"""
        try:
            return mysql.connector.connect(**DB_CONFIG)
        except Exception as e:
            print(f"Database connection error: {e}")
            return None
    
    def base64_to_image(self, base64_string):
        """Chuyển đổi base64 thành image"""
        try:
            # Loại bỏ prefix data:image/...;base64,
            if ',' in base64_string:
                base64_string = base64_string.split(',')[1]
            
            image_data = base64.b64decode(base64_string)
            image = Image.open(io.BytesIO(image_data))
            return cv2.cvtColor(np.array(image), cv2.COLOR_RGB2BGR)
        except Exception as e:
            print(f"Base64 to image error: {e}")
            return None
    
    def save_face_to_dataset(self, user_id, image, image_count):
        """Lưu ảnh khuôn mặt vào dataset/<user_id>/ theo mẫu User.{user_id}.{count}.jpg"""
        try:
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            faces = face_detector.detectMultiScale(gray, 1.3, 5)

            saved_faces = []
            for (x, y, w, h) in faces:
                face_img = gray[y:y+h, x:x+w]
                filename = f"User.{user_id}.{image_count}.jpg"
                # Lưu dưới thư mục riêng của user: dataset/<user_id>/
                user_dir = os.path.join(self.dataset_path, str(user_id))
                os.makedirs(user_dir, exist_ok=True)
                filepath = os.path.join(user_dir, filename)
                cv2.imwrite(filepath, face_img)
                saved_faces.append(filepath)

            return saved_faces
        except Exception as e:
            print(f"Save face error: {e}")
            return []
    
    def train_model(self, user_id=None):
        """Training model từ dataset"""
        try:
            face_samples = []
            ids = []
            
            if user_id:
                # Training cho một user cụ thể theo cấu trúc dataset/<user_id>/User.<user_id>.<count>.jpg
                # Đọc các file trong thư mục con của user
                try:
                    user_dir = os.path.join(self.dataset_path, str(user_id))
                    all_files = os.listdir(user_dir)
                except Exception as e:
                    return False, f"Không thể đọc thư mục dataset của user: {str(e)}"

                image_paths = [
                    os.path.join(user_dir, f)
                    for f in all_files
                    if f.startswith(f"User.{user_id}.") and f.endswith('.jpg')
                ]

                if not image_paths:
                    return False, "Không tìm thấy dữ liệu khuôn mặt"
            else:
                # Training cho tất cả users
                image_paths = []
                for root, dirs, files in os.walk(self.dataset_path):
                    for file in files:
                        if file.endswith('.jpg'):
                            image_paths.append(os.path.join(root, file))
            
            for image_path in image_paths:
                try:
                    pil_image = Image.open(image_path).convert('L')
                    img_numpy = np.array(pil_image, 'uint8')
                    
                    # Lấy user_id từ tên file
                    filename = os.path.basename(image_path)
                    if 'User.' in filename:
                        user_id_from_file = int(filename.split('.')[1])
                    else:
                        continue
                    
                    faces = face_detector.detectMultiScale(img_numpy)
                    for (x, y, w, h) in faces:
                        face_samples.append(img_numpy[y:y+h, x:x+w])
                        ids.append(user_id_from_file)
                except Exception as e:
                    print(f"Error processing {image_path}: {e}")
                    continue
            
            if len(face_samples) == 0:
                return False, "Không có dữ liệu khuôn mặt để training"
            
            # Training model
            recognizer.train(face_samples, np.array(ids))
            recognizer.write(self.model_path)
            
            return True, f"Training thành công với {len(face_samples)} ảnh"
        except Exception as e:
            print(f"Training error: {e}")
            return False, f"Lỗi training: {str(e)}"
    
    def recognize_face(self, image):
        """Nhận diện khuôn mặt"""
        try:
            if not os.path.exists(self.model_path):
                return None, 0, "Model chưa được training"
            
            recognizer.read(self.model_path)
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            faces = face_detector.detectMultiScale(gray, 1.2, 5)
            
            if len(faces) == 0:
                return None, 0, "Không phát hiện khuôn mặt"
            
            # Lấy khuôn mặt lớn nhất
            (x, y, w, h) = max(faces, key=lambda face: face[2] * face[3])
            face_roi = gray[y:y+h, x:x+w]
            
            # Nhận diện
            user_id, confidence = recognizer.predict(face_roi)
            
            # Chuyển đổi confidence thành percentage (confidence càng thấp càng chính xác)
            accuracy = max(0, 100 - confidence)
            
            return user_id, accuracy, "Nhận diện thành công"
        except Exception as e:
            print(f"Recognition error: {e}")
            return None, 0, f"Lỗi nhận diện: {str(e)}"
    
    def get_user_info(self, user_id):
        """Lấy thông tin user từ database"""
        try:
            conn = self.get_db_connection()
            if not conn:
                return None
            
            cursor = conn.cursor(dictionary=True)
            cursor.execute("""
                SELECT af.*, u.name as user_name, u.email as user_email
                FROM admin_faces af 
                LEFT JOIN users u ON af.user_id = u.id 
                WHERE af.user_id = %s
            """, (user_id,))
            
            result = cursor.fetchone()
            conn.close()
            return result
        except Exception as e:
            print(f"Get user info error: {e}")
            return None

# Khởi tạo API instance
face_api = FaceRecognitionAPI()

@app.route('/api/face/capture', methods=['POST'])
def capture_face():
    """API chụp và lưu ảnh khuôn mặt"""
    try:
        data = request.get_json()
        user_id = data.get('user_id')
        image_data = data.get('image')
        image_count = data.get('image_count', 1)
        user_info = data.get('user_info', {})
        
        if not user_id or not image_data:
            return jsonify({'success': False, 'message': 'Thiếu thông tin bắt buộc'})
        
        # Chuyển đổi base64 thành image
        image = face_api.base64_to_image(image_data)
        if image is None:
            return jsonify({'success': False, 'message': 'Không thể xử lý ảnh'})
        
        # Lưu ảnh vào dataset
        saved_faces = face_api.save_face_to_dataset(user_id, image, image_count)
        
        if not saved_faces:
            return jsonify({'success': False, 'message': 'Không phát hiện khuôn mặt trong ảnh'})
        
        # Lưu thông tin user vào database (chỉ lần đầu)
        if image_count == 1 and user_info:
            try:
                conn = face_api.get_db_connection()
                if conn:
                    cursor = conn.cursor()
                    cursor.execute("""
                        INSERT INTO admin_faces (user_id, email, full_name, role_name, created_at, updated_at)
                        VALUES (%s, %s, %s, %s, %s, %s)
                        ON DUPLICATE KEY UPDATE
                        email = VALUES(email),
                        full_name = VALUES(full_name),
                        role_name = VALUES(role_name),
                        updated_at = VALUES(updated_at)
                    """, (
                        user_id,
                        user_info.get('email'),
                        user_info.get('full_name'),
                        user_info.get('role'),
                        datetime.now(),
                        datetime.now()
                    ))
                    conn.commit()
                    conn.close()
            except Exception as e:
                print(f"Database save error: {e}")
        
        return jsonify({
            'success': True,
            'message': f'Đã lưu {len(saved_faces)} ảnh khuôn mặt',
            'faces_saved': len(saved_faces)
        })
    
    except Exception as e:
        print(f"Capture face error: {e}")
        return jsonify({'success': False, 'message': f'Lỗi: {str(e)}'})

@app.route('/api/face/train', methods=['POST'])
def train_faces():
    """API training model"""
    try:
        data = request.get_json()
        user_id = data.get('user_id')
        
        success, message = face_api.train_model(user_id)
        
        return jsonify({
            'success': success,
            'message': message
        })
    
    except Exception as e:
        print(f"Train faces error: {e}")
        return jsonify({'success': False, 'message': f'Lỗi training: {str(e)}'})

@app.route('/api/face/recognize', methods=['POST'])
def recognize_face():
    """API nhận diện khuôn mặt"""
    try:
        data = request.get_json()
        image_data = data.get('image')
        
        if not image_data:
            return jsonify({'success': False, 'message': 'Thiếu dữ liệu ảnh'})
        
        # Chuyển đổi base64 thành image
        image = face_api.base64_to_image(image_data)
        if image is None:
            return jsonify({'success': False, 'message': 'Không thể xử lý ảnh'})
        
        # Nhận diện khuôn mặt
        user_id, accuracy, message = face_api.recognize_face(image)
        
        if user_id is None:
            return jsonify({
                'success': False,
                'message': message,
                'accuracy': accuracy
            })
        
        # Lấy thông tin user
        user_info = face_api.get_user_info(user_id)
        
        return jsonify({
            'success': True,
            'message': message,
            'user_id': int(user_id),
            'accuracy': round(accuracy, 2),
            'user_info': user_info
        })
    
    except Exception as e:
        print(f"Recognize face error: {e}")
        return jsonify({'success': False, 'message': f'Lỗi nhận diện: {str(e)}'})

@app.route('/api/face/users', methods=['GET'])
def get_registered_users():
    """API lấy danh sách users đã đăng ký"""
    try:
        conn = face_api.get_db_connection()
        if not conn:
            return jsonify({'success': False, 'message': 'Lỗi kết nối database'})
        
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM admin_faces ORDER BY created_at DESC")
        users = cursor.fetchall()
        conn.close()
        
        return jsonify({
            'success': True,
            'data': users
        })
    
    except Exception as e:
        print(f"Get users error: {e}")
        return jsonify({'success': False, 'message': f'Lỗi: {str(e)}'})

@app.route('/api/face/delete/<int:user_id>', methods=['DELETE'])
def delete_user_face(user_id):
    """API xóa dữ liệu khuôn mặt user"""
    try:
        # Xóa thư mục dataset của user: dataset/<user_id>
        user_folder = os.path.join(face_api.dataset_path, str(user_id))
        if os.path.exists(user_folder):
            import shutil
            shutil.rmtree(user_folder)
        
        # Xóa từ database
        conn = face_api.get_db_connection()
        if conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM admin_faces WHERE user_id = %s", (user_id,))
            conn.commit()
            conn.close()
        
        return jsonify({
            'success': True,
            'message': 'Đã xóa dữ liệu khuôn mặt'
        })
    
    except Exception as e:
        print(f"Delete user face error: {e}")
        return jsonify({'success': False, 'message': f'Lỗi: {str(e)}'})

if __name__ == '__main__':
    print("🚀 Face Recognition API đang khởi động...")
    print("📡 Server: http://localhost:5000")
    print("🔧 Endpoints:")
    print("   POST /api/face/capture - Chụp và lưu ảnh khuôn mặt")
    print("   POST /api/face/train - Training model")
    print("   POST /api/face/recognize - Nhận diện khuôn mặt")
    print("   GET  /api/face/users - Danh sách users")
    print("   DELETE /api/face/delete/<user_id> - Xóa user")
    app.run(debug=True, host='0.0.0.0', port=5000)
