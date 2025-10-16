#!/usr/bin/env python3
"""
Интерактивная настройка компонентов Graph Viewer
Проверка зависимостей, SSH ключей, конфигурации
"""

import os
import sys
import subprocess
from pathlib import Path
from typing import Optional

from .config_manager import ConfigManager


def log(message):
    """Вывод в stderr чтобы не нарушать MCP протокол"""
    print(message, file=sys.stderr, flush=True)


class InteractiveSetup:
    """Интерактивная настройка и проверка зависимостей"""
    
    def __init__(self, config: ConfigManager):
        """
        Args:
            config: Менеджер конфигурации
        """
        self.config = config
        self.interactive = sys.stdin.isatty()
    
    def check_all(self):
        """Проверить все зависимости"""
        log("\n🔍 Проверка зависимостей Graph Viewer...")
        log("")
        
        # 1. npm зависимости
        self.check_and_install_npm_dependencies()
        
        # 2. SSH ключи
        self.check_and_create_ssh_key()
        
        # 3. SSH конфигурация
        self.check_and_create_ssh_config()
        
        # 4. Python пакеты
        self.check_python_packages()
        
        log("\n✅ Проверка зависимостей завершена")
    
    def check_and_install_npm_dependencies(self):
        """Проверить и установить npm зависимости"""
        frontend_dir = self.config.get_path('project.root') / self.config.get('paths.frontend')
        
        if not self._check_npm_deps(frontend_dir):
            log("⚠️  npm зависимости не установлены")
            
            if self.config.get('options.auto_install_npm'):
                # Автоматическая установка
                log("   Автоматическая установка включена")
                self._install_npm_deps(frontend_dir)
            elif self.interactive:
                # Спросить пользователя
                if self._ask_user("Установить npm зависимости сейчас?"):
                    self._install_npm_deps(frontend_dir)
                else:
                    log("   ⚠️  Пропущено. Установите вручную: cd {} && npm install".format(frontend_dir))
            else:
                # Неинтерактивный режим - показать инструкцию
                log("   ℹ️  Установите вручную: cd {} && npm install".format(frontend_dir))
        else:
            log("✓ npm зависимости установлены")
    
    def check_and_create_ssh_key(self):
        """Проверить и создать SSH ключ"""
        ssh_key = Path(self.config.get('ssh.key_path', '~/.ssh/id_ed25519')).expanduser()
        
        if not ssh_key.exists():
            log(f"⚠️  SSH ключ не найден: {ssh_key}")
            
            if self.config.get('options.auto_create_ssh_key'):
                # Автоматическое создание
                log("   Автоматическое создание включено")
                self._create_ssh_key(ssh_key)
                self._copy_ssh_key_to_server()
            elif self.interactive:
                # Спросить пользователя
                if self._ask_user("Создать SSH ключ сейчас?"):
                    self._create_ssh_key(ssh_key)
                    if self._ask_user("Скопировать ключ на сервер?"):
                        self._copy_ssh_key_to_server()
                else:
                    log(f"   ⚠️  Пропущено. Создайте ключ вручную: ssh-keygen -t ed25519 -f {ssh_key}")
            else:
                # Неинтерактивный режим
                log(f"   ℹ️  Создайте ключ вручную: ssh-keygen -t ed25519 -f {ssh_key}")
        else:
            log(f"✓ SSH ключ найден: {ssh_key}")
    
    def check_and_create_ssh_config(self):
        """Проверить и создать SSH конфигурацию"""
        ssh_alias = self.config.get('remote_server.ssh_alias', 'vuege-server')
        
        if not self._check_ssh_config(ssh_alias):
            log(f"⚠️  SSH алиас '{ssh_alias}' не найден в ~/.ssh/config")
            
            if self.config.get('options.auto_create_ssh_config'):
                # Автоматическое создание
                log("   Автоматическое создание SSH конфигурации включено")
                self._create_ssh_config()
            elif self.interactive:
                # Спросить пользователя
                if self._ask_user(f"Создать SSH конфигурацию для '{ssh_alias}'?"):
                    self._create_ssh_config()
                else:
                    log("   ⚠️  Пропущено")
            else:
                # Неинтерактивный режим
                log("   ℹ️  Создайте конфигурацию вручную или установите auto_create_ssh_config: true")
        else:
            log(f"✓ SSH алиас '{ssh_alias}' найден")
    
    def check_python_packages(self):
        """Проверить Python пакеты"""
        required = {
            'arango': 'python-arango',
            'flask': 'flask',
            'flask_cors': 'flask-cors',
            'yaml': 'pyyaml'
        }
        
        missing = []
        for module, package in required.items():
            try:
                __import__(module)
            except ImportError:
                missing.append(package)
        
        if missing:
            log(f"⚠️  Отсутствующие Python пакеты: {', '.join(missing)}")
            log(f"   Установите: pip install {' '.join(missing)}")
        else:
            log("✓ Все Python пакеты установлены")
    
    def _check_npm_deps(self, frontend_dir: Path) -> bool:
        """Проверить установлены ли npm зависимости"""
        node_modules = frontend_dir / 'node_modules'
        package_json = frontend_dir / 'package.json'
        
        if not package_json.exists():
            log(f"   ⚠️  package.json не найден: {package_json}")
            return False
        
        if not node_modules.exists():
            return False
        
        # Проверить что node_modules не пустой
        try:
            return len(list(node_modules.iterdir())) > 0
        except:
            return False
    
    def _install_npm_deps(self, frontend_dir: Path) -> bool:
        """Установить npm зависимости"""
        log(f"   Установка npm зависимостей в {frontend_dir}...")
        
        try:
            result = subprocess.run(
                ['npm', 'install'],
                cwd=frontend_dir,
                capture_output=True,
                text=True,
                timeout=300  # 5 минут
            )
            
            if result.returncode == 0:
                log("   ✓ npm зависимости установлены")
                return True
            else:
                log(f"   ✗ Ошибка установки: {result.stderr}")
                return False
                
        except subprocess.TimeoutExpired:
            log("   ✗ Таймаут установки (>5 минут)")
            return False
        except FileNotFoundError:
            log("   ✗ npm не найден. Установите Node.js")
            return False
        except Exception as e:
            log(f"   ✗ Ошибка: {e}")
            return False
    
    def _check_ssh_config(self, alias: str) -> bool:
        """Проверить существует ли SSH алиас"""
        ssh_config = Path.home() / '.ssh' / 'config'
        
        if not ssh_config.exists():
            return False
        
        try:
            with open(ssh_config) as f:
                content = f.read()
                return f'Host {alias}' in content
        except:
            return False
    
    def _create_ssh_config(self):
        """Создать SSH конфигурацию"""
        ssh_config_path = Path.home() / '.ssh' / 'config'
        ssh_dir = ssh_config_path.parent
        
        # Создать директорию если не существует
        ssh_dir.mkdir(mode=0o700, exist_ok=True)
        
        # Параметры из конфигурации
        alias = self.config.get('remote_server.ssh_alias')
        host = self.config.get('remote_server.host')
        user = self.config.get('remote_server.user')
        key_path = self.config.get('ssh.key_path', '~/.ssh/id_ed25519')
        
        config_entry = f"""
# fedoc - Удаленный сервер с ArangoDB
Host {alias}
    HostName {host}
    User {user}
    IdentityFile {key_path}
    StrictHostKeyChecking no
    UserKnownHostsFile=/dev/null
"""
        
        try:
            # Проверяем, существует ли уже
            if ssh_config_path.exists():
                with open(ssh_config_path, 'r') as f:
                    if f'Host {alias}' in f.read():
                        log(f"   ℹ️  Алиас '{alias}' уже существует в {ssh_config_path}")
                        return
            
            # Добавляем в конец файла
            with open(ssh_config_path, 'a') as f:
                f.write(config_entry)
            
            log(f"   ✓ SSH конфигурация создана: {ssh_config_path}")
            log(f"      Алиас: {alias} → {user}@{host}")
            
        except Exception as e:
            log(f"   ✗ Ошибка создания SSH конфигурации: {e}")
    
    def _create_ssh_key(self, key_path: Path):
        """Создать SSH ключ"""
        log(f"   Создание SSH ключа: {key_path}")
        
        try:
            # Создать директорию если не существует
            key_path.parent.mkdir(mode=0o700, exist_ok=True)
            
            subprocess.run([
                'ssh-keygen',
                '-t', 'ed25519',
                '-f', str(key_path),
                '-N', '',  # Без пароля
                '-C', f'fedoc-{self.config.hostname}'
            ], check=True, capture_output=True)
            
            log(f"   ✓ SSH ключ создан: {key_path}")
            log(f"   ✓ Публичный ключ: {key_path}.pub")
            
        except subprocess.CalledProcessError as e:
            log(f"   ✗ Ошибка создания ключа: {e.stderr.decode()}")
        except Exception as e:
            log(f"   ✗ Ошибка: {e}")
    
    def _copy_ssh_key_to_server(self):
        """Скопировать SSH ключ на сервер"""
        user = self.config.get('remote_server.user')
        host = self.config.get('remote_server.host')
        key_path = Path(self.config.get('ssh.key_path', '~/.ssh/id_ed25519')).expanduser()
        
        server = f"{user}@{host}"
        
        log(f"   Копирование SSH ключа на сервер: {server}")
        log("   (Потребуется ввести пароль)")
        
        try:
            subprocess.run([
                'ssh-copy-id',
                '-i', f"{key_path}.pub",
                server
            ], check=True)
            
            log(f"   ✓ SSH ключ скопирован на {server}")
            
        except subprocess.CalledProcessError:
            log(f"   ✗ Ошибка копирования ключа")
            log(f"   Скопируйте вручную: ssh-copy-id -i {key_path}.pub {server}")
        except Exception as e:
            log(f"   ✗ Ошибка: {e}")
    
    def _ask_user(self, question: str, default: bool = True) -> bool:
        """
        Спросить у пользователя (только в интерактивном режиме)
        
        Args:
            question: Вопрос
            default: Значение по умолчанию
            
        Returns:
            True если пользователь ответил да
        """
        if not self.interactive:
            return default
        
        prompt = f"{question} [{'Y/n' if default else 'y/N'}]: "
        try:
            response = input(prompt).strip().lower()
            if not response:
                return default
            return response in ['y', 'yes', 'да', 'д']
        except (EOFError, KeyboardInterrupt):
            log("\n")
            return default



