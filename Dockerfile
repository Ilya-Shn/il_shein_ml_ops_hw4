FROM python:3.11-slim
WORKDIR /work
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
ENV DBT_PROFILES_DIR=/work/dbt
ENV DBT_SEND_ANONYMOUS_USAGE_STATS=false
ENV DBT_USE_COLORS=false
