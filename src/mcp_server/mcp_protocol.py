#!/usr/bin/env python3
"""
Минимальная реализация MCP (Model Context Protocol) для fedoc
MCP использует JSON-RPC 2.0 через stdio
"""

import json
import sys
from typing import Any, Dict, List, Optional


class MCPServer:
    """Базовая реализация MCP сервера по протоколу JSON-RPC 2.0"""
    
    def __init__(self, name: str, version: str):
        self.name = name
        self.version = version
        self.tools = {}
        self.running = True
        
    def register_tool(self, name: str, func, schema: Dict[str, Any]):
        """
        Зарегистрировать инструмент (tool)
        
        Args:
            name: Имя инструмента
            func: Функция-обработчик
            schema: JSON Schema для параметров инструмента
        """
        self.tools[name] = {
            "function": func,
            "schema": schema
        }
    
    def send_response(self, request_id: Optional[Any], result: Any = None, error: Optional[Dict] = None):
        """Отправить JSON-RPC ответ"""
        response = {
            "jsonrpc": "2.0",
            "id": request_id
        }
        
        if error:
            response["error"] = error
        else:
            response["result"] = result
        
        # Отправляем в stdout
        json.dump(response, sys.stdout)
        sys.stdout.write('\n')
        sys.stdout.flush()
    
    def send_notification(self, method: str, params: Any = None):
        """Отправить JSON-RPC notification (без id)"""
        notification = {
            "jsonrpc": "2.0",
            "method": method
        }
        
        if params is not None:
            notification["params"] = params
        
        # Отправляем в stdout
        json.dump(notification, sys.stdout)
        sys.stdout.write('\n')
        sys.stdout.flush()
    
    def send_error(self, request_id: Optional[Any], code: int, message: str, data: Any = None):
        """Отправить ошибку"""
        error = {
            "code": code,
            "message": message
        }
        if data:
            error["data"] = data
        
        self.send_response(request_id, error=error)
    
    def handle_initialize(self, request_id: Any, params: Dict) -> None:
        """Обработать initialize запрос"""
        result = {
            "protocolVersion": "2024-11-05",
            "capabilities": {
                "tools": {}
            },
            "serverInfo": {
                "name": self.name,
                "version": self.version
            }
        }
        self.send_response(request_id, result)
        
        # MCP протокол требует отправить initialized notification
        self.send_notification("notifications/initialized")
    
    def handle_tools_list(self, request_id: Any, params: Dict) -> None:
        """Обработать tools/list запрос - вернуть список доступных инструментов"""
        tools_list = []
        
        for name, tool in self.tools.items():
            tools_list.append({
                "name": name,
                "description": tool["schema"].get("description", ""),
                "inputSchema": tool["schema"]
            })
        
        result = {
            "tools": tools_list
        }
        self.send_response(request_id, result)
    
    def handle_tools_call(self, request_id: Any, params: Dict) -> None:
        """Обработать tools/call запрос - вызвать инструмент"""
        tool_name = params.get("name")
        arguments = params.get("arguments", {})
        
        if tool_name not in self.tools:
            self.send_error(request_id, -32601, f"Tool not found: {tool_name}")
            return
        
        try:
            # Вызываем функцию инструмента
            func = self.tools[tool_name]["function"]
            result = func(**arguments)
            
            # MCP ожидает результат в определенном формате
            response = {
                "content": [
                    {
                        "type": "text",
                        "text": json.dumps(result, ensure_ascii=False, indent=2)
                    }
                ]
            }
            
            self.send_response(request_id, response)
            
        except Exception as e:
            self.send_error(request_id, -32603, f"Tool execution error: {str(e)}", {"exception": str(e)})
    
    def handle_request(self, request: Dict) -> None:
        """Обработать JSON-RPC запрос"""
        request_id = request.get("id")
        method = request.get("method")
        params = request.get("params", {})
        
        # Маршрутизация запросов
        if method == "initialize":
            self.handle_initialize(request_id, params)
        elif method == "tools/list":
            self.handle_tools_list(request_id, params)
        elif method == "tools/call":
            self.handle_tools_call(request_id, params)
        elif method == "shutdown":
            self.send_response(request_id, {})
            self.running = False
        else:
            self.send_error(request_id, -32601, f"Method not found: {method}")
    
    def run(self):
        """Запустить MCP сервер (читать из stdin, писать в stdout)"""
        # MCP протокол требует чистый stdout - никаких логов!
        
        # Читаем запросы из stdin
        for line in sys.stdin:
            if not line.strip():
                continue
            
            try:
                request = json.loads(line)
                self.handle_request(request)
                
                if not self.running:
                    break
                    
            except json.JSONDecodeError as e:
                sys.stderr.write(f"❌ JSON decode error: {e}\n")
                sys.stderr.flush()
            except Exception as e:
                sys.stderr.write(f"❌ Error handling request: {e}\n")
                sys.stderr.flush()


