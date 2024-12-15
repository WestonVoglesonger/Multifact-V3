# Front-end Build Steps
FROM node:18 as build
COPY ./frontend/package.json /workspace/frontend/package.json
COPY ./frontend/angular.json /workspace/frontend/angular.json
WORKDIR /workspace/frontend
RUN npm install -g @angular/cli && npm install
ENV SHELL=/bin/bash
RUN ng analytics disable
COPY ./frontend/src /workspace/frontend/src
COPY ./frontend/*.json /workspace/frontend
RUN ng build --optimization --output-path ../static


# Back-end Build Steps
FROM python:3.11-slim-buster
WORKDIR /app
RUN pip install --upgrade pip && \
    pip install -r /workspaces/The-Innovation-Club/backend/requirements.txt
COPY ./backend/ .
CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "1380"] 

EXPOSE 1380