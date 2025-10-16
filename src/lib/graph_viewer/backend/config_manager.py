#!/usr/bin/env python3
"""
Менеджер конфигурации Graph Viewer с поддержкой профилей машин
"""

import os
import sys
import socket
import yaml
from pathlib import Path
from typing import Dict, Any, Optional
from datetime import datetime
from copy import deepcopy


def log(message):
    """Вывод в stderr чтобы не нарушать MCP протокол"""
    print(message, file=sys.stderr, flush=True)


class ConfigManager:
    """
    Менеджер конфигурации с поддержкой профилей машин
    
    Порядок загрузки (приоритет от низкого к высокому):
    1. config/graph_viewer.yaml          - базовые параметры
    2. config/machines/{user}-{hostname}.yaml - профиль машины
    3. config/graph_viewer.local.yaml    - локальные переопределения
    4. Переменные окружения              - финальное переопределение
    """
    
    def __init__(self, project_root: Optional[Path] = None):
        """
        Args:
            project_root: Корень проекта fedoc (auto-detect если None)
        """
        if project_root is None:
            # Автоопределение корня проекта (5 уровней вверх от этого файла)
            project_root = Path(__file__).parent.parent.parent.parent.parent
        
        self.project_root = Path(project_root).resolve()
        self.config_dir = self.project_root / 'config'
        
        # Определяем текущую машину
        self.username = os.getenv('USER', 'unknown')
        self.hostname = self._detect_hostname()
        self.machine_name = f"{self.username}-{self.hostname}"
        
        # Загружаем конфигурацию
        self.config = self._load_layered_config()
        
    def _detect_hostname(self) -> str:
        """Определить имя машины (без домена)"""
        hostname = socket.gethostname()
        # Убираем доменное имя, оставляем только hostname
        return hostname.split('.')[0]
    
    def _detect_os(self) -> str:
        """Определить ОС"""
        import platform
        system = platform.system().lower()
        
        if system == 'linux':
            # Попытка определить дистрибутив
            try:
                with open('/etc/os-release') as f:
                    for line in f:
                        if line.startswith('PRETTY_NAME='):
                            return line.split('=')[1].strip().strip('"')
            except:
                pass
            return 'linux'
        elif system == 'darwin':
            return 'macOS'
        elif system == 'windows':
            return 'Windows'
        else:
            return system
    
    def _load_yaml(self, path: Path) -> Dict[str, Any]:
        """Загрузить YAML файл"""
        try:
            if not path.exists():
                return {}
            
            with open(path, 'r', encoding='utf-8') as f:
                content = yaml.safe_load(f) or {}
                return content
        except Exception as e:
            log(f"⚠️  Ошибка загрузки {path}: {e}")
            return {}
    
    def _deep_merge(self, base: Dict, override: Dict) -> Dict:
        """
        Глубокое слияние словарей
        
        Args:
            base: Базовый словарь
            override: Словарь переопределений
            
        Returns:
            Объединенный словарь
        """
        result = deepcopy(base)
        
        for key, value in override.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                # Рекурсивное слияние вложенных словарей
                result[key] = self._deep_merge(result[key], value)
            else:
                # Простое переопределение
                result[key] = deepcopy(value)
        
        return result
    
    def _load_layered_config(self) -> Dict[str, Any]:
        """Загрузить конфигурацию слоями"""
        config = {}
        
        # Слой 1: Базовая конфигурация
        base_path = self.config_dir / 'graph_viewer.yaml'
        base_config = self._load_yaml(base_path)
        
        if not base_config:
            log(f"⚠️  Базовая конфигурация не найдена: {base_path}")
            log("   Использую defaults")
            base_config = self._default_config()
        else:
            log(f"✓ Загружена базовая конфигурация: {base_path}")
        
        config = self._deep_merge(config, base_config)
        
        # Слой 2: Профиль машины
        machine_path = self.config_dir / 'machines' / f'{self.machine_name}.yaml'
        
        if machine_path.exists():
            machine_config = self._load_yaml(machine_path)
            config = self._deep_merge(config, machine_config)
            log(f"✓ Загружен профиль машины: {self.machine_name}")
        else:
            # Машина не найдена
            if config.get('machines', {}).get('ask_if_unknown', True):
                log(f"\n⚠️  Профиль машины '{self.machine_name}' не найден")
                
                # В интерактивном режиме создаем профиль
                if sys.stdin.isatty():
                    machine_config = self._create_machine_profile_interactive()
                    config = self._deep_merge(config, machine_config)
                else:
                    # В неинтерактивном режиме (MCP) - создаем с defaults
                    log("   Создаю профиль с defaults (неинтерактивный режим)")
                    machine_config = self._create_machine_profile_defaults()
                    config = self._deep_merge(config, machine_config)
                    
                    # Сохраняем профиль для следующего раза
                    if config.get('machines', {}).get('save_new_profiles', True):
                        self._save_machine_profile(machine_config)
                        log(f"✓ Профиль сохранен: {machine_path}")
                        log("   Закоммитьте файл, если хотите поделиться настройками")
        
        # Слой 3: Локальные переопределения
        local_path = self.config_dir / 'graph_viewer.local.yaml'
        if local_path.exists():
            local_config = self._load_yaml(local_path)
            config = self._deep_merge(config, local_config)
            log("✓ Загружены локальные переопределения")
        
        # Слой 4: Переменные окружения
        config = self._override_from_env(config)
        
        # Слой 5: Загрузка секретов из .env
        self._load_secrets(self.config_dir / '.secrets.env')
        
        return config
    
    def _default_config(self) -> Dict[str, Any]:
        """Конфигурация по умолчанию"""
        return {
            'remote_server': {
                'host': '176.108.244.252',
                'user': 'user1',
                'ssh_alias': 'vuege-server'
            },
            'arango': {
                'host': 'http://localhost:8529',
                'database': 'fedoc',
                'user': 'root',
                'password_env': 'ARANGO_PASSWORD'
            },
            'ports': {
                'ssh_tunnel': 8529,
                'api_server': 8899,
                'vite_server': 5173
            },
            'paths': {
                'frontend': 'src/lib/graph_viewer/frontend',
                'backend': 'src/lib/graph_viewer/backend',
                'venv_python': 'venv/bin/python'
            },
            'options': {
                'auto_install_npm': False,
                'auto_create_ssh_config': True,
                'auto_open_browser': True,
                'check_dependencies': True,
                'timeout_seconds': 30
            }
        }
    
    def _create_machine_profile_defaults(self) -> Dict[str, Any]:
        """Создать профиль машины с разумными defaults"""
        return {
            'machine': {
                'hostname': self.hostname,
                'username': self.username,
                'os': self._detect_os(),
                'description': f"Машина {self.machine_name} (auto-created)",
                'added': datetime.now().strftime('%Y-%m-%d'),
                'auto_created': True
            },
            'ssh': {
                'key_path': '~/.ssh/id_ed25519',
                'config_path': '~/.ssh/config'
            },
            'project': {
                'root': str(self.project_root)
            },
            'options': {
                'auto_open_browser': True
            }
        }
    
    def _create_machine_profile_interactive(self) -> Dict[str, Any]:
        """
        Интерактивное создание профиля для новой машины
        
        Returns:
            Dict с конфигурацией новой машины
        """
        log("\nСоздание профиля для новой машины")
        log("(нажмите Enter для использования значения по умолчанию)")
        log("")
        
        # Начинаем с defaults
        machine_config = self._create_machine_profile_defaults()
        
        # Спрашиваем дополнительные параметры
        try:
            description = input(f"Описание машины [{machine_config['machine']['description']}]: ").strip()
            if description:
                machine_config['machine']['description'] = description
            
            ssh_key = input(f"Путь к SSH ключу [{machine_config['ssh']['key_path']}]: ").strip()
            if ssh_key:
                machine_config['ssh']['key_path'] = ssh_key
            
            project_root = input(f"Корень проекта [{self.project_root}]: ").strip()
            if project_root:
                machine_config['project']['root'] = project_root
            
            auto_browser = self._ask_yes_no("Автоматически открывать браузер?", default=True)
            machine_config['options']['auto_open_browser'] = auto_browser
            
            # Предлагаем сохранить
            save = self._ask_yes_no(f"\nСохранить профиль в config/machines/{self.machine_name}.yaml?", default=True)
            if save:
                self._save_machine_profile(machine_config)
                log(f"✓ Профиль сохранен")
                log("  Не забудьте закоммитить файл, если хотите поделиться настройками")
            
        except (EOFError, KeyboardInterrupt):
            log("\n⚠️  Прервано. Использую defaults")
        
        return machine_config
    
    def _save_machine_profile(self, config: Dict):
        """Сохранить профиль машины в файл"""
        machines_dir = self.config_dir / 'machines'
        machines_dir.mkdir(parents=True, exist_ok=True)
        
        profile_path = machines_dir / f"{self.machine_name}.yaml"
        
        try:
            with open(profile_path, 'w', encoding='utf-8') as f:
                yaml.dump(config, f, default_flow_style=False, allow_unicode=True, sort_keys=False)
        except Exception as e:
            log(f"⚠️  Ошибка сохранения профиля: {e}")
    
    def _ask_yes_no(self, question: str, default: bool = True) -> bool:
        """Спросить пользователя да/нет"""
        prompt = f"{question} [{'Y/n' if default else 'y/N'}]: "
        try:
            response = input(prompt).strip().lower()
            if not response:
                return default
            return response in ['y', 'yes', 'да', 'д']
        except (EOFError, KeyboardInterrupt):
            return default
    
    def _override_from_env(self, config: Dict) -> Dict:
        """Переопределить значения из переменных окружения"""
        
        # SSH
        if os.getenv('FEDOC_SSH_HOST'):
            config.setdefault('remote_server', {})['host'] = os.getenv('FEDOC_SSH_HOST')
        if os.getenv('FEDOC_SSH_USER'):
            config.setdefault('remote_server', {})['user'] = os.getenv('FEDOC_SSH_USER')
        
        # ArangoDB
        if os.getenv('ARANGO_HOST'):
            config.setdefault('arango', {})['host'] = os.getenv('ARANGO_HOST')
        if os.getenv('ARANGO_DB'):
            config.setdefault('arango', {})['database'] = os.getenv('ARANGO_DB')
        if os.getenv('ARANGO_USER'):
            config.setdefault('arango', {})['user'] = os.getenv('ARANGO_USER')
        
        # Порты
        if os.getenv('GRAPH_VIEWER_API_PORT'):
            config.setdefault('ports', {})['api_server'] = int(os.getenv('GRAPH_VIEWER_API_PORT'))
        if os.getenv('GRAPH_VIEWER_FRONTEND_PORT'):
            config.setdefault('ports', {})['vite_server'] = int(os.getenv('GRAPH_VIEWER_FRONTEND_PORT'))
        
        return config
    
    def _load_secrets(self, env_file: Path):
        """Загрузить секреты из .env файла"""
        if not env_file.exists():
            return
        
        try:
            with open(env_file) as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#') and '=' in line:
                        key, value = line.split('=', 1)
                        os.environ[key.strip()] = value.strip()
            
            log(f"✓ Загружены секреты из {env_file}")
        except Exception as e:
            log(f"⚠️  Ошибка загрузки секретов: {e}")
    
    def get(self, key: str, default=None) -> Any:
        """
        Получить значение конфигурации по ключу
        
        Поддерживает точечную нотацию: 'remote_server.host'
        
        Args:
            key: Ключ (может быть с точками)
            default: Значение по умолчанию
            
        Returns:
            Значение из конфигурации или default
        """
        keys = key.split('.')
        value = self.config
        
        for k in keys:
            if isinstance(value, dict):
                value = value.get(k)
                if value is None:
                    return default
            else:
                return default
        
        return value if value is not None else default
    
    def get_path(self, key: str, relative_to_project: bool = True) -> Path:
        """
        Получить путь из конфигурации
        
        Args:
            key: Ключ конфигурации
            relative_to_project: Если True, относительные пути разрешаются от project_root
            
        Returns:
            Path объект
        """
        value = self.get(key)
        if value is None:
            raise ValueError(f"Путь не найден в конфигурации: {key}")
        
        path = Path(value).expanduser()
        
        if not path.is_absolute() and relative_to_project:
            path = self.project_root / path
        
        return path.resolve()
    
    def get_password(self, env_var_name: str = None) -> Optional[str]:
        """
        Получить пароль из переменной окружения
        
        Args:
            env_var_name: Имя переменной окружения (или берется из config)
            
        Returns:
            Пароль или None
        """
        if env_var_name is None:
            env_var_name = self.get('arango.password_env', 'ARANGO_PASSWORD')
        
        password = os.getenv(env_var_name)
        
        if not password:
            log(f"⚠️  Пароль не найден: {env_var_name}")
            log(f"   Установите переменную окружения или создайте config/.secrets.env")
        
        return password
    
    def is_first_run(self) -> bool:
        """Проверить, первый ли это запуск (нет профиля машины)"""
        machine_path = self.config_dir / 'machines' / f'{self.machine_name}.yaml'
        return not machine_path.exists()
    
    def __repr__(self) -> str:
        return f"ConfigManager(machine='{self.machine_name}', project_root='{self.project_root}')"


# Singleton instance для удобства
_config_manager_instance = None

def get_config() -> ConfigManager:
    """Получить глобальный экземпляр ConfigManager (singleton)"""
    global _config_manager_instance
    if _config_manager_instance is None:
        _config_manager_instance = ConfigManager()
    return _config_manager_instance



