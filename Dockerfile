# ============================================
# Ironbrew 2 Discord Bot - FINAL FIXED
# ============================================

FROM mcr.microsoft.com/dotnet/sdk:3.1-focal

ENV DEBIAN_FRONTEND=noninteractive
ENV DOTNET_CLI_TELEMETRY_OPTOUT=1
ENV IRONBREW_PATH=/opt/ironbrew-2
ENV PYTHONUNBUFFERED=1

# ============================================
# Install Dependencies
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

RUN echo "=== LuaJIT ===" && luajit -v

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

RUN echo "=== Lua ===" && lua -v
RUN echo "=== Luac ===" && luac -v

# ============================================
# CREATE SYMLINKS - PENTING!
# Ironbrew mencari di /usr/bin/
# ============================================
RUN ln -sf /usr/local/bin/lua /usr/bin/lua && \
    ln -sf /usr/local/bin/luac /usr/bin/luac && \
    ln -sf /usr/bin/luajit /usr/bin/luajit || true

# Verify symlinks
RUN echo "=== Verify Paths ===" && \
    which lua && \
    which luac && \
    which luajit && \
    ls -la /usr/bin/lua* || true

# ============================================
# Clone Ironbrew 2
# ============================================
RUN git clone https://github.com/Trollicus/ironbrew-2.git ${IRONBREW_PATH}

WORKDIR ${IRONBREW_PATH}

# ============================================
# Setup LuaSrcDiet
# ============================================
RUN mkdir -p ${IRONBREW_PATH}/Lua/Minifier

RUN cd ${IRONBREW_PATH}/Lua/Minifier && \
    git clone https://github.com/jirutka/luasrcdiet.git temp_lsd || true && \
    if [ -d "temp_lsd/luasrcdiet" ]; then cp -r temp_lsd/luasrcdiet/* . ; \
    elif [ -d "temp_lsd/src" ]; then cp -r temp_lsd/src/* . ; \
    else find temp_lsd -name "*.lua" -exec cp {} . \; ; fi && \
    rm -rf temp_lsd && ls -la

RUN cd ${IRONBREW_PATH}/Lua/Minifier && \
    if [ ! -f "llex.lua" ]; then \
        git clone https://github.com/LuaDist/luasrcdiet.git temp2 || true && \
        if [ -d "temp2/src" ]; then cp -r temp2/src/* . ; fi && \
        find temp2 -name "*.lua" -exec cp {} . \; 2>/dev/null || true && \
        rm -rf temp2 ; \
    fi && ls -la

# Create fs.lua
RUN printf '%s\n' \
    '-- Filesystem module' \
    'local M = {}' \
    'function M.read_file(path, mode)' \
    '    local f, err = io.open(path, mode or "r")' \
    '    if not f then return nil, err end' \
    '    local content = f:read("*a")' \
    '    f:close()' \
    '    return content' \
    'end' \
    'function M.write_file(path, data, mode)' \
    '    local f, err = io.open(path, mode or "w")' \
    '    if not f then return nil, err end' \
    '    f:write(data)' \
    '    f:close()' \
    '    return true' \
    'end' \
    'return M' > ${IRONBREW_PATH}/Lua/Minifier/fs.lua

# Create init.lua
RUN printf '%s\n' \
    '-- LuaSrcDiet init' \
    'return {' \
    '    _VERSION = "1.0.0",' \
    '    _HOMEPAGE = "https://github.com/jirutka/luasrcdiet"' \
    '}' > ${IRONBREW_PATH}/Lua/Minifier/init.lua

# Verify files
RUN echo "=== LuaSrcDiet Files ===" && ls -la ${IRONBREW_PATH}/Lua/Minifier/

# ============================================
# Build Ironbrew 2
# ============================================
RUN dotnet restore "IronBrew2 CLI/IronBrew2 CLI.csproj" || true

RUN dotnet build "IronBrew2 CLI/IronBrew2 CLI.csproj" -c Debug -o ${IRONBREW_PATH}/publish

RUN echo "=== Build ===" && ls -la ${IRONBREW_PATH}/publish/

# ============================================
# TEST Ironbrew 2
# ============================================
RUN echo "=== Test Ironbrew ===" && \
    echo 'print("Hello")' > /tmp/test.lua && \
    cd ${IRONBREW_PATH}/publish && \
    timeout 60 dotnet "IronBrew2 CLI.dll" /tmp/test.lua 2>&1 && \
    echo "=== Output Files ===" && \
    ls -la *.lua 2>/dev/null || echo "Checking other locations..." && \
    ls -la ${IRONBREW_PATH}/publish/out.lua 2>/dev/null && \
    head -5 ${IRONBREW_PATH}/publish/out.lua 2>/dev/null || echo "No out.lua" && \
    rm -f /tmp/test.lua ${IRONBREW_PATH}/publish/out.lua ${IRONBREW_PATH}/publish/*.lua 2>/dev/null || true

# ============================================
# Setup Bot
# ============================================
WORKDIR /app

COPY bot/requirements.txt .
RUN pip3 install --no-cache-dir -r requirements.txt

COPY bot/ .

RUN mkdir -p /app/temp

ENV IRONBREW_PATH=/opt/ironbrew-2

EXPOSE 10000

CMD ["python3", "main.py"]
