FROM python:3.9-alpine as build

WORKDIR /home/converter

RUN apk add --no-cache gcc libc-dev g++
RUN pip install --no-cache-dir pipenv
COPY Pipfile* ./
RUN pipenv install --system --clear

FROM python:3.9-alpine
COPY --from=build /usr/local/lib/python3.9/site-packages /usr/local/lib/python3.9/site-packages
COPY --from=build /usr/lib/libstdc++* /usr/lib/
WORKDIR /home/converter

COPY . .

USER 1337:1337
ENTRYPOINT [ "python3", "converter.py"]
