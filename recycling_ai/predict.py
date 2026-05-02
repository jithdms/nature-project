import tensorflow as tf
import numpy as np
from tensorflow.keras.preprocessing import image
import os

# 모델 불러오기
model = tf.keras.models.load_model('recycling_ai/recycle_person_detector.h5')

def predict_image(img_path, threshold=0.8):
    img = image.load_img(img_path, target_size=(224,224))
    img_array = image.img_to_array(img) / 255.0
    img_array = np.expand_dims(img_array, axis=0)

    pred = model.predict(img_array)[0][0]

    if pred > threshold:
        return f"✅ recycling (분리수거 행동 있음) | score: {pred:.4f}"
    else:
        return f"❌ non_recycling (분리수거 행동 없음) | score: {pred:.4f}"

# 테스트할 이미지 폴더
folder_path = 'recycling_ai/test_images'

try:
    for filename in os.listdir(folder_path):
        if filename.lower().endswith(('.jpg', '.jpeg', '.png')):
            img_path = os.path.join(folder_path, filename)
            result = predict_image(img_path)
            print(f"{filename}: {result}")
except Exception as e:
    print("❌ 예측 중 오류 발생:", e)
