from typing import List
from llm_advisory.llm_advisor import LLMAdvisorDataArtefact


def compile_data_artefacts(data_artefacts: List[LLMAdvisorDataArtefact]) -> str:
    """Compile data artefacts into a formatted string for LLM consumption
    
    Args:
        data_artefacts: List of data artefacts to compile
        
    Returns:
        Formatted string containing all data artefacts
    """
    if not data_artefacts:
        return "No data available"
    
    compiled_output = []
    
    for artefact in data_artefacts:
        if artefact.output_mode == "markdown_table":
            # For markdown table format
            compiled_output.append(f"## {artefact.description}")
            if isinstance(artefact.artefact, list) and len(artefact.artefact) > 0:
                # Assume it's a list of rows/dicts that can be formatted as table
                headers = list(artefact.artefact[0].keys()) if artefact.artefact else []
                if headers:
                    compiled_output.append("| " + " | ".join(headers) + " |")
                    compiled_output.append("| " + " | ".join(["---"] * len(headers)) + " |")
                    for row in artefact.artefact:
                        row_data = [str(row.get(header, "")) for header in headers]
                        compiled_output.append("| " + " | ".join(row_data) + " |")
            else:
                # Single dict or other format
                compiled_output.append(str(artefact.artefact))
        else:
            # Default text format
            compiled_output.append(f"### {artefact.description}")
            compiled_output.append(str(artefact.artefact))
        
        compiled_output.append("")  # Add spacing between artefacts
    
    return "\n".join(compiled_output)


def create_advisor_prompt(base_prompt: str, context_data: str = "") -> str:
    """Create a prompt for an advisor
    
    Args:
        base_prompt: The base prompt for the advisor
        context_data: Additional context data to include
        
    Returns:
        Complete prompt string
    """
    if context_data:
        return f"{base_prompt}\n\nContext Data:\n{context_data}"
    return base_prompt