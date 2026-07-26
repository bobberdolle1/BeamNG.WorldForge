# Frontend development image for BeamNG.WorldForge.
#
# This image runs the Vite dev server. For a production deployment build the
# frontend once and let the backend serve it from `backend/static`
# (see build.py) - there is no need to run Node at all.
FROM node:20-alpine

WORKDIR /app

COPY package.json package-lock.json* ./

# `npm ci` installs exactly what the lockfile pins, so an image rebuilt months
# from now is identical to today's. `npm install` silently resolves newer minor
# versions, which is how a working image starts failing with no change to the
# repository. (The pnpm branch was dead code: there is no pnpm-lock.yaml here.)
RUN if [ -f package-lock.json ]; then npm ci; else npm install; fi

COPY . .

EXPOSE 5173

CMD ["npm", "run", "dev", "--", "--host"]
