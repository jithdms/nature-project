from flask import Flask, render_template, request, redirect, url_for, session, jsonify
from flask_mysqldb import MySQL
from flask_bcrypt import Bcrypt
from google_auth_oauthlib.flow import Flow

from datetime import date, datetime
import requests
import os

# from google_fit import get_google_fit_steps

from google_fit import fetch_google_fit_steps  # 수정된 함수 사용
from google_auth_oauthlib.flow import Flow

from flask import Flask, request, jsonify
from tensorflow.keras.models import load_model
from PIL import Image
import numpy as np

os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'

app = Flask(__name__)
app.secret_key = 'your_secret_key'
app.config['MYSQL_HOST'] = 'localhost'
app.config['MYSQL_USER'] = 'root'
app.config['MYSQL_PASSWORD'] = '1234'
app.config['MYSQL_DB'] = 'nature'
bcrypt = Bcrypt(app)
mysql = MySQL(app)

model = load_model("recycle_person_detector.h5")
IMAGE_SIZE = (224, 224)
THRESHOLD = 0.5

@app.route('/predict', methods=['POST'])
def predict():
    if 'image' not in request.files:
        return jsonify({'error': 'No image uploaded'}), 400

    file = request.files['image']
    image = Image.open(file).convert('RGB')
    image = image.resize((224, 224))  # 모델 입력 크기와 맞추기
    image = np.array(image) / 255.0
    image = np.expand_dims(image, axis=0)

    pred = model.predict(image)[0][0]
    print("예측값:", pred)

    result = "recycling" if pred >= THRESHOLD else "not_recycling"

    if result == "recycling" and 'username' in session:
        cur = mysql.connection.cursor()

        # 사용자 ID 조회
        cur.execute("SELECT id FROM users WHERE username = %s", (session['username'],))
        user = cur.fetchone()

        if user:
            user_id = user[0]
            today = date.today()

            # ✅ 오늘 분리배출 적립 횟수 확인
            cur.execute("""
                SELECT COUNT(*) FROM point_history
                WHERE user_id = %s AND type = '적립'
                AND description = '분리배출 인증' AND DATE(date) = %s
            """, (user_id, today))
            count = cur.fetchone()[0]

            if count < 10:
                point = 10

                # 포인트 지급
                add_point_to_user(user_id, point)

                # 포인트 기록
                cur.execute("""
                    INSERT INTO point_history (user_id, type, description, point)
                    VALUES (%s, '적립', %s, %s)
                """, (user_id, '분리배출 인증', point))

                mysql.connection.commit()
                message = f"✅ 분리배출 인식! {point}포인트 적립 ({count + 1}/10)"
            else:
                message = "⚠️ 오늘은 분리배출 포인트 최대 10회를 초과했습니다."
        else:
            message = "사용자 정보 없음"

        cur.close()
        return jsonify({'result': result, 'message': message})

    return jsonify({'result': result})


@app.route("/google-fit/login")
def google_fit_login():
    flow = Flow.from_client_secrets_file(
        "client_secret.json",
        scopes=["https://www.googleapis.com/auth/fitness.activity.read"],
        redirect_uri="https://4ed59455fbeb.ngrok-free.app/google-fit/callback"
    )
    auth_url, _ = flow.authorization_url(prompt='consent')
    return redirect(auth_url)

