# Wildlife Tracker API

This backend application pulls wildlife sighting data from the iNaturalist API for a specific region. It is built using FastAPI, and is designed to be containerized with Docker for scalable deployment.

## Features

- Pulls real-time wildlife observations from iNaturalist
- Region-based search support (e.g., New York City area)
- FastAPI server with clean endpoint structure
- Dockerized setup with `docker-compose`
- Configurable via environment variables

## Getting Started

### Prerequisites

- Docker
- Docker Compose
- (Optional) Python 3.11 if running without Docker

### Installation

1. Clone the repository:

   git clone https://github.com/yourusername/wildlife-tracker.git
   cd wildlife-tracker

2. Create a `.env` file in the root directory with the following:

   INAT_API_BASE=https://api.inaturalist.org/v1
   REGION_LAT=40.730610
   REGION_LNG=-73.935242
   RADIUS_KM=5

3. Build and start the container:

   docker-compose up --build

4. Visit the API locally at:

   http://localhost:8000/inat-test

## Project Structure

wildlife-tracker/
├── app/
│   ├── main.py               # FastAPI app entry point
│   └── ...
├── Dockerfile                # Docker build instructions
├── docker-compose.yml        # Compose file for development
├── requirements.txt          # Python dependencies
├── .env                      # Environment configuration
└── README.md

## API Endpoints

- GET `/inat-test`  
  Fetches recent wildlife observations near the configured latitude/longitude using iNaturalist's public API.

## Environment Configuration

All configuration is set via the `.env` file:

- INAT_API_BASE - iNaturalist API base URL
- REGION_LAT - Latitude of the search region
- REGION_LNG - Longitude of the search region
- RADIUS_KM - Radius around the lat/lng in kilometers

## Development Notes

To run outside Docker:

1. Install dependencies:

   pip install -r requirements.txt

2. Set environment variables manually or use `python-dotenv`.

3. Run the app locally:

   uvicorn app.main:app --reload

## Database Integration (Optional/Future)

If integrating a database (e.g., PostgreSQL), consider:

- Tables:
  - `observations`
  - `users`
  - `photos`
  - `taxa`
- Use scripts to:
  - Clean raw API data
  - Normalize nested structures
  - Insert into database using SQLAlchemy or raw SQL
