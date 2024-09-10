import os
import secrets
import configparser
import subprocess
import shutil
import re
import time
from flask import Flask, jsonify, request
from flask_jwt_extended import JWTManager, jwt_required, create_access_token, get_jwt_identity
import mysql.connector
from mysql.connector import Error
from loguru import logger as log

# 全局变量
## flask配置文件地址
config_file = "/data/project/config.ini"
db_config = {}
default_admin_password = ""


# 检查端口是否启动的函数
def check_port(port):
    try:
        # 执行netstat命令
        result = subprocess.run(["netstat", "-ntlp"], stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, check=True)
        # 搜索端口号
        if re.search(f":{port}\\s", result.stdout):
            return True
        else:
            return False
    except subprocess.CalledProcessError as e:
        print(f"An error occurred: {e}")
        return False


def check_and_start_local_mysql():
    log.info("检查本地mysql服务")
    # 检查是否已经启动
    if check_port(3306):
        log.info("本地mysql已经启动")
    else:
        # 启动本地数据库
        start_mysql_command = "mysqld -u mysql"
        try:
            # 运行初始化命令
            # 使用subprocess.Popen来执行命令，使其在后台运行
            process = subprocess.Popen(start_mysql_command, shell=True)
            # 打印出进程ID
            log.debug(f"mysqld started with PID {process.pid}")
            for index in range(10):
                if check_port(3306):
                    break
                else:
                    time.sleep(1)
            else:
                raise Exception("数据库端口未启动")
            log.info("启动本地数据库成功")
        except subprocess.CalledProcessError as e:
            # 打印错误信息，并退出程序
            log.error("启动本地数据库失败 ", e)
            raise


# 检查日志判断数据库是否完成初始化
def check_innodb_initialization():
    try:
        # 执行grep命令搜索日志条目
        result = subprocess.run(["grep", "InnoDB initialization has ended", "/var/log/mysql/mysqld.log"], text=True, capture_output=True, check=True)
        # 检查结果中是否有输出
        if result.stdout:
            log.info("数据库已完成初始化，跳过")
            return True
        else:
            log.info("数据库未完成初始化，进行初始化")
            return False
    except subprocess.CalledProcessError:
        # grep没有找到匹配项
        log.info("数据库未完成初始化，进行初始化")
        return False


def get_local_db_datadir(local_db_config):
    # 使用configparser来解析MYSQL配置文件
    log.info(f"加载mysql配置文件: {local_db_config}")
    config = configparser.ConfigParser()
    config.read(local_db_config)

    # 获取datadir的值
    data_directory = config["mysqld"].get("datadir", None)
    if data_directory is None:
        raise Exception("无法在配置文件中找到 'datadir' 设置")
    else:
        # 检查datadir是否存在
        if not os.path.exists(data_directory):
            print(f"'{data_directory}' 不存在，正在创建...")
            # 创建数据目录
            os.makedirs(data_directory)
        return data_directory


def init_config():
    # 初始化
    global admin_password
    global db_config
    # 读取配置文件默认值
    # config.ini文件不存在时使用的默认值
    default_config = {
        "db_default_host": "127.0.0.1",
        "db_default_root_password": "root@123",
        "db_default_user_name": "flask",
        "db_default_user_password": "flask@123",
        "db_default_database_name": "flask",
        "local_db_config": "/etc/my.cnf.d/mysql-server.cnf",
        "default_admin_password": "admin@123",
    }

    # 创建一个带有默认值的ConfigParser对象
    config = configparser.ConfigParser(defaults=default_config)
    config.read(config_file, encoding="UTF-8")
    db_default_host = config["DB"].get("db_default_host")
    db_default_root_password = config["DB"].get("db_default_root_password")
    db_default_user_name = config["DB"].get("db_default_user_name")
    db_default_user_password = config["DB"].get("db_default_user_password")
    db_default_database_name = config["DB"].get("db_default_database_name")
    local_db_config = config["DB"].get("local_db_config")
    default_admin_password = config["DB"].get("default_admin_password")

    # 读取环境变量
    db_host = os.getenv("DB_HOST", db_default_host)
    db_root_password = os.getenv("DB_ROOT_PASSWORD", db_default_root_password)
    db_user = os.getenv("DB_USER", db_default_user_name)
    db_password = os.getenv("DB_PASSWORD", db_default_user_password)
    db_database_name = os.getenv("DB_NAME", db_default_database_name)
    use_ext_db = os.getenv("EXT_DB", "false")

    admin_password = os.getenv("ADMIN_PASSWORD", default_admin_password)

    # 数据库配置信息
    db_config = {"host": db_host, "user": db_user, "password": db_password, "database": db_database_name}

    # 使用本地数据库，需要进行初始化
    log.debug(f"use_ext_db： {use_ext_db}")
    if use_ext_db == "false":
        log.info("当前应用使用本地数据库")

        if not check_innodb_initialization():
            log.info("初始化本地mysql")
            # 先删除数据目录信息
            try:
                data_directory = get_local_db_datadir(local_db_config)
                # 删除目录及其所有内容
                shutil.rmtree(data_directory)
                log.info(f"目录 {data_directory} 已被删除")

                # 重新创建目录
                os.makedirs(data_directory)
                log.info(f"目录 {data_directory} 已被重新创建")

            except PermissionError:
                raise Exception(f"错误: 没有足够的权限来删除或创建 {data_directory}，请使用root用户运行此脚本")
            except Exception as e:
                raise Exception(f"发生错误: {e}")

            # 将目录所有权改回给 MySQL 用户和组
            try:
                subprocess.run(["chown", "-R", "mysql:mysql", data_directory], check=True)
                log.info(f"已将 {data_directory} 的所有权更改为 mysql 用户和组。")
            except Exception as e:
                log.error(f"更改权限时发生错误: {e}")
                raise

            try:
                subprocess.run(["chmod", "-R", "700", data_directory], check=True)
                log.info(f"更改{data_directory}目录权限为700")

            except subprocess.CalledProcessError as e:
                log.info(f"更改{data_directory}目录权限异常")

            # 未进行初始化时
            init_mysql_command = ["mysqld", "-u", "mysql", "--initialize-insecure"]
            try:
                # 运行初始化命令
                subprocess.run(init_mysql_command, check=True)
                log.info("初始化本地数据库成功")
            except subprocess.CalledProcessError as e:
                # 打印错误信息，并退出程序
                log.error("初始化本地数据库失败 ", e)
                raise

            check_and_start_local_mysql()

            # 创建默认root和普通用户
            sql_commands = f"""
            CREATE DATABASE IF NOT EXISTS flask;
            ALTER USER 'root'@'localhost' IDENTIFIED BY '{db_root_password}';
            CREATE USER IF NOT EXISTS '{db_user}'@'localhost' IDENTIFIED BY '{db_password}';
            GRANT ALL PRIVILEGES ON *.* TO '{db_user}'@'localhost';
            FLUSH PRIVILEGES;
            """
            try:
                # 执行mysql命令
                proc = subprocess.run(
                    ["mysql", "-u", "root"], input=sql_commands, text=True, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE
                )
                print(proc.stdout)
                log.info(f"本地数据库root密码修改成功, 用户'{db_user}' 已创建.")
            except subprocess.CalledProcessError as e:
                log.error("执行mysql初始化库命令失败:", e.stderr)

        else:
            check_and_start_local_mysql()


