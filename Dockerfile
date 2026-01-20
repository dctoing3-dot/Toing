# ============================================
# Ironbrew 2 Discord Bot
# .NET Core 3.1 + Lua 5.1 + Python Discord Bot
# ============================================

FROM mcr.microsoft.com/dotnet/sdk:3.1-focal

LABEL maintainer="your-email@example.com"
LABEL description="Ironbrew 2 Discord Bot"

# Environment variables
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
    wget http://www.lua.org/ftp/lua-5.1.5.tar.gz && \
    tar -xzf lua-5.1.5.tar.gz && \
    cd lua-5.1.5 && \
    make linux && \
    make install && \
    cd / && \
    rm -rf /tmp/lua-5.1.5*

# Verify Lua
RUN lua -v

# ============================================
# Clone & Build Ironbrew 2
# ============================================
RUN git clone https://github.com/Trollicus/ironbrew-2.git ${IRONBREW_PATH}

WORKDIR ${IRONBREW_PATH}

RUN dotnet restore && \
    dotnet build -c Release && \
    dotnet publish -c Release -o /opt/ironbrew-2/publish

# ============================================
# Setup Discord Bot
# ============================================
WORKDIR /app

# Copy bot files
COPY bot/requirements.txt .
RUN pip3 install --no-cache-dir -r requirements.txt

COPY bot/ .

# Create directories
RUN mkdir -p /app/input /app/output /app/temp

# Make ironbrew accessible
ENV IRONBREW_DLL=/opt/ironbrew-2/publish/IronBrew2.dll

# Expose port (Render membutuhkan ini)
EXPOSE 10000

# Start bot
CMD ["python3", "main.py"]
