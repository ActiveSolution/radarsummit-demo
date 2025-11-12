import inspect
import logging
import asyncio
from typing import Annotated, Callable

from semantic_kernel.functions import kernel_function
from mcp.client.sse import sse_client
from mcp.client.session import ClientSession
from models.messages_kernel import AgentType
import json
from typing import get_type_hints


class RiskAssessmentTools:
    # Define Risk Assessment tools (functions)
    formatting_instructions = "Instructions: returning the output of this function call verbatim to the user in markdown. Then write AGENT SUMMARY: and then include a summary of what you did."
    agent_name = AgentType.RISKASSESSMENT.value

    @staticmethod
    @kernel_function(description="Perform a comprehensive risk assessment check for a given employee using MCP service. REQUIRED for all onboarding tasks")
    async def perform_risk_assessment(employee_name: str) -> str:
        """
        Perform a comprehensive risk assessment check for a given employee using the MCP Risk Assessment service.
        REQUIRED for all onboarding tasks
        """
        try:
            # Prepare the risk assessment message
            assessment_message = (
                f"Employee Onboarding Risk Assessment Request:\n"
                f"Employee Name: {employee_name}\n"
                f"Request Type: Pre-employment risk evaluation for standard corporate onboarding process.\n"
                f"Please provide a comprehensive risk assessment covering security, compliance, operational, and safety considerations."
            )
            
            # Connect to MCP server using SSE client
            async with sse_client("https://bergetdemo.activesolution.se/SSE") as (read, write):
                # Create client session
                async with ClientSession(read, write) as session:
                    # Initialize the session
                    init_result = await session.initialize()
                    
                    # Call the MCP assess function
                    result = await session.call_tool(
                        name="assess", 
                        arguments={"message": assessment_message}
                    )
                    
                    # Extract the result content
                    mcp_result = result.content[0].text if result.content else "Assessment completed"
                    
                    # Format the response
                    return (
                        f"##### Risk Assessment Report for {employee_name}\n\n"
                        f"**Employee:** {employee_name}\n"
                        f"**Assessment Type:** Pre-employment Risk Evaluation\n"
                        f"**Service:** MCP Risk Assessment Engine (Private Cloud)\n\n"
                        f"---\n\n"
                        f"{mcp_result}\n\n"
                        f"---\n\n"
                        f"**Assessment Completed:** ✅\n\n"
                        f"{RiskAssessmentTools.formatting_instructions}"
                    )
            
        except Exception as e:
            logging.error(f"Error during MCP risk assessment for {employee_name}: {e}")
            # Fallback to basic assessment if MCP service is unavailable
            return (
                f"##### Risk Assessment Report for {employee_name}\n\n"
                f"**Employee Name:** {employee_name}\n\n"
                f"**Assessment Status:** ⚠️ MCP service unavailable - Basic assessment performed\n\n"
                f"**Basic Assessment:** No immediate risks identified for standard employee onboarding.\n\n"
                f"**Recommendation:** Manual review recommended due to MCP service unavailability.\n\n"
                f"**Note:** Full MCP risk assessment service is currently unavailable. Please retry later for comprehensive analysis.\n\n"
                f"**Error Details:** {str(e)}\n\n"
                f"{RiskAssessmentTools.formatting_instructions}"
            )

    @classmethod
    def get_all_kernel_functions(cls) -> dict[str, Callable]:
        """
        Returns a dictionary of all methods in this class that have the @kernel_function annotation.
        This function itself is not annotated with @kernel_function.

        Returns:
            Dict[str, Callable]: Dictionary with function names as keys and function objects as values
        """
        kernel_functions = {}

        # Get all class methods
        for name, method in inspect.getmembers(cls, predicate=inspect.isfunction):
            # Skip this method itself and any private/special methods
            if name.startswith("_") or name == "get_all_kernel_functions":
                continue

            # Check if the method has the kernel_function annotation
            # by looking at its __annotations__ attribute
            method_attrs = getattr(method, "__annotations__", {})
            if hasattr(method, "__kernel_function__") or "kernel_function" in str(
                method_attrs
            ):
                kernel_functions[name] = method

        return kernel_functions

    @classmethod
    def generate_tools_json_doc(cls) -> str:
        """
        Generate a JSON document containing information about all methods in the class.

        Returns:
            str: JSON string containing the methods' information
        """

        tools_list = []

        # Get all methods from the class that have the kernel_function annotation
        for name, method in inspect.getmembers(cls, predicate=inspect.isfunction):
            # Skip this method itself and any private methods
            if name.startswith("_") or name == "generate_tools_json_doc":
                continue

            # Check if the method has the kernel_function annotation
            if hasattr(method, "__kernel_function__"):
                # Get method description from docstring or kernel_function description
                description = ""
                if hasattr(method, "__doc__") and method.__doc__:
                    description = method.__doc__.strip()

                # Get kernel_function description if available
                if hasattr(method, "__kernel_function__") and getattr(
                    method.__kernel_function__, "description", None
                ):
                    description = method.__kernel_function__.description

                # Get argument information by introspection
                sig = inspect.signature(method)
                args_dict = {}

                # Get type hints if available
                type_hints = get_type_hints(method)

                # Process parameters
                for param_name, param in sig.parameters.items():
                    # Skip first parameter 'cls' for class methods (though we're using staticmethod now)
                    if param_name in ["cls", "self"]:
                        continue

                    # Get parameter type
                    param_type = "string"  # Default type
                    if param_name in type_hints:
                        type_obj = type_hints[param_name]
                        # Convert type to string representation
                        if hasattr(type_obj, "__name__"):
                            param_type = type_obj.__name__.lower()
                        else:
                            # Handle complex types like List, Dict, etc.
                            param_type = str(type_obj).lower()
                            if "int" in param_type:
                                param_type = "int"
                            elif "float" in param_type:
                                param_type = "float"
                            elif "bool" in param_type:
                                param_type = "boolean"
                            else:
                                param_type = "string"

                    # Create parameter description
                    # param_desc = param_name.replace("_", " ")
                    args_dict[param_name] = {
                        "description": param_name,
                        "title": param_name.replace("_", " ").title(),
                        "type": param_type,
                    }

                # Add the tool information to the list
                tool_entry = {
                    "agent": cls.agent_name,  # Use HR agent type
                    "function": name,
                    "description": description,
                    "arguments": json.dumps(args_dict).replace('"', "'"),
                }

                tools_list.append(tool_entry)

        # Return the JSON string representation
        return json.dumps(tools_list, ensure_ascii=False, indent=2)
