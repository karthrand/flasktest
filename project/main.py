from flask import Flask, jsonify, request
from flask_jwt_extended import (
    JWTManager, jwt_required, create_access_token,
    get_jwt_identity
)
import mysql.connector
from mysql.connector import Error
import secrets
import os 

app = Flask(__name__)


# 配置JWT密钥
## 如果环境变量未配置JWT_SECRET_KEY，则生成一个安全的密钥
secret_key = secrets.token_urlsafe(64)
app.config['JWT_SECRET_KEY'] = os.environ.get('JWT_SECRET_KEY', secret_key)
jwt = JWTManager(app)

# 读取环境变量
db_host = os.getenv('DB_HOST')
db_user = os.getenv('DB_USER')
db_password = os.getenv('DB_PASSWORD')
db_name = os.getenv('DB_NAME')

# 数据库配置信息
db_config = {
    'host': db_host,
    'user': db_user,
    'password': db_password,
    'database': db_name
}

# 数据库连接函数
def get_db_connection():
    connection = None
    try:
        connection = mysql.connector.connect(**db_config)
    except Error as e:
        print(f"数据库连接错误: {e}")
    return connection

# 数据库检测及初始化
@app.before_request
def check_and_create_users_table():
    """
    在处理第一个请求之前检查数据库连接并创建表
    """
    connection = None
    try:
        # 建立数据库连接
        print( f"db_config: {db_config}")
        connection = mysql.connector.connect(**db_config)
        # 检查并创建表
        cursor = connection.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INT AUTO_INCREMENT PRIMARY KEY,
                username VARCHAR(255) NOT NULL,
                password VARCHAR(255) NOT NULL
            )
        """)
        # 查找admin用户
        cursor.execute("SELECT * FROM users WHERE username = 'admin'")
        admin_info = cursor.fetchone()

        # 获取环境变量中的管理员密码
        admin_password = os.getenv('ADMIN_PASSWORD')
        if not admin_password:
            raise ValueError("环境变量 ADMIN_PASSWORD 未设置")

        if not admin_info:
            # 如果admin不存在，则插入admin用户
            cursor.execute(
                "INSERT INTO users (username, password) VALUES (%s, %s)", 
                ('admin', admin_password)
            )
        else:
            # 如果环境变量中的密码与数据库中存储的密码不一致，则更新数据库中的密码
            if admin_info[2] != admin_password:  # 假定密码存储在返回元组的第三个位置（索引2）
                cursor.execute(
                    "UPDATE users SET password = %s WHERE username = 'admin'", 
                    (admin_password,)
                )
        
        connection.commit()
    except Error as e:
        print(f"数据库连接失败或执行错误: {e}")
    finally:
        if cursor:
            cursor.close()
        if connection and connection.is_connected():
            connection.close()


# 用户注册路由
@app.route('/register', methods=['POST'])
@jwt_required()
def register():
    username = request.json.get('username', None)
    password = request.json.get('password', None)

    if not username or not password:
        return jsonify({"message": "Missing username or password"}), 400

    conn = get_db_connection()
    if conn is None:
        return jsonify({"message": "Database connection failed"}), 500

    cursor = conn.cursor(buffered=True)  # 使用缓冲游标

    try:
        # 首先检查用户名是否已存在
        cursor.execute("SELECT * FROM users WHERE username = %s", (username,))
        if cursor.fetchone():
            return jsonify({"message": "Username already exists"}), 409
        
        # 如果用户不存在，插入新用户
        cursor.execute(
            "INSERT INTO users (username, password) VALUES (%s, %s)", 
            (username, password)
        )
        conn.commit()
        
    except Error as e:
        print(f"Database error: {e}")
        return jsonify({"message": "Database error"}), 500
    finally:
        cursor.close()
        conn.close()

    return jsonify({"message": "User created successfully"}), 201

# 用户登录路由
@app.route('/login', methods=['POST'])
def login():
    username = request.json.get('username', None)
    password = request.json.get('password', None)

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True, buffered=True)

    cursor.execute("SELECT * FROM users WHERE username = %s", (username,))
    user_record = cursor.fetchone()

    cursor.close()
    conn.close()

    if user_record and user_record['password'] == password:
        access_token = create_access_token(identity=username)
        return jsonify(access_token=access_token)
    else:
        return jsonify({"message": "Bad username or password"}), 401

# 受保护的路由
@app.route('/private', methods=['GET'])
@jwt_required()
def protected():
    current_user = get_jwt_identity()
    return jsonify(logged_in_as=current_user), 200

# 不受保护的路由
@app.route('/public', methods=['GET'])
def unprotected():
    return jsonify(message="Success"), 200

if __name__ == '__main__':
    app.run(host='0.0.0.0', debug=True)
 