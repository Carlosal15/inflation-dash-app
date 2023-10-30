FROM python:3.12

COPY . ./
RUN pip install .


CMD ["python","inflation_app/app.py"]

EXPOSE 8080