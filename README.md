# Background

Example repo for exploring Maxar open data locally. Uses a collection of projects based on [eoAPI](https://eoapi.dev/):

- **pgSTAC** database for accessing STAC collections & items in PostgreSQL - [https://github.com/stac-utils/pgstac](https://github.com/stac-utils/pgstac)
- **STAC API** built on top of FastAPI - [https://github.com/stac-utils/stac-fastapi](https://github.com/stac-utils/stac-fastapi)
- **STAC Items And Mosaic Raster Tiles** API to create dynamic mosaics based on search queries, built on top of [https://github.com/stac-utils/titiler-pgstac](https://github.com/stac-utils/titiler-pgstac)
- **OGC Features and Vector Tiles** API with a PostGIS backend, built on top of [https://github.com/developmentseed/tipg](https://github.com/developmentseed/tipg)
- **A STAC Catalog browsing UI** based on the Radiant Earth browser - [https://github.com/radiantearth/stac-browser](https://github.com/radiantearth/stac-browser)

---

## Getting started

Assumes you have installed [`docker`](https://www.docker.com/) and [`uv`](https://docs.astral.sh/uv).

Start Docker and run:

```zsh
make init
```

This will:

- Check you have the necessary tools installed and running (`uv`, `docker`)
- Build and start all Docker services in the background
- Create a Python virtual environment with `uv` and install pre-commit hooks
- Unzip and load the files in the `data/` directory into the pgSTAC database

---

## Returning to the project

If you have already run `make init` and just want to bring services back up (e.g. after restarting your machine):

```zsh
make start
```

This starts the existing Docker containers without rebuilding images or reloading data. To check that everything is running:

```zsh
make ps
```

---

## Make commands

| Command | Description |
|---|---|
| `make init` | First-time setup: build images, start services, install deps, load data |
| `make start` | Start existing services (no rebuild, no data load) |
| `make stop` | Stop services without removing containers |
| `make down` | Stop and remove containers |
| `make ps` | Show status of all services |
| `make logs` | Tail logs from all services |
| `make logs SERVICE=stac-fastapi` | Tail logs from a specific service |
| `make install` | Sync Python deps and install pre-commit hooks |
| `make test` | Run the test suite with pytest |
| `make check` | Run all code quality checks (ruff, pyrefly, nox) |
| `make build` | Rebuild all Docker images and restart services |
| `make build-browser` | Rebuild only the STAC Browser image (e.g. after config changes) |
| `make rebuild` | Full teardown and reinitialise from scratch |
| `make clean` | Stop services and remove build artifacts and database data |

Run `make help` to see a summary at any time.

---

## Exploring data

Once collections and items have been loaded, browse the collections with the [browser UI](http://localhost:8085), or run the [`maxar_example.ipynb` notebook](https://github.com/jap546/eo-maxar-example/blob/main/notebooks/maxar_example.ipynb) for worked examples.

The notebook uses a `pydantic`-based `MaxarCollection` class that wraps the STAC and raster APIs and provides methods for visualising imagery directly in Jupyter.

---

## Troubleshooting

**OSM base map tiles not loading in the STAC Browser**

The STAC Browser image must be rebuilt for tile fixes to take effect:

```zsh
make build-browser
```

**Services not responding after `make start`**

Check the service status and logs:

```zsh
make ps
make logs
```

**Database is empty after `make start`**

The pgSTAC database persists in `.pgdata/`. If it has been removed (e.g. after `make clean`), reload the data:

```zsh
make setup-db
```
