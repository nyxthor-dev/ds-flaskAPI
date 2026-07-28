# routes/tools.py
"""
Definición de herramientas estándar (basadas en OpenAI).
Este archivo es solo para referencia y documentación.
La lógica real de tool calling usa las herramientas que envía el cliente.
"""

# Herramientas estándar que soportan la mayoría de las extensiones
STANDARD_TOOLS = {
    "read_file": {
        "type": "function",
        "function": {
            "name": "read_file",
            "description": "Read the contents of a file",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "The path to the file to read"
                    }
                },
                "required": ["path"]
            }
        }
    },
    "write_file": {
        "type": "function",
        "function": {
            "name": "write_file",
            "description": "Write content to a file",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "The path to the file to write"
                    },
                    "content": {
                        "type": "string",
                        "description": "The content to write to the file"
                    }
                },
                "required": ["path", "content"]
            }
        }
    },
    "execute_command": {
        "type": "function",
        "function": {
            "name": "execute_command",
            "description": "Execute a shell command",
            "parameters": {
                "type": "object",
                "properties": {
                    "command": {
                        "type": "string",
                        "description": "The command to execute"
                    },
                    "cwd": {
                        "type": "string",
                        "description": "The working directory for the command"
                    }
                },
                "required": ["command"]
            }
        }
    },
    "ask_followup_question": {
        "type": "function",
        "function": {
            "name": "ask_followup_question",
            "description": "Ask the user a follow-up question",
            "parameters": {
                "type": "object",
                "properties": {
                    "question": {
                        "type": "string",
                        "description": "The question to ask"
                    },
                    "follow_up": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Possible answers"
                    }
                },
                "required": ["question"]
            }
        }
    },
    "update_todo_list": {
        "type": "function",
        "function": {
            "name": "update_todo_list",
            "description": "Create or update a todo list",
            "parameters": {
                "type": "object",
                "properties": {
                    "todos": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "List of todo items"
                    }
                },
                "required": ["todos"]
            }
        }
    },
    "attempt_completion": {
        "type": "function",
        "function": {
            "name": "attempt_completion",
            "description": "Mark the task as completed",
            "parameters": {
                "type": "object",
                "properties": {
                    "result": {
                        "type": "string",
                        "description": "The final result"
                    }
                },
                "required": ["result"]
            }
        }
    },
    "search_files": {
        "type": "function",
        "function": {
            "name": "search_files",
            "description": "Search for files matching a pattern",
            "parameters": {
                "type": "object",
                "properties": {
                    "pattern": {
                        "type": "string",
                        "description": "The glob pattern to search for"
                    },
                    "directory": {
                        "type": "string",
                        "description": "The directory to search in"
                    }
                },
                "required": ["pattern"]
            }
        }
    }
}