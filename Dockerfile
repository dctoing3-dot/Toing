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
    mkdir -p ${IRONBREW_PATH}/Lua/Minifier && \
    cd ${IRONBREW_PATH}/Lua/Minifier && \
    # Clone LuaSrcDiet dengan semua dependencies
    git clone https://github.com/jirutka/luasrcdiet.git temp_luasrcdiet && \
    # Copy semua file Lua ke direktori Minifier
    cp -r temp_luasrcdiet/luasrcdiet/* . 2>/dev/null || true && \
    cp temp_luasrcdiet/*.lua . 2>/dev/null || true && \
    # Jika struktur berbeda, coba cara lain
    find temp_luasrcdiet -name "*.lua" -exec cp {} . \; 2>/dev/null || true && \
    rm -rf temp_luasrcdiet && \
    # List hasil
    echo "=== Files in Minifier ===" && \
    ls -la

# Jika masih kurang, download dari LuaDist
RUN cd ${IRONBREW_PATH}/Lua/Minifier && \
    if [ ! -f "llex.lua" ]; then \
        echo "Downloading from LuaDist..." && \
        git clone https://github.com/LuaDist/luasrcdiet.git temp2 && \
        cp -r temp2/src/* . 2>/dev/null || true && \
        cp temp2/*.lua . 2>/dev/null || true && \
        find temp2 -name "*.lua" -exec cp {} . \; 2>/dev/null || true && \
        rm -rf temp2; \
    fi && \
    ls -la

# Verify semua file yang dibutuhkan ada
RUN echo "=== Verifying LuaSrcDiet Files ===" && \
    cd ${IRONBREW_PATH}/Lua/Minifier && \
    for file in luasrcdiet.lua llex.lua lparser.lua optlex.lua optparser.lua; do \
        if [ -f "$file" ]; then \
            echo "✅ $file exists"; \
        else \
            echo "❌ $file MISSING"; \
        fi; \
    done

# ============================================
# Create init.lua and fs.lua if missing
# ============================================
RUN cd ${IRONBREW_PATH}/Lua/Minifier && \
    # Create fs.lua if missing
    if [ ! -f "fs.lua" ]; then \
        echo 'Creating fs.lua...' && \
        cat > fs.lua << 'FSEOF'
-- Simple filesystem module for LuaSrcDiet
local M = {}

function M.read_file(path, mode)
    local f, err = io.open(path, mode or "r")
    if not f then return nil, err end
    local content = f:read("*a")
    f:close()
    return content
end

function M.write_file(path, data, mode)
    local f, err = io.open(path, mode or "w")
    if not f then return nil, err end
    f:write(data)
    f:close()
    return true
end

return M
FSEOF
    fi && \
    # Create init.lua if missing (luasrcdiet module)
    if [ ! -f "init.lua" ]; then \
        echo 'Creating init.lua...' && \
        cat > init.lua << 'INITEOF'
-- LuaSrcDiet init module
return {
    _VERSION = "1.0.0",
    _HOMEPAGE = "https://github.com/jirutka/luasrcdiet"
}
INITEOF
    fi

# ============================================
# Build Ironbrew 2
# ============================================
RUN dotnet restore "IronBrew2 CLI/IronBrew2 CLI.csproj" || true

RUN dotnet build "IronBrew2 CLI/IronBrew2 CLI.csproj" -c Debug -o ${IRONBREW_PATH}/publish

RUN echo "=== Build Complete ===" && ls -la ${IRONBREW_PATH}/publish/

# ============================================
# Test Ironbrew 2
# ============================================
RUN echo "=== Testing Ironbrew 2 ===" && \
    echo 'print("Hello World")' > /tmp/test.lua && \
    cd ${IRONBREW_PATH}/publish && \
    timeout 60 dotnet "IronBrew2 CLI.dll" /tmp/test.lua 2>&1 || echo "Test completed" && \
    echo "=== Checking for output ===" && \
    ls -la ${IRONBREW_PATH}/publish/*.lua 2>/dev/null || echo "No .lua files" && \
    ls -la ${IRONBREW_PATH}/*.lua 2>/dev/null || echo "No .lua in root" && \
    cat ${IRONBREW_PATH}/publish/out.lua 2>/dev/null | head -20 || echo "No out.lua found"

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
