from __future__ import annotations

from pathlib import Path

import imageio.v2 as imageio
from PIL import Image, ImageDraw, ImageFont, ImageOps


ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "reports" / "media" / "teacher_recovery_route_evidence"
FIG_DIR = ROOT / "reports" / "figures" / "failure_aware_vppv"
FPS = 8


def load_font(size: int, bold: bool = False):
    names = ["arialbd.ttf", "DejaVuSans-Bold.ttf"] if bold else ["arial.ttf", "DejaVuSans.ttf"]
    for name in names:
        try:
            return ImageFont.truetype(name, size)
        except OSError:
            pass
    return ImageFont.load_default()


FONT_TITLE = load_font(34, bold=True)
FONT_SUBTITLE = load_font(22)
FONT_H2 = load_font(22, bold=True)
FONT_BODY = load_font(17)
FONT_SMALL = load_font(14)


def wrap(draw: ImageDraw.ImageDraw, text: str, font, width: int) -> list[str]:
    words = text.split()
    lines: list[str] = []
    current = ""
    for word in words:
        candidate = f"{current} {word}".strip()
        if draw.textbbox((0, 0), candidate, font=font)[2] <= width:
            current = candidate
        else:
            if current:
                lines.append(current)
            current = word
    if current:
        lines.append(current)
    return lines


def draw_wrapped(
    draw: ImageDraw.ImageDraw,
    xy: tuple[int, int],
    text: str,
    font,
    fill: tuple[int, int, int],
    width: int,
    line_gap: int = 6,
) -> int:
    x, y = xy
    for line in wrap(draw, text, font, width):
        draw.text((x, y), line, font=font, fill=fill)
        y += font.size + line_gap
    return y


