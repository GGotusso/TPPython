FROM python
WORKDIR /src
ADD . .
RUN pip install -r requirements.txt
CMD kopf run /src/main.py --verbose