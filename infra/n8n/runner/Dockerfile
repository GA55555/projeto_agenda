FROM node:22-alpine AS pdf-deps

WORKDIR /build/pdf-evolucao
RUN apk add --no-cache font-dejavu
COPY pdf/package.json pdf/package-lock.json ./
RUN npm ci --omit=dev --ignore-scripts
COPY pdf/index.js ./

FROM n8nio/runners:2.33.0 AS runtime

USER root
RUN sed -i \
    's|"NODE_FUNCTION_ALLOW_EXTERNAL": "moment"|"NODE_FUNCTION_ALLOW_EXTERNAL": "@agenda/pdf-evolucao"|' \
    /etc/n8n-task-runners.json \
    && grep -F '"NODE_FUNCTION_ALLOW_EXTERNAL": "@agenda/pdf-evolucao"' \
        /etc/n8n-task-runners.json
COPY --from=pdf-deps /usr/share/fonts/dejavu /usr/share/fonts/dejavu
COPY --from=pdf-deps --chown=runner:runner /build/pdf-evolucao \
    /opt/runners/task-runner-javascript/node_modules/@agenda/pdf-evolucao
USER runner

FROM runtime AS test
COPY --chown=runner:runner pdf/test.js \
    /opt/runners/task-runner-javascript/node_modules/@agenda/pdf-evolucao/test.js
ENTRYPOINT ["node", "/opt/runners/task-runner-javascript/node_modules/@agenda/pdf-evolucao/test.js"]

FROM runtime AS final
