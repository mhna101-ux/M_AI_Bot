import subprocess

def execute_system_command(command: str) -> str:
    try:
        # Run local system command
        result = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True,
            timeout=60
        )
        output = result.stdout
        if result.stderr:
            output += f"\nErrors:\n{result.stderr}"
        return output if output.strip() else "Command executed successfully with no output."
    except Exception as e:
        return f"Failed to execute command: {e}"

def get_system_tool_schema() -> dict:
    return {
        "type": "function",
        "function": {
            "name": "SystemTerminal",
            "description": "Useful for executing local system terminal commands on the host machine. Input should be a valid shell command.",
            "parameters": {
                "type": "object",
                "properties": {
                    "command": {
                        "type": "string",
                        "description": "A valid shell command to execute on the local system."
                    }
                },
                "required": ["command"]
            }
        }
    }
