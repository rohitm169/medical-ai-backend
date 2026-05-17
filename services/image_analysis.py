"""
============================================
IMAGE ANALYSIS SERVICE
============================================
Image processing, validation, resizing,
compression, and metadata extraction.
"""

import io
import os
from typing import Optional, Dict, Any, Tuple
from PIL import Image, ImageOps, UnidentifiedImageError


# ============================================
# IMAGE ANALYZER CLASS
# ============================================
class ImageAnalyzer:
    """Service class for image processing and analysis"""

    # ============================================
    # CONFIGURATION
    # ============================================
    MAX_WIDTH = 1024
    MAX_HEIGHT = 1024
    DEFAULT_QUALITY = 85
    MIN_QUALITY = 50
    MAX_QUALITY = 95

    MAX_FILE_SIZE_BYTES = 5 * 1024 * 1024  # 5 MB
    MIN_FILE_SIZE_BYTES = 100  # 100 bytes minimum

    MIN_WIDTH = 50
    MIN_HEIGHT = 50

    SUPPORTED_FORMATS = {'JPEG', 'PNG', 'WEBP', 'GIF', 'BMP'}
    OUTPUT_FORMAT = 'JPEG'


    # ============================================
    # PROCESS IMAGE
    # ============================================
    @staticmethod
    def process_image(
        image_bytes: bytes,
        max_width: int = None,
        max_height: int = None,
        quality: int = None
    ) -> Optional[bytes]:
        """
        Process an image: validate, resize, optimize, and convert.

        Args:
            image_bytes: Original image binary data
            max_width: Maximum width (default 1024)
            max_height: Maximum height (default 1024)
            quality: Output quality 1-100 (default 85)

        Returns:
            bytes: Processed image bytes or None if failed
        """

        if not image_bytes:
            return None

        max_width = max_width or ImageAnalyzer.MAX_WIDTH
        max_height = max_height or ImageAnalyzer.MAX_HEIGHT
        quality = quality or ImageAnalyzer.DEFAULT_QUALITY

        # Clamp quality
        quality = max(ImageAnalyzer.MIN_QUALITY, min(ImageAnalyzer.MAX_QUALITY, quality))

        try:
            # Open image
            image = Image.open(io.BytesIO(image_bytes))

            # Auto-rotate based on EXIF data
            try:
                image = ImageOps.exif_transpose(image)
            except Exception:
                pass

            # Convert to RGB if necessary
            if image.mode in ('RGBA', 'LA', 'P'):
                background = Image.new('RGB', image.size, (255, 255, 255))

                if image.mode == 'P':
                    image = image.convert('RGBA')

                if image.mode in ('RGBA', 'LA'):
                    background.paste(image, mask=image.split()[-1])
                    image = background
                else:
                    image = image.convert('RGB')

            elif image.mode != 'RGB':
                image = image.convert('RGB')

            # Resize if needed
            if image.width > max_width or image.height > max_height:
                image = ImageAnalyzer.resize_image(
                    image,
                    max_width=max_width,
                    max_height=max_height
                )

            # Save to bytes
            output_buffer = io.BytesIO()

            image.save(
                output_buffer,
                format=ImageAnalyzer.OUTPUT_FORMAT,
                quality=quality,
                optimize=True,
                progressive=True
            )

            output_buffer.seek(0)
            return output_buffer.getvalue()

        except UnidentifiedImageError:
            print("[PROCESS IMAGE ERROR] Cannot identify image format")
            return None

        except Exception as e:
            print(f"[PROCESS IMAGE ERROR] {str(e)}")
            return None


    # ============================================
    # VALIDATE IMAGE
    # ============================================
    @staticmethod
    def validate_image(image_bytes: bytes) -> Tuple[bool, str]:
        """
        Validate an image's content and properties.

        Args:
            image_bytes: Image binary data

        Returns:
            tuple: (is_valid, message)
        """

        if not image_bytes:
            return False, 'No image data provided'

        # Check size
        size = len(image_bytes)

        if size < ImageAnalyzer.MIN_FILE_SIZE_BYTES:
            return False, 'Image file is too small'

        if size > ImageAnalyzer.MAX_FILE_SIZE_BYTES:
            return False, f'Image exceeds maximum size of {ImageAnalyzer.MAX_FILE_SIZE_BYTES // (1024 * 1024)} MB'

        try:
            image = Image.open(io.BytesIO(image_bytes))

            # Verify it's a real image
            image.verify()

            # Reopen since verify() closes the file
            image = Image.open(io.BytesIO(image_bytes))

            # Check format
            if image.format and image.format.upper() not in ImageAnalyzer.SUPPORTED_FORMATS:
                return False, f'Unsupported image format: {image.format}'

            # Check dimensions
            if image.width < ImageAnalyzer.MIN_WIDTH or image.height < ImageAnalyzer.MIN_HEIGHT:
                return False, f'Image too small. Minimum: {ImageAnalyzer.MIN_WIDTH}x{ImageAnalyzer.MIN_HEIGHT}'

            if image.width > 10000 or image.height > 10000:
                return False, 'Image dimensions too large'

            # Check if image is corrupted
            try:
                image.load()
            except Exception:
                return False, 'Image file is corrupted'

            return True, 'Image is valid'

        except UnidentifiedImageError:
            return False, 'Cannot identify image format. File may be corrupted or not a valid image'

        except Exception as e:
            return False, f'Image validation failed: {str(e)}'


    # ============================================
    # RESIZE IMAGE
    # ============================================
    @staticmethod
    def resize_image(
        image: Image.Image,
        max_width: int = None,
        max_height: int = None,
        maintain_aspect: bool = True
    ) -> Image.Image:
        """
        Resize an image while maintaining aspect ratio.

        Args:
            image: PIL Image object
            max_width: Maximum width
            max_height: Maximum height
            maintain_aspect: Keep aspect ratio (default True)

        Returns:
            Image: Resized PIL Image
        """

        if not image:
            return None

        max_width = max_width or ImageAnalyzer.MAX_WIDTH
        max_height = max_height or ImageAnalyzer.MAX_HEIGHT

        try:
            if maintain_aspect:
                # Calculate new dimensions maintaining aspect ratio
                ratio = min(
                    max_width / image.width,
                    max_height / image.height
                )

                if ratio >= 1:
                    return image

                new_width = int(image.width * ratio)
                new_height = int(image.height * ratio)

                # Use high quality resampling
                resized = image.resize(
                    (new_width, new_height),
                    Image.Resampling.LANCZOS
                )

                return resized

            else:
                # Force exact dimensions
                return image.resize(
                    (max_width, max_height),
                    Image.Resampling.LANCZOS
                )

        except Exception as e:
            print(f"[RESIZE ERROR] {str(e)}")
            return image


    # ============================================
    # COMPRESS IMAGE
    # ============================================
    @staticmethod
    def compress_image(
        image_bytes: bytes,
        target_size_kb: int = 500,
        min_quality: int = 50
    ) -> Optional[bytes]:
        """
        Compress an image to a target file size.

        Args:
            image_bytes: Original image bytes
            target_size_kb: Target size in KB
            min_quality: Minimum quality threshold

        Returns:
            bytes: Compressed image or None
        """

        if not image_bytes:
            return None

        target_size_bytes = target_size_kb * 1024

        # If already smaller, return as is
        if len(image_bytes) <= target_size_bytes:
            return image_bytes

        try:
            image = Image.open(io.BytesIO(image_bytes))

            # Convert to RGB
            if image.mode != 'RGB':
                image = image.convert('RGB')

            # Try different quality levels
            quality = ImageAnalyzer.DEFAULT_QUALITY

            while quality >= min_quality:
                output = io.BytesIO()
                image.save(
                    output,
                    format='JPEG',
                    quality=quality,
                    optimize=True
                )

                if output.tell() <= target_size_bytes:
                    output.seek(0)
                    return output.getvalue()

                quality -= 5

            # If still too large, resize
            scale = 0.9
            while scale > 0.3:
                new_width = int(image.width * scale)
                new_height = int(image.height * scale)

                resized = image.resize(
                    (new_width, new_height),
                    Image.Resampling.LANCZOS
                )

                output = io.BytesIO()
                resized.save(
                    output,
                    format='JPEG',
                    quality=min_quality,
                    optimize=True
                )

                if output.tell() <= target_size_bytes:
                    output.seek(0)
                    return output.getvalue()

                scale -= 0.1

            # Return best effort
            output.seek(0)
            return output.getvalue()

        except Exception as e:
            print(f"[COMPRESS ERROR] {str(e)}")
            return None


    # ============================================
    # GET IMAGE INFO
    # ============================================
    @staticmethod
    def get_image_info(image_bytes: bytes) -> Dict[str, Any]:
        """
        Extract metadata and information from an image.

        Args:
            image_bytes: Image binary data

        Returns:
            dict: Image information
        """

        if not image_bytes:
            return {}

        try:
            image = Image.open(io.BytesIO(image_bytes))

            info = {
                'format': image.format,
                'mode': image.mode,
                'width': image.width,
                'height': image.height,
                'size_bytes': len(image_bytes),
                'size_kb': round(len(image_bytes) / 1024, 2),
                'size_mb': round(len(image_bytes) / (1024 * 1024), 2),
                'aspect_ratio': round(image.width / image.height, 2) if image.height > 0 else 0,
                'megapixels': round((image.width * image.height) / 1000000, 2),
                'has_transparency': image.mode in ('RGBA', 'LA', 'P'),
                'is_animated': getattr(image, 'is_animated', False)
            }

            # Try to get EXIF data
            try:
                exif_data = image._getexif() if hasattr(image, '_getexif') else None

                if exif_data:
                    info['has_exif'] = True
                    info['exif_count'] = len(exif_data)
                else:
                    info['has_exif'] = False

            except Exception:
                info['has_exif'] = False

            # DPI information
            if 'dpi' in image.info:
                info['dpi'] = image.info['dpi']

            return info

        except Exception as e:
            print(f"[GET INFO ERROR] {str(e)}")
            return {
                'error': str(e),
                'size_bytes': len(image_bytes)
            }


    # ============================================
    # CONVERT FORMAT
    # ============================================
    @staticmethod
    def convert_format(
        image_bytes: bytes,
        target_format: str = 'JPEG',
        quality: int = 85
    ) -> Optional[bytes]:
        """
        Convert image to a different format.

        Args:
            image_bytes: Original image bytes
            target_format: Target format (JPEG, PNG, WEBP)
            quality: Quality for lossy formats

        Returns:
            bytes: Converted image or None
        """

        if not image_bytes:
            return None

        target_format = target_format.upper()

        if target_format not in ('JPEG', 'PNG', 'WEBP'):
            print(f"[CONVERT ERROR] Unsupported target format: {target_format}")
            return None

        try:
            image = Image.open(io.BytesIO(image_bytes))

            # Handle transparency for JPEG
            if target_format == 'JPEG' and image.mode in ('RGBA', 'LA', 'P'):
                background = Image.new('RGB', image.size, (255, 255, 255))

                if image.mode == 'P':
                    image = image.convert('RGBA')

                if image.mode in ('RGBA', 'LA'):
                    background.paste(image, mask=image.split()[-1])
                    image = background

            elif image.mode != 'RGB' and target_format == 'JPEG':
                image = image.convert('RGB')

            output = io.BytesIO()

            save_args = {'format': target_format, 'optimize': True}

            if target_format == 'JPEG':
                save_args['quality'] = quality
                save_args['progressive'] = True
            elif target_format == 'WEBP':
                save_args['quality'] = quality

            image.save(output, **save_args)
            output.seek(0)

            return output.getvalue()

        except Exception as e:
            print(f"[CONVERT FORMAT ERROR] {str(e)}")
            return None


    # ============================================
    # CREATE THUMBNAIL
    # ============================================
    @staticmethod
    def create_thumbnail(
        image_bytes: bytes,
        size: int = 200,
        quality: int = 85
    ) -> Optional[bytes]:
        """
        Create a thumbnail from an image.

        Args:
            image_bytes: Original image bytes
            size: Thumbnail size (square)
            quality: JPEG quality

        Returns:
            bytes: Thumbnail bytes or None
        """

        if not image_bytes:
            return None

        try:
            image = Image.open(io.BytesIO(image_bytes))

            # Convert to RGB
            if image.mode != 'RGB':
                if image.mode in ('RGBA', 'LA', 'P'):
                    background = Image.new('RGB', image.size, (255, 255, 255))

                    if image.mode == 'P':
                        image = image.convert('RGBA')

                    if image.mode in ('RGBA', 'LA'):
                        background.paste(image, mask=image.split()[-1])
                        image = background
                    else:
                        image = image.convert('RGB')
                else:
                    image = image.convert('RGB')

            # Create thumbnail
            image.thumbnail((size, size), Image.Resampling.LANCZOS)

            # Save
            output = io.BytesIO()
            image.save(
                output,
                format='JPEG',
                quality=quality,
                optimize=True
            )

            output.seek(0)
            return output.getvalue()

        except Exception as e:
            print(f"[THUMBNAIL ERROR] {str(e)}")
            return None


    # ============================================
    # CROP IMAGE
    # ============================================
    @staticmethod
    def crop_image(
        image_bytes: bytes,
        left: int,
        top: int,
        right: int,
        bottom: int
    ) -> Optional[bytes]:
        """
        Crop an image to specified dimensions.

        Args:
            image_bytes: Original image bytes
            left: Left coordinate
            top: Top coordinate
            right: Right coordinate
            bottom: Bottom coordinate

        Returns:
            bytes: Cropped image or None
        """

        if not image_bytes:
            return None

        try:
            image = Image.open(io.BytesIO(image_bytes))

            # Validate crop coordinates
            if left < 0 or top < 0:
                return None

            if right > image.width or bottom > image.height:
                return None

            if left >= right or top >= bottom:
                return None

            # Crop
            cropped = image.crop((left, top, right, bottom))

            # Convert to RGB if needed
            if cropped.mode != 'RGB':
                cropped = cropped.convert('RGB')

            output = io.BytesIO()
            cropped.save(
                output,
                format='JPEG',
                quality=ImageAnalyzer.DEFAULT_QUALITY,
                optimize=True
            )

            output.seek(0)
            return output.getvalue()

        except Exception as e:
            print(f"[CROP ERROR] {str(e)}")
            return None


    # ============================================
    # ROTATE IMAGE
    # ============================================
    @staticmethod
    def rotate_image(
        image_bytes: bytes,
        degrees: int = 90
    ) -> Optional[bytes]:
        """
        Rotate an image by specified degrees.

        Args:
            image_bytes: Original image bytes
            degrees: Rotation angle (90, 180, 270)

        Returns:
            bytes: Rotated image or None
        """

        if not image_bytes:
            return None

        valid_degrees = [0, 90, 180, 270, -90, -180, -270]
        if degrees not in valid_degrees:
            print(f"[ROTATE ERROR] Invalid degrees: {degrees}")
            return None

        try:
            image = Image.open(io.BytesIO(image_bytes))

            # Rotate
            if degrees != 0:
                rotated = image.rotate(-degrees, expand=True)
            else:
                rotated = image

            # Convert to RGB if needed
            if rotated.mode != 'RGB':
                rotated = rotated.convert('RGB')

            output = io.BytesIO()
            rotated.save(
                output,
                format='JPEG',
                quality=ImageAnalyzer.DEFAULT_QUALITY,
                optimize=True
            )

            output.seek(0)
            return output.getvalue()

        except Exception as e:
            print(f"[ROTATE ERROR] {str(e)}")
            return None


    # ============================================
    # FLIP IMAGE
    # ============================================
    @staticmethod
    def flip_image(
        image_bytes: bytes,
        horizontal: bool = True
    ) -> Optional[bytes]:
        """
        Flip an image horizontally or vertically.

        Args:
            image_bytes: Original image bytes
            horizontal: True for horizontal flip, False for vertical

        Returns:
            bytes: Flipped image or None
        """

        if not image_bytes:
            return None

        try:
            image = Image.open(io.BytesIO(image_bytes))

            if horizontal:
                flipped = image.transpose(Image.FLIP_LEFT_RIGHT)
            else:
                flipped = image.transpose(Image.FLIP_TOP_BOTTOM)

            if flipped.mode != 'RGB':
                flipped = flipped.convert('RGB')

            output = io.BytesIO()
            flipped.save(
                output,
                format='JPEG',
                quality=ImageAnalyzer.DEFAULT_QUALITY,
                optimize=True
            )

            output.seek(0)
            return output.getvalue()

        except Exception as e:
            print(f"[FLIP ERROR] {str(e)}")
            return None


    # ============================================
    # CHECK IMAGE QUALITY
    # ============================================
    @staticmethod
    def check_image_quality(image_bytes: bytes) -> Dict[str, Any]:
        """
        Check the quality of an image for medical analysis.

        Args:
            image_bytes: Image binary data

        Returns:
            dict: Quality assessment
        """

        if not image_bytes:
            return {
                'is_suitable': False,
                'score': 0,
                'issues': ['No image data']
            }

        issues = []
        score = 100

        try:
            image = Image.open(io.BytesIO(image_bytes))

            # Check size
            file_size_kb = len(image_bytes) / 1024

            if file_size_kb < 10:
                issues.append('Image file is very small (under 10KB)')
                score -= 20

            # Check dimensions
            if image.width < 200 or image.height < 200:
                issues.append('Image resolution is too low')
                score -= 30

            if image.width < 500 and image.height < 500:
                issues.append('Image resolution may be insufficient for detailed analysis')
                score -= 10

            # Check aspect ratio
            aspect_ratio = image.width / image.height if image.height > 0 else 0

            if aspect_ratio > 3 or aspect_ratio < 0.33:
                issues.append('Unusual aspect ratio detected')
                score -= 5

            # Check format
            if image.format and image.format.upper() not in ('JPEG', 'PNG', 'WEBP'):
                issues.append(f'Suboptimal format: {image.format}')
                score -= 10

            score = max(0, score)

            return {
                'is_suitable': score >= 50,
                'score': score,
                'quality_level': ImageAnalyzer.get_quality_level(score),
                'issues': issues if issues else ['No major issues detected'],
                'recommendations': ImageAnalyzer.get_quality_recommendations(score, issues)
            }

        except Exception as e:
            return {
                'is_suitable': False,
                'score': 0,
                'issues': [f'Quality check failed: {str(e)}']
            }


    # ============================================
    # GET QUALITY LEVEL
    # ============================================
    @staticmethod
    def get_quality_level(score: int) -> str:
        """Get quality level description from score"""

        if score >= 90:
            return 'excellent'
        elif score >= 75:
            return 'good'
        elif score >= 50:
            return 'fair'
        elif score >= 30:
            return 'poor'
        else:
            return 'very_poor'


    # ============================================
    # GET QUALITY RECOMMENDATIONS
    # ============================================
    @staticmethod
    def get_quality_recommendations(
        score: int,
        issues: list
    ) -> list:
        """Get recommendations based on quality issues"""

        recommendations = []

        if score < 50:
            recommendations.append('Consider taking a new photo with better quality')

        if any('resolution' in issue.lower() for issue in issues):
            recommendations.append('Use higher resolution camera settings')

        if any('small' in issue.lower() for issue in issues):
            recommendations.append('Take photo at closer distance for more detail')

        if any('format' in issue.lower() for issue in issues):
            recommendations.append('Save as JPEG or PNG for best compatibility')

        recommendations.extend([
            'Use good lighting (natural daylight preferred)',
            'Hold camera steady to avoid blur',
            'Focus directly on the affected area',
            'Use a neutral background'
        ])

        return recommendations[:5]


    # ============================================
    # BATCH PROCESS IMAGES
    # ============================================
    @staticmethod
    def batch_process(
        images: list,
        max_width: int = None,
        max_height: int = None,
        quality: int = None
    ) -> list:
        """
        Process multiple images in batch.

        Args:
            images: List of image bytes
            max_width: Max width for all
            max_height: Max height for all
            quality: Quality for all

        Returns:
            list: List of processed image dicts
        """

        results = []

        for index, image_bytes in enumerate(images):
            try:
                processed = ImageAnalyzer.process_image(
                    image_bytes,
                    max_width=max_width,
                    max_height=max_height,
                    quality=quality
                )

                if processed:
                    results.append({
                        'index': index,
                        'success': True,
                        'data': processed,
                        'original_size': len(image_bytes),
                        'processed_size': len(processed)
                    })
                else:
                    results.append({
                        'index': index,
                        'success': False,
                        'error': 'Processing failed'
                    })

            except Exception as e:
                results.append({
                    'index': index,
                    'success': False,
                    'error': str(e)
                })

        return results