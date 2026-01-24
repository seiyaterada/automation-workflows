#!/usr/bin/env python3
"""
Helper module for working with Excalidraw flowchart generation.

Provides utilities for:
- Parsing job descriptions into flowchart DSL
- Common DSL patterns and templates
- Integration with generate_excalidraw.py

This is meant to be imported by orchestration layer or used as a standalone script.
"""

from typing import Dict, List, Optional
import re
from pathlib import Path
import subprocess


class ExcalidrawDSL:
    """Builder class for constructing Excalidraw DSL strings."""
    
    def __init__(self, direction: str = "TB", spacing: int = 60):
        self.direction = direction
        self.spacing = spacing
        self.lines: List[str] = []
    
    def add_directive(self, directive: str, value: str) -> 'ExcalidrawDSL':
        """Add a directive like @direction or @spacing."""
        self.lines.insert(0, f"@{directive} {value}")
        return self
    
    def add_flow(self, flow: str) -> 'ExcalidrawDSL':
        """Add a flow line (e.g., '(Start) -> [Process] -> (End)')."""
        self.lines.append(flow)
        return self
    
    def build(self) -> str:
        """Build the final DSL string."""
        dsl_parts = [
            f"@direction {self.direction}",
            f"@spacing {self.spacing}",
            ""  # Empty line after directives
        ]
        dsl_parts.extend(self.lines)
        return "\n".join(dsl_parts)


class FlowchartPattern:
    """Common flowchart patterns for different scenarios."""
    
    @staticmethod
    def simple_process(steps: List[str]) -> str:
        """Create a simple linear process: Start -> Step1 -> Step2 -> End."""
        builder = ExcalidrawDSL()
        
        flow = "(Start)"
        for step in steps:
            flow += f" -> [{step}]"
        flow += " -> (End)"
        
        builder.add_flow(flow)
        return builder.build()
    
    @staticmethod
    def decision_branch(
        start: str,
        decision: str,
        yes_path: List[str],
        no_path: List[str]
    ) -> str:
        """Create a decision-based flow with two branches."""
        builder = ExcalidrawDSL()
        
        # Main flow to decision
        builder.add_flow(f"({start}) -> {{{decision}?}}")
        
        # Yes path
        yes_flow = f"{{{decision}?}} -> \"yes\""
        for step in yes_path:
            yes_flow += f" -> [{step}]"
        yes_flow += " -> (Done)"
        builder.add_flow(yes_flow)
        
        # No path
        no_flow = f"{{{decision}?}} -> \"no\""
        for step in no_path:
            no_flow += f" -> [{step}]"
        no_flow += " -> (End)"
        builder.add_flow(no_flow)
        
        return builder.build()
    
    @staticmethod
    def api_integration() -> str:
        """Standard API integration pattern with error handling."""
        builder = ExcalidrawDSL()
        builder.add_flow("(Start) -> [Receive Request] -> {Valid?}")
        builder.add_flow("{Valid?} -> \"no\" -> [Return Error] -> (End)")
        builder.add_flow("{Valid?} -> \"yes\" -> [Call External API] -> {Success?}")
        builder.add_flow("{Success?} -> \"no\" -> [Log Failure] -> (End)")
        builder.add_flow("{Success?} -> \"yes\" -> [Process Response] -> [Return Data] -> (End)")
        return builder.build()
    
    @staticmethod
    def retry_loop(
        start: str,
        action: str,
        check: str,
        max_retries: bool = True
    ) -> str:
        """Create a retry loop pattern."""
        builder = ExcalidrawDSL()
        builder.add_flow(f"({start}) -> [{action}] -> {{{check}?}}")
        builder.add_flow(f"{{{check}?}} -> \"yes\" -> [Process Result] -> (Done)")
        
        if max_retries:
            builder.add_flow(f"{{{check}?}} -> \"no\" -> {{Max Retries?}}")
            builder.add_flow(f"{{Max Retries?}} -> \"yes\" -> [Report Failure] -> (End)")
            builder.add_flow(f"{{Max Retries?}} -> \"no\" -> [Adjust Parameters] -> [{action}]")
        else:
            builder.add_flow(f"{{{check}?}} -> \"no\" -> [Adjust Parameters] -> [{action}]")
        
        return builder.build()


