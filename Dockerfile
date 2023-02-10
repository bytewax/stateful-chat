FROM bytewax/bytewax:latest-python3.10

ENV PYTHONUNBUFFERED 1

COPY . .

RUN pip install -r requirements.txt

RUN ["chmod", "+x", "utils/commands.sh"]
ENTRYPOINT ["utils/commands.sh"]