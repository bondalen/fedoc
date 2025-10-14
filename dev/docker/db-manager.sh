#!/bin/bash
# =============================================================================
# Скрипт управления базами данных fedoc
# =============================================================================

set -e

COMPOSE_FILE="docker-compose.prod.yml"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Цвета для вывода
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Функция вывода с цветом
print_info() {
    echo -e "${BLUE}ℹ ${NC}$1"
}

print_success() {
    echo -e "${GREEN}✓${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}⚠${NC} $1"
}

print_error() {
    echo -e "${RED}✗${NC} $1"
}

# =============================================================================
# Проверка .env файла
# =============================================================================
check_env() {
    if [ ! -f ".env" ]; then
        print_error "Файл .env не найден!"
        print_info "Создайте его из шаблона: cp .env.example .env"
        print_info "Затем установите надежные пароли в файле .env"
        exit 1
    fi
    
    # Проверка, что пароли изменены
    if grep -q "change_me_to_strong_password" .env 2>/dev/null; then
        print_error "Пароли в .env не изменены!"
        print_info "Установите надежные пароли в файле .env"
        exit 1
    fi
    
    print_success "Файл .env найден и настроен"
}

# =============================================================================
# Команды управления
# =============================================================================

# Запуск ArangoDB
start_arango() {
    print_info "Запуск ArangoDB..."
    check_env
    docker-compose -f $COMPOSE_FILE up -d arangodb
    print_success "ArangoDB запущен"
    show_status
}

# Запуск PostgreSQL
start_postgres() {
    print_info "Запуск PostgreSQL..."
    check_env
    docker-compose -f $COMPOSE_FILE up -d postgres
    print_success "PostgreSQL запущен"
    show_status
}

# Запуск базовых БД (ArangoDB + PostgreSQL)
start_basic() {
    print_info "Запуск базовых БД (ArangoDB + PostgreSQL)..."
    check_env
    docker-compose -f $COMPOSE_FILE up -d arangodb postgres
    print_success "Базовые БД запущены"
    show_status
}

# Запуск всех БД
start_all() {
    print_info "Запуск всех БД (ArangoDB + PostgreSQL + MS SQL)..."
    check_env
    docker-compose -f $COMPOSE_FILE up -d
    print_success "Все БД запущены"
    show_status
}

# Запуск MS SQL отдельно
start_mssql() {
    print_info "Запуск MS SQL Server..."
    check_env
    docker-compose -f $COMPOSE_FILE up -d mssql
    print_success "MS SQL Server запущен"
    show_status
}

# Остановка всех БД
stop_all() {
    print_info "Остановка всех БД..."
    docker-compose -f $COMPOSE_FILE stop
    print_success "Все БД остановлены"
}

# Остановка ArangoDB
stop_arango() {
    print_info "Остановка ArangoDB..."
    docker-compose -f $COMPOSE_FILE stop arangodb
    print_success "ArangoDB остановлен"
}

# Остановка PostgreSQL
stop_postgres() {
    print_info "Остановка PostgreSQL..."
    docker-compose -f $COMPOSE_FILE stop postgres
    print_success "PostgreSQL остановлен"
}

# Остановка только MS SQL
stop_mssql() {
    print_info "Остановка MS SQL Server..."
    docker-compose -f $COMPOSE_FILE stop mssql
    print_success "MS SQL Server остановлен"
}

# Полная остановка и удаление контейнеров
down() {
    print_warning "ВНИМАНИЕ: Контейнеры будут удалены (данные сохранятся в volumes)"
    read -p "Продолжить? (y/N): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        docker-compose -f $COMPOSE_FILE down
        print_success "Контейнеры удалены"
    else
        print_info "Отменено"
    fi
}

# Статус БД
show_status() {
    echo ""
    print_info "Статус баз данных:"
    echo ""
    docker-compose -f $COMPOSE_FILE ps
    echo ""
    print_info "Потребление ресурсов:"
    docker stats --no-stream --format "table {{.Container}}\t{{.CPUPerc}}\t{{.MemUsage}}\t{{.MemPerc}}" $(docker-compose -f $COMPOSE_FILE ps -q 2>/dev/null) 2>/dev/null || echo "Нет запущенных контейнеров"
}

# Логи БД
show_logs() {
    local service=$1
    if [ -z "$service" ]; then
        print_error "Укажите сервис: arangodb, postgres или mssql"
        exit 1
    fi
    docker-compose -f $COMPOSE_FILE logs -f --tail=100 $service
}

# Бэкап БД
backup() {
    local service=$1
    local backup_dir="./backups"
    local timestamp=$(date +%Y%m%d_%H%M%S)
    
    mkdir -p $backup_dir
    
    case $service in
        arangodb)
            print_info "Создание бэкапа ArangoDB..."
            tar -czf "$backup_dir/arango_$timestamp.tar.gz" ./arango-data
            print_success "Бэкап создан: $backup_dir/arango_$timestamp.tar.gz"
            ;;
        postgres)
            print_info "Создание бэкапа PostgreSQL..."
            docker-compose -f $COMPOSE_FILE exec -T postgres pg_dumpall -U postgres | gzip > "$backup_dir/postgres_$timestamp.sql.gz"
            print_success "Бэкап создан: $backup_dir/postgres_$timestamp.sql.gz"
            ;;
        mssql)
            print_info "Создание бэкапа MS SQL..."
            tar -czf "$backup_dir/mssql_$timestamp.tar.gz" ./mssql-data
            print_success "Бэкап создан: $backup_dir/mssql_$timestamp.tar.gz"
            ;;
        all)
            print_info "Создание бэкапа всех БД..."
            backup arangodb
            backup postgres
            backup mssql
            ;;
        *)
            print_error "Неизвестный сервис: $service"
            print_info "Доступные: arangodb, postgres, mssql, all"
            exit 1
            ;;
    esac
}