def extract_process_steps(description: str) -> Dict[str, any]:
    """
    Extract structured process information from a job description.
    
    Returns a dict with:
        - trigger: What starts the process
        - steps: List of action steps
        - decisions: List of decision points
        - loops: List of potential loops/retries
        - outputs: Final outputs/deliverables
    """
    result = {
        'trigger': None,
        'steps': [],
        'decisions': [],
        'loops': [],
        'outputs': []
    }
    
    # Look for trigger words
    trigger_patterns = [
        r'(?:start|trigger|begin|initiate)(?:s)?\s+(?:with|by|when|from)\s+([^.]+)',
        r'(?:user|staff|admin)\s+(?:logs in|submits|clicks|requests|uploads)',
        r'(?:webhook|cron|scheduled|event)\s+(?:receives|fires|triggers)'
    ]
    
    for pattern in trigger_patterns:
        match = re.search(pattern, description, re.IGNORECASE)
        if match:
            result['trigger'] = match.group(0).strip()
            break
    
    # Look for decision points (if/when/based on/depending on)
    decision_patterns = [
        r'(?:if|when|whether)\s+([^,.\n]+)',
        r'(?:based on|depending on)\s+([^,.\n]+)',
        r'(?:check|verify|validate)\s+(?:if|whether|that)\s+([^,.\n]+)'
    ]
    
    for pattern in decision_patterns:
        matches = re.finditer(pattern, description, re.IGNORECASE)
        for match in matches:
            result['decisions'].append(match.group(1).strip())
    
    # Look for loops/retries
    loop_patterns = [
        r'(?:retry|try again|repeat|until|loop)',
        r'(?:for each|iterate|batch)',
        r'(?:resubmit|fix and|correct and)'
    ]
    
    for pattern in loop_patterns:
        if re.search(pattern, description, re.IGNORECASE):
            result['loops'].append(pattern)
    
    # Look for outputs/deliverables
    output_patterns = [
        r'(?:generate|create|produce|output|deliver|send|export)\s+([^,.\n]+)',
        r'(?:result|output|deliverable)(?:s)?\s+(?:is|are|include)(?:s)?\s+([^,.\n]+)'
    ]
    
    for pattern in output_patterns:
        matches = re.finditer(pattern, description, re.IGNORECASE)
        for match in matches:
            result['outputs'].append(match.group(1).strip())
    
    return result


def generate_from_description(
    description: str,
    output_filename: str,
    auto_infer: bool = True
) -> Dict:
    """
    High-level function to generate flowchart from a job description.
    
    Args:
        description: Job description or process description text
        output_filename: Name for the output file
        auto_infer: Whether to automatically infer missing steps
    
    Returns:
        dict with generation result
    """
    # This is a placeholder - in practice, the orchestration layer (LLM)
    # would do the reasoning and DSL generation. This function just shows
    # the interface that the orchestration would use.
    
    extracted = extract_process_steps(description)
    
    # For now, return the extracted info so orchestration can use it
    return {
        'extracted': extracted,
        'message': 'Use extracted info to build DSL with ExcalidrawDSL class or FlowchartPattern',
        'next_step': 'Call generate_excalidraw.py with the built DSL'
    }


def save_and_generate(dsl_content: str, output_filename: str) -> Dict:
    """
    Save DSL and generate excalidraw file.
    
    Args:
        dsl_content: The DSL string
        output_filename: Output filename (without .excalidraw extension)
    
    Returns:
        dict with 'success', 'output_path', 'message' keys
    """
    # Get the path to generate_excalidraw.py
    script_dir = Path(__file__).parent
    generate_script = script_dir / "generate_excalidraw.py"
    
    if not generate_script.exists():
        return {
            'success': False,
            'output_path': None,
            'message': f'generate_excalidraw.py not found at {generate_script}'
        }
    
    # Call the generation script
    cmd = [
        'python3',
        str(generate_script),
        '--dsl',
        dsl_content,
        '--output',
        output_filename
    ]
    
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            check=True
        )
        
        # Parse output to get file path
        output_lines = result.stdout.split('\n')
        file_path = None
        for line in output_lines:
            if 'File location:' in line:
                file_path = line.split('File location:')[1].strip()
        
        return {
            'success': True,
            'output_path': file_path,
            'message': 'Successfully generated flowchart',
            'stdout': result.stdout
        }
        
    except subprocess.CalledProcessError as e:
        return {
            'success': False,
            'output_path': None,
            'message': f'Error generating flowchart: {e}',
            'stderr': e.stderr
        }


# Example usage
if __name__ == '__main__':
    # Example 1: Using the DSL builder
    print("Example 1: Simple process")
    print("=" * 50)
    
    dsl = FlowchartPattern.simple_process([
        "Validate Input",
        "Process Data",
        "Save to Database"
    ])
    print(dsl)
    print()
    
    # Example 2: API integration
    print("Example 2: API integration pattern")
    print("=" * 50)
    
    dsl = FlowchartPattern.api_integration()
    print(dsl)
    print()
    
    # Example 3: Custom DSL
    print("Example 3: Custom DSL builder")
    print("=" * 50)
    
    builder = ExcalidrawDSL(direction="LR", spacing=80)
    builder.add_flow("(User Input) -> [Validate] -> {Valid?}")
    builder.add_flow("{Valid?} -> \"no\" -> [Show Error] -> (End)")
    builder.add_flow("{Valid?} -> \"yes\" -> [Process] -> [Save] -> (Success)")
    
    print(builder.build())
    print()
    
    # Example 4: Generate actual file
    print("Example 4: Generate flowchart file")
    print("=" * 50)
    
    result = save_and_generate(
        FlowchartPattern.simple_process(["Step 1", "Step 2", "Step 3"]),
        "example_simple_process"
    )
    
    if result['success']:
        print(f"✅ {result['message']}")
        print(f"File: {result['output_path']}")
    else:
        print(f"❌ {result['message']}")
