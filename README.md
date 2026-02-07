# Photo Mosaic Generator - Ralph Wiggum Loop Edition

A high-performance Python script that generates photo mosaics where the overall pattern matches a target image, with intelligent square cropping for non-square tiles.

## Overview

This script creates a mosaic where:
- Each small tile in the mosaic is a real photo from your tile folder
- The arrangement of tiles creates a larger image that matches your target photo
- Non-square images are intelligently cropped to their most interesting region
- Optimized for high-quality poster printing

## Installation

```bash
# Install dependencies
pip install -r requirements.txt
```

### Requirements
- Python 3.8+
- Pillow (PIL)
- NumPy
- SciPy (for edge detection, with fallback available)

## Quick Start

### Basic Usage
```bash
python photo_mosaic.py target_image.jpg ./tiles_folder
```

### High-Quality Poster (36" × 24" at 300 DPI)
```bash
python photo_mosaic.py target.jpg ./tiles --size 4320 2880 --tile-size 120
```

### With Title
```bash
python photo_mosaic.py target.jpg ./tiles --title "My Amazing Poster" --output poster.jpg
```

## Command Line Arguments

### Positional Arguments
- `target_image`: Path to the image you want to create a mosaic pattern from
- `tile_folder`: Path to folder containing tile images

### Optional Arguments

| Argument | Default | Description |
|----------|---------|-------------|
| `--size WIDTH HEIGHT` | 4320 2880 | Output dimensions in pixels (default: 36"×24" at 300 DPI) |
| `--tile-size PIXELS` | 120 | Individual tile size in pixels (square) |
| `--title TEXT` | None | Add a 2-inch white border with title text at bottom |
| `--output FILENAME` | mosaic_output.jpg | Output filename |
| `--dpi DPI` | 300 | DPI for print calculations (affects title border size) |
| `--threads NUM` | 4 | Number of threads for tile loading |

## Usage Examples

### Small preview version
```bash
python photo_mosaic.py photo.jpg ./tiles --size 1920 1280 --tile-size 64 --output preview.jpg
```

### High-quality 24"×18" poster
```bash
python photo_mosaic.py photo.jpg ./tiles --size 7200 5400 --tile-size 100 --output poster_large.jpg
```

### With centered title
```bash
python photo_mosaic.py photo.jpg ./tiles --title "Family Memories 2024" --output titled_poster.jpg
```

### Custom tile size (smaller = more detail, slower)
```bash
python photo_mosaic.py photo.jpg ./tiles --tile-size 80 --output high_detail.jpg
```

## How It Works

### Ralph Wiggum Loop: 10 Refactoring Iterations

This script was built using the "Ralph Wiggum Loop" methodology - starting simple and refactoring 10 times for performance and robustness:

1. **Loop 1**: Basic functionality - core mosaic logic
2. **Loop 2**: Smart crop algorithm using edge detection for non-square images
3. **Loop 3**: Tile caching and deduplication via hashing
4. **Loop 4**: Comprehensive error handling and input validation
5. **Loop 5**: Parallel tile loading with ThreadPoolExecutor
6. **Loop 6**: Memory-efficient image loading and resizing
7. **Loop 7**: NumPy optimizations for color matching
8. **Loop 8**: Progress indicators and user feedback
9. **Loop 9**: PIL optimization for final output
10. **Loop 10**: Final polish, argument parsing, edge case handling

### Smart Cropping Algorithm

Non-square images are cropped to their most interesting region using edge detection:
- Computes edge intensity using Sobel filters (with fallback to Laplacian)
- Finds the square crop window with highest edge density
- Preserves the most visually important part of each tile

### Color Matching

For efficiency:
- Pre-computes average color of each tile once
- For each position in the mosaic, finds the closest matching tile
- Uses Euclidean distance in RGB color space
- Duplicate tiles are skipped (same file detected via MD5 hash)

## Performance Tuning

### Faster Processing
- Decrease `--tile-size` (e.g., 60 instead of 120) - fewer total tiles to process
- Decrease `--size` (e.g., 2048 1536) - smaller output resolution
- Increase `--threads` - more parallel tile loading

