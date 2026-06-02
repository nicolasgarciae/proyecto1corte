#!/usr/bin/env bash
# Dump periodico de MySQL a /backups.
# Genera un snapshot logico consistente (mysqldump --single-transaction)
# que Duplicati luego respalda cifrado.
set -uo pipefail

INTERVAL="${BACKUP_INTERVAL:-3600}"   # segundos entre dumps (default 1h)
KEEP="${BACKUP_KEEP:-24}"             # cuantos dumps locales conservar
OUT_DIR="/backups"

mkdir -p "$OUT_DIR"
echo "[backup] iniciado. intervalo=${INTERVAL}s, conservar=${KEEP} dumps"

while true; do
  ts="$(date +%Y%m%d_%H%M%S)"
  file="${OUT_DIR}/${MYSQL_DB}_${ts}.sql"

  if mysqldump \
        --single-transaction \
        --quick \
        --skip-lock-tables \
        -h "${MYSQL_HOST:-mysql}" \
        -u"${MYSQL_USER}" \
        -p"${MYSQL_PASSWORD}" \
        "${MYSQL_DB}" > "${file}" 2>/tmp/dump_err; then
    size="$(du -h "${file}" | cut -f1)"
    echo "[backup] ok  ${file} (${size})"
  else
    echo "[backup] FALLO dump:"; cat /tmp/dump_err
    rm -f "${file}"
  fi

  # retencion: borra los dumps mas viejos, conserva los KEEP mas nuevos
  ls -1t "${OUT_DIR}"/*.sql 2>/dev/null | tail -n +"$((KEEP + 1))" | xargs -r rm -f

  sleep "${INTERVAL}"
done
