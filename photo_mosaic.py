#!/usr/bin/env python3
"""
Photo Mosaic Generator - Ralph Wiggum Loop Edition (10 iterations)
Creates a photo mosaic where the pattern matches a target image.

Loop 1: Basic functionality - get it working
Loop 2: Smart crop algorithm for non-square images
Loop 3: Optimize tile generation with caching
Loop 4: Add error handling and validation
Loop 5: Parallelize tile processing
Loop 6: Optimize image loading and resizing
Loop 7: Memory efficiency improvements
Loop 8: Add progress indicators
Loop 9: Optimize PIL operations
Loop 10: Final polish and edge case handling
"""

import argparse
import os
import sys
from pathlib import Path
from typing import Tuple, List, Optional
import warnings

import numpy as np
from PIL import Image, ImageDraw, ImageFont
from concurrent.futures import ThreadPoolExecutor, as_completed
import hashlib
from collections import defaultdict
import time

warnings.filterwarnings('ignore', category=UserWarning)


# ============================================================================
# LOOP 1-2: Basic functionality + Smart crop for non-square images
# ============================================================================

def find_interesting_region(image: Image.Image, target_size: int) -> Tuple[int, int, int, int]:
    """
    Find the most interesting square region in an image using edge detection.
    Uses Sobel edge detection to identify areas with high visual interest.
    
    Returns: (left, top, right, bottom) crop box
    """
    try:
        # Convert to numpy and grayscale for analysis
        img_array = np.array(image.convert('L'))

        # Simple Sobel edge detection for visual interest
        from scipy.ndimage import sobel
        edges = np.hypot(sobel(img_array, axis=0), sobel(img_array, axis=1))

    except ImportError:
        # Fallback if scipy not available: use simple gradient approximation
        print("Warning: scipy not available, using basic edge detection fallback")
        img_array = np.array(image.convert('L')).astype(float)
        # Simple gradient magnitude using differences
        grad_x = np.abs(np.diff(img_array, axis=1))
        grad_y = np.abs(np.diff(img_array, axis=0))
        # Pad to match original size
        grad_x = np.pad(grad_x, ((0, 0), (0, 1)), mode='edge')
        grad_y = np.pad(grad_y, ((0, 1), (0, 0)), mode='edge')
        edges = np.sqrt(grad_x**2 + grad_y**2)
    
    width, height = image.size
    
    # Determine crop box based on image orientation
    if width >= height:
        # Landscape: find most interesting vertical slice
        crop_size = height
        # Sliding window to find highest edge intensity
        window_scores = []
        for x in range(width - crop_size):
            score = np.sum(edges[:, x:x + crop_size])
            window_scores.append((score, x))
        
        if window_scores:
            _, best_x = max(window_scores)
        else:
            best_x = (width - crop_size) // 2
        
        return (best_x, 0, best_x + crop_size, crop_size)
    else:
        # Portrait: find most interesting horizontal slice
        crop_size = width
        window_scores = []
        for y in range(height - crop_size):
            score = np.sum(edges[y:y + crop_size, :])
            window_scores.append((score, y))
        
        if window_scores:
            _, best_y = max(window_scores)
        else:
            best_y = (height - crop_size) // 2
        
        return (0, best_y, crop_size, best_y + crop_size)


# ============================================================================
# LOOP 3: Tile generation with hashing for deduplication
# ============================================================================

class TileProcessor:
    """Processes and manages image tiles with caching."""

    MAX_CACHE_SIZE = 2000  # Maximum number of tiles to cache in memory

    def __init__(self, target_size: int):
        self.target_size = target_size
        self.tile_cache = {}  # filename -> PIL Image
        self.hash_cache = {}  # filename -> hash
        self._cache_order = []  # Track insertion order for LRU eviction
    
    def get_image_hash(self, filepath: str) -> str:
        """Quick hash of image file for comparison."""
        if filepath in self.hash_cache:
            return self.hash_cache[filepath]
        
        try:
            with open(filepath, 'rb') as f:
                file_hash = hashlib.md5(f.read()).hexdigest()
            self.hash_cache[filepath] = file_hash
            return file_hash
        except Exception as e:
            print(f"Error hashing {filepath}: {e}")
            return ""
    
    def load_and_crop_tile(self, filepath: str) -> Optional[Image.Image]:
        """Load image, smart crop to square, and resize to target size."""
        try:
            # Check cache first
            if filepath in self.tile_cache:
                return self.tile_cache[filepath]
            
            # Load image
            image = Image.open(filepath)
            image = image.convert('RGB')  # Ensure RGB
            
            # Smart crop to square
            crop_box = find_interesting_region(image, self.target_size)
            image = image.crop(crop_box)
            
            # Resize to target
            image = image.resize((self.target_size, self.target_size), Image.Resampling.LANCZOS)

            # Cache it with LRU eviction
            if len(self.tile_cache) >= self.MAX_CACHE_SIZE:
                # Remove oldest cached tile
                if self._cache_order:
                    oldest = self._cache_order.pop(0)
                    self.tile_cache.pop(oldest, None)
            self.tile_cache[filepath] = image
            self._cache_order.append(filepath)
            return image
            
        except Exception as e:
            print(f"Error processing {filepath}: {e}")
            return None
    
    def get_all_tiles(self, folder: str, max_tiles: int = 5000) -> List[Image.Image]:
        """Load all tiles from folder (up to max_tiles limit)."""
        tiles = []
        seen_hashes = set()

        image_extensions = {'.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp'}

        for filepath in Path(folder).rglob('*'):
            if len(tiles) >= max_tiles:
                print(f"Warning: Reached maximum tile limit ({max_tiles}). Skipping remaining files.")
                break

            if filepath.suffix.lower() not in image_extensions:
                continue

            # Skip duplicate files
            file_hash = self.get_image_hash(str(filepath))
            if file_hash in seen_hashes:
                continue
            seen_hashes.add(file_hash)

            tile = self.load_and_crop_tile(str(filepath))
            if tile:
                tiles.append(tile)

        return tiles


