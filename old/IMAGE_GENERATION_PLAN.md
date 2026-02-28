# Image Generation Implementation Plan

## Current State

**Problem**: The `AssetGenerator` class currently returns placeholder URLs (`https://placeholder.com/...`) instead of generating actual images. This causes broken visualizations in the game.

**Current Code Location**: `backend/app/services/pipeline/layer4_generation.py` - `AssetGenerator.generate_assets()`

## Solution Options

### Option 1: OpenAI DALL-E 3 (Recommended)
**Pros:**
- High quality images
- Already have OpenAI client setup in `LLMService`
- Simple API integration
- Good for educational/diagram-style images

**Cons:**
- Costs per image (~$0.04/image for DALL-E 3)
- Rate limits apply
- Requires `OPENAI_API_KEY`

**Implementation:**
- Use existing `openai` client from `LLMService`
- Call `openai.images.generate()` with prompt
- Download image and store locally or upload to CDN
- Return permanent URL

### Option 2: Anthropic Image Generation (if available)
**Pros:**
- Consistent with existing Anthropic usage
- May have better prompt understanding

**Cons:**
- Anthropic doesn't currently offer image generation API
- Would need to use third-party service

### Option 3: Stable Diffusion API (Replicate, Stability AI, etc.)
**Pros:**
- Lower cost options available
- Good for technical diagrams
- Multiple providers (Replicate, Stability AI, Hugging Face)

**Cons:**
- Additional API key needed
- Quality may vary
- More complex integration

### Option 4: Hybrid Approach
- Use DALL-E 3 for high-quality educational images
- Fallback to cheaper service for simple diagrams
- Cache generated images to reduce API calls

## Recommended Implementation: OpenAI DALL-E 3

### Architecture

```
AssetGenerator.generate_assets()
  ↓
ImageGenerationService.generate_image(prompt)
  ↓
1. Call OpenAI DALL-E 3 API
2. Download generated image
3. Store image (local filesystem or cloud storage)
4. Return permanent URL
```

### Storage Strategy

**Option A: Local Filesystem** (Simple, good for development)
- Store in `backend/static/generated_images/`
- Serve via FastAPI static file serving
- URL: `http://localhost:8000/static/generated_images/{image_id}.png`

**Option B: Cloud Storage** (Production-ready)
- Upload to S3, Cloudinary, or similar
- Return CDN URL
- Better for scalability

**Option C: Database Storage** (Not recommended)
- Store base64 in database
- Inefficient for large images

### Implementation Steps

1. **Create ImageGenerationService**
   - Location: `backend/app/services/image_generation_service.py`
   - Methods:
     - `generate_image(prompt: str, size: str = "1024x1024") -> str` (returns URL)
     - `_download_image(url: str) -> bytes`
     - `_store_image(image_data: bytes, image_id: str) -> str` (returns storage URL)

2. **Update AssetGenerator**
   - Replace placeholder logic with actual image generation
   - Use `ImageGenerationService` to generate images
   - Handle errors gracefully (fallback to placeholder if generation fails)

3. **Add Image Storage**
   - Create `backend/static/generated_images/` directory
   - Add FastAPI static file route
   - Generate unique image IDs (UUID-based)

4. **Error Handling**
   - Retry logic for API failures
   - Fallback to placeholder if generation fails
   - Log all generation attempts

5. **Caching Strategy**
   - Cache generated images by prompt hash
   - Avoid regenerating same images
   - Store cache metadata in database

### Code Structure

```python
# backend/app/services/image_generation_service.py
class ImageGenerationService:
    def __init__(self):
        self.openai_client = openai.OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        self.storage_path = Path("backend/static/generated_images")
        self.storage_path.mkdir(parents=True, exist_ok=True)
    
    def generate_image(self, prompt: str, size: str = "1024x1024") -> str:
        """Generate image and return URL"""
        # 1. Check cache first
        # 2. Call DALL-E 3 API
        # 3. Download image
        # 4. Store locally
        # 5. Return URL
        pass
```

### Environment Variables

Add to `.env`:
```
OPENAI_API_KEY=your_key_here
IMAGE_GENERATION_ENABLED=true
IMAGE_STORAGE_PATH=backend/static/generated_images
IMAGE_CACHE_ENABLED=true
```

### API Integration Details

**DALL-E 3 API Call:**
```python
response = openai_client.images.generate(
    model="dall-e-3",
    prompt=prompt,
    size=size,  # "1024x1024", "1792x1024", or "1024x1792"
    quality="standard",  # or "hd" for higher quality
    n=1
)
image_url = response.data[0].url
```

### Cost Considerations

- DALL-E 3: ~$0.04 per image (standard), ~$0.08 (HD)
- For 10 images per game: ~$0.40 per game
- Caching can significantly reduce costs

### Error Handling

```python
try:
    image_url = self.generate_image(prompt)
except OpenAIError as e:
    logger.error(f"Image generation failed: {e}")
    # Fallback to placeholder
    return placeholder_url
except Exception as e:
    logger.error(f"Unexpected error in image generation: {e}")
    return placeholder_url
```

### Testing Strategy

1. Unit tests for ImageGenerationService
2. Mock OpenAI API responses
3. Test error handling and fallbacks
4. Test image storage and URL generation
5. Integration test with actual API (optional)

### Migration Path

1. **Phase 1**: Implement basic DALL-E 3 integration
2. **Phase 2**: Add caching to reduce API calls
3. **Phase 3**: Add cloud storage for production
4. **Phase 4**: Add fallback providers (if needed)

### Files to Create/Modify

1. **New**: `backend/app/services/image_generation_service.py`
2. **Modify**: `backend/app/services/pipeline/layer4_generation.py` (AssetGenerator)
3. **Modify**: `backend/app/main.py` (add static file serving)
4. **New**: `backend/static/generated_images/` (directory)
5. **Modify**: `.env.example` (add image generation config)

### Next Steps

1. ✅ Review plan
2. Implement ImageGenerationService
3. Update AssetGenerator to use real image generation
4. Add static file serving for images
5. Test with sample prompts
6. Add error handling and fallbacks
7. Add caching mechanism
8. Update documentation