@app.route("/google-fit/callback")
def google_fit_callback():
    # 1. Google OAuth 인증 완료
    flow = Flow.from_client_secrets_file(
        "client_secret.json",
        scopes=["https://www.googleapis.com/auth/fitness.activity.read"],
        redirect_uri="https://4ed59455fbeb.ngrok-free.app/google-fit/callback"
    )
    flow.fetch_token(authorization_response=request.url)
    credentials = flow.credentials

    # 2. access_token을 세션에 저장
    session['google_fit_token'] = credentials.token

    # 3. Google Fit API에서 걸음 수 가져오기
    try:
        step_count = fetch_google_fit_steps(credentials.token)
    except Exception as e:
        return f"걸음 수 가져오기 실패: {e}", 500

    # 4. 사용자 정보 가져오기
    if 'username' not in session:
        return redirect(url_for('login'))

    cur = mysql.connection.cursor()
    cur.execute("SELECT id FROM users WHERE username = %s", (session['username'],))
    user = cur.fetchone()

    if not user:
        cur.close()
        return "사용자 정보를 찾을 수 없습니다.", 400

    user_id = user[0]
    today = date.today()

    # 5. DB에 걸음 수 저장 또는 업데이트
    cur.execute("SELECT id FROM walking_steps WHERE user_id = %s AND date = %s", (user_id, today))
    exists = cur.fetchone()

    if exists:
        cur.execute("UPDATE walking_steps SET step_count = %s WHERE user_id = %s AND date = %s",
                    (step_count, user_id, today))
    else:
        cur.execute("INSERT INTO walking_steps (user_id, date, step_count) VALUES (%s, %s, %s)",
                    (user_id, today, step_count))

    mysql.connection.commit()
    cur.close()

    # 6. 홈으로 리디렉트
    return redirect(url_for('home'))

@app.route('/main')
def main_page():
    user_id = session.get('user_id')
    user = get_user(user_id)  # 사용자 정보 불러오기

    return render_template('main.html',
        username=user.username,
        point=user.current_point,
        total_point=user.max_point_held,  # <-- 누적 대신 최고 보유 포인트
        badge=user.badge_path,
        icon=user.grade_icon,
        grade=user.grade_name,
        step_count=user.step_count
    )



@app.route('/register', methods=['GET'])
def register():
    return render_template('register.html')

# @app.route('/')
# def home():
#     if 'username' in session:
#         return render_template('main.html', username=session['username'])
#     else:
#         return redirect(url_for('login'))

@app.route('/')
def home():
    if 'username' not in session:
        return redirect(url_for('login'))

    cur = mysql.connection.cursor()

    # 유저 정보
    cur.execute("""
        SELECT users.id, users.point, users.max_point_held, grades.name, grades.icon, grades.badge_image
        FROM users
        JOIN grades ON users.grade_id = grades.id
        WHERE users.username = %s
    """, (session['username'],))
    result = cur.fetchone()

    if not result:
        cur.close()
        return "사용자 정보를 찾을 수 없습니다.", 400

    user_id, point, max_point_held, grade_name, icon, badge = result

    # ✅ 관리자 메시지 확인
    cur.execute("SELECT message FROM temp_alerts WHERE user_id = %s", (user_id,))
    alert_row = cur.fetchone()

    admin_message = alert_row[0] if alert_row else None

    # ✅ 메시지 한 번만 보여주기 위해 삭제
    if alert_row:
        cur.execute("DELETE FROM temp_alerts WHERE user_id = %s", (user_id,))
        mysql.connection.commit()

    cur.close()

    step_count = session.get('step_count', 0)

    return render_template("main.html",
        username=session['username'],
        point=point,
        grade=grade_name,
        icon=icon,
        badge=badge,
        step_count=step_count,
        total_point=max_point_held,
        admin_message=admin_message  # ✅ 전달
    )



@app.route('/api/register', methods=['POST'])
def api_register():
    data = request.get_json()
    username = data.get('username')
    email = data.get('email')
    password = data.get('password')

    if not username or not email or not password:
        return jsonify({'message': '입력값 누락'}), 400

    cur = mysql.connection.cursor()
    cur.execute("SELECT id FROM users WHERE username = %s OR email = %s", (username, email))
    if cur.fetchone():
        return jsonify({'message': '이미 존재하는 아이디 또는 이메일입니다.'}), 409

    hashed_pw = bcrypt.generate_password_hash(password).decode('utf-8')

    # 기본 포인트 0 → 등급 ID 계산
    point = 0
    grade_id = get_grade_id_by_point(point)

    cur.execute("INSERT INTO users (username, password, email, point, grade_id) VALUES (%s, %s, %s, %s, %s)",
                (username, hashed_pw, email, point, grade_id))
    mysql.connection.commit()
    cur.close()

    return jsonify({'message': '회원가입 성공'}), 200

