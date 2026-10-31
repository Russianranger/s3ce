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


def analyze_gameplay_overlay(image_path, evidence_prefix=None, viewport=None):
    """Recognize only known onboarding dialogs and the real pause/save menu."""
    image = Image.open(image_path).convert('RGB')
    viewport = viewport or (0, 0, *image.size)
    crop_box = rectangle(viewport, (440, 80, 1475, 940))
    crop = image.crop(crop_box)
    encoded = io.BytesIO()
    crop.save(encoded, format='PNG')
    run = subprocess.run(['tesseract', 'stdin', 'stdout', '--psm', '6', 'tsv'],
                         input=encoded.getvalue(), stdout=subprocess.PIPE,
                         stderr=subprocess.PIPE, timeout=30, check=True)
    tsv = run.stdout.decode(errors='replace')
    words = []
    lines = {}
    for row in csv.DictReader(io.StringIO(tsv), delimiter='\t'):
        if row.get('level') != '5' or not row.get('text', '').strip() or float(row['conf']) < 45:
            continue
        x, y, w, h = (int(row[key]) for key in ('left', 'top', 'width', 'height'))
        word = {'text': row['text'], 'confidence': float(row['conf']),
                'box': [crop_box[0] + x, crop_box[1] + y, crop_box[0] + x + w, crop_box[1] + y + h]}
        words.append(word)
        key = tuple(row[k] for k in ('page_num', 'block_num', 'par_num', 'line_num'))
        lines.setdefault(key, []).append(word)
    text = ' '.join(word['text'] for word in words)
    compact = normalized(text)
    area_scale = ((viewport[2] - viewport[0]) / 1920) * ((viewport[3] - viewport[1]) / 1080)

    def control(box, color):
        box = rectangle(viewport, box)
        region = image.crop(box)
        points = []
        for y in range(region.height):
            for x in range(region.width):
                r, g, b = region.getpixel((x, y))
                matches = ((g > r + 20 and g > b + 20 and g > 90) if color == 'green'
                           else (b > r + 40 and b > g + 30 and g > 100 and b > 180))
                if matches:
                    points.append((x + box[0], y + box[1]))
        if len(points) < 1500 * area_scale:
            return None
        bounds = [min(p[0] for p in points), min(p[1] for p in points),
                  max(p[0] for p in points), max(p[1] for p in points)]
        sx, sy = (viewport[2] - viewport[0]) / 1920, (viewport[3] - viewport[1]) / 1080
        if not (70 * sx <= bounds[2] - bounds[0] <= 220 * sx
                and 70 * sy <= bounds[3] - bounds[1] <= 230 * sy):
            return None
        return {'center': [(bounds[0] + bounds[2]) / 2, (bounds[1] + bounds[3]) / 2],
                'bounds': bounds, 'colored_pixels': len(points)}

    blue_x = control((390, 180, 610, 560), 'blue')
    center = image.crop(rectangle(viewport, (620, 420, 1300, 620)))
    bright = sum(r > 140 and g > 160 and b > 170 for r, g, b in center.getdata()) / (center.width * center.height)
    result = {'kind': 'unknown' if bright > .55 or blue_x else 'none',
              'text': text, 'center_panel_bright_fraction': bright, 'blue_x': blue_x,
              'point': None, 'viewport': list(viewport), 'words': words}
    if 'yourSimhasanewwish'.lower() in compact or 'lockinthiswish' in compact:
        result.update(kind='new-wish', control=control((1020, 600, 1230, 960), 'green'))
    elif ('recipes' in compact and 'purchase' in compact) or 'corsicanbistro' in compact:
        result.update(kind='recipes', control=blue_x)
    elif 'editappearance' in compact or 'whenyoursimisathome' in compact:
        result.update(kind='edit-appearance', control=blue_x)
    elif 'savegameprogress' in compact and 'mainmenu' in compact:
        result.update(kind='save-confirmation', control=control((1020, 600, 1230, 960), 'green'))
    elif 'paused' in compact or ('saveandcontinue' in compact and 'helpabout' in compact):
        for group in lines.values():
            if normalized(' '.join(w['text'] for w in group)) == 'saveandquittomenu':
                result.update(kind='pause-menu', point=[(viewport[0] + viewport[2]) / 2,
                              (min(w['box'][1] for w in group) + max(w['box'][3] for w in group)) / 2])
                break
    if result.get('control'):
        result['point'] = result['control']['center']
    if result['kind'] not in ('none', 'unknown') and result['point'] is None:
        result['kind'] = 'unknown'
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
