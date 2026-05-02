-- SQLBook: Code

create database nature;

use nature;

CREATE TABLE users (
    id INT AUTO_INCREMENT PRIMARY KEY,
    username VARCHAR(50) UNIQUE NOT NULL,
    password VARCHAR(255) NOT NULL,
    email VARCHAR(100),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    point INT DEFAULT 0,
    grade_id INT,
    FOREIGN KEY (grade_id) REFERENCES grades(id)
);

ALTER TABLE users ADD is_admin BOOLEAN DEFAULT FALSE;

ALTER TABLE users CONVERT TO CHARACTER SET utf8mb4;


CREATE TABLE grades (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(20) NOT NULL,           -- 등급 이름 (예: 씨앗, 새싹)
    min_point INT NOT NULL,
    max_point INT NOT NULL,
    icon VARCHAR(10),                    -- 이모지 (예: 🌱, 🌸)
    badge_image VARCHAR(255)             -- 뱃지 이미지 경로 (예: seed.png)
);

ALTER TABLE grades CONVERT TO CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci;


INSERT INTO grades (name, min_point, max_point, icon, badge_image) VALUES
('씨앗', 0, 100, '🌱', 'badges/seed.png'),
('새싹', 101, 300, '🌱', 'badges/sprout.png'),
('열매', 301, 600, '🍎', 'badges/fruit.png'),
('봉오리', 601, 1000, '🌿', 'badges/bud.png'),
('꽃', 1001, 1500, '🌸', 'badges/flower.png'),
('묘목', 1501, 2200, '🌲', 'badges/seedling.png'),
('성목', 2201, 3500, '🌳', 'badges/tree.png'),
('세계수', 3501, 5000, '🌍', 'badges/worldtree.png');


0~100 : 씨앗
101~300 : 새싹
301~600 : 열매
601~1000 : 봉오리
1001~1500 : 꽃
1501~2200 : 묘목
2201~3500 : 성목 
3501~5000 :  세계수

CREATE TABLE shop_items (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    point INT NOT NULL,
    stock INT NOT NULL
);

INSERT INTO shop_items (name, point, stock) VALUES
('문화상품권 5,000원권', 500, 20),
('스타벅스 아메리카노 기프티콘', 700, 15),
('이모지 꾸러미 뱃지 세트', 300, 30),
('에코백 (친환경 재질)', 1000, 10),
('탄소중립 메달 디지털 뱃지', 200, 50),
('텀블러 할인 쿠폰', 400, 25);

CREATE TABLE user_purchases (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    item_id INT NOT NULL,
    purchased_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id),
    FOREIGN KEY (item_id) REFERENCES shop_items(id)
);

ALTER TABLE users ADD COLUMN max_point_held INT DEFAULT 0;

CREATE TABLE walking_steps (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    date DATE NOT NULL,
    step_count INT DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id)
);

ALTER TABLE walking_steps ADD COLUMN rewarded_steps INT DEFAULT 0;

CREATE TABLE transport_records (
  id INT AUTO_INCREMENT PRIMARY KEY,
  user_id INT NOT NULL,
  distance_km FLOAT NOT NULL,
  speed_kmh FLOAT NOT NULL,
  is_public_transport BOOLEAN,
  transport_type VARCHAR(20),
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);
ALTER TABLE transport_records ADD COLUMN date DATE;


CREATE TABLE bike_records (
  id INT AUTO_INCREMENT PRIMARY KEY,
  user_id INT NOT NULL,
  date DATE NOT NULL,
  distance FLOAT,
  speed FLOAT,
  FOREIGN KEY (user_id) REFERENCES users(id)
);

CREATE TABLE point_history (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    type VARCHAR(20),  -- 예: '적립', '사용'
    description TEXT,
    point INT,          -- + 또는 - 값 가능
    date DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

CREATE TABLE temp_alerts (
  id INT AUTO_INCREMENT PRIMARY KEY,
  user_id INT NOT NULL,
  message VARCHAR(255),
  FOREIGN KEY (user_id) REFERENCES users(id)
);
