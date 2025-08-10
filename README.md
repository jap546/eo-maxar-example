# Background

Example repo for exploring Maxar open data locally. Uses a collection of projects based on [eoAPI](https://eoapi.dev/):

- **pgSTAC** database for accessing STAC collections & items in PostgreSQL - [https://github.com/stac-utils/pgstac](https://github.com/stac-utils/pgstac)
- **STAC API** built on top of FastAPI [https://github.com/stac-utils/stac-fastapi](https://github.com/stac-utils/stac-fastapi)
- **STAC Items And Mosaic Raster Tiles** API to create dynamic mosaics based on search queries, built on top of [https://github.com/stac-utils/titiler-pgstac](https://github.com/stac-utils/titiler-pgstac)
- **OGC Features and Vector Tiles** API with a PostGIS backend, built on top of [https://github.com/developmentseed/tipg](https://github.com/developmentseed/tipg)
- **A STAC Catalog browsing UI** based on the radiant earth browser : [https://github.com/radiantearth/stac-browser](https://github.com/radiantearth/stac-browser)

---

## Getting started

Assumes you have installed [`docker`](https://www.docker.com/) and [`uv`](https://docs.astral.sh/uv).

Have added a `Makefile` for convenience. Start docker and run:

```zsh
make init
```

This will:

- Check you have the necessary tools installed and running (e.g. `uv`, `docker`)
- Builds and starts all the necessary services in the background using `docker compose up -d`
- Creates a Python virtual environment with `uv`
- Unzips and loads the files in the `~/data` directory into the `pgSTAC` database started by Docker

If you need to do a complete rebuild, run:

```zsh
make rebuild
```

This will tear everything down and restart the installation process from scratch.

---

## Exploring data

Once the collections and items have been loaded you can have a quick look at the collections with the [browser UI](http://localhost:8085), but I'd recommend using the [`maxar_example.ipynb` notebook](https://github.com/jap546/eo-maxar-example/blob/main/notebooks/maxar_example.ipynb) to run some examples.

This uses a basic `pydantic` model approach and comes with various methods to make it simpler to interact with the subset of Maxar collections with Python.

---

## TO DO

- Add unit tests with `pytest`
- Change detection pre vs post disaster
- Move away from notebooks and build a frontend app linking with Docker services
- Explore scrollytelling feasibility
