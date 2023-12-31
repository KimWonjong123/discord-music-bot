FROM python:3
ENV PYTHONUNBUFFERED 1
RUN apt-get update
RUN apt-get upgrade -y
RUN apt-get install -y ffmpeg
RUN mkdir /app
WORKDIR /app/
COPY requirements.txt /app/
RUN pip install -r requirements.txt
COPY . /app/
CMD ["python", "main.py"]