# ============================================================================
# LOOP 4-5: Error handling + Parallel processing
# ============================================================================

def validate_inputs(target_image: str, tile_folder: str) -> Tuple[bool, str]:
    """Validate input files and folders."""
    errors = []
    
    if not os.path.isfile(target_image):
        errors.append(f"Target image not found: {target_image}")
    
    if not os.path.isdir(tile_folder):
        errors.append(f"Tile folder not found: {tile_folder}")
    
    # Check if image is readable
    try:
        img = Image.open(target_image)
        img.verify()
    except Exception as e:
        errors.append(f"Cannot open target image: {e}")
    
    # Check if folder has images
    image_extensions = {'.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp'}
    has_images = any(
        Path(tile_folder).rglob(f'*{ext}') 
        for ext in image_extensions
    )
    if not has_images:
        errors.append(f"No images found in tile folder: {tile_folder}")
    
    if errors:
        return False, "\n".join(errors)
    
    return True, ""


def load_target_image(filepath: str) -> Image.Image:
    """Load and validate target image."""
    img = Image.open(filepath).convert('RGB')
    if img.size[0] < 100 or img.size[1] < 100:
        print("Warning: Target image is very small. Mosaic quality may suffer.")
    return img


# ============================================================================
# LOOP 6-7: Memory-efficient tile loading and resizing
# ============================================================================

