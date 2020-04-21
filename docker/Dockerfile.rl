FROM sanicframework/sanic:LTS

ARG buildno
ARG gitcommithash

RUN echo "Build number: $buildno"

RUN apk add --no-cache curl unzip git libxml2-dev libxslt-dev

RUN echo "Based on commit: $gitcommithash"
RUN mkdir -p /opt && cd /opt && \
    curl -ssL -o rs.zip https://github.com/repronim/reprolib-server/archive/${gitcommithash}.zip && \
    unzip rs.zip && rm rs.zip && \
    mv reprolib-server* reprolib-server

WORKDIR /opt
RUN git clone --depth 1 https://github.com/ReproNim/reproschema

WORKDIR /opt/reprolib-server
RUN pip3 install -r requirements.txt
ENTRYPOINT ["python3", "-m", "main"]
