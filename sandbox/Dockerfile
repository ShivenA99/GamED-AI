# GamED.AI v2 - Code Verification Sandbox
# This container is used to verify generated React components

FROM node:20-alpine

# Set working directory
WORKDIR /app

# Install basic dependencies for Next.js testing
RUN npm init -y && \
    npm install react react-dom next typescript @types/react @types/node && \
    npm install --save-dev eslint @typescript-eslint/eslint-plugin @typescript-eslint/parser

# Copy test harness
COPY test-harness/ ./test-harness/

# Create tsconfig.json
RUN echo '{ \
  "compilerOptions": { \
    "target": "es5", \
    "lib": ["dom", "dom.iterable", "esnext"], \
    "allowJs": true, \
    "skipLibCheck": true, \
    "strict": true, \
    "noEmit": true, \
    "esModuleInterop": true, \
    "module": "esnext", \
    "moduleResolution": "bundler", \
    "resolveJsonModule": true, \
    "isolatedModules": true, \
    "jsx": "preserve", \
    "incremental": true, \
    "paths": { "@/*": ["./*"] } \
  }, \
  "include": ["**/*.ts", "**/*.tsx"], \
  "exclude": ["node_modules"] \
}' > tsconfig.json

# Default command: run TypeScript check
CMD ["npx", "tsc", "--noEmit"]