@app.route('/api/steps')
def api_steps():
    if 'username' not in session or 'google_fit_token' not in session:
        return jsonify({'error': '인증 필요'}), 401

    access_token = session['google_fit_token']

    try:
        step_count = fetch_google_fit_steps(access_token)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

    cur = mysql.connection.cursor()
    cur.execute("SELECT id FROM users WHERE username = %s", (session['username'],))
    user = cur.fetchone()

    if not user:
        cur.close()
        return jsonify({'error': '사용자 없음'}), 400

    user_id = user[0]
    today = date.today()

    # 현재 걷기 기록 조회
    cur.execute("SELECT id, rewarded_steps FROM walking_steps WHERE user_id = %s AND date = %s", (user_id, today))
    row = cur.fetchone()

    if row:
        walking_id, rewarded_steps = row
        cur.execute("UPDATE walking_steps SET step_count = %s WHERE id = %s", (step_count, walking_id))
    else:
        rewarded_steps = 0
        cur.execute("""
            INSERT INTO walking_steps (user_id, date, step_count, rewarded_steps)
            VALUES (%s, %s, %s, %s)
        """, (user_id, today, step_count, 0))
        mysql.connection.commit()
        cur.execute("SELECT id FROM walking_steps WHERE user_id = %s AND date = %s", (user_id, today))
        walking_id = cur.fetchone()[0]

    # ✅ 포인트 지급 로직
    new_rewardable_steps = step_count - rewarded_steps
    if new_rewardable_steps >= 1000:
        reward_units = new_rewardable_steps // 1000
        reward_points = reward_units * 10

        # 포인트 지급
        cur.execute("SELECT point FROM users WHERE id = %s", (user_id,))
        current_point = cur.fetchone()[0]
        new_point = current_point + reward_points

        grade_id = get_grade_id_by_point(new_point)
        cur.execute("""
            UPDATE users 
            SET point = %s, grade_id = %s 
            WHERE id = %s
        """, (new_point, grade_id, user_id))

        # 지급된 보상 걸음 수 갱신
        cur.execute("""
            UPDATE walking_steps 
            SET rewarded_steps = rewarded_steps + %s 
            WHERE id = %s
        """, (reward_units * 1000, walking_id))

        # ✅ 포인트 히스토리 기록 추가
        cur.execute("""
            INSERT INTO point_history (user_id, type, description, point)
            VALUES (%s, '적립', %s, %s)
        """, (user_id, f'걷기 {reward_units * 1000}보 달성', reward_points))

        mysql.connection.commit()

    cur.close()
    return jsonify({'step_count': step_count})

@app.route('/api/transport', methods=['POST'])
def transport_record():
    if 'username' not in session:
        return jsonify({'error': '로그인 필요'}), 401

    data = request.get_json()
    distance = data.get('distance')
    speed = data.get('speed')
    transport_type = data.get('transport_type', '')

    if distance is None or speed is None:
        return jsonify({'error': '데이터 부족'}), 400

    is_bus = 10 <= speed <= 60
    today = date.today()

    cur = mysql.connection.cursor()
    cur.execute("SELECT id FROM users WHERE username = %s", (session['username'],))
    user = cur.fetchone()

    if not user:
        cur.close()
        return jsonify({'error': '유저 없음'}), 400

    user_id = user[0]

    # ✅ 이동 기록은 항상 저장
    cur.execute("""
        INSERT INTO transport_records (
            user_id, date, distance_km, speed_kmh, is_public_transport, transport_type
        ) VALUES (%s, %s, %s, %s, %s, %s)
    """, (user_id, today, distance, speed, is_bus, transport_type))

    message = "❌ 대중교통으로 인식되지 않았지만 기록은 저장되었습니다."

    # ✅ 포인트 지급 or 기록만 남기기
    if is_bus:
        earned_point = int(distance * 10)
        add_point_to_user(user_id, earned_point)

        # 포인트 적립 기록
        cur.execute("""
            INSERT INTO point_history (user_id, type, description, point)
            VALUES (%s, '적립', %s, %s)
        """, (user_id, f'대중교통 {distance:.1f}km 이용', earned_point))

        message = f'✅ 대중교통 이용으로 {earned_point}포인트 적립!'
    else:
        # ✅ 적립 없이 기록만 남김
        cur.execute("""
            INSERT INTO point_history (user_id, type, description, point)
            VALUES (%s, '기록', %s, %s)
        """, (user_id, f'교통이용 감지 (속도 {speed:.1f}km/h)', 0))

    mysql.connection.commit()
    cur.close()

    return jsonify({'message': message})

