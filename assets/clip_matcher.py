import cv2
import torch
import open_clip
from PIL import Image

_model = None
_preprocess = None
_tokenizer = None


def _load():
    global _model, _preprocess, _tokenizer
    if _model is None:
        _model, _, _preprocess = open_clip.create_model_and_transforms(
            "ViT-B-32-quickgelu", pretrained="openai"
        )
        _tokenizer = open_clip.get_tokenizer("ViT-B-32-quickgelu")
        _model.eval()
    return _model, _preprocess, _tokenizer


def _extract_frames(video_path: str, n: int = 3):
    cap = cv2.VideoCapture(video_path)
    total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    frames = []
    if total < 1:
        cap.release()
        return frames
    indices = [int(total * f) for f in (0.1, 0.5, 0.9)][:n]
    for idx in indices:
        cap.set(cv2.CAP_PROP_POS_FRAMES, idx)
        ret, frame = cap.read()
        if ret:
            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            frames.append(Image.fromarray(rgb))
    cap.release()
    return frames


def match_score(video_path: str, description: str) -> float:
    """Returns 0-1 semantic similarity between video frames and a text description."""
    model, preprocess, tokenizer = _load()
    frames = _extract_frames(video_path)
    if not frames:
        return 0.0

    with torch.no_grad():
        image_input = torch.stack([preprocess(f) for f in frames])
        image_features = model.encode_image(image_input)
        image_features /= image_features.norm(dim=-1, keepdim=True)
        avg_image_feature = image_features.mean(dim=0, keepdim=True)
        avg_image_feature /= avg_image_feature.norm(dim=-1, keepdim=True)

        text_input = tokenizer([description])
        text_features = model.encode_text(text_input)
        text_features /= text_features.norm(dim=-1, keepdim=True)

        cosine_sim = (avg_image_feature @ text_features.T).item()

    # Raw CLIP cosine similarity for genuine matches typically falls in ~0.15-0.35.
    # Rescale into a 0-1 usable score.
    score = (cosine_sim - 0.12) / (0.35 - 0.12)
    return max(0.0, min(1.0, score))


if __name__ == "__main__":
    import sys
    path, desc = sys.argv[1], sys.argv[2]
    print(f"match_score: {match_score(path, desc):.3f}")
