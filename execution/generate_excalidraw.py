#!/usr/bin/env python3
"""
Generate Excalidraw flowcharts from DSL descriptions.

Uses @swiftlysingh/excalidraw-cli via npx to create .excalidraw JSON files.
Part of the execution layer - deterministic tool called by orchestration.

Usage:
    python generate_excalidraw.py --dsl "DSL content" --output "filename.excalidraw"
    python generate_excalidraw.py --dsl-file "path/to/dsl.txt" --output "filename.excalidraw"
"""

import argparse
import subprocess
import sys
import os
from pathlib import Path


def ensure_tmp_directory():
    """Create .tmp directory if it doesn't exist."""
    tmp_dir = Path(__file__).parent.parent / ".tmp"
    tmp_dir.mkdir(exist_ok=True)
    return tmp_dir


def generate_excalidraw(dsl_content: str, output_filename: str) -> dict:
    """
    Generate an Excalidraw file from DSL content.
    
    Args:
        dsl_content: The DSL string defining the flowchart
        output_filename: Name of the output file (e.g., "my_flow.excalidraw")
    
    Returns:
        dict with 'success', 'output_path', and 'message' keys
    """
    # Ensure .tmp directory exists
    tmp_dir = ensure_tmp_directory()
    
    # Construct full output path
    if not output_filename.endswith('.excalidraw'):
        output_filename += '.excalidraw'
    
    output_path = tmp_dir / output_filename
    
    # Build the npx command
    # Using --inline flag to pass DSL directly
    cmd = [
        'npx',
        '@swiftlysingh/excalidraw-cli',
        'create',
        '--inline',
        dsl_content,
        '-o',
        str(output_path)
    ]
    
    try:
        # Execute the command
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            check=True
        )
        
        # Check if file was created
        if output_path.exists():
            return {
                'success': True,
                'output_path': str(output_path),
                'message': f'Successfully generated flowchart: {output_path}',
                'stdout': result.stdout,
                'stderr': result.stderr
            }
        else:
            return {
                'success': False,
                'output_path': None,
                'message': 'Command executed but file was not created',
                'stdout': result.stdout,
                'stderr': result.stderr
            }
            
    except subprocess.CalledProcessError as e:
        return {
            'success': False,
            'output_path': None,
            'message': f'Error executing excalidraw-cli: {e}',
            'stdout': e.stdout,
            'stderr': e.stderr
        }
    except FileNotFoundError:
        return {
            'success': False,
            'output_path': None,
            'message': 'npx not found. Please ensure Node.js is installed.',
            'stdout': '',
            'stderr': ''
        }
    except Exception as e:
        return {
            'success': False,
            'output_path': None,
            'message': f'Unexpected error: {str(e)}',
            'stdout': '',
            'stderr': ''
        }


def main():
    parser = argparse.ArgumentParser(
        description='Generate Excalidraw flowcharts from DSL',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Generate from inline DSL
  python generate_excalidraw.py --dsl "(Start) -> [Step 1] -> (End)" --output "simple_flow"
  
  # Generate from DSL file
  python generate_excalidraw.py --dsl-file "my_flow.dsl" --output "my_flow"
  
  # With full DSL syntax
  python generate_excalidraw.py --dsl "@direction TB
@spacing 60

(Start) -> [Process] -> {Decision?}
{Decision?} -> 'yes' -> (Done)
{Decision?} -> 'no' -> [Retry] -> [Process]" --output "decision_flow"
        """
    )
    
    dsl_group = parser.add_mutually_exclusive_group(required=True)
    dsl_group.add_argument(
        '--dsl',
        type=str,
        help='DSL content as a string'
    )
    dsl_group.add_argument(
        '--dsl-file',
        type=str,
        help='Path to file containing DSL content'
    )
    
    parser.add_argument(
        '--output',
        type=str,
        required=True,
        help='Output filename (will be saved to .tmp/ directory)'
    )
    
    parser.add_argument(
        '--verbose',
        action='store_true',
        help='Print verbose output including stdout/stderr'
    )
    
    args = parser.parse_args()
    
    # Get DSL content
    if args.dsl:
        dsl_content = args.dsl
    else:
        try:
            with open(args.dsl_file, 'r') as f:
                dsl_content = f.read()
        except FileNotFoundError:
            print(f"Error: DSL file not found: {args.dsl_file}", file=sys.stderr)
            sys.exit(1)
        except Exception as e:
            print(f"Error reading DSL file: {e}", file=sys.stderr)
            sys.exit(1)
    
    # Generate the flowchart
    result = generate_excalidraw(dsl_content, args.output)
    
    # Print results
    if result['success']:
        print(f"✅ {result['message']}")
        print(f"\nOpen at: https://excalidraw.com")
        print(f"File location: {result['output_path']}")
        
        if args.verbose and (result['stdout'] or result['stderr']):
            print("\n--- Command Output ---")
            if result['stdout']:
                print(result['stdout'])
            if result['stderr']:
                print(result['stderr'], file=sys.stderr)
        
        sys.exit(0)
    else:
        print(f"❌ {result['message']}", file=sys.stderr)
        
        if result['stdout']:
            print("\nStdout:", file=sys.stderr)
            print(result['stdout'], file=sys.stderr)
        
        if result['stderr']:
            print("\nStderr:", file=sys.stderr)
            print(result['stderr'], file=sys.stderr)
        
        sys.exit(1)


if __name__ == '__main__':
    main()
