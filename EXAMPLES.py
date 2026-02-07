#!/usr/bin/env python3
"""
Photo Mosaic Generator - Usage Examples and Test Suite

This file demonstrates various ways to use the photo_mosaic.py script.
Includes helper functions and example commands.
"""

import subprocess
import sys
from pathlib import Path


def print_example(title, description, command):
    """Pretty print an example."""
    print("\n" + "="*70)
    print(f"📸 {title}")
    print("="*70)
    print(f"Description: {description}\n")
    print("Command:")
    print(f"  {command}\n")


def show_usage_examples():
    """Display various usage examples."""
    
    print("\n" + "="*70)
    print("PHOTO MOSAIC GENERATOR - USAGE EXAMPLES")
    print("="*70)
    
    # Example 1
    print_example(
        "BASIC MOSAIC",
        "Create a simple mosaic with default settings (36\"×24\" poster)",
        "python photo_mosaic.py target.jpg ./tiles_folder"
    )
    
    # Example 2
    print_example(
        "WITH TITLE",
        "Add a 2-inch white border with centered title text",
        "python photo_mosaic.py target.jpg ./tiles --title 'My Poster' --output poster.jpg"
    )
    
    # Example 3
    print_example(
        "QUICK PREVIEW",
        "Fast, low-resolution preview for testing before final render",
        "python photo_mosaic.py target.jpg ./tiles --size 1280 960 --tile-size 80 --output preview.jpg"
    )
    
    # Example 4
    print_example(
        "ULTRA HIGH QUALITY",
        "Fine-grained mosaic with small tiles (takes longer but very detailed)",
        "python photo_mosaic.py target.jpg ./tiles --size 4320 2880 --tile-size 60 --output ultra_hd.jpg"
    )
    
    # Example 5
    print_example(
        "LARGE POSTER (24×18 inches)",
        "Create a larger format poster at 300 DPI",
        "python photo_mosaic.py target.jpg ./tiles --size 7200 5400 --tile-size 120 --output large_poster.jpg"
    )
    
    # Example 6
    print_example(
        "FAST PROCESSING",
        "Optimize for speed (fewer, larger tiles)",
        "python photo_mosaic.py target.jpg ./tiles --size 2560 1920 --tile-size 160 --output fast.jpg"
    )
    
    # Example 7
    print_example(
        "CUSTOM DPI FOR DIFFERENT PRINTS",
        "Adjust border size for 150 DPI print (larger text)",
        "python photo_mosaic.py target.jpg ./tiles --dpi 150 --title 'Title' --output custom_dpi.jpg"
    )
    
    # Example 8
    print_example(
        "PARALLEL LOADING",
        "Use more threads for faster tile loading (on multi-core systems)",
        "python photo_mosaic.py target.jpg ./tiles --threads 8 --output fast_load.jpg"
    )


def show_dimension_guide():
    """Show common print dimensions and recommended settings."""
    
    print("\n" + "="*70)
    print("PRINT DIMENSIONS & RECOMMENDED SETTINGS")
    print("="*70)
    
    dimensions = [
        ("8×6 inches (standard photo)", 2400, 1800, 100),
        ("11×8.5 inches (letter)", 3300, 2550, 110),
        ("16×12 inches", 4800, 3600, 120),
        ("18×12 inches", 5400, 3600, 120),
        ("24×18 inches (large poster)", 7200, 5400, 120),
        ("36×24 inches (extra large)", 10800, 7200, 120),
        ("48×36 inches (billboard)", 14400, 10800, 120),
    ]
    
    print("\nAll at 300 DPI (typical for quality prints):\n")
    print(f"{'Size':<25} {'Pixels (W×H)':<20} {'Tile Size':<12} {'Command'}")
    print("-" * 80)
    
    for label, width, height, tile_size in dimensions:
        print(f"{label:<25} {width}×{height:<13} {tile_size:<12} "
              f"--size {width} {height} --tile-size {tile_size}")


def show_tile_recommendations():
    """Show recommendations for tile selection."""
    
    print("\n" + "="*70)
    print("TILE FOLDER RECOMMENDATIONS")
    print("="*70)
    
    print("""
1. SIZE & QUANTITY
   - Minimum: 100 tiles
   - Recommended: 300-1000 tiles
   - More tiles = better color palette = better mosaic quality
   
2. IMAGE CHARACTERISTICS
   - Mix of different subjects (faces, landscapes, objects, etc.)
   - Good lighting and exposure
   - Variety of colors and tones
   - Can be square or rectangular (script crops intelligently)
   
3. FOLDER STRUCTURE
   - Can be flat or nested in subfolders
   - Supported formats: JPG, JPEG, PNG, GIF, BMP, WEBP
   - Script automatically deduplicates files
   
4. WHAT WORKS WELL
   - Instagram feed (various personal photos)
   - Family photos
   - Stock photo collections
   - Photo library with diverse subjects
   - Screenshots, UI elements (for creative mosaic styles)
   
5. WHAT DOESN'T WORK WELL
   - All similar colors/subjects (low diversity)
   - Very dark or very bright images
   - Blurry or out-of-focus photos
   - Single color tiles (degrades mosaic quality)

6. OPTIMIZATION TIPS
   - Remove corrupted files
   - Cull near-duplicate photos
   - Ensure consistent quality/exposure
   - Test with different --tile-size values
""")


