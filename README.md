# 说明

- 基于flask的简单接口模拟测试镜像

# 支持的功能

## flask服务

| 端口 | 协议 | 路径      | 鉴权 | 方法 | 功能                             |
| ---- | ---- | --------- | ---- | ---- | -------------------------------- |
| 5000 | http | /public   | 否   | GET  | 不需要鉴权，message返回"success" |
| 5000 | http | /login    | 是   | POST | 用户登录，返回token              |
| 5000 | http | /registry | 是   | POST | 注册用户                         |
| 5000 | http | /private  | 上   | GET  | 返回请求用户信息                 |

注：

- 默认管理员账户：admin
- 默认管理员密码：admin@123
- 可通过环境变量ADMIN_PASSWORD在启动时设置管理员密码

## 数据库

- 默认使用独立、外置的mysql8数据库容器
- 可设置环境变量EXT_DB = false，使用flask容器内置的mysql
- 可更改docker-compose自定义已有的数据库，配置DB开头的环境变量即可

# 部署

* 使用docker-compose管理生命周期

## 安装Docker

- docker安装，请参考[官方文档](https://docs.docker.com/get-docker/)

## 创建默认docker网络

- 使用Linux终端或者Windows终端(如PowerShell))执行命令，创建自定义网络，如test
- docker-compose无法使用默认的bridge网络，因此必须新建
- subnet(子网)、gateway(网关)和网络名称(test)，可根据需求更改

```bash
docker network create --driver bridge --subnet 172.20.0.0/16 --gateway 172.20.0.1 test
```

## 拉取镜像(可选)

- 启动docker-compose时会自动拉取

```bash
docker pull karthrand/flasktest:latest
```

## 创建目录与卷(可选)

- 使用卷挂载的目的是为了将数据保存在宿主机上，使得容器停止再启动或者容器重建后，数据不丢失
- docker-compose中挂载卷的方式有三种
  - 创建docker管理的卷
  - 使用绝对路径挂载卷
  - 使用相对路径挂载卷
- 请根据实际需求选择操作系统和卷的挂载方式、挂载目录

### Linux

- 使用docker卷

  - 创建的卷实际默认目录为/var/lib/docker/volumes/

    ```bash
    docker volume create flasktest
    docker volume create mysql
    ```
- 使用绝对路径

```bash
# 创建存放docker-compose的目录
mkdir -p /data/compose/flasktest
# 创建存放数据的目录
mkdir -p /data/flasktest/project
mkdir -p /data/mysql
```

- 使用相对路径

```bash
mkdir -p /data/compose/flasktest
mkdir -p /data/compose/flasktest/flasktest/project
mkdir -p /data/compose/flasktest/mysql
```

### Windows

- 使用docker卷
  - 打开Docker Desktop，进入Volume界面后点击右上角Create，创建新的存储，如flasktest
  - 以相同的方法创建mysql挂载卷，如mysql

[ ![flasktest-01-volume.webp](https://img.oudezhinu.com/img/1/flasktest-01-volume.webp)](https://img.oudezhinu.com/img/1/flasktest-01-volume.webp)

- 使用绝对路径
  - Windows右键创建对应文件夹即可，如
    - D:\Programs\Docker\compose\flasktest
    - D:\Programs\Docker\data\flasktest\project
    - D:\Programs\Docker\data\mysql
- 使用相对路径：
  - Windows右键创建对应文件夹即可，如

    - D:\Programs\Docker\compose\flasktest
    - D:\Programs\Docker\compose\flasktest\flasktest\project
    - D:\Programs\Docker\compose\flasktest\mysql

## 创建docker-compose.yml文件

### Linux

- 获取Linux下docker-compose.yml文件
  - [github](https://github.com/karthrand/flasktest/blob/main/docker-compose-linux.yml)
  - [gitee](https://gitee.com/karthrand/flasktest/blob/main/docker-compose-linux.yml)
- 更改docker-compose-linux.yml为docker-compose.yml

### Windows

- 获取Windows下docker-compose.yml文件
  - [github](https://github.com/karthrand/flasktest/blob/main/docker-compose-windows.yml)
  - [gitee](https://gitee.com/karthrand/flasktest/blob/main/docker-compose-windows.yml)
- 更改docker-compose-windows.yml为docker-compose.yml

## 启动容器

- 使用终端进入到docker-compose.yml文件所在目录

  - windows下终端使用poweshell、wsl、cmd皆可
  - windows

    ```powershell
    cd D:\Programs\Docker\compose\flasktest
    ```
  - linux

    ```bash
    cd /data/compose/flasktest
    ```
- 启动容器

  ```bash
  docker compose up -d
  ```
- 其他命令(可选)

  - 停止容器

    ```bash
    docker compose stop
    ```
  - 销毁容器

    ```bash
    docker compose down
    ```

## nginx设置转发(可选)

- 查找nginx的配置文件，如/etc/nginx/nginx.conf
- 添加转发规则

  - 默认flasktest的端口为5000
  - http模块下80端口的server添加以下内容，类似
  - 此处以flasktest的容器为172.20.0.3为例，请根据实际更改

```yaml
http {
    # http模块的配置，此处省略
    ......
    server {
        listen       80;
        server_name  nginx;
        root         /usr/share/nginx/html;
        index  index.html index.htm;

        # Load configuration files for the default server block.
        include /etc/nginx/default.d/*.conf;

        location / {
  
        }

        location /public {
            proxy_pass http://172.20.0.3:5000/public;
            proxy_set_header Authorization $http_authorization;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
        }

        location /private {
            proxy_pass http://172.20.0.3:5000/private;
            proxy_set_header Authorization $http_authorization;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
        }

        location /register {
            proxy_pass http://172.20.0.3:5000/register;
            proxy_set_header Authorization $http_authorization;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
        }

        location /login {
            proxy_pass http://172.20.0.3:5000/login;
            proxy_set_header Authorization $http_authorization;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
        }

        error_page 404 /404.html;
            location = /40x.html {
        }

        error_page 500 502 503 504 /50x.html;
            location = /50x.html {
        }
    }
}
```

- 校验配置文件是否正确并生效

  ```bash
  # 检测配置文件
  nginx -t
  # nginx重新加载
  nginx -s reload
  ```
