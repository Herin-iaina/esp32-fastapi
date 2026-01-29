#!/bin/bash

# Checklist de Vérification - Système d'Incubation
# Usage: bash verify.sh

echo "🔍 Vérification du Système d'Incubation v2.0"
echo "=============================================="
echo ""

PASS="✅"
FAIL="❌"
WARNING="⚠️"

# Compteurs
TOTAL=0
PASSED=0
FAILED=0

# Fonction de test
test_command() {
    local name="$1"
    local cmd="$2"
    local expected="$3"
    
    TOTAL=$((TOTAL + 1))
    echo -n "[$TOTAL] $name... "
    
    if eval "$cmd" &>/dev/null; then
        echo "$PASS"
        PASSED=$((PASSED + 1))
    else
        echo "$FAIL"
        FAILED=$((FAILED + 1))
    fi
}

# Tests
echo "🐳 Docker & Conteneurs:"
test_command "Docker installé" "command -v docker"
test_command "Backend container running" "docker ps | grep -q esp32-backend"
test_command "Database container running" "docker ps | grep -q esp32-db"
test_command "Frontend container running" "docker ps | grep -q esp32-frontend || docker ps | grep -q nginx"

echo ""
echo "🌐 Connectivité API:"
test_command "Backend health check" "curl -s http://localhost:8000/api/health | grep -q 'ok'"
test_command "API documentation" "curl -s http://localhost:8000/docs > /dev/null"

echo ""
echo "🐘 PostgreSQL:"
test_command "PostgreSQL connection" "docker exec esp32-db psql -U user -d smartelia_db -c 'SELECT 1;' 2>/dev/null"
test_command "users table exists" "docker exec esp32-db psql -U user -d smartelia_db -c \"SELECT EXISTS(SELECT 1 FROM information_schema.tables WHERE table_name='users')\" 2>/dev/null | grep -q 't'"
test_command "parameter_data table exists" "docker exec esp32-db psql -U user -d smartelia_db -c \"SELECT EXISTS(SELECT 1 FROM information_schema.tables WHERE table_name='parameter_data')\" 2>/dev/null | grep -q 't'"
test_command "data_temp table exists" "docker exec esp32-db psql -U user -d smartelia_db -c \"SELECT EXISTS(SELECT 1 FROM information_schema.tables WHERE table_name='data_temp')\" 2>/dev/null | grep -q 't'"

echo ""
echo "👤 Utilisateurs:"
ADMIN_COUNT=$(docker exec esp32-db psql -U user -d smartelia_db -c "SELECT COUNT(*) FROM login WHERE user_name='admin';" 2>/dev/null | grep -o '[0-9]' | head -1)
if [ "$ADMIN_COUNT" = "1" ]; then
    echo "[*] Admin user exists... $PASS"
    PASSED=$((PASSED + 1))
else
    echo "[*] Admin user exists... $FAIL"
    FAILED=$((FAILED + 1))
fi
TOTAL=$((TOTAL + 1))

echo ""
echo "🔐 Authentification:"
test_command "Login endpoint works" "curl -s -X POST http://localhost:8000/api/auth/login -H 'Content-Type: application/json' -d '{\"username\":\"admin\",\"password\":\"test123456\"}' | grep -q 'access_token'"

echo ""
echo "⚙️ Paramètres:"
test_command "GET /parameter works" "curl -s http://localhost:8000/api/parameter | grep -q 'temp_incubation'"
test_command "Parameter data in response" "curl -s http://localhost:8000/api/parameter | grep -q 'espece'"

echo ""
echo "📁 Frontend Files:"
test_command "Frontend dist exists" "[ -d 'frontend/dist' ]"
test_command "Frontend index.html exists" "[ -f 'frontend/dist/index.html' ]"

echo ""
echo "📄 Documentation:"
test_command "README exists" "[ -f 'README.md' ]"
test_command "USER_GUIDE exists" "[ -f 'USER_GUIDE.md' ]"
test_command "TEST_PLAN exists" "[ -f 'TEST_PLAN.md' ]"
test_command "CHANGELOG exists" "[ -f 'CHANGELOG.md' ]"
test_command "TROUBLESHOOTING exists" "[ -f 'TROUBLESHOOTING.md' ]"

echo ""
echo "🔧 Scripts:"
test_command "start.sh executable" "[ -x 'start.sh' ]"
test_command "stop.sh executable" "[ -x 'stop.sh' ]"

echo ""
echo "═══════════════════════════════════════════════"
echo ""
echo "📊 Résultats: $PASSED / $TOTAL ✅"
echo ""

if [ $FAILED -gt 0 ]; then
    echo "$FAIL $FAILED tests échoués"
    echo ""
    echo "Pour plus de détails, consulter TROUBLESHOOTING.md"
    exit 1
else
    echo "🎉 Tous les tests sont passés!"
    echo ""
    echo "Le système est prêt pour l'utilisation:"
    echo "  → http://localhost:8000"
    echo "  → Admin: test123456"
    exit 0
fi
