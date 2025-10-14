#!/bin/bash
# =============================================================================
# Скрипт автоматического развертывания fedoc БД на production сервере
# Сервер: 176.108.244.252
# =============================================================================

set -e

SERVER="user1@176.108.244.252"
REPO_URL="https://github.com/bondalen/fedoc.git"
INSTALL_DIR="/home/user1/fedoc"

# Цвета
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m'

print_info() { echo -e "${BLUE}ℹ ${NC}$1"; }
print_success() { echo -e "${GREEN}✓${NC} $1"; }
print_warning() { echo -e "${YELLOW}⚠${NC} $1"; }
print_error() { echo -e "${RED}✗${NC} $1"; }
print_step() { echo -e "\n${BLUE}==>${NC} ${GREEN}$1${NC}\n"; }

# =============================================================================
# Шаг 1: Проверка доступа к серверу
# =============================================================================
check_server_access() {
    print_step "Шаг 1: Проверка доступа к серверу"
    
    if ssh -o ConnectTimeout=10 $SERVER "echo 'OK'" &>/dev/null; then
        print_success "Доступ к серверу $SERVER установлен"
    else
        print_error "Не удалось подключиться к серверу $SERVER"
        print_info "Проверьте SSH ключи и доступность сервера"
        exit 1
    fi
}

# =============================================================================
# Шаг 2: Очистка старых Docker образов
# =============================================================================
cleanup_old_images() {
    print_step "Шаг 2: Очистка старых Docker образов на сервере"
    
    ssh $SERVER << 'ENDSSH'
        # Удалить старый образ openjdk если есть
        if docker images | grep -q openjdk; then
            echo "Удаление старого образа openjdk:21-slim..."
            docker rmi openjdk:21-slim || true
        fi
        
        # Очистка неиспользуемых образов
        echo "Очистка неиспользуемых Docker ресурсов..."
        docker system prune -f
        
        echo "Проверка свободного места:"
        df -h / | tail -1
ENDSSH
    
    print_success "Очистка завершена"
}

# =============================================================================
# Шаг 3: Клонирование/обновление репозитория
# =============================================================================
setup_repository() {
    print_step "Шаг 3: Клонирование/обновление репозитория fedoc"
    
    ssh $SERVER << ENDSSH
        if [ -d "$INSTALL_DIR" ]; then
            echo "Репозиторий уже существует, обновление..."
            cd $INSTALL_DIR
            git pull
        else
            echo "Клонирование репозитория..."
            cd /home/user1
            git clone $REPO_URL
        fi
        
        cd $INSTALL_DIR/docker
        
        # Создать необходимые директории
        mkdir -p arango-data arango-apps postgres-data mssql-data backups
        mkdir -p init-scripts/arango init-scripts/postgres init-scripts/mssql
        
        # Сделать скрипт исполняемым
        chmod +x db-manager.sh
        
        echo "Структура создана"
ENDSSH
    
    print_success "Репозиторий готов"
}

# =============================================================================
# Шаг 4: Настройка .env файла
# =============================================================================
setup_env_file() {
    print_step "Шаг 4: Настройка .env файла с паролями"
    
    print_warning "ВАЖНО: Необходимо установить надежные пароли!"
    echo ""
    
    # Проверить, существует ли уже .env
    if ssh $SERVER "[ -f $INSTALL_DIR/docker/.env ]"; then
        print_warning ".env файл уже существует на сервере"
        read -p "Перезаписать? (y/N): " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            print_info "Пропуск настройки .env"
            return
        fi
    fi
    
    # Генерация безопасных паролей
    print_info "Генерация безопасных паролей..."
    
    ARANGO_PASS=$(openssl rand -base64 24 | tr -d "=+/" | cut -c1-24)
    POSTGRES_PASS=$(openssl rand -base64 24 | tr -d "=+/" | cut -c1-24)
    # MS SQL требует специальный формат
    MSSQL_PASS="Ms$(openssl rand -base64 12 | tr -d "=+/" | cut -c1-10)@2025"
    
    echo ""
    print_info "Сгенерированные пароли:"
    echo "ArangoDB:   $ARANGO_PASS"
    echo "PostgreSQL: $POSTGRES_PASS"
    echo "MS SQL:     $MSSQL_PASS"
    echo ""
    
    print_warning "СОХРАНИТЕ ЭТИ ПАРОЛИ В БЕЗОПАСНОМ МЕСТЕ!"
    echo ""
    read -p "Нажмите Enter для продолжения..."
    
    # Создать .env на сервере
    ssh $SERVER << ENDSSH
        cat > $INSTALL_DIR/docker/.env << 'EOF'
# Пароли для баз данных fedoc
# Создано автоматически: $(date +%Y-%m-%d)

ARANGO_PASSWORD=$ARANGO_PASS
POSTGRES_PASSWORD=$POSTGRES_PASS
MSSQL_PASSWORD=$MSSQL_PASS
EOF
        chmod 600 $INSTALL_DIR/docker/.env
ENDSSH
    
    print_success ".env файл создан и настроен"
}

