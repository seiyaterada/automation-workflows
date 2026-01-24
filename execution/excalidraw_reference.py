#!/usr/bin/env python3
"""
Quick reference and testing script for Excalidraw flowchart generation.

Run this to see all available patterns and test the system.
"""

from excalidraw_helpers import ExcalidrawDSL, FlowchartPattern, save_and_generate


def demo_all_patterns():
    """Generate examples of all available patterns."""
    
    patterns = {
        'simple_process': FlowchartPattern.simple_process([
            "Receive Input",
            "Validate Data", 
            "Process Request",
            "Return Result"
        ]),
        
        'api_integration': FlowchartPattern.api_integration(),
        
        'decision_branch': FlowchartPattern.decision_branch(
            start="User Request",
            decision="Authenticated",
            yes_path=["Load Dashboard", "Display Data"],
            no_path=["Show Login", "Redirect"]
        ),
        
        'retry_loop': FlowchartPattern.retry_loop(
            start="Start Scrape",
            action="Fetch Data",
            check="Success",
            max_retries=True
        ),
    }
    
    print("=" * 70)
    print("EXCALIDRAW FLOWCHART PATTERN REFERENCE")
    print("=" * 70)
    print()
    
    for name, dsl in patterns.items():
        print(f"\n📊 {name.upper().replace('_', ' ')}")
        print("-" * 70)
        print(dsl)
        print()
        
        # Optionally generate files
        # result = save_and_generate(dsl, f"pattern_{name}")
        # if result['success']:
        #     print(f"✅ Generated: {result['output_path']}")
    
    print("\n" + "=" * 70)
    print("To generate any of these patterns:")
    print("  python3 excalidraw_helpers.py")
    print("=" * 70)


def quick_test():
    """Quick test to verify everything works."""
    print("\n🧪 Running quick test...")
    
    dsl = FlowchartPattern.simple_process(["Test Step 1", "Test Step 2"])
    result = save_and_generate(dsl, "quick_test")
    
    if result['success']:
        print(f"✅ Test passed! File: {result['output_path']}")
        return True
    else:
        print(f"❌ Test failed: {result['message']}")
        return False


if __name__ == '__main__':
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == '--test':
        success = quick_test()
        sys.exit(0 if success else 1)
    else:
        demo_all_patterns()