@app.route('/api/bike', methods=['POST'])
def api_bike():
    if 'user_id' not in session:
        return jsonify({"error": "로그인 필요"}), 401

    user_id = session['user_id']
    data = request.get_json()
    distance = float(data.get('distance', 0))
    speed = float(data.get('speed', 0))

    point_earned = int(distance * 10)
    now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    try:
        cur = mysql.connection.cursor()

        # ✅ 포인트 기록
        cur.execute("""
            INSERT INTO point_history (user_id, type, description, point, date)
            VALUES (%s, '적립', %s, %s, %s)
        """, (user_id, f'자전거 {distance:.2f}km 이용', point_earned, now))

        # ✅ 현재 포인트 업데이트
        add_point_to_user(user_id, point_earned)

        # ✅ 자전거 이용 기록 저장
        cur.execute("""
            INSERT INTO bike_records (user_id, date, distance, speed)
            VALUES (%s, CURDATE(), %s, %s)
        """, (user_id, distance, speed))

        mysql.connection.commit()
        cur.close()

        return jsonify({
            "message": f"✅ {point_earned}P가 적립되었습니다!",
            "point": point_earned
        })

    except Exception as e:
        print("🚨 DB 저장 실패:", e)
        return jsonify({"error": "서버 오류 발생"}), 500



@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        identifier = request.form['username']
        password = request.form['password']

        cur = mysql.connection.cursor()
        cur.execute("SELECT * FROM users WHERE username = %s OR email = %s", (identifier, identifier))
        user = cur.fetchone()
        cur.close()

        if user and bcrypt.check_password_hash(user[2], password):
            session['username'] = user[1]
            session['user_id'] = user[0]
            session['is_admin'] = user[7]

            # ✅ Google Fit 연동 토큰이 없다면 리디렉션
            if 'google_fit_token' not in session:
                return redirect(url_for('google_fit_login'))

            return redirect(url_for('home'))
        else:
            return '로그인 실패'

    return render_template('login.html')



@app.route('/logout')
def logout():
    session.pop('username', None)
    session.pop('is_admin', None)
    return redirect(url_for('home'))

@app.route('/admin')
def admin_page():
    if not session.get('is_admin'):
        return "접근 권한이 없습니다.", 403

    cur = mysql.connection.cursor()

    # 상품 목록 가져오기
    cur.execute("SELECT * FROM shop_items")
    items = cur.fetchall()

    # ✅ "자전거", "분리배출", "교통이용" 포함된 내역만 추출
    cur.execute("""
        SELECT ph.user_id, u.username, ph.description, ph.point, ph.date
        FROM point_history ph
        JOIN users u ON ph.user_id = u.id
        WHERE ph.description LIKE '%자전거%'
           OR ph.description LIKE '%분리배출%'
           OR ph.description LIKE '%교통이용%'
        ORDER BY ph.date DESC
    """)
    raw_missions = cur.fetchall()
    cur.close()

    # ✅ 템플릿에 전달할 형식 맞추기
    missions = [
        (row[0], row[1], row[2], f"{row[3]}P", row[4].strftime("%Y-%m-%d %H:%M"))
        for row in raw_missions
    ]

    return render_template('admin.html', items=items, missions=missions)


