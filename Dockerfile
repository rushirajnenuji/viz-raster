# Use an official Python base image
FROM python:3.9-slim

# Install transitive dependencies
RUN apt-get update \
    && apt-get install -y g++ git libspatialindex-dev libgdal-dev libproj-dev

# Set a working directory inside the container
WORKDIR /app

# Install pdgstaging from GitHub repo
RUN pip install git+https://github.com/rushirajnenuji/viz-raster.git

# Set the default command (optional, useful for debugging)
CMD ["python3"]
