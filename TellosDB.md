# Futbol Tellos Database Schema

UPDATED ON MARCH 19, 2026

## Connection Details

| Property | Value                                      |
| -------- | ------------------------------------------ |
| Host     | `db.mosxqfeuzhhkyufpztjk.supabase.co`      |
| Port     | `5432`                                     |
| Database | `postgres`                                 |
| User     | `postgres`                                 |
| Password | `$SUPABASE_TELLOS_PASSWORD` (env variable) |

### Connection String

```
postgresql://postgres:${SUPABASE_TELLOS_PASSWORD}@db.mosxqfeuzhhkyufpztjk.supabase.co:5432/postgres
```

### psql Command

```bash
PGPASSWORD=$SUPABASE_TELLOS_PASSWORD psql -h db.mosxqfeuzhhkyufpztjk.supabase.co -p 5432 -d postgres -U postgres
```

---

## Table: `canchas`

Courts/fields available for reservation.

### Columns

| Column       | Type                     | Nullable | Default  |
| ------------ | ------------------------ | -------- | -------- |
| `id`         | bigint                   | NOT NULL | identity |
| `created_at` | timestamp with time zone | NOT NULL | `now()`  |
| `nombre`     | text                     | YES      | -        |
| `cantidad`   | text                     | YES      | -        |
| `img`        | text                     | YES      | -        |
| `local`      | smallint                 | YES      | -        |
| `precio`     | text                     | YES      | -        |

### Constraints

| Name           | Type        | Column |
| -------------- | ----------- | ------ |
| `Canchas_pkey` | PRIMARY KEY | `id`   |

### Indexes

| Name           | Definition                          |
| -------------- | ----------------------------------- |
| `Canchas_pkey` | `UNIQUE INDEX ... USING btree (id)` |

### RLS Policies

**RLS Enabled:** Yes

| Policy                                   | Command | USING  | WITH CHECK |
| ---------------------------------------- | ------- | ------ | ---------- |
| `Enable read access for all users`       | SELECT  | `true` | -          |
| `Allow update canchas for authenticated` | UPDATE  | `true` | `true`     |

---

## Table: `reservas`

Individual reservations for courts.

### Columns

| Column                     | Type                        | Nullable | Default             | Description          |
| -------------------------- | --------------------------- | -------- | ------------------- | -------------------- |
| `id`                       | uuid                        | NOT NULL | `gen_random_uuid()` | Primary key          |
| `created_at`               | timestamp with time zone    | NOT NULL | `now()`             | Creation timestamp   |
| `hora_inicio`              | timestamp without time zone | YES      | -                   | Start time           |
| `hora_fin`                 | timestamp without time zone | YES      | -                   | End time             |
| `nombre_reserva`           | text                        | YES      | -                   | Customer name        |
| `celular_reserva`          | text                        | YES      | -                   | Customer phone       |
| `correo_reserva`           | text                        | YES      | -                   | Customer email       |
| `sinpe_reserva`            | text                        | YES      | -                   | SINPE mobile number  |
| `confirmada`               | boolean                     | NOT NULL | `false`             | Confirmation status  |
| `confirmada_por`           | text                        | YES      | -                   | Confirmed by (admin) |
| `cancha_id`                | bigint                      | YES      | -                   | FK to canchas        |
| `precio`                   | integer                     | YES      | -                   | Price                |
| `arbitro`                  | boolean                     | YES      | `false`             | Referee requested    |
| `pago_checkeado`           | boolean                     | YES      | `false`             | Payment verified     |
| `reservacion_fija_id`      | bigint                      | YES      | -                   | FK to reservas_fijas |
| `recordatorio_24h_enviado` | timestamp without time zone | YES      | -                   | 24h reminder sent    |

### Constraints

