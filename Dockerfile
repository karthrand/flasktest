ARG ARCH=amd64
FROM karthrand/openeuler-${ARCH}:22.03-lts-sp2
LABEL maintainer="karthrand"
LABEL "description.content" = "simple flask test image"

# 目录变量, 各种文件默认存放目录
ARG WORK_PATH=/data
ARG SCRIPT_PATH=$WORK_PATH/script
ARG RESOURCE_PATH=$WORK_PATH/resource
ARG PROJECT_PATH=$WORK_PATH/project
ENV ENV_PROJECT_PATH=${PROJECT_PATH}
ENV ENV_SCRIPT_PATH=${SCRIPT_PATH}

# 时区环境变量，设置为东八区
ENV  TZ=Asia/Shanghai
# 中文编码兼容
ENV LANG=C.UTF-8

# 拷贝文件夹
COPY script $SCRIPT_PATH
COPY resource $RESOURCE_PATH

# 安装必备软件

RUN  chmod +x ${SCRIPT_PATH}/start.sh && chmod +x ${SCRIPT_PATH}/init.sh  && \
# 下面为内网时，使用内网源
# mv -f $RESOURCE_PATH/source/openEuler.repo  /etc/yum.repos.d/openEuler.repo && \
dnf -y update && dnf -y install net-tools iproute wget vim gcc gcc-c++ bind-utils python3-pip passwd hostname openssh findutils systemd unzip iputils lrzsz  && \
# 配置pip阿里源
mkdir ~/.pip && cp ${RESOURCE_PATH}/pip.conf ~/.pip && \
# 安装pip包相关，缓存层级
python3 -m pip install -r ${RESOURCE_PATH}/requirements.txt && \
# 其他运行任务
ln -fs /usr/share/zoneinfo/${TZ} /etc/localtime && echo ${TZ} > /etc/timezone && \
# 执行bash初始化脚本
bash ${SCRIPT_PATH}/init.sh ${SCRIPT_PATH} ${RESOURCE_PATH} ${ARCH} && \
# python指向python3
ln -sf /usr/bin/python3 /usr/bin/python && \
# 减少层级，清理缓存
dnf clean all && \
rm -rf /var/cache/dnf/
# 端口
EXPOSE 5000

# 启动脚本
ENTRYPOINT  ["/usr/local/bin/dumb-init", "--"]
CMD ["bash", "-c", "${ENV_SCRIPT_PATH}/start.sh ${ENV_PROJECT_PATH}"]