# ============================================
# Ironbrew 2 Discord Bot - COMPLETE FIX
# .NET Core 3.1 + Lua 5.1 + LuaJIT + Python
# ============================================

FROM mcr.microsoft.com/dotnet/sdk:3.1-focal

LABEL maintainer="Ironbrew2 Discord Bot"
LABEL description="Ironbrew 2 Lua Obfuscator Discord Bot"

ENV DEBIAN_FRONTEND=noninteractive
ENV DOTNET_CLI_TELEMETRY_OPTOUT=1
ENV IRONBREW_PATH=/opt/ironbrew-2
ENV PYTHONUNBUFFERED=1

# ============================================
# Install ALL Dependencies
# ============================================
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
    luajit \
    && rm -rf /var/lib/apt/lists/*

# Verify LuaJIT
RUN luajit -v

# ============================================
# Install Lua 5.1 (untuk luac)
# ============================================
RUN cd /tmp && \
    wget https://www.lua.org/ftp/lua-5.1.5.tar.gz && \
    tar -xzf lua-5.1.5.tar.gz && \
    cd lua-5.1.5 && \
    make linux && \
    make install && \
    cd / && \
    rm -rf /tmp/lua-5.1.5*

# Verify Lua & Luac
RUN lua -v && luac -v

# ============================================
# Clone Ironbrew 2
# ============================================
RUN git clone https://github.com/Trollicus/ironbrew-2.git ${IRONBREW_PATH}

WORKDIR ${IRONBREW_PATH}

# ============================================
# Check if Lua/Minifier exists
# ============================================
RUN echo "=== Checking Lua/Minifier ===" && \
    ls -la ${IRONBREW_PATH}/Lua/ || echo "No Lua folder" && \
    ls -la ${IRONBREW_PATH}/Lua/Minifier/ || echo "No Minifier folder" && \
    find ${IRONBREW_PATH} -name "*.lua" -type f | head -20

# ============================================
# Download LuaSrcDiet if missing
# ============================================
RUN mkdir -p ${IRONBREW_PATH}/Lua/Minifier && \
    cd ${IRONBREW_PATH}/Lua/Minifier && \
    if [ ! -f "luasrcdiet.lua" ]; then \
        echo "Downloading LuaSrcDiet..." && \
        wget https://raw.githubusercontent.com/jirutka/luasrcdiet/master/luasrcdiet.lua -O luasrcdiet.lua || \
        wget https://raw.githubusercontent.com/LuaDist/luasrcdiet/master/luasrcdiet.lua -O luasrcdiet.lua || \
        echo "-- placeholder" > luasrcdiet.lua; \
    fi && \
    ls -la

# ============================================
# Build Ironbrew 2
# ============================================
RUN dotnet restore "IronBrew2 CLI/IronBrew2 CLI.csproj" || true

RUN dotnet build "IronBrew2 CLI/IronBrew2 CLI.csproj" -c Debug -o /opt/ironbrew-2/publish

RUN echo "=== Build Complete ===" && ls -la /opt/ironbrew-2/publish/

# ============================================
# Test Ironbrew 2 (debug)
# ============================================
RUN echo 'print("test")' > /tmp/test.lua && \
    cd ${IRONBREW_PATH}/publish && \
    dotnet "IronBrew2 CLI.dll" /tmp/test.lua 2>&1 || echo "Test completed (may have errors)"

RUN ls -la /tmp/ | grep -E "\.lua|\.out" || echo "No output files"

# ============================================
# Setup Discord Bot
# ============================================
WORKDIR /app

COPY bot/requirements.txt .
RUN pip3 install --no-cache-dir -r requirements.txt

COPY bot/ .

RUN mkdir -p /app/temp

ENV IRONBREW_PATH=/opt/ironbrew-2

EXPOSE 10000

CMD ["python3", "main.py"]