@app.route('/admin/user/<username>')
def get_user_info(username):
    if not session.get('is_admin'):
        return jsonify({'found': False, 'error': '권한 없음'}), 403

    cur = mysql.connection.cursor()
    cur.execute("""
        SELECT id, username, email, created_at, point, grade_id, is_admin
        FROM users
        WHERE username = %s
    """, (username,))
    user = cur.fetchone()
    cur.close()

    if user:
        return jsonify({
            'found': True,
            'id': user[0],
            'username': user[1],
            'email': user[2],
            'created_at': user[3].strftime('%Y-%m-%d %H:%M'),
            'point': user[4],
            'grade_id': user[5],
            'is_admin': user[6]
        })
    else:
        return jsonify({'found': False})


# @app.route('/admin/users', methods=['GET'])
# def get_users():
#     if not session.get('is_admin'):
#         return "권한 없음", 403

#     keyword = request.args.get('keyword', '')

#     cur = mysql.connection.cursor()
#     if keyword:
#         cur.execute("""
#             SELECT id, username, email, created_at, point, grade_id, is_admin
#             FROM users
#             WHERE username LIKE %s
#         """, (f"%{keyword}%",))
#     else:
#         cur.execute("""
#             SELECT id, username, email, created_at, point, grade_id, is_admin
#             FROM users
#         """)
#     users = cur.fetchall()
#     cur.close()

#     return jsonify(users)

@app.route('/admin/point', methods=['POST'])
def update_user_point():
    if not session.get('is_admin'):
        return jsonify({'message': '권한 없음'}), 403

    data = request.get_json()
    identifier = data.get('identifier')
    amount = data.get('amount')

    if not identifier or amount is None:
        return jsonify({'message': '입력값이 부족합니다'}), 400

    cur = mysql.connection.cursor()

    cur.execute("""
        SELECT id, point, max_point_held FROM users 
        WHERE id = %s OR username = %s OR email = %s
    """, (identifier, identifier, identifier))
    result = cur.fetchone()

    if not result:
        cur.close()
        return jsonify({'message': '해당 유저를 찾을 수 없습니다'}), 404

    user_id, current_point, max_point_held = result
    new_point = max(0, current_point + amount)
    updated_max_point = max(new_point, max_point_held or 0)
    grade_id = get_grade_id_by_point(new_point)

    cur.execute("""
        UPDATE users 
        SET point = %s, grade_id = %s, max_point_held = %s 
        WHERE id = %s
    """, (new_point, grade_id, updated_max_point, user_id))

    # ✅ 포인트 히스토리 기록 추가
    point_type = '적립' if amount > 0 else '차감'
    description = f'관리자에 의해 포인트 {point_type}'
    cur.execute("""
        INSERT INTO point_history (user_id, type, description, point)
        VALUES (%s, %s, %s, %s)
    """, (user_id, point_type, description, amount))

    # ✅ 알림 메시지 (선택)
    msg = f"{abs(amount)} 포인트가 관리자에 의해 {point_type}되었습니다."
    cur.execute("INSERT INTO temp_alerts (user_id, message) VALUES (%s, %s)", (user_id, msg))

    mysql.connection.commit()
    cur.close()

    return jsonify({'message': f'{amount:+} 포인트가 적용되었습니다.'})

@app.route('/admin/missions')
def admin_missions():
    if not session.get('is_admin'):
        return "접근 권한 없음", 403

    cur = mysql.connection.cursor()
    cur.execute("""
        SELECT ph.user_id, u.username, ph.description, ph.point, ph.date
        FROM point_history ph
        JOIN users u ON ph.user_id = u.id
        WHERE ph.description LIKE '미션:%'
        ORDER BY ph.date DESC
    """)
    rows = cur.fetchall()
    cur.close()

    missions = [{
        'user_id': row[0],
        'username': row[1],
        'mission_name': row[2][4:],  # '미션:' 이후만 표시
        'point': row[3],
        'date': row[4].strftime("%Y-%m-%d %H:%M")
    } for row in rows]

    return render_template('admin_missions.html', missions=missions)


