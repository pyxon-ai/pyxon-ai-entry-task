"""
Setup script to initialize the project structure
"""
import os
from pathlib import Path
import shutil

def setup_project():
    """Create necessary directories and move files"""
    
    print("="*60)
    print("Setting up Arabic RAG Document Parser")
    print("="*60)
    
    # Get project root
    project_root = Path(__file__).parent
    
    # Create directories
    directories = [
        'data',
        'output',
        'databases',
    ]
    
    print("\n1. Creating directories...")
    for directory in directories:
        dir_path = project_root / directory
        dir_path.mkdir(exist_ok=True)
        print(f"   ✓ {directory}/")
    
    # Move test files to data directory
    print("\n2. Organizing test files...")
    test_files = ['file_ar.pdf', 'file.txt']
    
    for filename in test_files:
        src = project_root / filename
        dst = project_root / 'data' / filename
        
        if src.exists():
            if not dst.exists():
                shutil.copy2(src, dst)
                print(f"   ✓ Copied {filename} to data/")
            else:
                print(f"   ⚠ {filename} already exists in data/")
        else:
            print(f"   ℹ {filename} not found (will need to add manually)")
    
    print("\n✅ Setup complete!")
    print("\nNext steps:")
    print("1. Activate virtual environment: .\\venv\\Scripts\\activate")
    print("2. Install dependencies: pip install -r requirements.txt")
    print("3. Run example: python examples\\example_usage.py")
    print("\nFor benchmark: python examples\\run_benchmark.py")


if __name__ == "__main__":
    setup_project()
