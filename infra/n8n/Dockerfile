ARG N8N_BASE_IMAGE=docker.n8n.io/n8nio/n8n:2.30.5
FROM ${N8N_BASE_IMAGE}

# n8n 2.30.5 assumes PostgreSQL returns firstEvent as Date. In this image the
# driver returns a string, which breaks the statistics rollup and leaves
# executions open. Upstream fix: n8n-io/n8n#34670 (commit 0316336).
USER root
RUN arquivo="$(find /usr/local/lib/node_modules/n8n/node_modules/.pnpm -path '*/@n8n/db/dist/repositories/workflow-statistics.repository.js' -print -quit)" \
    && test -n "$arquivo" \
    && grep -Fq 'firstEventMs: r.firstEvent.getTime()' "$arquivo" \
    && sed -i 's/firstEventMs: r\.firstEvent\.getTime()/firstEventMs: new Date(r.firstEvent).getTime()/' "$arquivo" \
    && grep -Fq 'firstEventMs: new Date(r.firstEvent).getTime()' "$arquivo"
USER node
