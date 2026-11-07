# Service Specification — version 3

Lab 4: Data Storage and Replication. Base URL: `http://127.0.0.1:5000`

> R1–R4 are the requirements from Lab 2 and Lab 3 (`GET /time`, Docker). Copy them from spec.md version 2.
> If your last number was not R4, shift the numbers below.

## Requirements from versions 1–2

- **R1–R4** — copy from spec.md version 2.

## New in version 3

### Files (object storage)

- **R5.** `POST /files` with JSON body `{"text": "..."}` saves a text file and returns **201** and `{"id": "<uuid>"}`.
- **R6.** The file is stored in the object storage bucket (`BUCKET` variable) under the key `files/<id>.txt`, not on the service's disk.
- **R7.** If the `text` field is missing or empty, the service returns **400**.
- **R8.** File size limit: **1 MB**. A larger file returns **400**.
- **R9.** `GET /files/{id}` returns **200** and `{"id": "...", "text": "..."}`; if there is no such file — **404**.
- **R10.** A saved file is still available after the service restarts.
- **R11.** If the object storage is unavailable, the service returns **503**.

### Counter (Redis primary + replica)

- **R12.** `POST /counter/increment` increases the counter by 1. Writes go to the primary only. Returns **200** and `{"value": n, "source": "primary"}`.
- **R13.** `GET /counter?from=primary|replica` reads the counter from the chosen node (default: primary). Returns **200** and `{"value": n, "source": "..."}`.
- **R14.** If Redis is unavailable, the service returns **503**.

## Assumptions

- **A1.** Replication is asynchronous: a read from the replica (`?from=replica`) **may return a stale value**. The replica catches up with the primary eventually (eventual consistency).
- **A2.** Failover is manual: the replica is promoted with `REPLICAOF NO ONE`, and the service is restarted with `REDIS_PRIMARY_PORT=6380`.

## Response codes

| Code | When |
|---|---|
| 200 | successful read or increment |
| 201 | file saved |
| 400 | missing or empty `text`, file larger than 1 MB |
| 404 | file not found |
| 503 | storage (S3 or Redis) unavailable |
