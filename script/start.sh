#!/bin/bash
ENV_PROJECT_PATH=$1

#启动flask服务
nohup python3 ${ENV_PROJECT_PATH}/main.py > output.log 2>&1 &

#启动sshd服务
/usr/sbin/sshd -d

#等待回调执行完，主进程再退出
wait
