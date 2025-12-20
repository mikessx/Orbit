FROM python:3.14-slim
WORKDIR /usr/local/orbit

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 5000

RUN useradd orbit
RUN usermod -a -G 1000 orbit
USER orbit

CMD ["uvicorn", "server:app", "--host", "0.0.0.0", "--port", "5000"]