| Name                                | Type        | Column                   | References           | On Update | On Delete |
| ----------------------------------- | ----------- | ------------------------ | -------------------- | --------- | --------- |
| `reservas_pkey`                     | PRIMARY KEY | `id`                     | -                    | -         | -         |
| `reservas_cancha_hora_unique`       | UNIQUE      | `cancha_id, hora_inicio` | -                    | -         | -         |
| `reservas_cancha_id_fkey`           | FOREIGN KEY | `cancha_id`              | `canchas(id)`        | NO ACTION | NO ACTION |
| `reservas_reservacion_fija_id_fkey` | FOREIGN KEY | `reservacion_fija_id`    | `reservas_fijas(id)` | NO ACTION | SET NULL  |

### Indexes

| Name                          | Definition                                              |
| ----------------------------- | ------------------------------------------------------- |
| `reservas_pkey`               | `UNIQUE INDEX ... USING btree (id)`                     |
| `reservas_cancha_hora_unique` | `UNIQUE INDEX ... USING btree (cancha_id, hora_inicio)` |

### Triggers

| Name                       | Event                   | For Each | Function                         |
| -------------------------- | ----------------------- | -------- | -------------------------------- |
| `trg_check_linked_canchas` | BEFORE INSERT OR UPDATE | ROW      | `check_reserva_linked_canchas()` |

### RLS Policies

**RLS Enabled:** Yes

| Policy                                             | Command | USING                    | WITH CHECK |
| -------------------------------------------------- | ------- | ------------------------ | ---------- |
| `Enable read access for all users`                 | SELECT  | `true`                   | -          |
| `CREATE_RESERVA`                                   | INSERT  | -                        | `true`     |
| `Allow update reservas`                            | UPDATE  | `true`                   | -          |
| `Allow update reservas for authenticated`          | UPDATE  | `true`                   | `true`     |
| `Allow update canchas for authenticated`           | UPDATE  | `true`                   | `true`     |
| `UPDATE_RESERVA`                                   | UPDATE  | -                        | `true`     |
| `Allow authenticated users to delete reservations` | DELETE  | `auth.uid() IS NOT NULL` | -          |

---

## Table: `reservas_fijas`

Recurring/fixed reservations (templates for weekly reservations).

### Columns

| Column                 | Type                     | Nullable | Default  | Description                |
| ---------------------- | ------------------------ | -------- | -------- | -------------------------- |
| `id`                   | bigint                   | NOT NULL | identity | Primary key                |
| `created_at`           | timestamp with time zone | NOT NULL | `now()`  | Creation timestamp         |
| `hora_inicio`          | time without time zone   | YES      | -        | Start time (time only)     |
| `hora_fin`             | time without time zone   | YES      | -        | End time (time only)       |
| `nombre_reserva_fija`  | text                     | YES      | -        | Customer name              |
| `celular_reserva_fija` | text                     | YES      | -        | Customer phone             |
| `correo_reserva_fija`  | text                     | YES      | -        | Customer email             |
| `precio`               | integer                  | YES      | -        | Price                      |
| `arbitro`              | boolean                  | YES      | -        | Referee requested          |
| `cancha_id`            | bigint                   | YES      | -        | FK to canchas              |
| `dia`                  | smallint                 | YES      | -        | Day of week (1=Mon, 7=Sun) |

### Constraints

| Name                            | Type        | Column      | References    | On Update | On Delete |
| ------------------------------- | ----------- | ----------- | ------------- | --------- | --------- |
| `reservas_fijas_pkey`           | PRIMARY KEY | `id`        | -             | -         | -         |
| `reservas_fijas_cancha_id_fkey` | FOREIGN KEY | `cancha_id` | `canchas(id)` | CASCADE   | SET NULL  |

### Indexes

| Name                  | Definition                          |
| --------------------- | ----------------------------------- |
| `reservas_fijas_pkey` | `UNIQUE INDEX ... USING btree (id)` |

### RLS Policies

**RLS Enabled:** Yes