# 관리자 페이지 상품 삭제
@app.route('/admin/delete-item/<int:item_id>', methods=['POST'])
def delete_item(item_id):
    if not session.get('is_admin'):
        return "권한 없음", 403

    cur = mysql.connection.cursor()

    # 1. 먼저 연결된 구매 기록 삭제
    cur.execute("DELETE FROM user_purchases WHERE item_id = %s", (item_id,))

    # 2. 그런 다음 상품 자체 삭제
    cur.execute("DELETE FROM shop_items WHERE id = %s", (item_id,))

    mysql.connection.commit()
    cur.close()

    return redirect(url_for('admin_page'))

# 상품 추가 기능
@app.route('/admin/add-item', methods=['POST'])
def add_item():
    if not session.get('is_admin'):
        return "권한 없음", 403

    name = request.form['name']
    point = request.form['price']   # 폼에서 price로 받지만 실제 테이블 컬럼은 point
    stock = request.form['stock']

    cur = mysql.connection.cursor()
    cur.execute("INSERT INTO shop_items (name, point, stock) VALUES (%s, %s, %s)", (name, point, stock))
    mysql.connection.commit()
    cur.close()

    return redirect(url_for('admin_page'))

from datetime import datetime

@app.route('/admin/users', methods=['GET'])
def get_users():
    if not session.get('is_admin'):
        return "권한 없음", 403

    keyword = request.args.get('keyword', '')

    cur = mysql.connection.cursor()
    if keyword:
        cur.execute("""
            SELECT id, username, email, created_at, point, grade_id, is_admin
            FROM users
            WHERE username LIKE %s
        """, (f"%{keyword}%",))
    else:
        cur.execute("""
            SELECT id, username, email, created_at, point, grade_id, is_admin
            FROM users
        """)

    raw_users = cur.fetchall()
    cur.close()

    # 가입일 포맷 적용
    users = []
    for u in raw_users:
        created_at = u[3].strftime("%Y년 %m월 %d일 %H시 %M분")  # 한국어 형식
        users.append([u[0], u[1], u[2], created_at, u[4], u[5], u[6]])

    return jsonify(users)

# @app.route('/point-history')
# def point_history():
#     if 'username' not in session:
#         return redirect(url_for('login'))

#     # 더미 데이터 (DB 연결 없이 표시용)
#     points = [
#         {'description': '분리배출 인증', 'point': +50, 'date': '2025-07-10'},
#         {'description': '걷기 5,000보 달성', 'point': +30, 'date': '2025-07-09'},
#         {'description': '문화상품권 교환', 'point': -500, 'date': '2025-07-08'}
#     ]

#     return render_template('point_history.html', points=points)


# @app.route('/purchase-history')
# def purchase_history():
#     if 'username' not in session:
#         return redirect(url_for('login'))

#     # 더미 데이터 (DB 연결 없이 표시용)
#     purchases = [
#         {'name': '문화상품권 5,000원권', 'point': 500, 'date': '2025-07-08'},
#         {'name': '텀블러 할인 쿠폰', 'point': 400, 'date': '2025-07-05'}
#     ]

#     return render_template('purchase_history.html', purchases=purchases)



# 회원가입 중복 확인
@app.route('/api/check-duplicate', methods=['POST'])
def check_duplicate():
    data = request.get_json()
    username = data.get('username')
    email = data.get('email')

    result = {'usernameExists': False, 'emailExists': False}
    cur = mysql.connection.cursor()

    if username:
        cur.execute("SELECT id FROM users WHERE username = %s", (username,))
        if cur.fetchone():
            result['usernameExists'] = True

    if email:
        cur.execute("SELECT id FROM users WHERE email = %s", (email,))
        if cur.fetchone():
            result['emailExists'] = True

    cur.close()
    return jsonify(result)


