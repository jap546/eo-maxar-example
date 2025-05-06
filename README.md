## Background
Example repo for exploring Maxar open data locally. Uses a collection of projects:
- **pgSTAC** database for accessing STAC collections & items in PostgreSQL - [https://github.com/stac-utils/pgstac](https://github.com/stac-utils/pgstac)
- **STAC API** built on top of FastAPI [https://github.com/stac-utils/stac-fastapi](https://github.com/stac-utils/stac-fastapi)
- **STAC Items And Mosaic Raster Tiles** API to create dynamic mosaics based on search queries, built on top of [https://github.com/stac-utils/titiler-pgstac](https://github.com/stac-utils/titiler-pgstac)
- **OGC Features and Vector Tiles** API with a PostGIS backend, built on top of [https://github.com/developmentseed/tipg](https://github.com/developmentseed/tipg)
- **A STAC Catalog browsing UI** based on the radiant earth browser : [https://github.com/radiantearth/stac-browser](https://github.com/radiantearth/stac-browser)

<p align="center">
  <img src="https://github.com/jap546/eo-maxar-example/blob/main/img/example.gif?raw=true" alt="animated" />
</p>

---
## Getting started
Assumes you have installed [`docker`](https://www.docker.com/) and [`uv`](https://docs.astral.sh/uv).

#### EO APIs
Quickest way to get set up is to use the pre-configured Docker file.  Clone the repo, start your Docker daemon and start the API services:
```
git clone https://github.com/jap546/eo-maxar-example.git
cd eo-maxar-example
open -a Docker
docker compose up
```

Several API endpoints get set up:
- STAC Metadata service [http://localhost:8081](http://localhost:8081)
- Raster service [http://localhost:8082](http://localhost:8082)
- OGC Features/Vector Tiles [http://localhost:8083](http://localhost:8083)
- STAC FastAPI browser UI [http://localhost:8085](http://localhost:8085)

#### Python dependencies
Open a new terminal and install the Python dependencies with `uv`, activate the environment and run the CLI command:
```
uv sync --all-groups
source .venv/bin/activate
uv run setup
```

This runs `main.py::setup` which does do three things:
- unzips the `data/collections.json.zip` and `data/items.json.zip` files
- run a `pypgstac` command to load each file into your dockerised `pgstac` database
- make the `pgstac` context entension enabled

#### Complete rebuild?
If you want to start from scratch (e.g. ingest new data, or just start afresh), rebuild everything:

```
docker compose down
rm -rf .pgdata
docker compose up --build
```

And then re-run the `setup` command.

---
## Exploring data

Once the collections and items have been loaded you can have a quick look at the collections with the [browser UI](http://localhost:8085), but I'd recommend using the `maxar_example.ipynb` notebook to run some examples.

This uses a basic `pydantic` model approach and comes with various methods to make it simpler to interact with the subset of Maxar collections.

---
## TO DO

- Add unit tests with `pytest`
- Add `pydantic` validation
- More OOP structuring of `pydantic` models adhering to SOLID principles
- Change detection pre vs post disaster: consider bands (multispectral, pano, does maxar offer SAR?), classifiers (XGBoost, CNN)
- Explore segementation and classification of images
- Build a frontend app using TypeScript
- Explore scrollytelling feasibility
