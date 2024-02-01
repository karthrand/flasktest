#!/bin/bash
# 外部传入变量
SCRIPT_PATH=$1
RESOURCE_PATH=$2
ARCH=$3

# 设置主机密码
echo cloud@123 | passwd root --stdin
# 设置sshd相关
sed -i 's/#Port 22/Port 22/' /etc/ssh/sshd_config
sed -i 's/#PermitRootLogin yes/PermitRootLogin yes/' /etc/ssh/sshd_config
cd /etc/ssh
ssh-keygen -t rsa -f /etc/ssh/ssh_host_rsa_key -N ''
ssh-keygen -t ecdsa -f /etc/ssh/ssh_host_ecdsa_key -N ''
ssh-keygen -t ed25519 -f /etc/ssh/ssh_host_ed25519_key -N ''