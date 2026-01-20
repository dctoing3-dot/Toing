# ============================================
# Ironbrew 2 Discord Bot - COMPLETE FIXED
# .NET Core 3.1 + Lua 5.1 + LuaJIT + LuaSrcDiet
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
RUN echo "=== LuaJIT Version ===" && luajit -v

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
RUN echo "=== Lua Version ===" && lua -v
RUN echo "=== Luac Version ===" && luac -v

# ============================================
# Clone Ironbrew 2
# ============================================
RUN git clone https://github.com/Trollicus/ironbrew-2.git ${IRONBREW_PATH}

WORKDIR ${IRONBREW_PATH}

# ============================================
# Download Complete LuaSrcDiet
# ============================================
RUN echo "=== Setting up LuaSrcDiet ===" && \
    mkdir -p ${IRONBREW_PATH}/Lua/Minifier

# Clone LuaSrcDiet dari jirutka
RUN cd ${IRONBREW_PATH}/Lua/Minifier && \
    git clone https://github.com/jirutka/luasrcdiet.git temp_lsd || true && \
    if [ -d "temp_lsd/luasrcdiet" ]; then \
        cp -r temp_lsd/luasrcdiet/* . ; \
    elif [ -d "temp_lsd/src" ]; then \
        cp -r temp_lsd/src/* . ; \
    else \
        find temp_lsd -name "*.lua" -exec cp {} . \; ; \
    fi && \
    rm -rf temp_lsd && \
    ls -la

# Jika masih kurang, clone dari LuaDist
RUN cd ${IRONBREW_PATH}/Lua/Minifier && \
    if [ ! -f "llex.lua" ]; then \
        echo "Downloading from LuaDist..." && \
        git clone https://github.com/LuaDist/luasrcdiet.git temp2 || true && \
        if [ -d "temp2/src" ]; then cp -r temp2/src/* . ; fi && \
        find temp2 -name "*.lua" -exec cp {} . \; 2>/dev/null || true && \
        rm -rf temp2 ; \
    fi && \
    ls -la

# ============================================
# Create fs.lua (filesystem module)
# ============================================
RUN echo '-- Simple filesystem module for LuaSrcDiet\n\
local M = {}\n\
\n\
function M.read_file(path, mode)\n\
    local f, err = io.open(path, mode or "r")\n\
    if not f then return nil, err end\n\
    local content = f:read("*a")\n\
    f:close()\n\
    return content\n\
end\n\
\n\
function M.write_file(path, data, mode)\n\
    local f, err = io.open(path, mode or "w")\n\
    if not f then return nil, err end\n\
    f:write(data)\n\
    f:close()\n\
    return true\n\
end\n\
\n\
return M' > ${IRONBREW_PATH}/Lua/Minifier/fs.lua

# ============================================
# Create init.lua (luasrcdiet module)
# ============================================
RUN echo '-- LuaSrcDiet init module\n\
return {\n\
    _VERSION = "1.0.0",\n\
    _HOMEPAGE = "https://github.com/jirutka/luasrcdiet"\n\
}' > ${IRONBREW_PATH}/Lua/Minifier/init.lua

# ============================================
# Verify LuaSrcDiet files
# ============================================
RUN echo "=== Verifying LuaSrcDiet Files ===" && \
    cd ${IRONBREW_PATH}/Lua/Minifier && \
    ls -la && \
    echo "--- Checking required files ---" && \
    for file in luasrcdiet.lua llex.lua lparser.lua optlex.lua optparser.lua fs.lua init.lua; do \
        if [ -f "$file" ]; then \
            echo "OK: $file" ; \
        else \
            echo "MISSING: $file" ; \
        fi ; \
    done

# ============================================
# Build Ironbrew 2
# ============================================
RUN dotnet restore "IronBrew2 CLI/IronBrew2 CLI.csproj" || true

RUN dotnet build "IronBrew2 CLI/IronBrew2 CLI.csproj" -c Debug -o ${IRONBREW_PATH}/publish

RUN echo "=== Build Complete ===" && ls -la ${IRONBREW_PATH}/publish/

# ============================================
# Test Ironbrew 2 (optional debug)
# ============================================
RUN echo "=== Testing Ironbrew 2 ===" && \
    echo 'print("Hello")' > /tmp/test.lua && \
    cd ${IRONBREW_PATH}/publish && \
    timeout 30 dotnet "IronBrew2 CLI.dll" /tmp/test.lua 2>&1 || echo "Test done" && \
    ls -la *.lua 2>/dev/null || echo "No output lua files" && \
    rm -f /tmp/test.lua

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
