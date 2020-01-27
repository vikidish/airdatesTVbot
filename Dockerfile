FROM python:3.7.6-slim-buster
ENV PYTHONUNBUFFERED 1

WORKDIR /usr/src/airdatesTVbot

COPY requirements.txt .
RUN pip install --upgrade pip
RUN pip install -r requirements.txt

COPY . .

RUN chown -R pyuser:pyuser .
USER pyuser

RUN python3 first_setup.py

CMD ["python3", "bot.py"]