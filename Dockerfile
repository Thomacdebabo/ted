FROM python:3.12-slim

WORKDIR /app

RUN pip install flask pydantic pyyaml requests gunicorn

COPY ted/ ted/

RUN mkdir -p /root/.ted-server/inbox
RUN mkdir -p /root/.ted-server/uploads

EXPOSE 5000

CMD ["gunicorn", "--bind", "0.0.0.0:5000", "--workers", "4", "--timeout", "120", "ted.app:app"]
