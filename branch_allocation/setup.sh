#!/bin/bash
# ── CollegeMatch Setup Script ─────────────────────────────
# Run this once after extracting the project:
#   chmod +x setup.sh && ./setup.sh

set -e

echo "🔧 Installing dependencies..."
pip install -r requirements.txt

echo "🗄  Running database migrations..."
python3 manage.py migrate

echo "👤 Creating admin user (admin / admin123)..."
python3 manage.py create_admin

echo ""
echo "✅ Setup complete!"
echo ""
echo "Start the server with:"
echo "   python manage.py runserver"
echo ""
echo "Then open: http://127.0.0.1:8000"
echo ""
echo "Login credentials:"
echo "   Admin   → username: admin       password: admin123"
echo "   Student → password: jee2025  (load demo data first)"
echo ""