def show_target_image_tips():
    """Show recommendations for target images."""
    
    print("\n" + "="*70)
    print("TARGET IMAGE SELECTION TIPS")
    print("="*70)
    
    print("""
WHAT MAKES A GOOD TARGET IMAGE:

✓ DO:
  - Use clear, well-composed images
  - High contrast between different areas
  - Recognizable subject matter
  - Good exposure (not too dark/bright)
  - Sufficient resolution (minimum 500×400 pixels)
  - Diverse colors throughout
  
✗ DON'T:
  - Very simple images (solid colors don't mosaic well)
  - Extreme close-ups of one object
  - Blurry or out-of-focus photos
  - Very low resolution images
  - Images with only 2-3 colors
  - Extremely high contrast (black and white only)

BEST SUBJECTS:
  - Portraits (faces have good detail)
  - Landscapes (varied colors/tones)
  - Group photos (multiple subjects)
  - Architecture (geometric patterns)
  - Nature scenes (plants, flowers)
  - Colorful objects/scenes

TEST DIFFERENT TARGETS:
  - Create previews with --size 1280 960 for quick testing
  - Try same target with different tile folders
  - Adjust --tile-size to see impact on perception
""")


def show_troubleshooting():
    """Show troubleshooting guide."""
    
    print("\n" + "="*70)
    print("TROUBLESHOOTING GUIDE")
    print("="*70)
    
    issues = {
        "Script runs but output looks wrong": [
            "- Try with more tiles in the tile folder",
            "- Increase --tile-size to see more detail per tile",
            "- Use a different target image with more detail",
            "- Verify tiles are good quality images",
        ],
        "Process is too slow": [
            "- Reduce --size to smaller resolution",
            "- Increase --tile-size (fewer tiles = faster)",
            "- Reduce number of files in tile folder",
            "- Use --threads to enable parallel loading",
            "- Close other applications to free memory",
        ],
        "Output image is too blurry": [
            "- Decrease --tile-size (smaller tiles = finer detail)",
            "- Add more tiles to folder for better color matching",
            "- Use target image with more detail",
        ],
        "Memory error / Out of memory": [
            "- Reduce --size to smaller dimensions",
            "- Reduce --tile-size value",
            "- Remove some images from tile folder",
            "- Close other applications",
            "- Try on a system with more RAM",
        ],
        "Tiles don't look like the target": [
            "- Verify tile folder has images in right colors",
            "- Tile palette might not have colors needed",
            "- Try with more diverse tile images",
            "- Target image might be too simple",
        ],
        "Title text looks wrong": [
            "- Adjust --dpi to change border size",
            "- Try longer/shorter title text",
            "- Verify target supports large borders",
        ],
    }
    
    for issue, solutions in issues.items():
        print(f"\n❓ {issue}")
        for solution in solutions:
            print(f"   {solution}")


def show_performance_tips():
    """Show performance optimization tips."""
    
    print("\n" + "="*70)
    print("PERFORMANCE OPTIMIZATION GUIDE")
    print("="*70)
    
    print("""
SPEED COMPARISON (approximate, depends on hardware):

Fast (30-60 seconds):
  python photo_mosaic.py target.jpg ./tiles \\
    --size 1920 1440 --tile-size 120

Medium (1-3 minutes):
  python photo_mosaic.py target.jpg ./tiles \\
    --size 4320 2880 --tile-size 120

Slow (5-10 minutes):
  python photo_mosaic.py target.jpg ./tiles \\
    --size 7200 5400 --tile-size 80

OPTIMIZATION STRATEGIES:

1. For Preview (5-10 seconds):
   --size 1280 960 --tile-size 80

2. For Final Print (1-2 minutes):
   --size 4320 2880 --tile-size 120

3. For Maximum Quality (5-10 minutes):
   --size 4320 2880 --tile-size 60

4. For Ultra-Large Posters (10+ minutes):
   --size 7200 5400 --tile-size 100

HARDWARE TIPS:
  - SSD faster than HDD
  - More RAM allows larger tile caches
  - Multi-core CPU helps with --threads
  - GPU won't help (CPU-bound algorithm)
""")


def main():
    """Display all examples and guides."""
    
    show_usage_examples()
    show_dimension_guide()
    show_tile_recommendations()
    show_target_image_tips()
    show_troubleshooting()
    show_performance_tips()
    
    print("\n" + "="*70)
    print("For detailed help: python photo_mosaic.py --help")
    print("="*70 + "\n")


if __name__ == '__main__':
    main()