# =============================================================================
# Шаг 5: Загрузка Docker образов
# =============================================================================
pull_docker_images() {
    print_step "Шаг 5: Загрузка Docker образов"
    
    print_info "Загрузка образов (это может занять несколько минут)..."
    
    ssh $SERVER << ENDSSH
        cd $INSTALL_DIR/docker
        docker-compose -f docker-compose.prod.yml pull
ENDSSH
    
    print_success "Docker образы загружены"
}

# =============================================================================
# Шаг 6: Запуск базовых БД
# =============================================================================
start_databases() {
    print_step "Шаг 6: Запуск базовых баз данных"
    
    print_info "Запуск ArangoDB и PostgreSQL..."
    
    ssh $SERVER << ENDSSH
        cd $INSTALL_DIR/docker
        ./db-manager.sh start
        
        echo ""
        echo "Ожидание запуска контейнеров (30 секунд)..."
        sleep 30
        
        echo ""
        ./db-manager.sh status
ENDSSH
    
    print_success "Базы данных запущены"
}

# =============================================================================
# Шаг 7: Проверка работоспособности
# =============================================================================
verify_deployment() {
    print_step "Шаг 7: Проверка работоспособности"
    
    print_info "Проверка API баз данных..."
    
    ssh $SERVER << 'ENDSSH'
        cd /home/user1/fedoc/docker
        
        echo "ArangoDB:"
        curl -s http://localhost:8529/_api/version | grep -q version && echo "✓ OK" || echo "✗ FAIL"
        
        echo "PostgreSQL:"
        docker exec fedoc-postgres psql -U postgres -c "SELECT 1;" &>/dev/null && echo "✓ OK" || echo "✗ FAIL"
ENDSSH
    
    print_success "Проверка завершена"
}

# =============================================================================
# Шаг 8: Показать информацию
# =============================================================================
show_info() {
    print_step "Развертывание завершено!"
    
    cat << EOF

${GREEN}✓ Базы данных успешно развернуты на сервере${NC}

${BLUE}Запущенные БД:${NC}
  • ArangoDB  (порт 8529)
  • PostgreSQL (порт 5432)

${BLUE}Доступ к Web UI ArangoDB:${NC}
  SSH туннель: ssh -L 8529:localhost:8529 $SERVER -N
  Затем: http://localhost:8529
  User: root
  Password: (см. на сервере в ~/.fedoc-passwords или в .env)

${BLUE}Управление БД на сервере:${NC}
  ssh $SERVER
  cd $INSTALL_DIR/docker
  ./db-manager.sh help

${BLUE}Запуск MS SQL Server (по требованию):${NC}
  ssh $SERVER
  cd $INSTALL_DIR/docker
  ./db-manager.sh start-mssql

${BLUE}Документация:${NC}
  • Полная инструкция: $INSTALL_DIR/docker/DEPLOYMENT.md
  • Справка: ./db-manager.sh help

${YELLOW}ВАЖНО: Пароли сохранены на сервере в:${NC}
  $INSTALL_DIR/docker/.env (chmod 600)

${YELLOW}Рекомендуется:${NC}
  1. Сохранить пароли в безопасном месте
  2. Настроить регулярные бэкапы: ./db-manager.sh backup all
  3. Мониторить ресурсы: ./db-manager.sh monitor

EOF
}

# =============================================================================
# Главная функция
# =============================================================================
main() {
    cat << EOF
${BLUE}═══════════════════════════════════════════════════════════════════${NC}
${GREEN}  Автоматическое развертывание fedoc БД на production сервере${NC}
${BLUE}═══════════════════════════════════════════════════════════════════${NC}

Сервер: $SERVER
Репозиторий: $REPO_URL
Директория: $INSTALL_DIR

Будут установлены:
  • ArangoDB 3.11 (Multi-Model БД)
  • PostgreSQL 16 (Реляционная БД)
  • MS SQL Server 2022 (по требованию)

EOF
    
    read -p "Продолжить развертывание? (y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        print_info "Развертывание отменено"
        exit 0
    fi
    
    echo ""
    
    check_server_access
    cleanup_old_images
    setup_repository
    setup_env_file
    pull_docker_images
    start_databases
    verify_deployment
    show_info
}

# Запуск
main "$@"

