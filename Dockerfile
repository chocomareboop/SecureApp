FROM python:3.12-slim

# gcc/make build the native parser; `file` powers the cover inspector.
RUN apt-get update \
 && apt-get install -y --no-install-recommends gcc make libc6-dev file \
 && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .
RUN make -C native clean all \
 && useradd --create-home --uid 10001 inkpost \
 && mkdir -p /app/instance \
 && chown -R inkpost:inkpost /app/instance

USER inkpost
ENV INKPOST_NATIVE_LIB=/app/native/build/libinkparser.so \
    INKPOST_HOST=0.0.0.0 \
    PYTHONUNBUFFERED=1
EXPOSE 5000

CMD ["python", "run.py"]