# # 등급 나누는 거
# def calculate_grade(point):
#     if point <= 100:
#         return "바닥부터 시작하는 멋있는 씨앗"
#     elif point <= 300:
#         return "집으로 다시 돌아가고 싶은 새싹"
#     elif point <= 600:
#         return "열매"
#     elif point <= 1000:
#         return "봉오리"
#     elif point <= 1500:
#         return "꽃"
#     elif point <= 2200:
#         return "묘목"
#     elif point <= 3500:
#         return "성목"
#     else:
#         return "세계수"

# def add_point_to_user(user_id, added_point):
#     cur = mysql.connection.cursor()

#     # 현재 포인트 가져오기
#     cur.execute("SELECT point FROM users WHERE id = %s", (user_id,))
#     result = cur.fetchone()
#     if not result:
#         return False

#     current_point = result[0]
#     new_point = current_point + added_point
#     new_grade = calculate_grade(new_point)

#     # 업데이트
#     cur.execute("UPDATE users SET point = %s, grade = %s WHERE id = %s", (new_point, new_grade, user_id))
#     mysql.connection.commit()
#     cur.close()
#     return True

# if __name__ == '__main__':
#     app.run(host='0.0.0.0', port=5000)

def get_grade_id_by_point(point):
    cur = mysql.connection.cursor()
    cur.execute("SELECT id FROM grades WHERE %s BETWEEN min_point AND max_point", (point,))
    result = cur.fetchone()
    cur.close()
    return result[0] if result else None

def add_point_to_user(user_id, added_point):
    cur = mysql.connection.cursor()

    cur.execute("SELECT point, max_point_held FROM users WHERE id = %s", (user_id,))
    result = cur.fetchone()
    if not result:
        return False

    current_point, max_point_held = result
    new_point = current_point + added_point

    # ✅ max_point_held 갱신 여부 판단
    updated_max_point = max(new_point, max_point_held)

    grade_id = get_grade_id_by_point(new_point)

    # ✅ point, grade_id, max_point_held 모두 반영
    cur.execute("""
        UPDATE users 
        SET point = %s, grade_id = %s, max_point_held = %s 
        WHERE id = %s
    """, (new_point, grade_id, updated_max_point, user_id))

    mysql.connection.commit()
    cur.close()
    return True


# @app.route('/shop')
# def shop():
#     if 'username' not in session:
#         return redirect(url_for('login'))

#     cur = mysql.connection.cursor()
#     cur.execute("SELECT * FROM shop_items")
#     items = cur.fetchall()
#     cur.close()

#     return render_template("shop.html", items=items)

@app.route('/purchase/<int:item_id>', methods=['POST'])
def purchase(item_id):
    if 'username' not in session:
        return redirect(url_for('login'))

    cur = mysql.connection.cursor()

    # 사용자 포인트 및 max_point_held 조회
    cur.execute("SELECT id, point, max_point_held FROM users WHERE username = %s", (session['username'],))
    user = cur.fetchone()
    if not user:
        cur.close()
        return "사용자 정보를 찾을 수 없습니다.", 400

    user_id, current_point, max_point_held = user

    # 상품 정보 조회
    cur.execute("SELECT name, point, stock FROM shop_items WHERE id = %s", (item_id,))
    item = cur.fetchone()
    if not item:
        cur.close()
        return "존재하지 않는 상품입니다.", 404

    item_name, item_point, stock = item

    # 재고 및 포인트 체크
    if stock <= 0:
        cur.close()
        return "품절된 상품입니다.", 400
    if current_point < item_point:
        cur.close()
        return "포인트가 부족합니다.", 400

    # 포인트 차감
    new_point = current_point - item_point

    # max_point_held는 줄이면 안 됨 → 현재 포인트보다 낮아져도 그대로 유지
    updated_max_point = max_point_held or 0  # None 방지

    # 유저 포인트만 차감, max_point_held는 그대로
    cur.execute("""
        UPDATE users 
        SET point = %s, max_point_held = %s
        WHERE id = %s
    """, (new_point, updated_max_point, user_id))

    # 구매 기록 저장
    cur.execute("INSERT INTO user_purchases (user_id, item_id) VALUES (%s, %s)", (user_id, item_id))

    # 상품 재고 감소
    cur.execute("UPDATE shop_items SET stock = stock - 1 WHERE id = %s", (item_id,))

    # 포인트 사용 내역 기록
    cur.execute("""
        INSERT INTO point_history (user_id, type, description, point)
        VALUES (%s, '사용', %s, %s)
    """, (user_id, f"{item_name} 구매", -item_point))

    mysql.connection.commit()
    cur.close()

    return redirect(url_for('shop', success=1))

