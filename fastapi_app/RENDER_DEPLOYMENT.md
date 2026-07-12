# Render Deployment Guide

This project can run on Render as a Docker Web Service.

## What to provide in Render

Set these environment variables:

- `DATABASE_URL`
- `SECRET_KEY`
- `PORT` is set by Render automatically, but the app also accepts `API_PORT`
- `API_HOST=0.0.0.0`
- `API_LOG_LEVEL=info`

If you want to keep the MySQL path instead, use the `MYSQL_*` variables, but for your current setup you said the database is SQL Server, so `DATABASE_URL` is the cleanest option.

## SQL Server connection string

Use a SQLAlchemy URL, not the JDBC string.

Example:

```text
mssql+pyodbc://db_admin:your_password@aquasense.database.windows.net:1433/fish_app?driver=ODBC+Driver+18+for+SQL+Server&Encrypt=yes&TrustServerCertificate=no
```

If your password has special characters, URL-encode it first.

## Render service type

Choose:

- `Web Service`
- `Environment: Docker`

Render will use the `Dockerfile` automatically.

## Deploy steps

1. Push the repo to GitHub.
2. Create a new Web Service in Render.
3. Connect the GitHub repo.
4. Select Docker deployment.
5. Add `DATABASE_URL` and `SECRET_KEY`.
6. Deploy.

## Model files

Make sure these are present in the repo or copied into the Docker image:

- `best.pt`
- `efficientnet_fish.h5`
- `clf_class_names.json`
- `model/Disease_model/saved_model/`

## Useful URLs after deploy

- `/health`
- `/docs`
- `/predict`

## Notes

- The app creates tables at startup.
- For Azure SQL Server, create the database first in Azure before deploying.
- The Docker image installs the Microsoft ODBC driver needed by `pyodbc`.