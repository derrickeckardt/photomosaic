"""
Test suite for the Photo Mosaic Generator
"""
import pytest
import os
import sys
import tempfile
import numpy as np
from PIL import Image

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from photo_mosaic import (
    find_interesting_region,
    TileProcessor,
    create_mosaic,
    add_title_border,
    validate_inputs,
    load_target_image
)


@pytest.fixture
def temp_dir():
    """Create temporary directory for test files."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield tmpdir


@pytest.fixture
def sample_image():
    """Create a sample test image."""
    img = Image.new('RGB', (200, 200), color='red')
    # Add some variation
    pixels = img.load()
    for x in range(100, 200):
        for y in range(100, 200):
            pixels[x, y] = (0, 0, 255)  # Blue quadrant
    return img


@pytest.fixture
def sample_tiles(temp_dir):
    """Create sample tile images."""
    tile_dir = os.path.join(temp_dir, 'tiles')
    os.makedirs(tile_dir)

    colors = ['red', 'green', 'blue', 'yellow', 'cyan', 'magenta']
    for i, color in enumerate(colors):
        img = Image.new('RGB', (100, 100), color=color)
        img.save(os.path.join(tile_dir, f'tile_{i}.jpg'))

    return tile_dir


@pytest.fixture
def target_image_path(temp_dir, sample_image):
    """Save sample image to file."""
    path = os.path.join(temp_dir, 'target.jpg')
    sample_image.save(path)
    return path


class TestFindInterestingRegion:
    """Test the smart cropping algorithm."""

    def test_square_image(self):
        """Square image should return full image bounds."""
        img = Image.new('RGB', (100, 100), color='white')
        box = find_interesting_region(img, 100)
        assert box == (0, 0, 100, 100)

    def test_landscape_image(self):
        """Landscape image should return square crop."""
        img = Image.new('RGB', (200, 100), color='white')
        box = find_interesting_region(img, 100)
        left, top, right, bottom = box
        assert right - left == 100  # Width of crop
        assert bottom - top == 100  # Height of crop
        assert top == 0  # Should crop from full height

    def test_portrait_image(self):
        """Portrait image should return square crop."""
        img = Image.new('RGB', (100, 200), color='white')
        box = find_interesting_region(img, 100)
        left, top, right, bottom = box
        assert right - left == 100  # Width of crop
        assert bottom - top == 100  # Height of crop
        assert left == 0  # Should crop from full width

    def test_finds_interesting_area(self):
        """Should find area with edges/contrast."""
        # Create image with interesting area on right side
        img = Image.new('RGB', (200, 100), color='white')
        pixels = img.load()
        # Add high contrast area on right
        for x in range(150, 200):
            for y in range(0, 100):
                pixels[x, y] = (0, 0, 0) if (x + y) % 2 == 0 else (255, 255, 255)

        box = find_interesting_region(img, 100)
        left, _, _, _ = box
        # Should prefer the right side with more edges
        assert left >= 50  # Should be towards the interesting area


class TestTileProcessor:
    """Test the tile processor class."""

    def test_init(self):
        processor = TileProcessor(120)
        assert processor.target_size == 120
        assert processor.tile_cache == {}
        assert processor.hash_cache == {}
        assert processor._cache_order == []

    def test_load_and_crop_tile(self, temp_dir):
        """Test loading and cropping a single tile."""
        # Create test image
        img = Image.new('RGB', (200, 150), color='blue')
        path = os.path.join(temp_dir, 'test.jpg')
        img.save(path)

        processor = TileProcessor(100)
        tile = processor.load_and_crop_tile(path)

        assert tile is not None
        assert tile.size == (100, 100)
        assert path in processor.tile_cache

    def test_tile_caching(self, temp_dir):
        """Test that tiles are cached."""
        img = Image.new('RGB', (100, 100), color='red')
        path = os.path.join(temp_dir, 'cached.jpg')
        img.save(path)

        processor = TileProcessor(50)
        tile1 = processor.load_and_crop_tile(path)
        tile2 = processor.load_and_crop_tile(path)

        assert tile1 is tile2  # Same object from cache

    def test_cache_limit(self, temp_dir):
        """Test that cache respects MAX_CACHE_SIZE."""
        processor = TileProcessor(10)
        processor.MAX_CACHE_SIZE = 3  # Small limit for testing

        # Create more tiles than cache size
        for i in range(5):
            img = Image.new('RGB', (20, 20), color='red')
            path = os.path.join(temp_dir, f'tile_{i}.jpg')
            img.save(path)
            processor.load_and_crop_tile(path)

        # Cache should not exceed limit
        assert len(processor.tile_cache) <= 3

    def test_get_all_tiles(self, sample_tiles):
        """Test loading all tiles from directory."""
        processor = TileProcessor(50)
        tiles = processor.get_all_tiles(sample_tiles)

        assert len(tiles) == 6  # 6 color tiles created
        for tile in tiles:
            assert tile.size == (50, 50)

    def test_max_tiles_limit(self, temp_dir):
        """Test max_tiles parameter."""
        tile_dir = os.path.join(temp_dir, 'many_tiles')
        os.makedirs(tile_dir)

        # Create 10 unique tiles with different colors
        for i in range(10):
            # Use different colors so they don't get deduplicated
            img = Image.new('RGB', (50, 50), color=(i * 25, 100, 200))
            img.save(os.path.join(tile_dir, f'tile_{i}.jpg'))

        processor = TileProcessor(25)
        tiles = processor.get_all_tiles(tile_dir, max_tiles=5)

        assert len(tiles) == 5  # Limited to 5

    def test_duplicate_detection(self, temp_dir):
        """Test that duplicate images are skipped."""
        tile_dir = os.path.join(temp_dir, 'dupes')
        os.makedirs(tile_dir)

        # Create identical images with different names
        img = Image.new('RGB', (50, 50), color='red')
        img.save(os.path.join(tile_dir, 'tile_a.jpg'))
        img.save(os.path.join(tile_dir, 'tile_b.jpg'))
        img.save(os.path.join(tile_dir, 'tile_c.jpg'))

        processor = TileProcessor(25)
        tiles = processor.get_all_tiles(tile_dir)

        assert len(tiles) == 1  # Only one unique tile

    def test_invalid_file_handling(self, temp_dir):
        """Test that invalid files are skipped gracefully."""
        tile_dir = os.path.join(temp_dir, 'invalid')
        os.makedirs(tile_dir)

        # Create valid tile
        img = Image.new('RGB', (50, 50), color='green')
        img.save(os.path.join(tile_dir, 'valid.jpg'))

        # Create invalid file
        with open(os.path.join(tile_dir, 'invalid.jpg'), 'w') as f:
            f.write('not an image')

        processor = TileProcessor(25)
        tiles = processor.get_all_tiles(tile_dir)

        assert len(tiles) == 1  # Only valid tile loaded


class TestCreateMosaic:
    """Test mosaic creation."""

    def test_create_simple_mosaic(self, sample_image, sample_tiles):
        """Test creating a basic mosaic."""
        processor = TileProcessor(50)
        tiles = processor.get_all_tiles(sample_tiles)

        mosaic = create_mosaic(
            sample_image,
            tiles,
            mosaic_width=4,
            mosaic_height=4,
            tile_size=50
        )

        assert mosaic is not None
        assert mosaic.size == (200, 200)  # 4*50 x 4*50

    def test_mosaic_with_progress(self, sample_image, sample_tiles):
        """Test mosaic creation with progress callback."""
        processor = TileProcessor(50)
        tiles = processor.get_all_tiles(sample_tiles)

        progress_calls = []
        def progress_callback(current, total):
            progress_calls.append((current, total))

        mosaic = create_mosaic(
            sample_image,
            tiles,
            mosaic_width=4,
            mosaic_height=4,
            tile_size=50,
            progress_callback=progress_callback
        )

        assert len(progress_calls) > 0
        assert mosaic is not None

    def test_mosaic_no_tiles_error(self, sample_image):
        """Test that empty tiles list raises error."""
        with pytest.raises(ValueError, match="No tiles available"):
            create_mosaic(sample_image, [], 4, 4, 50)


class TestAddTitleBorder:
    """Test title border functionality."""

    def test_adds_border(self, sample_image):
        """Test that border is added."""
        bordered = add_title_border(sample_image, "Test Title", dpi=100)

        # Border should make image larger
        assert bordered.width > sample_image.width
        assert bordered.height > sample_image.height

    def test_border_size(self, sample_image):
        """Test border size calculation."""
        dpi = 100
        expected_border = int(2 * dpi)  # 2 inches

        bordered = add_title_border(sample_image, "Test", dpi=dpi)

        width_increase = bordered.width - sample_image.width
        height_increase = bordered.height - sample_image.height

        assert width_increase == expected_border * 2  # Border on both sides
        assert height_increase == expected_border * 2


class TestValidateInputs:
    """Test input validation."""

    def test_valid_inputs(self, target_image_path, sample_tiles):
        """Test validation with valid inputs."""
        valid, error = validate_inputs(target_image_path, sample_tiles)
        assert valid is True
        assert error == ""

    def test_missing_target(self, sample_tiles):
        """Test validation with missing target image."""
        valid, error = validate_inputs('/nonexistent/image.jpg', sample_tiles)
        assert valid is False
        assert 'not found' in error.lower()

    def test_missing_tile_folder(self, target_image_path):
        """Test validation with missing tile folder."""
        valid, error = validate_inputs(target_image_path, '/nonexistent/folder')
        assert valid is False
        assert 'not found' in error.lower()


class TestLoadTargetImage:
    """Test target image loading."""

    def test_load_valid_image(self, target_image_path):
        """Test loading valid image."""
        img = load_target_image(target_image_path)
        assert img is not None
        assert img.mode == 'RGB'

    def test_converts_to_rgb(self, temp_dir):
        """Test that non-RGB images are converted."""
        # Create grayscale image
        img = Image.new('L', (100, 100), color=128)
        path = os.path.join(temp_dir, 'gray.jpg')
        img.save(path)

        loaded = load_target_image(path)
        assert loaded.mode == 'RGB'


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