| Policy                                               | Command | USING  | WITH CHECK |
| ---------------------------------------------------- | ------- | ------ | ---------- |
| `Allow authenticated users to read reservas_fijas`   | SELECT  | `true` | -          |
| `Allow authenticated users to insert reservas_fijas` | INSERT  | -      | `true`     |
| `Allow authenticated users to update reservas_fijas` | UPDATE  | `true` | `true`     |
| `Allow authenticated users to delete reservas_fijas` | DELETE  | `true` | -          |

---

## Table: `pagos`

Payment records linked to reservations.

### Columns

| Column           | Type                     | Nullable | Default             | Description            |
| ---------------- | ------------------------ | -------- | ------------------- | ---------------------- |
| `id`             | bigint                   | NOT NULL | identity            | Primary key            |
| `created_at`     | timestamp with time zone | NOT NULL | `now()`             | Creation timestamp     |
| `reserva_id`     | uuid                     | YES      | `gen_random_uuid()` | FK to reservas         |
| `monto_sinpe`    | bigint                   | YES      | -                   | SINPE payment amount   |
| `monto_efectivo` | bigint                   | YES      | -                   | Cash payment amount    |
| `nota`           | text                     | YES      | -                   | Notes                  |
| `completo`       | boolean                  | YES      | -                   | Payment complete       |
| `sinpe_pago`     | text                     | YES      | -                   | SINPE reference/number |
| `checkeado`      | boolean                  | YES      | `false`             | Verified by admin      |
| `creado_por`     | text                     | YES      | -                   | Created by (admin)     |

### Constraints

| Name                    | Type        | Column       | References     | On Update | On Delete |
| ----------------------- | ----------- | ------------ | -------------- | --------- | --------- |
| `pagos_pkey`            | PRIMARY KEY | `id`         | -              | -         | -         |
| `pagos_reserva_id_fkey` | FOREIGN KEY | `reserva_id` | `reservas(id)` | CASCADE   | CASCADE   |

### Indexes

| Name         | Definition                          |
| ------------ | ----------------------------------- |
| `pagos_pkey` | `UNIQUE INDEX ... USING btree (id)` |

### RLS Policies

**RLS Enabled:** Yes

| Policy                                      | Command | USING  | WITH CHECK |
| ------------------------------------------- | ------- | ------ | ---------- |
| `Allow authenticated users to read pagos`   | SELECT  | `true` | -          |
| `Allow authenticated users to insert pagos` | INSERT  | -      | `true`     |

---

## Table: `retos`

Challenge/match reservations between two teams.

### Columns

| Column              | Type                        | Nullable | Default             | Description             |
| ------------------- | --------------------------- | -------- | ------------------- | ----------------------- |
| `id`                | uuid                        | NOT NULL | `gen_random_uuid()` | Primary key             |
| `created_at`        | timestamp without time zone | NOT NULL | `now()`             | Creation timestamp      |
| `hora_inicio`       | timestamp without time zone | YES      | -                   | Start time              |
| `hora_fin`          | timestamp without time zone | YES      | -                   | End time                |
| `local`             | text                        | YES      | -                   | Location (Guada/Sabana) |
| `fut`               | smallint                    | YES      | -                   | Football type (5, 7, 8) |
| `arbitro`           | boolean                     | YES      | -                   | Referee requested       |
| `equipo1_nombre`    | text                        | YES      | -                   | Team 1 name             |
| `equipo1_encargado` | text                        | YES      | -                   | Team 1 contact person   |
| `equipo1_celular`   | text                        | YES      | -                   | Team 1 phone            |
| `equipo1_correo`    | text                        | YES      | -                   | Team 1 email            |
| `equipo2_nombre`    | text                        | YES      | -                   | Team 2 name             |
| `equipo2_encargado` | text                        | YES      | -                   | Team 2 contact person   |
| `equipo2_celular`   | text                        | YES      | -                   | Team 2 phone            |
| `cancha_id`         | bigint                      | YES      | -                   | FK to canchas           |
| `reserva_id`        | uuid                        | YES      | -                   | FK to reservas (unique) |

### Constraints

