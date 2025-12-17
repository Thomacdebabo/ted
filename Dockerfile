FROM python:3.12-slim

WORKDIR /app

RUN pip install flask pydantic pyyaml requests

COPY ted/ ted/
RUN mkdir -p /root/.ted-server/inbox

EXPOSE 5000

CMD ["python", "-m", "ted.app"]