### Better Quality
- Increase `--tile-size` - each tile larger, more detail visible
- Increase number of tiles in your tile folder - more options for color matching
- Use higher resolution target image
- Ensure target image is well-composed

### File Size
The script automatically optimizes JPEG output at 95% quality. If needed:
- Reduce `--size` to lower resolution
- Reduce tile folder size (fewer unique tiles used)

## Tips for Best Results

1. **Target Image**: Use a clear, well-lit image with good contrast and color range. Avoid very dark or very bright images.

2. **Tile Images**: 
   - More tiles = better color matching = better mosaic
   - Aim for 200-1000 tile images minimum
   - Variety in colors helps fill the palette
   - Diverse subjects work better than similar-looking photos

3. **Tile Size vs Detail**:
   - Larger tile size (120+) = more visible detail but fewer tiles
   - Smaller tile size (60-80) = finer mosaic but may run slower

4. **Print Quality**:
   - Default (4320×2880 at 300 DPI) = professional 36"×24" poster
   - Increase tile size if output is huge (avoids excessive file size)
   - Reduce tile size if you want ultra-fine detail

5. **Title Text**:
   - Adds a 2-inch white border with centered black text
   - Works best with poster dimensions
   - Adjust DPI if border size looks wrong

## Troubleshooting

### "No images found in tile folder"
- Check that images are in the folder or subfolders
- Supported formats: JPG, JPEG, PNG, GIF, BMP, WEBP
- Ensure files are actually image files (not corrupted)

### Very slow processing
- Reduce `--size` or `--tile-size`
- Decrease number of tiles in folder (cull duplicates/similar images)
- Check system memory usage

### Mosaic quality is poor
- Add more unique tiles to your folder
- Use a better target image (clearer, more detail)
- Increase tile size to see more detail per tile
- Try a smaller tile size for finer color matching

### Crashes with large files
- Reduce `--size` to smaller resolution
- Reduce number of tiles
- Increase system RAM or close other applications

## Technical Details

### Color Space
Uses RGB color space for efficiency. Tiles are normalized to RGB even if they're RGBA or other formats.

### Caching
- Loads each tile once and caches it in memory
- Duplicate tile files are detected via MD5 hash and skipped
- Cache is built during initial tile loading phase

### Memory Usage
Approximate formula: `(mosaic_width × mosaic_height × tile_size²) / (1024² MB) × 3`

For default settings (4320×2880, 120px tiles):
- Mosaic grid: 36×24 = 864 tiles
- Output image: ~10 MB in memory before compression

### Performance
- Processing speed primarily depends on number of tiles and tile size
- 1000 tiles with 120px size: ~2-5 seconds on modern CPU
- Initial tile loading is parallelized for faster startup

## Examples

### Gallery-Quality Family Photo Mosaic
```bash
# Collect 500 family photos in a folder
python photo_mosaic.py family_photo.jpg ./family_photos \
  --size 4320 2880 \
  --tile-size 120 \
  --title "The Johnson Family - 2024" \
  --output family_mosaic.jpg
```

### Quick Preview
```bash
# Create a quick low-res preview (5 seconds)
python photo_mosaic.py photo.jpg ./tiles \
  --size 1280 960 \
  --tile-size 80 \
  --output preview.jpg
```

### Ultra-Fine Detail
```bash
# Smaller tiles for maximum detail
python photo_mosaic.py photo.jpg ./tiles \
  --size 4320 2880 \
  --tile-size 60 \
  --title "Ultra Detail Mosaic" \
  --output ultra_detail.jpg
```

## License

Use freely for personal and commercial projects.

## Support

If you encounter issues:
1. Verify all file paths exist
2. Check that the tile folder contains actual image files
3. Try with a smaller `--size` or `--tile-size` first
4. Ensure target image is a valid image file
5. Check available system memory for very large outputs

---

**Created with the Ralph Wiggum Loop**: Eat my shorts, optimization! (I'm learning!)
