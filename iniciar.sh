#!/bin/bash
# ============================================================
# iniciar.sh — Sistema SQL Interactivo · BD UTN
# ============================================================

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
HTML_FILE="$SCRIPT_DIR/Ejercicios_SQL_Guia.html"

echo ""
echo "  🐳 Levantando PostgreSQL + Adminer..."
echo ""

cd "$SCRIPT_DIR"
docker compose up -d

if [ $? -ne 0 ]; then
  echo "  ❌ Error al levantar Docker. ¿Está Docker Desktop corriendo?"
  exit 1
fi

echo ""
echo "  ⏳ Esperando que PostgreSQL esté listo..."
sleep 4

echo ""
echo "  ✅ Sistema listo!"
echo ""
echo "  ┌─────────────────────────────────────────────┐"
echo "  │  🌐 Adminer (cliente SQL web)               │"
echo "  │     http://localhost:8080                   │"
echo "  │                                             │"
echo "  │  Conectar con:                              │"
echo "  │    Sistema:   PostgreSQL                    │"
echo "  │    Servidor:  postgres                      │"
echo "  │    Usuario:   admin                         │"
echo "  │    Password:  admin                         │"
echo "  │    Base:      utn_bd                        │"
echo "  └─────────────────────────────────────────────┘"
echo ""

# Abrir Adminer y la guía de ejercicios
open http://localhost:5050

echo "  📋 SQL Playground abierto en el navegador."
echo ""
echo "  Para detener: docker compose down"
echo "  Para borrar todo: docker compose down -v"
echo ""
