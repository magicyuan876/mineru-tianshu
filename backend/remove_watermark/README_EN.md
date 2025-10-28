# 🎨 Watermark Removal Module

Intelligent watermark detection and removal system based on YOLO11x + LaMa.

> **⚠️ Experimental Feature**: This module is currently experimental. Results depend on watermark type and image quality.

## 📋 Table of Contents

- [Technical Solution](#-technical-solution)
- [Quick Start](#-quick-start)
- [Optimization Guide](#-optimization-guide)
- [Supported Formats](#-supported-formats)
- [API Usage](#-api-usage)
- [FAQ](#-faq)

---

## 🔧 Technical Solution

### Core Technology Stack

```
Image Watermark Removal Pipeline:
Input Image
  ↓
YOLO11x Detect Watermark Location (Specialized Model)
  ↓
Generate Watermark Mask + Dilation
  ↓
LaMa Deep Learning Inpainting (or OpenCV Fallback)
  ↓
Output Clean Image

PDF Processing Pipeline:
Input PDF
  ↓
Auto-detect Type
  ↓
  ├─ Editable PDF → PyMuPDF Remove Watermark Objects
  └─ Scanned PDF → Convert to Images → Remove Watermarks → Reassemble PDF
```

### Key Components

| Component | Description | Advantages |
|-----------|-------------|-----------|
| **YOLO11x** | Specialized detection model trained on watermark datasets | High precision watermark location and boundary detection |
| **LaMa** | Large Mask Inpainting deep learning repair model | Natural filling of large watermark areas |
| **PyMuPDF** | PDF processing library | Watermark object removal for editable PDFs |
| **OpenCV** | Computer vision library | Fallback solution (when LaMa unavailable) |

---

## 🚀 Quick Start

### 1. Install Dependencies

All dependencies are integrated into the main project:

```bash
cd backend
pip install -r requirements.txt
```

### 2. Use via Web Interface

1. Start the service (refer to main project README)
2. Open the web interface, submit task
3. Check **"Enable Watermark Removal"** in the submission form
4. Optional: Adjust detection parameters

### 3. First Run

First run will automatically download the YOLO11x model (~200MB) from HuggingFace. Ensure network connection.

Model cache location: `~/.cache/watermark_models/`

---

## 💡 Optimization Guide

### Which Watermarks Work Best?

✅ **Recommended Use Cases**:

- Regular text/logo watermarks (e.g., "Copyright", company logos)
- Fixed position, medium contrast watermarks
- Watermarks with clear distinction from background
- Good image quality with moderate resolution

❌ **May Not Work Well**:

- Large-area background watermarks (covering entire image)
- Semi-transparent, low-contrast watermarks
- Artistic watermarks deeply integrated with content
- Very low resolution or severely distorted images

### Parameter Tuning Recommendations

#### 1. **Detection Confidence Threshold**

**Default: 0.35**

- **Lower (0.2-0.3)**:
  - ✅ Suitable for: Unclear, semi-transparent, low-contrast watermarks
  - ⚠️ Risk: May falsely detect normal content

- **Higher (0.4-0.5)**:
  - ✅ Suitable for: Clear watermarks, avoid false detection
  - ⚠️ Risk: May miss some watermarks

#### 2. **Removal Range Extension (Dilation)**

**Default: 10 pixels**

- **Smaller (0-5)**:
  - ✅ Suitable for: Precise watermark boundaries, concerned about affecting surrounding content
  - ⚠️ Risk: May leave watermark edge residue

- **Larger (15-30)**:
  - ✅ Suitable for: Blurred watermark edges with ghosting
  - ⚠️ Risk: May remove too much normal content

### Real-World Cases

#### Case 1: Clear Logo Watermark

```yaml
Scenario: Company logo in image corner
Recommended Parameters:
  - Confidence: 0.35 (default)
  - Dilation: 10 (default)
Effect: ⭐⭐⭐⭐⭐
```

#### Case 2: Semi-Transparent Text Watermark

```yaml
Scenario: Semi-transparent "Sample" text in image center
Recommended Parameters:
  - Confidence: 0.25 (lower)
  - Dilation: 15 (increase)
Effect: ⭐⭐⭐⭐
```

#### Case 3: Large-Area Background Watermark

```yaml
Scenario: Entire image covered with diagonally repeated watermarks
Recommended Parameters:
  - Confidence: 0.3
  - Dilation: 20
Effect: ⭐⭐⭐ (depends on watermark complexity)
Note: This type is most unstable
```

### How to Get Better Results?

#### Option 1: Use Custom YOLO Model (Recommended)

If default model doesn't work well, train your own YOLO model:

1. **Collect Data**: Prepare training dataset
   - Dataset size depends on watermark type complexity and diversity
   - Refer to Ultralytics YOLO official documentation for dataset requirements
   - Data should cover different scenarios, angles, lighting conditions for better generalization

2. **Annotate Watermarks**: Use tools like LabelImg, Roboflow to annotate watermark positions
   - Bounding boxes should accurately fit watermark regions
   - Prepare dataset in YOLO format (train/val/test splits)

3. **Train Model**: Use Ultralytics YOLO framework for training
   - Recommend starting with pre-trained weights (e.g., yolo11x.pt) for fine-tuning
   - Adjust training parameters based on validation performance
   - Detailed tutorial: <https://docs.ultralytics.com/>

4. **Replace Model**: Replace trained model in cache directory

```python
from watermark_remover import WatermarkRemover

# Use custom model
remover = WatermarkRemover(
    model_path="/path/to/your/custom_model.pt",
    device="cuda",
    use_lama=True
)
```

#### Option 2: Batch Test to Find Best Parameters

```python
import itertools

# Parameter combinations
confidences = [0.25, 0.30, 0.35, 0.40]
dilations = [5, 10, 15, 20]

# Batch test
for conf, dil in itertools.product(confidences, dilations):
    result = remover.remove_watermark(
        image_path="test.jpg",
        output_path=f"result_c{conf}_d{dil}.jpg",
        conf_threshold=conf,
        dilation=dil
    )
```

#### Option 3: Check Debug Files

Debug files are automatically saved with each processing:

```
watermark_removed/
├── detection_*.jpg  # Check if detection boxes are accurate
├── mask_*.jpg       # Check if mask range is appropriate
└── clean_*.jpg      # Final result
```

**Debug Steps**:

1. Check `detection_*.jpg` to verify all watermarks are detected
2. If missed → Lower confidence
3. If false detection → Raise confidence
4. Check `mask_*.jpg` to verify removal range is appropriate
5. If residue remains → Increase dilation
6. If too much removed → Decrease dilation

---

## 📄 Supported Formats

### Image Formats

| Format | Support | Notes |
|--------|---------|-------|
| PNG | ✅ | Recommended, lossless format |
| JPG/JPEG | ✅ | Common format |
| BMP | ✅ | Bitmap format |
| TIFF | ✅ | High quality format |
| WebP | ✅ | Modern format |

### PDF Formats

| Type | Processing Method | Effect |
|------|------------------|--------|
| Editable PDF | PyMuPDF remove watermark objects | ⭐⭐⭐⭐ |
| Scanned PDF | Convert to images → Remove watermarks → Reassemble | ⭐⭐⭐ |

---

## 🔌 API Usage

### Python API

```python
from remove_watermark import WatermarkRemover

# Initialize
remover = WatermarkRemover(
    device="cuda",        # Use GPU (or "cpu")
    use_lama=True        # Use LaMa inpainting
)

# Remove image watermark
result = remover.remove_watermark(
    image_path="input.png",
    output_path="output.png",
    conf_threshold=0.35,  # Detection confidence
    dilation=10          # Mask dilation
)

# Cleanup resources
remover.cleanup()
```

### REST API

Use via main project's Web API:

```bash
curl -X POST http://localhost:8000/api/v1/tasks/submit \
  -F 'file=@image.png' \
  -F 'backend=paddleocr-vl' \
  -F 'remove_watermark=true' \
  -F 'watermark_conf_threshold=0.35' \
  -F 'watermark_dilation=10'
```

---

## ❓ FAQ

### Q1: Why can't watermarks be detected?

**Possible Reasons**:

1. Confidence threshold too high → Lower to 0.25-0.30
2. Watermark type not in training data → Consider training custom model
3. Watermark too blurry or transparent → Check original image quality

**Solution**: Check `detection_*.jpg` file to confirm detection boxes

### Q2: Why are there residues after removal?

**Possible Reasons**:

1. Dilation value too small → Increase to 15-20
2. Watermark edges blurry → Increase dilation value
3. Complex watermark → May need multiple passes

**Solution**: Check `mask_*.jpg` file to confirm mask coverage is complete

### Q3: Why was normal content also removed?

**Possible Reasons**:

1. Confidence too low causing false detection → Raise to 0.4-0.5
2. Dilation value too large → Reduce to 5-10
3. Normal content similar to watermark → Need more precise model

**Solution**: Check `detection_*.jpg` and `mask_*.jpg` to adjust parameters

### Q4: First run is very slow?

**Reason**: First run needs to download YOLO11x model (~200MB)

**Solution**:

- Ensure network connection is normal
- Users in China may need to configure proxy
- Model is cached locally, subsequent runs start instantly

### Q5: GPU memory insufficient?

**Solution**:

```python
# Use CPU
remover = WatermarkRemover(device="cpu", use_lama=True)

# Or don't use LaMa (more memory efficient)
remover = WatermarkRemover(device="cuda", use_lama=False)
```

### Q6: Large-area background watermarks don't work well?

**Explanation**: Large-area background watermarks are the most difficult to handle because:

- Watermarks cover wide area, repair region is large
- Easily damage original image structure
- YOLO may not detect completely

**Suggestions**:

- In this case, traditional image processing methods may work better
- Consider using other specialized tools
- Or accept partial residue and manually post-process

---

## 📚 Technical References

- **YOLO11x**: [Ultralytics YOLO](https://github.com/ultralytics/ultralytics)
- **LaMa**: [Resolution-robust Large Mask Inpainting](https://arxiv.org/abs/2109.07161)
- **PyMuPDF**: [PDF Processing Library](https://pymupdf.readthedocs.io/)

---

## 🎯 Summary

### ✅ Advantages

- Automatic detection, no manual watermark position annotation needed
- Deep learning repair with natural results
- Support for multiple image and PDF formats
- GPU acceleration for fast processing
- Adjustable parameters for different scenarios

### ⚠️ Limitations

- Effect depends on watermark type and image quality
- Limited effectiveness for large-area background watermarks
- First run requires model download
- Some special watermarks may require custom models

### 🚀 Best Practices

1. **Test First**: Test on small sample set
2. **Tune Parameters**: Adjust parameters based on detection visualization
3. **Check Debug**: Use debug files to analyze issues
4. **Train Model**: Consider custom model when effect is poor

---

**Need Help?** Check main project [README](../../README_EN.md) or submit an Issue.
