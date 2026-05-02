import tensorflow as tf
from tensorflow.keras.preprocessing.image import ImageDataGenerator
from tensorflow.keras.callbacks import EarlyStopping, ModelCheckpoint
import matplotlib.pyplot as plt
import os

# 데이터셋 경로 (절대 경로 또는 Colab/실행 환경에 맞게 조정 필요)
train_dir = 'recycling_ai/dataset'  # 'recycling', 'non_recycling' 폴더 포함되어야 함

# 이미지 전처리 및 증강 (최소화)
datagen = ImageDataGenerator(
    rescale=1./255,
    validation_split=0.2,
    horizontal_flip=True  # 가장 안전한 증강만 유지
)

try:
    # 학습 데이터 제너레이터
    train_generator = datagen.flow_from_directory(
        train_dir,
        target_size=(224, 224),
        batch_size=32,
        class_mode='binary',
        subset='training',
        shuffle=True
    )

    # 검증 데이터 제너레이터
    val_generator = datagen.flow_from_directory(
        train_dir,
        target_size=(224, 224),
        batch_size=32,
        class_mode='binary',
        subset='validation',
        shuffle=True
    )

    # 클래스 확인 (예측 해석할 때 필요)
    if train_generator.class_indices:
        print("클래스 인덱스:", train_generator.class_indices)
    else:
        print("❗ 클래스 인덱스를 불러올 수 없습니다. 데이터셋을 확인하세요.")

    # CNN 모델 구성
    model = tf.keras.models.Sequential([
        tf.keras.layers.Input(shape=(224,224,3)),
        tf.keras.layers.Conv2D(32, (3,3), activation='relu'),
        tf.keras.layers.MaxPooling2D(2,2),

        tf.keras.layers.Conv2D(64, (3,3), activation='relu'),
        tf.keras.layers.MaxPooling2D(2,2),

        tf.keras.layers.Flatten(),
        tf.keras.layers.Dense(128, activation='relu'),
        tf.keras.layers.Dropout(0.5),
        tf.keras.layers.Dense(1, activation='sigmoid')
    ])

    # 모델 컴파일
    model.compile(
        optimizer='adam',
        loss='binary_crossentropy',
        metrics=['accuracy']
    )

    # 콜백 설정
    early_stop = EarlyStopping(monitor='val_loss', patience=3, restore_best_weights=True)
    checkpoint = ModelCheckpoint('recycling_ai/best_model.h5', monitor='val_loss', save_best_only=True)

    # 학습 시작
    history = model.fit(
        train_generator,
        validation_data=val_generator,
        epochs=20,
        callbacks=[early_stop, checkpoint]
    )

    # 학습 정확도 시각화
    plt.plot(history.history['accuracy'], label='Train Accuracy', color='red')
    plt.plot(history.history['val_accuracy'], label='Validation Accuracy', color='blue')
    plt.title('Training and Validation Accuracy')
    plt.legend()
    plt.show()

    # 최종 모델 저장
    model.save('recycling_ai/recycle_person_detector.h5')
    print("✅ 모델 학습 및 저장 완료")

except Exception as e:
    print("❌ 전체 실행 중 오류 발생:", e)

