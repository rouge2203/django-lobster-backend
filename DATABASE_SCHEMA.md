# Futbol Tellos Database Schema

## Connection Details

| Property | Value |
|----------|-------|
| Host | `db.mosxqfeuzhhkyufpztjk.supabase.co` |
| Port | `5432` |
| Database | `postgres` |
| User | `postgres` |
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

| Column | Type | Nullable | Default |
|--------|------|----------|---------|
| `id` | bigint | NOT NULL | - |
| `created_at` | timestamp with time zone | NOT NULL | `now()` |
| `nombre` | text | YES | - |
| `cantidad` | text | YES | - |
| `img` | text | YES | - |
| `local` | smallint | YES | - |
| `precio` | text | YES | - |

### Constraints

| Name | Type | Column |
|------|------|--------|
| `Canchas_pkey` | PRIMARY KEY | `id` |

### Indexes

| Name | Definition |
|------|------------|
| `Canchas_pkey` | `UNIQUE INDEX ... USING btree (id)` |

### RLS Policies

**RLS Enabled:** Yes

| Policy | Command | USING | WITH CHECK |
|--------|---------|-------|------------|
| `Enable read access for all users` | SELECT | `true` | - |
| `Allow update canchas for authenticated` | UPDATE | `true` | `true` |

---

## Table: `reservas`

Individual reservations for courts.

### Columns

| Column | Type | Nullable | Default | Description |
|--------|------|----------|---------|-------------|
| `id` | uuid | NOT NULL | `gen_random_uuid()` | Primary key |
| `created_at` | timestamp with time zone | NOT NULL | `now()` | Creation timestamp |
| `hora_inicio` | timestamp without time zone | YES | - | Start time |
| `hora_fin` | timestamp without time zone | YES | - | End time |
| `nombre_reserva` | text | YES | - | Customer name |
| `celular_reserva` | text | YES | - | Customer phone |
| `correo_reserva` | text | YES | - | Customer email |
| `sinpe_reserva` | text | YES | - | SINPE mobile number |
| `confirmada` | boolean | NOT NULL | `false` | Confirmation status |
| `confirmada_por` | text | YES | - | Confirmed by (admin) |
| `cancha_id` | bigint | YES | - | FK to canchas |
| `precio` | integer | YES | - | Price |
| `arbitro` | boolean | YES | `false` | Referee requested |
| `pago_checkeado` | boolean | YES | `false` | Payment verified |
| `reservacion_fija_id` | bigint | YES | - | FK to reservas_fijas |
| `recordatorio_24h_enviado` | timestamp without time zone | YES | - | 24h reminder sent |

### Constraints

| Name | Type | Column | References | On Update | On Delete |
|------|------|--------|------------|-----------|-----------|
| `reservas_pkey` | PRIMARY KEY | `id` | - | - | - |
| `reservas_cancha_id_fkey` | FOREIGN KEY | `cancha_id` | `canchas(id)` | NO ACTION | NO ACTION |
| `reservas_reservacion_fija_id_fkey` | FOREIGN KEY | `reservacion_fija_id` | `reservas_fijas(id)` | NO ACTION | SET NULL |

### Indexes

| Name | Definition |
|------|------------|
| `reservas_pkey` | `UNIQUE INDEX ... USING btree (id)` |

### RLS Policies

**RLS Enabled:** Yes

| Policy | Command | USING | WITH CHECK |
|--------|---------|-------|------------|
| `Enable read access for all users` | SELECT | `true` | - |
| `CREATE_RESERVA` | INSERT | - | `true` |
| `Allow update reservas` | UPDATE | `true` | - |
| `Allow update reservas for authenticated` | UPDATE | `true` | `true` |
| `Allow update canchas for authenticated` | UPDATE | `true` | `true` |
| `UPDATE_RESERVA` | UPDATE | - | `true` |
| `Allow authenticated users to delete reservations` | DELETE | `auth.uid() IS NOT NULL` | - |

---

## Table: `reservas_fijas`

Recurring/fixed reservations (templates for weekly reservations).

### Columns

| Column | Type | Nullable | Default | Description |
|--------|------|----------|---------|-------------|
| `id` | bigint | NOT NULL | identity | Primary key |
| `created_at` | timestamp with time zone | NOT NULL | `now()` | Creation timestamp |
| `hora_inicio` | time without time zone | YES | - | Start time (time only) |
| `hora_fin` | time without time zone | YES | - | End time (time only) |
| `nombre_reserva_fija` | text | YES | - | Customer name |
| `celular_reserva_fija` | text | YES | - | Customer phone |
| `correo_reserva_fija` | text | YES | - | Customer email |
| `precio` | integer | YES | - | Price |
| `arbitro` | boolean | YES | - | Referee requested |
| `cancha_id` | bigint | YES | - | FK to canchas |
| `dia` | smallint | YES | - | Day of week (1=Mon, 7=Sun) |