| Name                    | Type        | Column       | References     | On Update | On Delete |
| ----------------------- | ----------- | ------------ | -------------- | --------- | --------- |
| `retos_pkey`            | PRIMARY KEY | `id`         | -              | -         | -         |
| `retos_reserva_id_key`  | UNIQUE      | `reserva_id` | -              | -         | -         |
| `retos_cancha_id_fkey`  | FOREIGN KEY | `cancha_id`  | `canchas(id)`  | NO ACTION | NO ACTION |
| `retos_reserva_id_fkey` | FOREIGN KEY | `reserva_id` | `reservas(id)` | CASCADE   | CASCADE   |

### Indexes

| Name                   | Definition                                  |
| ---------------------- | ------------------------------------------- |
| `retos_pkey`           | `UNIQUE INDEX ... USING btree (id)`         |
| `retos_reserva_id_key` | `UNIQUE INDEX ... USING btree (reserva_id)` |

### RLS Policies

**RLS Enabled:** Yes

| Policy                                | Command | USING                           | WITH CHECK                      |
| ------------------------------------- | ------- | ------------------------------- | ------------------------------- |
| `Allow public select on retos`        | SELECT  | `true`                          | -                               |
| `Enable read access for all users`    | SELECT  | `true`                          | -                               |
| `Allow public insert on retos`        | INSERT  | -                               | `true`                          |
| `Allow authenticated update on retos` | UPDATE  | `auth.role() = 'authenticated'` | `auth.role() = 'authenticated'` |
| `Allow authenticated delete on retos` | DELETE  | `auth.role() = 'authenticated'` | -                               |

---

## Table: `cierres`

Closing/settlement records for accounting periods.

### Columns

| Column       | Type                     | Nullable | Default             | Description        |
| ------------ | ------------------------ | -------- | ------------------- | ------------------ |
| `id`         | bigint                   | NOT NULL | identity            | Primary key        |
| `created_at` | timestamp with time zone | NOT NULL | `now()`             | Creation timestamp |
| `inicio`     | date                     | YES      | -                   | Period start date  |
| `fin`        | date                     | YES      | -                   | Period end date    |
| `creado_por` | uuid                     | YES      | `gen_random_uuid()` | FK to auth.users   |
| `nota`       | text                     | YES      | -                   | Notes              |
| `faltantes`  | bigint                   | YES      | -                   | Missing amount     |
| `cierre_pdf` | text                     | YES      | -                   | PDF report URL     |

### Constraints

| Name                      | Type        | Column       | References       | On Update | On Delete |
| ------------------------- | ----------- | ------------ | ---------------- | --------- | --------- |
| `cierres_pkey`            | PRIMARY KEY | `id`         | -                | -         | -         |
| `cierres_creado_por_fkey` | FOREIGN KEY | `creado_por` | `auth.users(id)` | CASCADE   | SET NULL  |

### Indexes

| Name           | Definition                          |
| -------------- | ----------------------------------- |
| `cierres_pkey` | `UNIQUE INDEX ... USING btree (id)` |

### RLS Policies

**RLS Enabled:** Yes

| Policy                                  | Command | USING  | WITH CHECK |
| --------------------------------------- | ------- | ------ | ---------- |
| `Allow authenticated read on cierres`   | SELECT  | `true` | -          |
| `Allow authenticated insert on cierres` | INSERT  | -      | `true`     |
| `Allow authenticated update on cierres` | UPDATE  | `true` | -          |
| `Allow authenticated delete on cierres` | DELETE  | `true` | -          |

---

## Table: `configuracion`

System configuration settings (opening/closing hours per location).

### Columns

| Column            | Type                     | Nullable | Default  | Description            |
| ----------------- | ------------------------ | -------- | -------- | ---------------------- |
| `id`              | bigint                   | NOT NULL | identity | Primary key            |
| `created_at`      | timestamp with time zone | NOT NULL | `now()`  | Creation timestamp     |
| `apertura_guada`  | time without time zone   | YES      | -        | Opening time Guadalupe |
| `apertura_sabana` | time without time zone   | YES      | -        | Opening time Sabana    |
| `cierre_guada`    | time without time zone   | YES      | -        | Closing time Guadalupe |
| `cierre_sabana`   | time without time zone   | YES      | -        | Closing time Sabana    |