def thumb(path: Path, size: tuple[int, int]) -> Image.Image:
    if not path.exists():
        image = Image.new("RGB", size, (236, 238, 240))
        draw = ImageDraw.Draw(image)
        draw.text((16, 16), f"Missing:\n{path.name}", font=FONT_SMALL, fill=(90, 90, 90))
        return image
    image = Image.open(path).convert("RGB")
    image = ImageOps.contain(image, size)
    canvas = Image.new("RGB", size, (248, 248, 248))
    canvas.paste(image, ((size[0] - image.width) // 2, (size[1] - image.height) // 2))
    return canvas


def draw_card(
    canvas: Image.Image,
    top: int,
    accent: tuple[int, int, int],
    mechanism: str,
    failure: str,
    evidence: str,
    route: str,
    result: str,
    image_path: Path,
) -> None:
    draw = ImageDraw.Draw(canvas)
    x = 42
    y = top
    w = canvas.width - 84
    h = 248
    draw.rounded_rectangle((x, y, x + w, y + h), radius=14, fill=(255, 255, 255), outline=(210, 214, 220), width=2)
    draw.rounded_rectangle((x, y, x + 12, y + h), radius=8, fill=accent)
    draw.text((x + 28, y + 20), mechanism, font=FONT_H2, fill=(28, 34, 42))

    labels = [
        ("Failure", failure),
        ("Evidence", evidence),
        ("Route", route),
        ("Result", result),
    ]
    text_x = x + 28
    text_y = y + 60
    for label, value in labels:
        draw.text((text_x, text_y), f"{label}:", font=FONT_SMALL, fill=accent)
        text_y = draw_wrapped(draw, (text_x + 112, text_y - 2), value, FONT_SMALL, (45, 50, 58), 535, line_gap=2)
        text_y += 7

    image = thumb(image_path, (345, 194))
    ix = x + w - 372
    iy = y + 28
    draw.rounded_rectangle((ix - 8, iy - 8, ix + 353, iy + 202), radius=10, fill=(245, 246, 248), outline=(226, 228, 232))
    canvas.paste(image, (ix, iy))


def build_storyboard() -> Image.Image:
    canvas = Image.new("RGB", (1280, 1380), (244, 246, 248))
    draw = ImageDraw.Draw(canvas)
    draw.text((42, 32), "Recovery Route Evidence For Surgical Robot Learning", font=FONT_TITLE, fill=(24, 30, 38))
    draw.text(
        (44, 78),
        "What fails, what evidence is used, which route is selected, and what the current simulator evidence proves.",
        font=FONT_SUBTITLE,
        fill=(80, 86, 96),
    )

    cards = [
        {
            "accent": (65, 111, 171),
            "mechanism": "1. Visual / depth / regressor bias",
            "failure": "The estimated target is shifted, so the tool can move correctly toward the wrong state.",
            "evidence": "visual residual, depth-scale proxy, target disagreement, local neighborhood conflict.",
            "route": "re-observe / re-estimate before continuing.",
            "result": "CircleRL gives a closed proxy rollout; true mixed SurRoL tables show review/re-estimate restores success in smoke-scale scripted-oracle runs.",
            "image_path": ROOT / "reports" / "media" / "circlerl_recovery_demo" / "frames" / "step_034_recovery_trigger.png",
        },
        {
            "accent": (58, 141, 96),
            "mechanism": "2. Approach-policy drift",
            "failure": "The approach movement enters a wrong near-target region or progress stalls despite plausible commands.",
            "evidence": "action-outcome mismatch, progress loss, atypical behavior embedding, replan signal.",
            "route": "low-gain corrective movement / replan.",
            "result": "Evidence is strongest in route tables, phase-aware curves, and behavior-derived routing; this route still needs a cleaner teacher-facing video.",
            "image_path": ROOT / "reports" / "figures" / "surrol_phase_aware" / "representative_distance_curves.png",
        },
        {
            "accent": (176, 113, 55),
            "mechanism": "3. Near-target occlusion or servo failure",
            "failure": "Near the target, visual/contact evidence becomes unreliable, so blind continuation is risky.",
            "evidence": "near-target flag, repeated commands without progress, handoff evidence, high-risk neighborhood.",
            "route": "pause, camera reposition, servo reset, or human review.",
            "result": "Supported by mechanism-router evidence and severity/holdout analysis; it is framed as review logic, not autonomous surgical deployment.",
            "image_path": FIG_DIR / "failure_aware_vppv_severity_holdout_routes.png",
        },
        {
            "accent": (143, 78, 155),
            "mechanism": "4. Mixed-fault routed recovery in SurRoL",
            "failure": "Visual/depth/near-target faults are injected together; the un-routed perturbed controller fails.",
            "evidence": "priority route triggers, visual re-estimation signal, recovery override, distance and success table.",
            "route": "priority routing: unsafe/near-target risk, then re-estimate visual/depth state, then correct drift.",
            "result": "Actual SurRoL/PyBullet scripted-oracle smoke run: perturbed 0/40, priority-routed 40/40.",
            "image_path": ROOT / "reports" / "media" / "failure_aware_vppv_true_mixed_recovery" / "surrol_true_mixed_priority_routed_recovery_final.png",
        },
    ]
    top = 130
    for item in cards:
        draw_card(canvas, top, **item)
        top += 290

    draw.rounded_rectangle((42, 1294, 1238, 1344), radius=12, fill=(235, 240, 246), outline=(210, 216, 224))
    draw.text(
        (64, 1309),
        "Boundary: these are simulator-route evidence assets. The recovery policies are scripted/proxy/oracle components, not a private learned surgical-policy checkpoint.",
        font=FONT_SMALL,
        fill=(62, 70, 82),
    )
    return canvas


def build_gif(storyboard: Image.Image) -> list[Image.Image]:
    slides: list[Image.Image] = []
    crop_boxes = [
        (0, 0, 1280, 430),
        (0, 330, 1280, 720),
        (0, 620, 1280, 1010),
        (0, 910, 1280, 1300),
        (0, 0, 1280, 1380),
    ]
    for box in crop_boxes:
        slide = storyboard.crop(box)
        slide = ImageOps.contain(slide, (960, 720))
        canvas = Image.new("RGB", (960, 720), (244, 246, 248))
        canvas.paste(slide, ((960 - slide.width) // 2, (720 - slide.height) // 2))
        slides.append(canvas)
    return slides


def resize_for_video(image: Image.Image, size: tuple[int, int] = (1280, 720)) -> Image.Image:
    image = ImageOps.contain(image.convert("RGB"), size)
    canvas = Image.new("RGB", size, (244, 246, 248))
    canvas.paste(image, ((size[0] - image.width) // 2, (size[1] - image.height) // 2))
    return canvas


def make_title_slide(title: str, body: str, accent: tuple[int, int, int]) -> Image.Image:
    slide = Image.new("RGB", (1280, 720), (244, 246, 248))
    draw = ImageDraw.Draw(slide)
    draw.rounded_rectangle((58, 70, 1222, 650), radius=22, fill=(255, 255, 255), outline=(210, 216, 224), width=2)
    draw.rectangle((58, 70, 76, 650), fill=accent)
    draw.text((112, 118), title, font=FONT_TITLE, fill=(24, 30, 38))
    draw_wrapped(draw, (114, 184), body, FONT_SUBTITLE, (65, 72, 84), 980, line_gap=10)
    return slide


def annotate_video_frame(frame: Image.Image, title: str, subtitle: str, accent: tuple[int, int, int]) -> Image.Image:
    image = resize_for_video(frame)
    draw = ImageDraw.Draw(image, "RGBA")
    draw.rectangle((0, 0, 1280, 104), fill=(0, 0, 0, 165))
    draw.rectangle((0, 0, 18, 104), fill=accent + (255,))
    draw.text((42, 16), title, font=FONT_H2, fill=(255, 255, 255))
    draw.text((42, 56), subtitle, font=FONT_BODY, fill=(235, 238, 242))
    return image


def sample_video(path: Path, title: str, subtitle: str, accent: tuple[int, int, int], max_frames: int = 72) -> list[Image.Image]:
    if not path.exists():
        return [make_title_slide(title, f"Missing video asset: {path.name}", accent)] * (FPS * 2)
    reader = imageio.get_reader(path)
    frames: list[Image.Image] = []
    try:
        for idx, frame in enumerate(reader):
            if idx % 3 != 0:
                continue
            frames.append(annotate_video_frame(Image.fromarray(frame).convert("RGB"), title, subtitle, accent))
            if len(frames) >= max_frames:
                break
    finally:
        reader.close()
    return frames or [make_title_slide(title, f"No readable frames in: {path.name}", accent)] * (FPS * 2)


def build_demo_video(storyboard: Image.Image) -> list[Image.Image]:
    frames: list[Image.Image] = []

    def hold(slide: Image.Image, seconds: float) -> None:
        frames.extend([resize_for_video(slide)] * int(seconds * FPS))

    hold(
        make_title_slide(
            "Teacher Demo: Recovery Routes",
            "This video is the teacher-facing entry point. It shows the recovery-route logic first, then links it to actual simulator footage. The recovery policies are scripted/proxy/oracle components, not a private learned surgical-policy checkpoint.",
            (65, 111, 171),
        ),
        3.5,
    )
    hold(storyboard.crop((0, 0, 1280, 430)), 3.0)
    frames.extend(
        sample_video(
            ROOT / "reports" / "media" / "circlerl_recovery_demo" / "circlerl_bias_recovery.mp4",
            "Route 1: visual/depth/regressor bias",
            "Biased target estimate causes drift; monitor recovery re-estimates the target and routes control back.",
            (65, 111, 171),
            max_frames=80,
        )
    )
    hold(storyboard.crop((0, 330, 1280, 720)), 3.0)
    hold(storyboard.crop((0, 620, 1280, 1010)), 3.0)
    frames.extend(
        sample_video(
            ROOT
            / "reports"
            / "media"
            / "failure_aware_vppv_true_mixed_recovery"
            / "surrol_true_mixed_priority_routed_recovery_slow.mp4",
            "Route 4: mixed-fault routed recovery in SurRoL",
            "Priority routing triggers re-estimation/recovery override in PyBullet; perturbed fails, routed succeeds in the smoke run.",
            (143, 78, 155),
            max_frames=96,
        )
    )
    hold(storyboard.crop((0, 0, 1280, 1380)), 4.0)
    hold(
        make_title_slide(
            "What this video proves",
            "It proves that the project has a visible simulator recovery-route demonstration and a traceable mechanism-to-route story. It does not prove autonomous recovery by a private learned surgical policy.",
            (70, 120, 90),
        ),
        3.5,
    )
    return [resize_for_video(frame) for frame in frames]


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    storyboard = build_storyboard()
    png_path = OUT_DIR / "teacher_recovery_route_storyboard.png"
    gif_path = OUT_DIR / "teacher_recovery_route_storyboard.gif"
    mp4_path = OUT_DIR / "teacher_recovery_route_demo.mp4"
    readme_path = OUT_DIR / "README.md"
    storyboard.save(png_path)
    imageio.mimsave(gif_path, build_gif(storyboard), duration=2.2)
    imageio.mimsave(mp4_path, [frame for frame in build_demo_video(storyboard)], fps=FPS, quality=8, macro_block_size=16)
    readme_path.write_text(
        "\n".join(
            [
                "# Teacher Recovery Route Evidence",
                "",
                "This folder contains a teacher-facing storyboard for the recovery-route evidence.",
                "It explains what each mechanism means, which evidence signal is used, which route is selected, and what the current simulator evidence can and cannot prove.",
                "",
                "| Asset | File |",
                "| --- | --- |",
                "| Storyboard PNG | [teacher_recovery_route_storyboard.png](teacher_recovery_route_storyboard.png) |",
                "| Storyboard GIF | [teacher_recovery_route_storyboard.gif](teacher_recovery_route_storyboard.gif) |",
                "| Teacher demo MP4 | [teacher_recovery_route_demo.mp4](teacher_recovery_route_demo.mp4) |",
                "",
                "Important boundary: this is a teacher-facing demo assembled from existing simulator outputs. It includes actual CircleRL proxy recovery footage and SurRoL scripted-oracle routed recovery footage, but it is not a new end-to-end learned-policy video. Some route families are currently supported mainly by route tables, figures, and trace evidence.",
                "",
            ]
        ),
        encoding="utf-8",
    )
    print(f"png={png_path}")
    print(f"gif={gif_path}")
    print(f"mp4={mp4_path}")
    print(f"readme={readme_path}")


if __name__ == "__main__":
    main()