### Constraints

| Name | Type | Column | References | On Update | On Delete |
|------|------|--------|------------|-----------|-----------|
| `reservas_fijas_pkey` | PRIMARY KEY | `id` | - | - | - |
| `reservas_fijas_cancha_id_fkey` | FOREIGN KEY | `cancha_id` | `canchas(id)` | CASCADE | SET NULL |

### Indexes

| Name | Definition |
|------|------------|
| `reservas_fijas_pkey` | `UNIQUE INDEX ... USING btree (id)` |

### RLS Policies

**RLS Enabled:** Yes

| Policy | Command | USING | WITH CHECK |
|--------|---------|-------|------------|
| `Allow authenticated users to read reservas_fijas` | SELECT | `true` | - |
| `Allow authenticated users to insert reservas_fijas` | INSERT | - | `true` |
| `Allow authenticated users to update reservas_fijas` | UPDATE | `true` | `true` |
| `Allow authenticated users to delete reservas_fijas` | DELETE | `true` | - |

---

## Table: `pagos`

Payment records linked to reservations.

### Columns

| Column | Type | Nullable | Default | Description |
|--------|------|----------|---------|-------------|
| `id` | bigint | NOT NULL | identity | Primary key |
| `created_at` | timestamp with time zone | NOT NULL | `now()` | Creation timestamp |
| `reserva_id` | uuid | YES | `gen_random_uuid()` | FK to reservas |
| `monto_sinpe` | bigint | YES | - | SINPE payment amount |
| `monto_efectivo` | bigint | YES | - | Cash payment amount |
| `nota` | text | YES | - | Notes |
| `completo` | boolean | YES | - | Payment complete |
| `sinpe_pago` | text | YES | - | SINPE reference/number |
| `checkeado` | boolean | YES | `false` | Verified by admin |
| `creado_por` | text | YES | - | Created by (admin) |

### Constraints

| Name | Type | Column | References | On Update | On Delete |
|------|------|--------|------------|-----------|-----------|
| `pagos_pkey` | PRIMARY KEY | `id` | - | - | - |
| `pagos_reserva_id_fkey` | FOREIGN KEY | `reserva_id` | `reservas(id)` | CASCADE | CASCADE |

### Indexes

| Name | Definition |
|------|------------|
| `pagos_pkey` | `UNIQUE INDEX ... USING btree (id)` |

### RLS Policies

**RLS Enabled:** Yes

| Policy | Command | USING | WITH CHECK |
|--------|---------|-------|------------|
| `Allow authenticated users to read pagos` | SELECT | `true` | - |
| `Allow authenticated users to insert pagos` | INSERT | - | `true` |

---

## Entity Relationships

```
┌─────────────┐
│   canchas   │
│─────────────│
│ id (PK)     │◄─────────────────────────────────┐
│ nombre      │                                   │
│ precio      │                                   │
└─────────────┘                                   │
      ▲                                           │
      │ FK (cancha_id)                            │ FK (cancha_id)
      │ ON DELETE: NO ACTION                      │ ON DELETE: SET NULL
      │                                           │
┌─────────────────────┐                    ┌──────────────────┐
│      reservas       │                    │  reservas_fijas  │
│─────────────────────│                    │──────────────────│
│ id (PK, uuid)       │◄───────────────────│ id (PK, bigint)  │
│ cancha_id (FK)      │  FK                │ cancha_id (FK)   │
│ reservacion_fija_id │  (reservacion_     │ dia (day of week)│
│ hora_inicio         │   fija_id)         │ hora_inicio      │
│ hora_fin            │  ON DELETE:        │ hora_fin         │
│ nombre_reserva      │  SET NULL          │ nombre_reserva   │
│ confirmada          │                    │ _fija            │
│ precio              │                    │ precio           │
└─────────────────────┘                    └──────────────────┘
      ▲
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

- **Cancha 6** is linked to canchas 4 & 5 in the application logic (LINKED_CANCHAS)
- **dia** in `reservas_fijas`: 1=Monday, 2=Tuesday, ..., 7=Sunday
- **reservas** uses `uuid` for primary key, others use `bigint`
- **reservas_fijas** uses `time` type (no date), **reservas** uses `timestamp`
- When a `reserva_fija` is deleted, related `reservas.reservacion_fija_id` is set to NULL (preserves history)
- When a `reserva` is deleted, related `pagos` are also deleted (CASCADE)
