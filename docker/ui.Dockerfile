FROM node:12.6.0-alpine

ARG gitcommithash

RUN apk add --no-cache curl unzip

RUN echo "Based on commit: $gitcommithash"
RUN mkdir -p /opt && cd /opt && \
    curl -ssL -o frontend.zip https://github.com/repronim/reproschema-ui/archive/${gitcommithash}.zip && \
    unzip frontend.zip && rm frontend.zip && \
    mv reproschema-ui* frontend
RUN cd /opt/frontend && \
#    sed -i 's#/reproschema-ui/#/ui/#g' config/index.js && \
    npm install && npm run build

WORKDIR /opt/frontend
ENTRYPOINT ["npm", "run", "serve"]
