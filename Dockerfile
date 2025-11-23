# ---- Builder Stage ----
# 使用 micromamba 镜像作为构建环境
FROM mambaorg/micromamba:1.5.6 as builder

# 复制环境定义文件
COPY --chown=$MAMBA_USER:$MAMBA_USER environment.yml /tmp/environment.yml

# 在一个单独的前缀中创建环境，并安装所有依赖
RUN micromamba create -p /tmp/env -f /tmp/environment.yml && \
    micromamba clean --all --yes

# ---- Final Stage ----
# 使用一个非常小的 "distroless" 风格镜像作为最终运行环境
FROM mambaorg/micromamba:1.5.6 as final

# 从构建阶段复制已安装好的环境
COPY --from=builder /tmp/env /opt/conda/

# 复制你的应用代码
COPY . /app
WORKDIR /app

# 设置 PATH，以便可以直接调用 python
ENV PATH="/opt/conda/bin:$PATH"

# 定义容器启动时执行的默认命令
CMD ["python", "main.py"]
