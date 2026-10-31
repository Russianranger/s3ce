#!/usr/bin/env python3
"""Read visible trait labels/checks from Android PNGs; never access game state."""
import argparse
import csv
import io
import json
from pathlib import Path
import re
import subprocess

from PIL import Image

TARGETS = ('Neat', 'Absent-Minded', 'Neurotic')


def normalized(text):
    return re.sub(r'[^a-z0-9]', '', text.lower())


def rectangle(viewport, box):
    left, top, right, bottom = viewport
    sx, sy = (right - left) / 1920, (bottom - top) / 1080
    return tuple(round(value) for value in (left + box[0] * sx, top + box[1] * sy,
                                            left + box[2] * sx, top + box[3] * sy))


def green_pixels(image, box):
    return sum(g > r + 20 and g > b + 20 and g > 90
               for r, g, b in image.crop(box).getdata())


def trait_status(image, viewport=None):
    viewport = viewport or (0, 0, *image.size)
    area_scale = ((viewport[2] - viewport[0]) / 1920) * ((viewport[3] - viewport[1]) / 1080)
    threshold = max(20, round(150 * area_scale))
    counts = [green_pixels(image, rectangle(viewport, (x - 35, 880, x + 35, 940)))
              for x in (1175, 1270, 1365, 1460, 1555)]
    next_pixels = green_pixels(image, rectangle(viewport, (1650, 900, 1800, 1050)))
    return {'bottom_green_pixels': counts, 'selected_count': sum(n > threshold for n in counts),
            'next_green_pixels': next_pixels, 'next_visible': next_pixels > 1500 * area_scale}


def analyze_traits(image_path, evidence_prefix=None, viewport=None):
    image = Image.open(image_path).convert('RGB')
    viewport = viewport or (0, 0, *image.size)
    crop_box = rectangle(viewport, (1250, 250, 1695, 855))
    crop = image.crop(crop_box)
    crop = crop.resize((crop.width * 2, crop.height * 2), Image.Resampling.LANCZOS)
    encoded = io.BytesIO()
    crop.save(encoded, format='PNG')
    run = subprocess.run(['tesseract', 'stdin', 'stdout', '--psm', '6', 'tsv'],
                         input=encoded.getvalue(), stdout=subprocess.PIPE,
                         stderr=subprocess.PIPE, timeout=30, check=True)
    tsv = run.stdout.decode(errors='replace')
    words = []
    for row in csv.DictReader(io.StringIO(tsv), delimiter='\t'):
        if row.get('level') != '5' or not row.get('text', '').strip():
            continue
        confidence = float(row['conf'])
        if confidence < 65:
            continue
        x, y, w, h = (float(row[key]) for key in ('left', 'top', 'width', 'height'))
        words.append({'text': row['text'], 'confidence': confidence,
                      'line': tuple(row[key] for key in ('page_num', 'block_num', 'par_num', 'line_num')),
                      'box': [crop_box[0] + x / 2, crop_box[1] + y / 2,
                              crop_box[0] + (x + w) / 2, crop_box[1] + (y + h) / 2]})
    status = trait_status(image, viewport)
    matches = {}
    area_scale = ((viewport[2] - viewport[0]) / 1920) * ((viewport[3] - viewport[1]) / 1080)
    sy = (viewport[3] - viewport[1]) / 1080
    for target in TARGETS:
        for start in range(len(words)):
            phrase = ''
            for end in range(start, min(start + 4, len(words))):
                phrase += normalized(words[end]['text'])
                if phrase != normalized(target):
                    continue
                group = words[start:end + 1]
                if len({word['line'] for word in group}) != 1:
                    continue
                bounds = [min(w['box'][0] for w in group), min(w['box'][1] for w in group),
                          max(w['box'][2] for w in group), max(w['box'][3] for w in group)]
                y = (bounds[1] + bounds[3]) / 2
                source_y = (y - viewport[1]) / sy
                # A clipped word can be recognized; only tap safely inside the list.
                if not 285 <= source_y <= 825:
                    continue
                gutter = rectangle(viewport, (1140, max(275, source_y - 55),
                                               1240, min(840, source_y + 55)))
                green = green_pixels(image, gutter)
                matches[target] = {'text': ' '.join(w['text'] for w in group),
                                   'confidence': min(w['confidence'] for w in group),
                                   'box': bounds, 'center_y': y, 'green_pixels': green,
                                   'checked': green > max(20, 150 * area_scale)}
                break
            if target in matches:
                break
    result = {**status, 'matches': matches, 'words': words, 'viewport': list(viewport)}
    if evidence_prefix:
        prefix = Path(evidence_prefix)
        prefix.parent.mkdir(parents=True, exist_ok=True)
        crop.save(str(prefix) + '.png')
        Path(str(prefix) + '.tsv').write_text(tsv)
        Path(str(prefix) + '.json').write_text(json.dumps(result, indent=2) + '\n')
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--image', required=True, type=Path)
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    print(json.dumps(analyze_traits(args.image, args.output), indent=2))
