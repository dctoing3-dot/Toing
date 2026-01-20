# ============================================
# Ironbrew 2 Discord Bot - Alternative Build
# ============================================

FROM mcr.microsoft.com/dotnet/sdk:3.1-focal

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
# Clone Ironbrew 2
# ============================================
RUN git clone https://github.com/Trollicus/ironbrew-2.git ${IRONBREW_PATH}

WORKDIR ${IRONBREW_PATH}

# ============================================
# Debug: List available configurations
# ============================================
RUN echo "=== Solution Content ===" && \
    cat IronBrew2_Core.sln | grep -A5 "GlobalSection(SolutionConfigurationPlatforms)" || true

RUN echo "=== Project files ===" && \
    find . -name "*.csproj" -exec echo "Found: {}" \;

# ============================================
# Build Ironbrew 2
# Try multiple approaches
# ============================================

# Approach 1: Build specific project dengan Debug
RUN dotnet restore "IronBrew2 CLI/IronBrew2 CLI.csproj" || true

RUN dotnet build "IronBrew2 CLI/IronBrew2 CLI.csproj" -c Debug -o /opt/ironbrew-2/publish || \
    dotnet build "IronBrew2 CLI/IronBrew2 CLI.csproj" -o /opt/ironbrew-2/publish || \
    (echo "Trying solution build..." && dotnet build -c Debug -o /opt/ironbrew-2/publish)

# Verify output
RUN echo "=== Published Files ===" && \
    ls -la /opt/ironbrew-2/publish/

# Find the actual DLL name
RUN echo "=== DLL Files ===" && \
    find /opt/ironbrew-2/publish -name "*.dll" -type f

# ============================================
# Setup Discord Bot
# ============================================
WORKDIR /app

COPY bot/requirements.txt .
RUN pip3 install --no-cache-dir -r requirements.txt

COPY bot/ .

RUN mkdir -p /app/input /app/output /app/temp

# Set DLL path - akan di-update setelah tahu nama exact
ENV IRONBREW_DLL=/opt/ironbrew-2/publish/IronBrew2.CLI.dll

EXPOSE 10000

CMD ["python3", "main.py"]
