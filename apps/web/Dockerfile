# Dev server for the controller UI. Build context: repo root (npm workspaces).
FROM node:22-alpine
WORKDIR /repo
COPY package.json package-lock.json ./
COPY apps/web/package.json apps/web/package.json
COPY libraries/typescript/ufme-types/package.json libraries/typescript/ufme-types/package.json
# The lockfile is generated on Windows, so add the Linux native builds of rollup/esbuild at matching versions.
RUN npm ci --no-audit --no-fund \
 && A=$(node -p process.arch) \
 && npm install --no-save --no-audit --no-fund \
      "@rollup/rollup-linux-$A-musl@$(node -p "require('rollup/package.json').version")" \
      "@esbuild/linux-$A@$(node -p "require('esbuild/package.json').version")"
COPY libraries/typescript libraries/typescript
COPY apps/web apps/web
WORKDIR /repo/apps/web
EXPOSE 5173
CMD ["npm", "run", "dev", "--", "--host", "0.0.0.0"]
