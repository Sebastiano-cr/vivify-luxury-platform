#!/bin/bash
# =============================================================================
# backup.sh — Backup Vivify databases + WORM storage
# Rotation: keeps 7 daily backups
# =============================================================================
set -euo pipefail

BACKUP_DIR="${BACKUP_DIR:-/var/www/vivify/backups}"
SHARED_DIR="${SHARED_DIR:-/var/www/vivify/shared}"
RETENTION_DAYS="${RETENTION_DAYS:-7}"
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
LOG_FILE="${BACKUP_DIR}/backup.log"

mkdir -p "$BACKUP_DIR"
exec > >(tee -a "$LOG_FILE") 2>&1

echo "[$(date '+%Y-%m-%d %H:%M:%S')] Backup iniciado"

# ── Databases ──
DB_DIR="$BACKUP_DIR/db/$TIMESTAMP"
mkdir -p "$DB_DIR"

for db in vivify_backend.db ledger_v2.db; do
  SRC="$SHARED_DIR/$db"
  if [ -f "$SRC" ]; then
    DEST="$DB_DIR/${db}.gz"
    sqlite3 "$SRC" ".backup '${DB_DIR}/${db}'" && gzip -f "$DB_DIR/$db"
    echo "  DB: $db -> $DEST ($(du -h "$DEST" | cut -f1))"
  else
    echo "  DB: $db — não encontrado, ignorado"
  fi
done

# ── WORM storage ──
WORM_DIR="$SHARED_DIR/worm"
if [ -d "$WORM_DIR" ]; then
  WORM_DEST="$BACKUP_DIR/worm/$TIMESTAMP"
  mkdir -p "$WORM_DEST"
  rsync -a "$WORM_DIR/" "$WORM_DEST/" 2>/dev/null
  echo "  WORM: $WORM_DIR -> $WORM_DEST"
fi

# ── Rotação ──
find "$BACKUP_DIR/db" -maxdepth 1 -type d -mtime +"$RETENTION_DAYS" -exec rm -rf {} \; 2>/dev/null
find "$BACKUP_DIR/worm" -maxdepth 1 -type d -mtime +"$RETENTION_DAYS" -exec rm -rf {} \; 2>/dev/null

# ── Limpeza de backups órfãos ──
find "$BACKUP_DIR/db" -maxdepth 1 -type f -mtime +"$RETENTION_DAYS" -delete 2>/dev/null

# ── Manifest ──
MANIFEST="$BACKUP_DIR/db/$TIMESTAMP/manifest.txt"
{
  echo "Backup: $TIMESTAMP"
  echo "Host:   $(hostname)"
  for f in "$DB_DIR"/*.gz; do
    [ -f "$f" ] && echo "  $(basename "$f"): $(sha256sum "$f" | cut -d' ' -f1)"
  done
} > "$MANIFEST"

echo "[$(date '+%Y-%m-%d %H:%M:%S')] Backup concluido — $DB_DIR"
ls -lh "$DB_DIR"/*.gz 2>/dev/null | awk '{print "  " $5 " " $NF}'
