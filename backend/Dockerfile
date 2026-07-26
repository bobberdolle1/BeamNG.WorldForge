# Backend image for BeamNG.WorldForge.
#
# Python 3.12 rather than 3.13: several pinned scientific packages (rasterio,
# scipy) had no 3.13 wheels at the pinned versions, so the previous image fell
# back to building them from source - a long, fragile build that CI never
# exercised because CI only tests 3.11/3.12.
FROM python:3.12-slim

# rasterio bundles its own GDAL in the wheel, so libgdal-dev and build-essential
# are no longer installed here; that removed ~700 MB from the image. libglib2.0-0
# stays for OpenCV, which is used by the optional AI segmentation path.
RUN apt-get update && apt-get install --no-install-recommends -y \
        libglib2.0-0 \
        curl \
    && rm -rf /var/lib/apt/lists/*

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# Dependencies first, so a code change does not invalidate the (slow) pip layer.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Run as an unprivileged user. The API writes user-supplied map names to disk;
# running that as root is an unnecessary escalation of any file-handling bug.
RUN mkdir -p config output temp \
    && useradd --create-home --uid 10001 worldforge \
    && chown -R worldforge:worldforge /app
USER worldforge

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
    CMD curl -fsS http://127.0.0.1:8000/api/health || exit 1

# No --reload: it doubles memory use and restarts the server on every file
# event. docker-compose.yml enables it explicitly for local development.
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