# @app.route('/admin/add-item', methods=['POST'])
# def add_item():
#     if not session.get('is_admin'):
#         return "권한 없음", 403

#     name = request.form['name']
#     price = request.form['price']
#     stock = request.form['stock']

#     cur = mysql.connection.cursor()
#     cur.execute("INSERT INTO shop_items (name, price, stock) VALUES (%s, %s, %s)", (name, price, stock))
#     mysql.connection.commit()
#     cur.close()

#     return redirect(url_for('admin_page'))

# @app.route('/admin/delete-item/<int:item_id>', methods=['POST'])
# def delete_item(item_id):
#     if not session.get('is_admin'):
#         return "권한 없음", 403

#     cur = mysql.connection.cursor()
#     cur.execute("DELETE FROM shop_items WHERE id = %s", (item_id,))
#     mysql.connection.commit()
#     cur.close()

#     return redirect(url_for('admin_page'))

@app.route('/shop')
def shop():
    if 'username' not in session:
        return redirect(url_for('login'))

    cur = mysql.connection.cursor()

    # 유저 포인트 가져오기
    cur.execute("SELECT point FROM users WHERE username = %s", (session['username'],))
    user_point = cur.fetchone()[0]

    # 아이템 목록 가져오기
    cur.execute("SELECT * FROM shop_items")
    items = cur.fetchall()
    cur.close()

    return render_template("shop.html", items=items, user_point=user_point)

@app.route('/point-history')
def point_history():
    if 'username' not in session:
        return redirect(url_for('login'))

    cur = mysql.connection.cursor()
    cur.execute("SELECT id FROM users WHERE username = %s", (session['username'],))
    user = cur.fetchone()
    if not user:
        cur.close()
        return "사용자 정보를 찾을 수 없습니다.", 400

    user_id = user[0]

    cur.execute("""
        SELECT type, description, point, date
        FROM point_history
        WHERE user_id = %s
        ORDER BY date DESC
    """, (user_id,))
    rows = cur.fetchall()
    cur.close()

    points = [{
        'type': row[0],
        'description': row[1],
        'point': row[2],
        'date': row[3].strftime("%Y-%m-%d %H:%M")
    } for row in rows]

    return render_template('point_history.html', points=points)

@app.route('/purchase-history')
def purchase_history():
    if 'username' not in session:
        return redirect(url_for('login'))

    cur = mysql.connection.cursor()

    # 사용자 ID 가져오기
    cur.execute("SELECT id FROM users WHERE username = %s", (session['username'],))
    user = cur.fetchone()
    if not user:
        cur.close()
        return "사용자 정보를 찾을 수 없습니다.", 400

    user_id = user[0]

    # 구매 내역 조회 (JOIN: 상품 이름 + 포인트 + 구매일)
    cur.execute("""
        SELECT s.name, s.point, up.purchased_at
        FROM user_purchases up
        JOIN shop_items s ON up.item_id = s.id
        WHERE up.user_id = %s
        ORDER BY up.purchased_at DESC
    """, (user_id,))
    rows = cur.fetchall()
    cur.close()

    # 날짜 포맷 등 가공
    purchases = []
    for row in rows:
        purchases.append({
            'name': row[0],
            'point': row[1],
            'date': row[2].strftime("%Y-%m-%d %H:%M")
        })

    return render_template('purchase_history.html', purchases=purchases)


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)