### Constraints

| Name                 | Type        | Column |
| -------------------- | ----------- | ------ |
| `configuracion_pkey` | PRIMARY KEY | `id`   |

### Indexes

| Name                 | Definition                          |
| -------------------- | ----------------------------------- |
| `configuracion_pkey` | `UNIQUE INDEX ... USING btree (id)` |

### RLS Policies

**RLS Enabled:** Yes

| Policy                                         | Command | USING  | WITH CHECK |
| ---------------------------------------------- | ------- | ------ | ---------- |
| `Enable read access for all users`             | SELECT  | `true` | -          |
| `Allow update configuracion for authenticated` | UPDATE  | `true` | `true`     |

---

## Table: `lista_espera`

Waiting list entries for fully booked time slots.

### Columns

| Column       | Type                        | Nullable | Default  | Description         |
| ------------ | --------------------------- | -------- | -------- | ------------------- |
| `id`         | bigint                      | NOT NULL | identity | Primary key         |
| `created_at` | timestamp with time zone    | NOT NULL | `now()`  | Creation timestamp  |
| `date`       | timestamp without time zone | YES      | -        | Requested date/time |
| `note`       | text                        | YES      | -        | Notes/contact info  |

### Constraints

| Name                | Type        | Column |
| ------------------- | ----------- | ------ |
| `lista_espera_pkey` | PRIMARY KEY | `id`   |

### Indexes

| Name                | Definition                          |
| ------------------- | ----------------------------------- |
| `lista_espera_pkey` | `UNIQUE INDEX ... USING btree (id)` |

### RLS Policies

**RLS Enabled:** Yes

| Policy                                             | Command | USING  | WITH CHECK |
| -------------------------------------------------- | ------- | ------ | ---------- |
| `Allow authenticated users to view lista_espera`   | SELECT  | `true` | -          |
| `Allow authenticated users to create lista_espera` | INSERT  | -      | `true`     |
| `Allow authenticated users to update lista_espera` | UPDATE  | `true` | `true`     |
| `Allow authenticated users to delete lista_espera` | DELETE  | `true` | -          |

---

## Database Functions

### `check_reserva_linked_canchas()`

Trigger function that prevents conflicting reservations between cancha 6 (full field) and canchas 1, 3, 5 (individual fields). If cancha 6 is being reserved, it checks that none of canchas 1, 3, 5 have a reservation at the same `hora_inicio`, and vice versa. Raises exception with SQLSTATE `23505` on conflict.

**Used by trigger:** `trg_check_linked_canchas` on `reservas` (BEFORE INSERT OR UPDATE)

---

## Entity Relationships

