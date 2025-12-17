FROM python:3.9-slim

WORKDIR /app

COPY ted/ ted/

RUN pip install flask pydantic

RUN mkdir -p /root/.ted-server/inbox

EXPOSE 5000

CMD ["python", "ted/app.py"]
