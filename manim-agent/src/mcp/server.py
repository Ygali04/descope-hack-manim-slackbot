import os
from typing import Dict, Any, List
import structlog

logger = structlog.get_logger()

class MCPServer:
    """Model Context Protocol server implementation for Cequence AI Gateway"""
    
    def __init__(self):
        self.server_name = os.getenv("MCP_SERVER_NAME", "manimpro-agent-b")
        self.version = os.getenv("MCP_VERSION", "1.0.0")
        
    def get_capabilities(self) -> Dict[str, Any]:
        """Return MCP server capabilities for Cequence"""
        return {
            "mcp": {
                "version": "1.0.0",
                "server": {
                    "name": self.server_name,
                    "version": self.version
                }
            },
            "capabilities": {
                "tools": {
                    "supported": True,
                    "list_tools": True,
                    "call_tool": True
                },
                "resources": {
                    "supported": False  # Not implementing resources for this demo
                },
                "prompts": {
                    "supported": False  # Not implementing prompts for this demo
                }
            },
            "tools": self.get_available_tools()
        }
    
    def get_available_tools(self) -> List[Dict[str, Any]]:
        """Return list of available MCP tools"""
        return [
            {
                "name": "generate_and_render",
                "description": "Generate and render educational Manim videos from topics",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "topic": {
                            "type": "string",
                            "description": "Educational topic to create video about",
                            "maxLength": 200,
                            "minLength": 3
                        },
                        "upload_url": {
                            "type": "string",
                            "description": "Pre-signed URL for uploading the rendered video",
                            "format": "uri"
                        },
                        "file_id": {
                            "type": "string",
                            "description": "Slack file ID for the upload"
                        },
                        "render": {
                            "type": "object",
                            "description": "Rendering parameters",
                            "properties": {
                                "quality": {
                                    "type": "string",
                                    "enum": ["low_quality", "medium_quality", "high_quality", "production_quality"],
                                    "default": "medium_quality"
                                },
                                "width": {
                                    "type": "integer",
                                    "minimum": 480,
                                    "maximum": 1920,
                                    "default": 1280
                                },
                                "height": {
                                    "type": "integer", 
                                    "minimum": 360,
                                    "maximum": 1080,
                                    "default": 720
                                },
                                "duration_s": {
                                    "type": "integer",
                                    "minimum": 5,
                                    "maximum": 300,
                                    "default": 30
                                },
                                "fps": {
                                    "type": "integer",
                                    "minimum": 15,
                                    "maximum": 60,
                                    "default": 30
                                }
                            }
                        }
                    },
                    "required": ["topic", "upload_url", "file_id"]
                }
            }
        ]
    
    def get_tool_by_name(self, name: str) -> Dict[str, Any]:
        """Get specific tool definition by name"""
        tools = self.get_available_tools()
        for tool in tools:
            if tool["name"] == name:
                return tool
        raise ValueError(f"Tool not found: {name}")
    
    def validate_tool_call(self, tool_name: str, arguments: Dict[str, Any]) -> None:
        """Validate a tool call against the schema"""
        tool = self.get_tool_by_name(tool_name)
        schema = tool["input_schema"]
        
        # Basic validation (in production, use jsonschema library)
        required = schema.get("required", [])
        for field in required:
            if field not in arguments:
                raise ValueError(f"Missing required field: {field}")
        
        # Validate specific fields
        if "topic" in arguments:
            topic = arguments["topic"]
            if not isinstance(topic, str) or len(topic) < 3 or len(topic) > 200:
                raise ValueError("Topic must be a string between 3-200 characters")
        
        if "render" in arguments:
            render_params = arguments["render"]
            if "width" in render_params:
                width = render_params["width"]
                if not (480 <= width <= 1920):
                    raise ValueError("Width must be between 480-1920")
            
            if "height" in render_params:
                height = render_params["height"]
                if not (360 <= height <= 1080):
                    raise ValueError("Height must be between 360-1080")
            
            if "duration_s" in render_params:
                duration = render_params["duration_s"]
                if not (5 <= duration <= 300):
                    raise ValueError("Duration must be between 5-300 seconds")
    
    def get_health_info(self) -> Dict[str, Any]:
        """Return server health information for monitoring"""
        return {
            "server": self.server_name,
            "version": self.version,
            "status": "healthy",
            "mcp_version": "1.0.0",
            "tools_available": len(self.get_available_tools()),
            "capabilities": ["tools"]
        } 