```
                                  ┌───────────────┐
                                  │  auth.users   │
                                  │───────────────│
                                  │ id (PK)       │
                                  └───────────────┘
                                          ▲
                                          │ FK (creado_por)
                                          │ ON DELETE: SET NULL
                                          │
┌─────────────┐                    ┌──────────────┐
│   canchas   │                    │   cierres    │
│─────────────│                    │──────────────│
│ id (PK)     │◄────────┐          │ id (PK)      │
│ nombre      │         │          │ creado_por   │
│ precio      │         │          │ inicio/fin   │
│ local       │         │          │ cierre_pdf   │
└─────────────┘         │          └──────────────┘
      ▲                 │
      │                 │          ┌──────────────────┐
      │ FK (cancha_id)  │          │  configuracion   │
      │                 │          │──────────────────│
      │                 │          │ id (PK)          │
      │                 │          │ apertura_guada   │
      │                 │          │ cierre_guada     │
      │                 │          │ apertura_sabana  │
      │                 │          │ cierre_sabana    │
      │                 │          └──────────────────┘
      │                 │
      │                 │          ┌──────────────────┐
      │                 │          │   lista_espera   │
      │                 │          │──────────────────│
      │                 │          │ id (PK)          │
      │                 │          │ date             │
      │                 │          │ note             │
      │                 │          └──────────────────┘
      │                 │
      │                 └──────────────────────────────────────┐
      │                                                        │
┌─────────────────────┐                              ┌──────────────────┐
│      reservas       │                              │  reservas_fijas  │
│─────────────────────│                              │──────────────────│
│ id (PK, uuid)       │◄─────────────────────────────│ id (PK, bigint)  │
│ cancha_id (FK)      │  FK (reservacion_fija_id)    │ cancha_id (FK)   │
│ reservacion_fija_id │  ON DELETE: SET NULL         │ dia (day of week)│
│ hora_inicio         │                              │ hora_inicio      │
│ hora_fin            │                              │ hora_fin         │
│ nombre_reserva      │                              │ nombre_reserva   │
│ confirmada          │                              │ _fija            │
│ precio              │                              │ precio           │
└─────────────────────┘                              └──────────────────┘
      ▲         ▲
      │         │
      │         │ FK (reserva_id) UNIQUE
      │         │ ON DELETE: CASCADE
      │         │
      │    ┌─────────────────────┐
      │    │       retos         │
      │    │─────────────────────│
      │    │ id (PK, uuid)       │
      │    │ reserva_id (FK, UQ) │
      │    │ cancha_id (FK)──────┼──► canchas
      │    │ equipo1_*           │
      │    │ equipo2_*           │
      │    │ fut, arbitro        │
      │    └─────────────────────┘
      │
      │ FK (reserva_id)
      │ ON DELETE: CASCADE
      │
┌─────────────────────┐
│       pagos         │
│─────────────────────│
│ id (PK)             │
│ reserva_id (FK)     │
│ monto_sinpe         │
│ monto_efectivo      │
│ completo            │
└─────────────────────┘
```

## Notes

### Primary Keys

- **reservas** and **retos** use `uuid` for primary key
- All other tables use `bigint` (identity)

### Locations

- **Cancha 6** is the full field composed of canchas 1, 3, 5 — enforced by the `check_reserva_linked_canchas()` trigger
- **local** field: `1` = Guadalupe, `2` = Sabana (in canchas)
- **configuracion** stores opening/closing hours per location

### Time Fields

- **reservas_fijas** uses `time` type (no date) - for recurring weekly slots
- **reservas** uses `timestamp` - for specific date/time reservations
- **dia** in `reservas_fijas`: 1=Monday, 2=Tuesday, ..., 7=Sunday

### Cascade Behavior

- When a `reserva_fija` is deleted → `reservas.reservacion_fija_id` set to NULL (preserves history)
- When a `reserva` is deleted → related `pagos` and `retos` are also deleted (CASCADE)
- When a `cancha` is deleted → `reservas_fijas.cancha_id` set to NULL

### Unique Constraints

- **reservas** has a UNIQUE constraint on `(cancha_id, hora_inicio)` — prevents double-booking
- **retos** has a UNIQUE constraint on `reserva_id` (one-to-one with reservas)

### Special Relationships

- **retos** has a UNIQUE constraint on `reserva_id` (one-to-one with reservas)
- **cierres** links to `auth.users` for tracking who created the closing report

### RLS Summary

| Table          | Anon Read | Anon Write  | Auth Required  |
| -------------- | --------- | ----------- | -------------- |
| canchas        | Yes       | No          | Update only    |
| reservas       | Yes       | Insert only | Update/Delete  |
| reservas_fijas | No        | No          | All operations |
| pagos          | No        | No          | Read/Insert    |
| retos          | Yes       | Insert only | Update/Delete  |
| cierres        | No        | No          | All operations |
| configuracion  | Yes       | No          | Update only    |
| lista_espera   | No        | No          | All operations |