app = Flask(__name__)

# 配置JWT密钥
## 如果环境变量未配置JWT_SECRET_KEY，则生成一个安全的密钥
secret_key = secrets.token_urlsafe(64)
app.config["JWT_SECRET_KEY"] = os.environ.get("JWT_SECRET_KEY", secret_key)
jwt = JWTManager(app)


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
        print(f"db_config: {db_config}")
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
        if not admin_password:
            raise ValueError("环境变量 ADMIN_PASSWORD 未设置")

        if not admin_info:
            # 如果admin不存在，则插入admin用户
            cursor.execute("INSERT INTO users (username, password) VALUES (%s, %s)", ("admin", admin_password))
        else:
            # 如果环境变量中的密码与数据库中存储的密码不一致，则更新数据库中的密码
            if admin_info[2] != admin_password:  # 假定密码存储在返回元组的第三个位置（索引2）
                cursor.execute("UPDATE users SET password = %s WHERE username = 'admin'", (admin_password,))

        connection.commit()
    except Error as e:
        print(f"数据库连接失败或执行错误: {e}")
    finally:
        if cursor:
            cursor.close()
        if connection and connection.is_connected():
            connection.close()


# 用户注册路由
@app.route("/register", methods=["POST"])
@jwt_required()
def register():
    username = request.json.get("username", None)
    password = request.json.get("password", None)

    if not username or not password:
        return jsonify({"message": "Missing username or password", "code": 400}), 400

    conn = get_db_connection()
    if conn is None:
        return jsonify({"message": "Database connection failed", "code": 500}), 500

    cursor = conn.cursor(buffered=True)  # 使用缓冲游标

    try:
        # 首先检查用户名是否已存在
        cursor.execute("SELECT * FROM users WHERE username = %s", (username,))
        if cursor.fetchone():
            return jsonify({"message": "Username already exists", "code": 409}), 409

        # 如果用户不存在，插入新用户
        cursor.execute("INSERT INTO users (username, password) VALUES (%s, %s)", (username, password))
        conn.commit()

    except Error as e:
        print(f"Database error: {e}")
        return jsonify({"message": "Database error", "code": 500}), 500
    finally:
        cursor.close()
        conn.close()

    return jsonify({"message": "User created successfully", "code": 201}), 201


# 用户登录路由
@app.route("/login", methods=["POST"])
def login():
    username = request.json.get("username", None)
    password = request.json.get("password", None)

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True, buffered=True)

    cursor.execute("SELECT * FROM users WHERE username = %s", (username,))
    user_record = cursor.fetchone()

    cursor.close()
    conn.close()

    if user_record and user_record["password"] == password:
        access_token = create_access_token(identity=username)
        return jsonify({"message": {"access_token": access_token}, "code": 200})
    else:
        return jsonify({"message": "Bad username or password", "code": 401}), 401


# 受保护的路由
@app.route("/private", methods=["GET"])
@jwt_required()
def protected():
    current_user = get_jwt_identity()
    return jsonify({"message": {"logged_in_as": current_user}, "code": 200}), 200


# 不受保护的路由
@app.route("/public", methods=["GET"])
def unprotected():
    return jsonify({"message": "Success", "code": 200}), 200


if __name__ == "__main__":
    init_config()
    app.run(host="0.0.0.0", debug=True)
