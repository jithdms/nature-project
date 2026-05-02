from flask import Flask, request
import tensorflow as tf
import numpy as np
from tensorflow.keras.preprocessing import image
import os
import uuid

# Flask 앱 초기화
app = Flask(__name__)

# ✅ 수정된 경로: 현재 폴더에 있는 모델 불러오기
model = tf.keras.models.load_model('recycle_person_detector.h5')

def predict_image(img_path, threshold=0.7):
    img = image.load_img(img_path, target_size=(224,224))
    img_array = image.img_to_array(img) / 255.0
    img_array = np.expand_dims(img_array, axis=0)
    pred = model.predict(img_array)[0][0]
    return f"✅ recycling | score: {pred:.4f}" if pred > threshold else f"❌ non_recycling | score: {pred:.4f}"

@app.route('/')
def index():
    return '''
    <h2>분리배출 판단 AI</h2>
    <form method="POST" action="/predict" enctype="multipart/form-data">
        <input type="file" name="image" accept="image/*" required><br><br>
        <button type="submit">예측하기</button>
    </form>
    '''

@app.route('/predict', methods=['POST'])
def predict():
    file = request.files.get('image')
    if not file:
        return '❌ 파일이 없습니다.', 400

    temp_filename = f"temp_{uuid.uuid4().hex}.jpg"
    file.save(temp_filename)

    try:
        result = predict_image(temp_filename)
    except Exception as e:
        result = f'❌ 예측 중 오류 발생: {str(e)}'
    finally:
        if os.path.exists(temp_filename):
            os.remove(temp_filename)

    return f'<h3>{result}</h3><a href="/">← 다시하기</a>'

if __name__ == '__main__':
    app.run(debug=True)