# Мониторинг в реальном времени
monitor() {
    print_info "Мониторинг БД (Ctrl+C для выхода)..."
    docker stats $(docker-compose -f $COMPOSE_FILE ps -q 2>/dev/null)
}

# Показать информацию о подключении
show_connections() {
    echo ""
    print_info "Информация для подключения к БД:"
    echo ""
    echo "ArangoDB:"
    echo "  Host: localhost:8529"
    echo "  User: root"
    echo "  Password: (см. ARANGO_PASSWORD в .env)"
    echo "  Web UI: http://localhost:8529"
    echo ""
    echo "PostgreSQL:"
    echo "  Host: localhost:5432"
    echo "  User: postgres"
    echo "  Password: (см. POSTGRES_PASSWORD в .env)"
    echo "  Connection: postgresql://postgres:PASSWORD@localhost:5432/postgres"
    echo ""
    echo "MS SQL Server:"
    echo "  Host: localhost:1433"
    echo "  User: sa"
    echo "  Password: (см. MSSQL_PASSWORD в .env)"
    echo "  Connection: Server=localhost,1433;User=sa;Password=PASSWORD"
    echo ""
    print_warning "Примечание: БД доступны только с localhost (127.0.0.1)"
}

# =============================================================================
# Главное меню
# =============================================================================

show_help() {
    cat << EOF
${BLUE}Управление базами данных fedoc${NC}

${GREEN}Использование:${NC}
  ./db-manager.sh <команда>

${GREEN}Команды:${NC}
  ${YELLOW}Запуск (все БД запускаются по требованию):${NC}
    start           - Запустить базовые БД (ArangoDB + PostgreSQL)
    start-all       - Запустить все БД включая MS SQL
    start-arango    - Запустить только ArangoDB
    start-postgres  - Запустить только PostgreSQL
    start-mssql     - Запустить только MS SQL Server

  ${YELLOW}Остановка:${NC}
    stop            - Остановить все БД
    stop-arango     - Остановить только ArangoDB
    stop-postgres   - Остановить только PostgreSQL
    stop-mssql      - Остановить только MS SQL Server
    down            - Остановить и удалить контейнеры (данные сохранятся)

  ${YELLOW}Информация:${NC}
    status          - Показать статус и потребление ресурсов
    logs <service>  - Показать логи (arangodb, postgres, mssql)
    connections     - Показать информацию для подключения
    monitor         - Мониторинг ресурсов в реальном времени

  ${YELLOW}Бэкапы:${NC}
    backup <service> - Создать бэкап (arangodb, postgres, mssql, all)

  ${YELLOW}Справка:${NC}
    help            - Показать эту справку

${GREEN}Примеры:${NC}
  ./db-manager.sh start              # Запустить ArangoDB + PostgreSQL
  ./db-manager.sh start-arango       # Запустить только ArangoDB
  ./db-manager.sh start-mssql        # Запустить только MS SQL Server
  ./db-manager.sh status             # Проверить статус
  ./db-manager.sh logs arangodb      # Посмотреть логи ArangoDB
  ./db-manager.sh backup all         # Создать бэкапы всех БД
  ./db-manager.sh stop-mssql         # Остановить MS SQL (освободить RAM)
  ./db-manager.sh stop               # Остановить все БД

${GREEN}Режимы работы (запуск по требованию):${NC}
  ${YELLOW}Минимальный:${NC} Ничего не запущено (0 MB RAM)
  
  ${YELLOW}Работа с fedoc:${NC}
    ./db-manager.sh start-arango     # Только ArangoDB (~600 MB)
  
  ${YELLOW}Работа с PostgreSQL проектами:${NC}
    ./db-manager.sh start-postgres   # Только PostgreSQL (~400 MB)
  
  ${YELLOW}Обычный режим:${NC}
    ./db-manager.sh start            # ArangoDB + PostgreSQL (~1 GB)
  
  ${YELLOW}Работа с FEMSQ:${NC}
    ./db-manager.sh start-mssql      # Добавить MS SQL (~2.5 GB total)
    # После работы:
    ./db-manager.sh stop-mssql       # Освободить ~1.5 GB RAM
  
  ${YELLOW}Экономия ресурсов:${NC}
    ./db-manager.sh stop             # Остановить всё (освободить всю RAM)

EOF
}

# =============================================================================
# Обработка команд
# =============================================================================

case "${1:-help}" in
    start)
        start_basic
        ;;
    start-all)
        start_all
        ;;
    start-arango)
        start_arango
        ;;
    start-postgres)
        start_postgres
        ;;
    start-mssql)
        start_mssql
        ;;
    stop)
        stop_all
        ;;
    stop-arango)
        stop_arango
        ;;
    stop-postgres)
        stop_postgres
        ;;
    stop-mssql)
        stop_mssql
        ;;
    down)
        down
        ;;
    status)
        show_status
        ;;
    logs)
        show_logs "$2"
        ;;
    backup)
        backup "${2:-all}"
        ;;
    monitor)
        monitor
        ;;
    connections)
        show_connections
        ;;
    help|--help|-h)
        show_help
        ;;
    *)
        print_error "Неизвестная команда: $1"
        echo ""
        show_help
        exit 1
        ;;
esac

