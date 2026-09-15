#!/usr/bin/env python3
"""
Setup the 3-mod structure for LibreVCMI:
1. LibreVCMI (librevcmi) - Only our created assets (GamSelBk.png, librevcmi_logo.png)
2. LibreVCMI-Stub (librevcmi-stub) - Remaining extracted assets to be replaced
3. LibreVCMI-BlackStub (librevcmi-blackstub) - Remaining assets as black placeholders with filenames
   - Content/Data/*.png (5315 files)
   - Content/Sprites/*.def (2597 files)
"""

import os
import shutil
import json
import struct
import multiprocessing as mp
from PIL import Image, ImageDraw, ImageFont

USER_MODS = os.path.expanduser("~/.local/share/vcmi/Mods")
REPO_MODS = "/home/fervi/LibreVCMI/Mods"
FONT_PATH = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
FONT_REG_PATH = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"

MOD_LIBRE = os.path.join(USER_MODS, "librevcmi")
MOD_STUB = os.path.join(USER_MODS, "librevcmi-stub")
MOD_BLACK = os.path.join(USER_MODS, "librevcmi-blackstub")

def make_black_stub_worker(args):
    src_path, dst_path, filename = args
    try:
        with Image.open(src_path) as im:
            w, h = im.size
            mode = im.mode
        
        out_mode = "RGBA" if "A" in mode else "RGB"
        bg = (0, 0, 0, 255) if out_mode == "RGBA" else (0, 0, 0)
        img = Image.new(out_mode, (w, h), bg)
        draw = ImageDraw.Draw(img)
        
        border_col = (100, 100, 100, 255) if out_mode == "RGBA" else (100, 100, 100)
        draw.rectangle([0, 0, w - 1, h - 1], outline=border_col)
        
        candidates = [filename, os.path.splitext(filename)[0]]
        chosen_font = None
        chosen_text = None
        chosen_tw, chosen_th = 0, 0
        
        for text in candidates:
            for fsize in range(min(28, max(7, int(h * 0.45))), 5, -1):
                font = ImageFont.truetype(FONT_PATH, fsize)
                bbox = draw.textbbox((0, 0), text, font=font)
                tw = bbox[2] - bbox[0]
                th = bbox[3] - bbox[1]
                if tw <= w - 4 and th <= h - 2:
                    chosen_font = font
                    chosen_text = text
                    chosen_tw, chosen_th = tw, th
                    break
            if chosen_font:
                break
                
        if not chosen_font:
            chosen_font = ImageFont.truetype(FONT_PATH, 6)
            chosen_text = os.path.splitext(filename)[0]
            bbox = draw.textbbox((0, 0), chosen_text, font=font)
            chosen_tw = bbox[2] - bbox[0]
            chosen_th = bbox[3] - bbox[1]
            
        tx = max(1, (w - chosen_tw) // 2)
        ty = max(1, (h - chosen_th) // 2)
        text_col = (255, 255, 255, 255) if out_mode == "RGBA" else (255, 255, 255)
        draw.text((tx, ty), chosen_text, fill=text_col, font=chosen_font)
        
        img.save(dst_path, compress_level=1)
        return True
    except Exception as e:
        print(f"Error processing {filename}: {e}")
        return False

_def_font_cache = {}
def get_def_font(size, bold=True):
    key = (size, bold)
    if key not in _def_font_cache:
        path = FONT_PATH if bold else FONT_REG_PATH
        try:
            _def_font_cache[key] = ImageFont.truetype(path, size)
        except Exception:
            _def_font_cache[key] = ImageFont.load_default()
    return _def_font_cache[key]

def render_def_frame_image(w, h, fw, fh, def_name, entry_name, is_cursor=False):
    img = Image.new('L', (w, h), color=1)
    if w < 4 or h < 4:
        return img.tobytes()

    draw = ImageDraw.Draw(img)
    draw.rectangle([0, 0, w - 1, h - 1], outline=3)

    if is_cursor:
        arrow = [(0, 0), (0, 11), (3, 8), (7, 8)]
        draw.polygon(arrow, fill=2)

    best_lines = []
    clean_entry = entry_name.lower().replace('.pcx', '').replace('.bmp', '')
    if clean_entry.upper() == def_name.upper():
        clean_entry = ""

    if clean_entry and h >= 32 and w >= 45:
        for sz in range(14, 7, -1):
            f1 = get_def_font(sz, bold=True)
            f2 = get_def_font(max(7, sz - 3), bold=False)
            b1 = draw.textbbox((0, 0), def_name, font=f1)
            w1, h1 = b1[2] - b1[0], b1[3] - b1[1]
            b2 = draw.textbbox((0, 0), clean_entry, font=f2)
            w2, h2 = b2[2] - b2[0], b2[3] - b2[1]
            if max(w1, w2) <= w - 6 and (h1 + h2 + 4) <= h - 6:
                best_lines = [(def_name, f1, w1, h1), (clean_entry, f2, w2, h2)]
                break

    if not best_lines:
        for sz in range(16, 6, -1):
            f = get_def_font(sz, bold=True)
            b1 = draw.textbbox((0, 0), def_name, font=f)
            w1, h1 = b1[2] - b1[0], b1[3] - b1[1]
            if w1 <= w - 4 and h1 <= h - 4:
                best_lines = [(def_name, f, w1, h1)]
                break

    if not best_lines:
        for chars in range(len(def_name), 0, -1):
            short = def_name[:chars]
            f = get_def_font(7, bold=False)
            b1 = draw.textbbox((0, 0), short, font=f)
            w1, h1 = b1[2] - b1[0], b1[3] - b1[1]
            if w1 <= w - 2 and h1 <= h - 2:
                best_lines = [(short, f, w1, h1)]
                break

    if best_lines:
        total_h = sum(line[3] for line in best_lines) + (len(best_lines) - 1) * 2
        cur_y = max(1, (h - total_h) // 2)
        for text, f, tw, th in best_lines:
            cur_x = max(2, (w - tw) // 2)
            draw.text((cur_x, cur_y), text, fill=2, font=f)
            cur_y += th + 2

    return img.tobytes()

def make_black_def_worker(args):
    src_path, dst_path, filename = args
    try:
        with open(src_path, 'rb') as f:
            data = f.read()

        if len(data) < 16 + 256 * 3:
            return False

        type_id, width, height, total_blocks = struct.unpack_from('<IIII', data, 0)
        it = 16 + 256 * 3

        is_cursor = (type_id == 0x46)
        def_base_name = os.path.splitext(filename)[0]

        blocks = []
        for b in range(total_blocks):
            if it + 16 > len(data):
                break
            block_id, total_entries = struct.unpack_from('<II', data, it)
            it += 16
            names = []
            for _ in range(total_entries):
                n_raw = data[it:it+13]
                names.append(n_raw)
                it += 13
            offsets = struct.unpack_from(f'<{total_entries}I', data, it)
            it += 4 * total_entries
            
            frames_info = []
            for i in range(total_entries):
                off = offsets[i]
                if off + 32 > len(data):
                    continue
                sz, fmt, fw, fh, w, h, lm, tm = struct.unpack_from('<IIIIIIii', data, off)
                entry_str = names[i].split(b'\x00')[0].decode('latin1', errors='replace')
                frames_info.append({
                    'name_raw': names[i],
                    'name_str': entry_str,
                    'orig_offset': off,
                    'fullWidth': fw,
                    'fullHeight': fh,
                    'width': w,
                    'height': h,
                    'leftMargin': lm,
                    'topMargin': tm,
                })
            blocks.append({
                'block_id': block_id,
                'total_entries': total_entries,
                'frames': frames_info
            })

        pal_bytes = bytearray(256 * 3)
        pal_bytes[0*3 : 0*3+3] = b'\x00\x00\x00' # Colorkey transparent
        pal_bytes[1*3 : 1*3+3] = b'\x05\x05\x05' # Black opaque
        pal_bytes[2*3 : 2*3+3] = b'\xff\xff\xff' # White
        pal_bytes[3*3 : 3*3+3] = b'\x50\x50\x50' # Gray border

        header_size = 16 + 768
        for b in blocks:
            header_size += 16 + b['total_entries'] * 13 + b['total_entries'] * 4

        frame_cache = {}
        current_frame_offset = header_size
        all_frame_data = bytearray()

        for b in blocks:
            block_offsets = []
            for finfo in b['frames']:
                orig_off = finfo['orig_offset']
                if orig_off in frame_cache:
                    block_offsets.append(frame_cache[orig_off])
                    continue

                w = finfo['width']
                h = finfo['height']
                fw = finfo['fullWidth']
                fh = finfo['fullHeight']
                lm = finfo['leftMargin']
                tm = finfo['topMargin']

                if w <= 0 or h <= 0:
                    w, h = 1, 1

                pixels = render_def_frame_image(w, h, fw, fh, def_base_name, finfo['name_str'], is_cursor=is_cursor)
                sprite_def = struct.pack('<IIIIIIii', 32 + len(pixels), 0, fw, fh, w, h, lm, tm)
                frame_bytes = sprite_def + pixels

                new_off = current_frame_offset
                frame_cache[orig_off] = new_off
                block_offsets.append(new_off)

                all_frame_data.extend(frame_bytes)
                current_frame_offset += len(frame_bytes)

            b['new_offsets'] = block_offsets

        out = bytearray()
        out.extend(struct.pack('<IIII', type_id, width, height, len(blocks)))
        out.extend(pal_bytes)

        for b in blocks:
            out.extend(struct.pack('<II8s', b['block_id'], b['total_entries'], b'\x00' * 8))
            for finfo in b['frames']:
                out.extend(finfo['name_raw'])
            for off in b['new_offsets']:
                out.extend(struct.pack('<I', off))

            if len(b['new_offsets']) < b['total_entries']:
                diff = b['total_entries'] - len(b['new_offsets'])
                last_off = b['new_offsets'][-1] if b['new_offsets'] else header_size
                out.extend(struct.pack(f'<{diff}I', *([last_off] * diff)))

        out.extend(all_frame_data)

        with open(dst_path, 'wb') as f:
            f.write(out)

        return True
    except Exception as e:
        print(f"Error processing DEF {filename}: {e}")
        return False

def main():
    print("=== Step 1: Setting up LibreVCMI-Stub ===")
    
    # Save our created assets
    our_assets = ["GamSelBk.png", "librevcmi_logo.png", "DiBoxBck.png"]
    temp_dir = "/home/fervi/.gemini/antigravity-cli/brain/ddb04420-2972-4bba-aec8-689d1a6f1b88/scratch/temp_our_assets"
    os.makedirs(temp_dir, exist_ok=True)
    for asset in our_assets:
        src = os.path.join(MOD_LIBRE, "Content/Data", asset)
        if os.path.exists(src):
            shutil.copy2(src, os.path.join(temp_dir, asset))
    
    stub_data_dir = os.path.join(MOD_STUB, "Content/Data")
    stub_sprites_dir = os.path.join(MOD_STUB, "Content/Sprites")

    # In librevcmi-stub, remove our created assets
    for asset in our_assets:
        p = os.path.join(stub_data_dir, asset)
        if os.path.exists(p):
            os.remove(p)
        
    stub_json = {
        "name": "LibreVCMI-Stub",
        "description": "Original extracted game assets to be replaced by LibreVCMI",
        "version": "0.1.0",
        "author": "LibreVCMI Project",
        "modType": "Graphical"
    }
    with open(os.path.join(MOD_STUB, "mod.json"), "w") as f:
        json.dump(stub_json, f, indent=4)
    print("LibreVCMI-Stub configured.")

    print("\n=== Step 2: Creating clean LibreVCMI with ONLY our assets ===")
    os.makedirs(os.path.join(MOD_LIBRE, "Content/Data"), exist_ok=True)
    for asset in our_assets:
        src = os.path.join(temp_dir, asset)
        if os.path.exists(src):
            shutil.copy2(src, os.path.join(MOD_LIBRE, "Content/Data", asset))
    
    libre_json = {
        "name": "LibreVCMI",
        "description": "LibreVCMI - Open-source assets made for VCMI",
        "version": "0.1.0",
        "author": "LibreVCMI Project",
        "contact": "https://github.com/fervi",
        "modType": "Graphical"
    }
    with open(os.path.join(MOD_LIBRE, "mod.json"), "w") as f:
        json.dump(libre_json, f, indent=4)
    print("LibreVCMI configured with only our created graphics.")

    print("\n=== Step 3: Generating LibreVCMI-BlackStub ===")
    black_data_dir = os.path.join(MOD_BLACK, "Content/Data")
    black_sprites_dir = os.path.join(MOD_BLACK, "Content/Sprites")
    os.makedirs(black_data_dir, exist_ok=True)
    os.makedirs(black_sprites_dir, exist_ok=True)
    
    black_json = {
        "name": "LibreVCMI-BlackStub",
        "description": "Black placeholder graphics with filenames for asset development in LibreVCMI",
        "version": "0.1.0",
        "author": "LibreVCMI Project",
        "modType": "Graphical"
    }
    with open(os.path.join(MOD_BLACK, "mod.json"), "w") as f:
        json.dump(black_json, f, indent=4)

    # 3a. Generate black Data/*.png
    data_files = os.listdir(stub_data_dir)
    png_tasks = []
    for f in data_files:
        src = os.path.join(stub_data_dir, f)
        dst = os.path.join(black_data_dir, f)
        if f.lower().endswith(".png"):
            png_tasks.append((src, dst, f))
        else:
            if not os.path.exists(dst):
                os.symlink(os.path.relpath(src, black_data_dir), dst)
            
    print(f"Generating {len(png_tasks)} black stub images in Data/ using {mp.cpu_count()} CPU cores...")
    with mp.Pool() as pool:
        results = pool.map(make_black_stub_worker, png_tasks)
    print(f"Generated {sum(results)} / {len(png_tasks)} black stub Data images.")

    # 3b. Generate black Sprites/*.def
    def_files = [f for f in os.listdir(stub_sprites_dir) if f.lower().endswith('.def')]
    def_tasks = [(os.path.join(stub_sprites_dir, f), os.path.join(black_sprites_dir, f), f) for f in def_files]
    print(f"Generating {len(def_tasks)} black stub animations in Sprites/ using {mp.cpu_count()} CPU cores...")
    with mp.Pool() as pool:
        def_results = pool.map(make_black_def_worker, def_tasks)
    print(f"Generated {sum(def_results)} / {len(def_tasks)} black stub DEF animations.")

    # 3c. Generate silent Sounds/*.wav
    black_sounds_dir = os.path.join(MOD_BLACK, "Content/Sounds")
    stub_sounds_dir = os.path.join(MOD_STUB, "Content/Sounds")
    if os.path.islink(black_sounds_dir):
        os.remove(black_sounds_dir)
    os.makedirs(black_sounds_dir, exist_ok=True)
    master_wav = "/tmp/silent_master.wav"
    import wave
    with wave.open(master_wav, 'wb') as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(22050)
        w.writeframes(b'\x00\x00' * 1102)
    with open(master_wav, 'rb') as f:
        wav_bytes = f.read()
    sound_files = [f for f in os.listdir(stub_sounds_dir) if f.lower().endswith('.wav')]
    print(f"Writing {len(sound_files)} silent WAV sound files...")
    for sf in sound_files:
        with open(os.path.join(black_sounds_dir, sf), 'wb') as out_f:
            out_f.write(wav_bytes)

    # 3d. Generate silent Music/*.mp3
    black_music_dir = os.path.join(MOD_BLACK, "Content/Music")
    stub_music_dir = os.path.join(MOD_STUB, "Content/Music")
    if os.path.islink(black_music_dir):
        os.remove(black_music_dir)
    os.makedirs(black_music_dir, exist_ok=True)
    master_mp3 = "/tmp/silent_master.mp3"
    import subprocess
    subprocess.run([
        "ffmpeg", "-f", "lavfi", "-i", "anullsrc=r=44100:cl=stereo",
        "-t", "1", "-q:a", "9", "-acodec", "libmp3lame", master_mp3, "-y"
    ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
    with open(master_mp3, 'rb') as f:
        mp3_bytes = f.read()
    music_files = [f for f in os.listdir(stub_music_dir) if f.lower().endswith('.mp3')]
    print(f"Writing {len(music_files)} silent MP3 music tracks...")
    for mf in music_files:
        with open(os.path.join(black_music_dir, mf), 'wb') as out_f:
            out_f.write(mp3_bytes)

    # 3e. Generate 1-frame placeholder Video/*.smk and *.bik
    black_video_dir = os.path.join(MOD_BLACK, "Content/Video")
    stub_video_dir = os.path.join(MOD_STUB, "Content/Video")
    if os.path.islink(black_video_dir):
        os.remove(black_video_dir)
    os.makedirs(black_video_dir, exist_ok=True)
    video_files = [f for f in os.listdir(stub_video_dir) if f.lower().endswith(('.smk', '.bik'))]
    print(f"Generating {len(video_files)} 1-frame placeholder videos...")
    def _video_job(vf):
        dst = os.path.join(black_video_dir, vf)
        esc = vf.replace("\\", "\\\\").replace(":", "\\:").replace("'", "\\'")
        subprocess.run([
            "ffmpeg",
            "-f", "lavfi", "-i", "color=c=black:s=640x480:r=1:d=1",
            "-f", "lavfi", "-i", "anullsrc=r=44100:cl=stereo:d=1",
            "-vf", f"drawtext=text='{esc}':fontcolor=white:fontsize=28:x=(w-text_w)/2:y=(h-text_h)/2",
            "-c:v", "vp8", "-c:a", "libvorbis", "-f", "webm", dst, "-y"
        ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    with mp.Pool(mp.cpu_count()) as pool:
        pool.map(_video_job, video_files)


    print("\n=== Step 4: Updating repository symlinks ===")
    for mod_name, mod_path in [
        ("librevcmi", MOD_LIBRE),
        ("librevcmi-stub", MOD_STUB),
        ("librevcmi-blackstub", MOD_BLACK)
    ]:
        link_path = os.path.join(REPO_MODS, mod_name)
        if os.path.islink(link_path) or os.path.exists(link_path):
            os.remove(link_path)
        os.symlink(mod_path, link_path)
        print(f"Created link {link_path} -> {mod_path}")

    print("\n=== Done! Summary of mods: ===")
    for m in [MOD_LIBRE, MOD_STUB, MOD_BLACK]:
        name = os.path.basename(m)
        num_files = sum(len(files) for _, _, files in os.walk(m))
        print(f"- {name}: {num_files} files")

if __name__ == "__main__":
    main()
