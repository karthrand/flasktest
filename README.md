# 说明
- 此为flask简单测试镜像

# 支持的功能




# 镜像构建


# 部署
## 创建默认docker网络
```bash
docker network create --driver bridge --subnet 172.20.0.0/16 --gateway 172.20.0.1 test
```



## nginx设置转发(可选)
- 查找nginx的配置文件，如/etc/nginx/nginx.conf
- 