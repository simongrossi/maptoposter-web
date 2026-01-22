FROM node:22-bullseye

# Install Python and pip
RUN apt-get update && apt-get install -y python3 python3-pip && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy package files
COPY package.json package-lock.json ./

# Install Node dependencies
RUN npm install

# Copy application code
COPY . .

# Install Python dependencies
# Using --no-cache-dir to keep image small
RUN if [ -f requirements.txt ]; then pip3 install --no-cache-dir -r requirements.txt; fi

# Build SvelteKit app
RUN npm run build

# Expose port
EXPOSE 4173

# Run the app
CMD ["node", "build/index.js"]
