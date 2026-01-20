# ============================================
# Ironbrew 2 Discord Bot
# .NET Core 3.1 + Lua 5.1 + Python Discord Bot
# ============================================

FROM mcr.microsoft.com/dotnet/sdk:3.1-focal

LABEL maintainer="Ironbrew2 Discord Bot"
LABEL description="Ironbrew 2 Lua Obfuscator Discord Bot"

ENV DEBIAN_FRONTEND=noninteractive
ENV DOTNET_CLI_TELEMETRY_OPTOUT=1
ENV IRONBREW_PATH=/opt/ironbrew-2
ENV PYTHONUNBUFFERED=1

# Install dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    wget \
    curl \
    build-essential \
    libreadline-dev \
    unzip \
    ca-certificates \
    python3 \
    python3-pip \
    python3-dev \
    && rm -rf /var/lib/apt/lists/*

# ... (sama seperti sebelumnya sampai build)

# ============================================
# Test Ironbrew 2 CLI
# ============================================
RUN echo 'print("test")' > /tmp/test.lua && \
    dotnet "/opt/ironbrew-2/publish/IronBrew2 CLI.dll" /tmp/test.lua > /tmp/test_output.txt 2>&1 || true && \
    echo "=== CLI Test Output ===" && \
    cat /tmp/test_output.txt && \
    echo "=== Output Length ===" && \
    wc -c /tmp/test_output.txt && \
    rm -f /tmp/test.lua /tmp/test_output.txt

# ... (lanjutan sama)
# ============================================
# Install Lua 5.1
# ============================================
RUN cd /tmp && \
    wget https://www.lua.org/ftp/lua-5.1.5.tar.gz && \
    tar -xzf lua-5.1.5.tar.gz && \
    cd lua-5.1.5 && \
    make linux && \
    make install && \
    cd / && \
    rm -rf /tmp/lua-5.1.5*

RUN lua -v

# ============================================
# Clone & Build Ironbrew 2
# ============================================
RUN git clone https://github.com/Trollicus/ironbrew-2.git ${IRONBREW_PATH}

WORKDIR ${IRONBREW_PATH}

RUN dotnet restore "IronBrew2 CLI/IronBrew2 CLI.csproj" || true

RUN dotnet build "IronBrew2 CLI/IronBrew2 CLI.csproj" -c Debug -o /opt/ironbrew-2/publish || \
    dotnet build "IronBrew2 CLI/IronBrew2 CLI.csproj" -o /opt/ironbrew-2/publish

RUN echo "=== Build Complete ===" && ls -la /opt/ironbrew-2/publish/

# ============================================
# Setup Discord Bot
# ============================================
WORKDIR /app

COPY bot/requirements.txt .
RUN pip3 install --no-cache-dir -r requirements.txt

COPY bot/ .

RUN mkdir -p /app/temp

ENV IRONBREW_CLI_DLL="/opt/ironbrew-2/publish/IronBrew2 CLI.dll"

EXPOSE 10000

CMD ["python3", "main.py"]