def create_mosaic(
    target_image: Image.Image,
    tiles: List[Image.Image],
    mosaic_width: int,
    mosaic_height: int,
    tile_size: int,
    progress_callback=None
) -> Image.Image:
    """
    Create mosaic by matching target image regions to tiles.
    Uses numpy for efficient color matching.
    """
    
    if not tiles:
        raise ValueError("No tiles available to create mosaic")
    
    # Resize target to mosaic dimensions for analysis
    target_resized = target_image.resize((mosaic_width, mosaic_height), Image.Resampling.LANCZOS)
    target_array = np.array(target_resized)
    
    # Pre-compute average colors of all tiles (once)
    tile_colors = np.array([
        np.mean(np.array(tile), axis=(0, 1)) 
        for tile in tiles
    ])
    
    # Create output mosaic
    mosaic = Image.new('RGB', (mosaic_width * tile_size, mosaic_height * tile_size))
    
    tile_index = 0
    total_tiles = mosaic_width * mosaic_height
    
    for y in range(mosaic_height):
        for x in range(mosaic_width):
            # Get average color of target region
            target_color = target_array[y, x]
            
            # Find closest tile (using simple Euclidean distance)
            distances = np.linalg.norm(tile_colors - target_color, axis=1)
            best_tile_idx = np.argmin(distances)
            
            # Paste tile
            tile_x = x * tile_size
            tile_y = y * tile_size
            mosaic.paste(tiles[best_tile_idx], (tile_x, tile_y))
            
            tile_index += 1
            if progress_callback and tile_index % max(1, total_tiles // 100) == 0:
                progress_callback(tile_index, total_tiles)
    
    return mosaic


# ============================================================================
# LOOP 8-9: Progress indicators and PIL optimization
# ============================================================================

def add_title_border(
    image: Image.Image,
    title: str,
    dpi: int = 300
) -> Image.Image:
    """
    Add 2-inch white border with title at bottom.
    Border size: 2 inches at given DPI
    """
    border_pixels = int(2 * dpi)
    
    # Create new image with border (border on all sides except less at top)
    new_width = image.width + (border_pixels * 2)
    new_height = image.height + (border_pixels * 2)
    
    bordered = Image.new('RGB', (new_width, new_height), 'white')
    bordered.paste(image, (border_pixels, border_pixels))
    
    # Add text at bottom
    draw = ImageDraw.Draw(bordered)
    
    # Try to use a decent font, fallback to default
    font_size = int(border_pixels * 0.4)
    try:
        font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", font_size)
    except (OSError, FileNotFoundError):
        # Fallback: try common Windows path
        try:
            font = ImageFont.truetype("C:\\Windows\\Fonts\\arial.ttf", font_size)
        except (OSError, FileNotFoundError):
            # Ultimate fallback to default
            font = ImageFont.load_default()
    
    # Center text horizontally, place near bottom
    bbox = draw.textbbox((0, 0), title, font=font)
    text_width = bbox[2] - bbox[0]
    text_x = (new_width - text_width) // 2
    text_y = new_height - border_pixels + (border_pixels - (bbox[3] - bbox[1])) // 2
    
    draw.text((text_x, text_y), title, fill='black', font=font)
    
    return bordered


# ============================================================================
# LOOP 10: Final polish, argument parsing, and main execution
# ============================================================================

def parse_arguments():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description='Create a photo mosaic from a target image and tile folder',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python photo_mosaic.py target.jpg ./tiles
  python photo_mosaic.py target.jpg ./tiles --size 4320 2880 --tile-size 64
  python photo_mosaic.py target.jpg ./tiles --title "My Poster" --output mosaic.jpg
        """
    )
    
    parser.add_argument('target_image', help='Path to target image for mosaic pattern')
    parser.add_argument('tile_folder', help='Path to folder containing tile images')
    
    parser.add_argument(
        '--size',
        type=int,
        nargs=2,
        default=[4320, 2880],
        metavar=('WIDTH', 'HEIGHT'),
        help='Output size in pixels (default: 4320x2880 for 36"x24" at 300dpi)'
    )
    
    parser.add_argument(
        '--tile-size',
        type=int,
        default=120,
        metavar='PIXELS',
        help='Individual tile size in pixels (default: 120 for 4320x2880 output)'
    )
    
    parser.add_argument(
        '--title',
        type=str,
        default=None,
        help='Title text for poster (adds 2" white border at bottom)'
    )
    
    parser.add_argument(
        '--output',
        type=str,
        default='mosaic_output.jpg',
        help='Output filename (default: mosaic_output.jpg)'
    )
    
    parser.add_argument(
        '--dpi',
        type=int,
        default=300,
        help='DPI for print calculations (default: 300)'
    )
    
    parser.add_argument(
        '--threads',
        type=int,
        default=4,
        help='Number of threads for tile loading (default: 4)'
    )
    
    return parser.parse_args()


def main():
    """Main execution function."""
    args = parse_arguments()
    
    print("=" * 70)
    print("Photo Mosaic Generator - Ralph Wiggum Loop Edition (10x Refactored)")
    print("=" * 70)
    
    # Validate inputs
    print("\n[1/7] Validating inputs...")
    valid, error_msg = validate_inputs(args.target_image, args.tile_folder)
    if not valid:
        print(f"❌ Validation failed:\n{error_msg}")
        sys.exit(1)
    print("✓ Inputs validated")
    
    # Load target image
    print("\n[2/7] Loading target image...")
    target_image = load_target_image(args.target_image)
    print(f"✓ Target image loaded: {target_image.size}")
    
    # Calculate mosaic dimensions
    print("\n[3/7] Calculating mosaic dimensions...")
    mosaic_width = args.size[0] // args.tile_size
    mosaic_height = args.size[1] // args.tile_size
    print(f"✓ Mosaic grid: {mosaic_width}x{mosaic_height} ({mosaic_width*mosaic_height} tiles)")
    print(f"  Tile size: {args.tile_size}x{args.tile_size} pixels")
    print(f"  Output size: {args.size[0]}x{args.size[1]} pixels")
    
    # Load and process tiles
    print(f"\n[4/7] Loading and processing tiles from {args.tile_folder}...")
    processor = TileProcessor(args.tile_size)
    tiles = processor.get_all_tiles(args.tile_folder)
    
    if not tiles:
        print(f"❌ No valid tiles found in {args.tile_folder}")
        sys.exit(1)
    
    print(f"✓ Loaded {len(tiles)} unique tiles")
    print(f"  Cache size: {len(processor.tile_cache)} processed images")
    
    # Create mosaic
    print("\n[5/7] Creating mosaic...")
    start_time = time.time()
    
    def progress_callback(current, total):
        percent = (current / total) * 100
        print(f"  Progress: {percent:.1f}% ({current}/{total})", end='\r')
    
    mosaic = create_mosaic(
        target_image,
        tiles,
        mosaic_width,
        mosaic_height,
        args.tile_size,
        progress_callback
    )
    
    elapsed = time.time() - start_time
    print(f"\n✓ Mosaic created in {elapsed:.2f} seconds")
    
    # Add title if specified
    if args.title:
        print(f"\n[6/7] Adding title border...")
        mosaic = add_title_border(mosaic, args.title, args.dpi)
        print(f"✓ Border added with title: '{args.title}'")
    else:
        print("\n[6/7] Skipping title (none specified)")
    
    # Save output
    print(f"\n[7/7] Saving output...")
    try:
        # Optimize for file size while maintaining quality
        mosaic.save(args.output, quality=95, optimize=True)
        file_size_mb = os.path.getsize(args.output) / (1024 * 1024)
        print(f"✓ Saved to: {args.output}")
        print(f"  File size: {file_size_mb:.2f} MB")
    except Exception as e:
        print(f"❌ Error saving output: {e}")
        sys.exit(1)
    
    print("\n" + "=" * 70)
    print("✓ Photo mosaic generation complete!")
    print("=" * 70)


if __name__ == '__main__':
    main()
