# Build Instructions

## Windows (Pre-built available)

Download from releases: https://github.com/bobberdolle1/BeamNG.WorldForge/releases

## Linux / macOS (Build from source)

### Prerequisites

**Linux:**
```bash
# Ubuntu/Debian
sudo apt-get update
sudo apt-get install -y python3.11 python3-pip nodejs npm libgdal-dev gdal-bin

# Fedora/RHEL
sudo dnf install -y python3.11 python3-pip nodejs npm gdal gdal-devel
```

**macOS:**
```bash
# Install Homebrew if not installed
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

# Install dependencies
brew install python@3.11 node gdal
```

### Build Steps

```bash
# 1. Clone repository
git clone https://github.com/bobberdolle1/BeamNG.WorldForge.git
cd BeamNG.WorldForge

# 2. Install Python dependencies
pip3 install -r backend/requirements.txt

# 3. Run build script
python3 build.py

# 4. Create archive
cd dist

# Linux
tar -czf BeamNG-WorldForge-Linux-x64.tar.gz BeamNG-WorldForge

# macOS
tar -czf BeamNG-WorldForge-macOS-x64.tar.gz BeamNG-WorldForge
```

### Run

```bash
cd dist/BeamNG-WorldForge
./BeamNG-WorldForge
```

Browser will open automatically at http://localhost:8000

### Troubleshooting

**Linux - Missing GDAL:**
```bash
export LD_LIBRARY_PATH=/usr/lib/x86_64-linux-gnu:$LD_LIBRARY_PATH
```

**macOS - Permission denied:**
```bash
chmod +x BeamNG-WorldForge
```

**macOS - "App is damaged":**
```bash
xattr -cr BeamNG-WorldForge
```

### File Sizes

- Linux: ~200MB
- macOS: ~220MB
- Windows: ~250MB

### Alternative: Docker

If building fails, use Docker instead:

```bash
docker-compose up -d
# Open http://localhost:5173
```
